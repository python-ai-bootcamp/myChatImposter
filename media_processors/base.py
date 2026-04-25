import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Any, Callable, List, Optional

from infrastructure.models import MediaProcessingJob, ProcessingResult
from infrastructure.db_schema import (
    COLLECTION_MEDIA_PROCESSING_JOBS,
    COLLECTION_MEDIA_PROCESSING_JOBS_HOLDING,
    COLLECTION_MEDIA_PROCESSING_JOBS_FAILED,
)
from media_processors.media_file_utils import resolve_media_path, delete_media_file


def format_processing_result(
    content: str,
    caption: str,
    mime_type: str,
    original_filename: Optional[str] = None,
    unprocessable_media: bool = False,
    display_media_type: Optional[str] = None,
) -> ProcessingResult:
    """Pure, module-level formatting function for ALL media processing outcomes.
    
    This is the SINGLE SOURCE OF TRUTH for output formatting. ALL processors
    (stub, error, vision, transcription) must route their output through this
    function. Direct bracket wrapping or caption handling in processors is
    prohibited.
    
    Contract:
    - If unprocessable_media is False, a prefix "{MediaType} Transcription: " is
      prepended to content. MediaType is derived from display_media_type if
      provided, otherwise from the major type of mime_type (e.g. "Audio", "Image").
    - content is always wrapped in square brackets: [content]
    - caption is always appended on the next line after brackets (even if empty)
    - original_filename, when present, is prepended before content as: file: <name>
    - unprocessable_media flag is forwarded to the ProcessingResult
    
    Args:
        content: The raw processing output text.
        caption: The original message caption (may be empty string).
        mime_type: The MIME type of the processed media (e.g. "audio/ogg").
        original_filename: The original filename of the media being processed.
        unprocessable_media: Whether the media was flagged/failed moderation.
        display_media_type: Optional override for the media type label in the prefix.
    
    Returns:
        ProcessingResult with formatted content string and flags set.
    """
    # Prefix injection: only for successful (processable) outcomes
    if not unprocessable_media:
        if display_media_type:
            media_label = display_media_type
        else:
            media_label = mime_type.split("/")[0].capitalize()
        content = f"{media_label} Transcription: {content}"
    
    parts = []
    if original_filename:
        parts.append(f"file: {original_filename}")
    parts.append(content)
    inner = "\n".join(parts)
    
    # Always bracket-wrap, always append caption on next line
    formatted = f"[{inner}]\n{caption}"
    
    return ProcessingResult(
        content=formatted,
        unprocessable_media=unprocessable_media,
    )


class BaseMediaProcessor(ABC):
    def __init__(self, handled_mime_types: List[str], processing_timeout: float = 60.0):
        self.handled_mime_types = handled_mime_types
        self.processing_timeout = processing_timeout

    async def process_job(self, job: MediaProcessingJob, get_bot_queues: Callable[[str], Any], db):
        """Full shared lifecycle — called by the worker pool for each job.
        
        6-step centralized lifecycle:
        1. Process: call process_media() with timeout guard
        2. Format: call format_processing_result() — single source of truth for output
        3. Persist: durable state anchor (status=completed with formatted result)
        4. Archive failed: copy to _failed collection for operator inspection
        5. Deliver: best-effort direct delivery if bot is active
        6. Cleanup: always remove the media file from staging
        """
        file_path = resolve_media_path(job.guid)
        try:
            # 1. PROCESS (with timeout guard)
            try:
                result = await asyncio.wait_for(
                    self.process_media(file_path, job.mime_type, job.bot_id),
                    timeout=self.processing_timeout,
                )
            except asyncio.TimeoutError:
                result = ProcessingResult(
                    content="Processing timed out",
                    failed_reason=f"TIMEOUT: processing exceeded {self.processing_timeout}s",
                    unprocessable_media=True,
                )

            # 2. FORMAT (centralized — single source of truth)
            formatted = format_processing_result(
                content=result.content,
                caption=job.placeholder_message.content,
                mime_type=job.mime_type,
                original_filename=job.original_filename,
                unprocessable_media=result.unprocessable_media,
                display_media_type=result.display_media_type,
            )
            # Preserve failed_reason from the raw result
            if result.failed_reason:
                formatted.failed_reason = result.failed_reason

            # 3. PERSIST (persistence-first — applies to ALL outcomes)
            persisted = await self._persist_result_first(job, formatted, db)
            if not persisted:
                return  # Job was already swept by cleanup — no further action

            # 4. ARCHIVE TO FAILED (operator inspection only)
            if formatted.failed_reason:
                await self._archive_to_failed(job, formatted, db)

            # 5. BEST-EFFORT DIRECT DELIVERY (bot is active)
            bot_queues = get_bot_queues(job.bot_id)
            if bot_queues:
                delivered = await bot_queues.update_message_by_media_id(
                    job.correspondent_id, job.guid, formatted.content
                )
                if delivered:
                    await self._remove_job(job, db)
                else:
                    logging.warning(
                        f"MEDIA PROCESSOR: Placeholder not found for GUID {job.guid} while bot is active; "
                        "removing job as unrecoverable."
                    )
                    await self._remove_job(job, db)

            # If bot is NOT active: job stays in _holding as status=completed.
            # When the bot reconnects, the reaping path will find it, inject the placeholder,
            # deliver, and delete it.

        except Exception as e:
            logging.exception("MEDIA PROCESSOR: unhandled exception")
            await self._handle_unhandled_exception(job, db, str(e), get_bot_queues)
        finally:
            # 6. GUARANTEE: media file is always removed from staging
            delete_media_file(job.guid)

    @abstractmethod
    async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:
        """Subclass implements ONLY this: actual AI/conversion logic.
        
        Returns raw content — formatting/bracket-wrapping is handled by process_job().
        The caption parameter has been removed; processors must NOT handle captions.
        """
        ...

    # --- Inherited Concrete Methods ---

    async def _persist_result_first(self, job: MediaProcessingJob, result: ProcessingResult, db) -> bool:
        """Durable state anchor: updates status to completed in active/holding collections.
        Works identically for success and failure outcomes."""
        update = {"$set": {"status": "completed", "result": result.content}}
        active_result = await db[COLLECTION_MEDIA_PROCESSING_JOBS].update_one({"_id": job.job_id}, update)
        if active_result.modified_count > 0:
            return True
        holding_result = await db[COLLECTION_MEDIA_PROCESSING_JOBS_HOLDING].update_one({"_id": job.job_id}, update)
        if holding_result.modified_count > 0:
            return True
        logging.warning(f"MEDIA PROCESSOR: Job record missing for GUID {job.guid}. Task result abandoned.")
        return False

    async def _archive_to_failed(self, job: MediaProcessingJob, result: ProcessingResult, db):
        """Archives a copy of the job to _failed for operator inspection ONLY.
        This is purely additive — the _failed collection is never used for delivery or recovery."""
        doc = {
            "bot_id": job.bot_id,
            "correspondent_id": job.correspondent_id,
            "placeholder_message": asdict(job.placeholder_message),
            "guid": job.guid,
            "mime_type": job.mime_type,
            "status": "failed",
            "result": result.content,
            "error": result.failed_reason,
            "quota_exceeded": job.quota_exceeded,
            "created_at": getattr(job, "created_at", None),
        }
        await db[COLLECTION_MEDIA_PROCESSING_JOBS_FAILED].insert_one(doc)

    async def _remove_job(self, job: MediaProcessingJob, db):
        """Clears the job from active and holding collections after delivery."""
        await db[COLLECTION_MEDIA_PROCESSING_JOBS].delete_one({"_id": job.job_id})
        await db[COLLECTION_MEDIA_PROCESSING_JOBS_HOLDING].delete_one({"_id": job.job_id})

    async def _handle_unhandled_exception(self, job: MediaProcessingJob, db, error: str, get_bot_queues=None):
        """Safety net: persists an error result, archives to _failed, and attempts best-effort
        delivery to the active bot queue so the placeholder is resolved promptly."""
        raw = ProcessingResult(content="Media processing failed", failed_reason=error, unprocessable_media=True)
        formatted = format_processing_result(
            content=raw.content,
            caption=job.placeholder_message.content,
            mime_type=job.mime_type,
            original_filename=job.original_filename,
            unprocessable_media=True,
        )
        formatted.failed_reason = raw.failed_reason
        
        persisted = await self._persist_result_first(job, formatted, db)
        if persisted:
            await self._archive_to_failed(job, formatted, db)
        # Best-effort delivery
        if get_bot_queues:
            try:
                bot_queues = get_bot_queues(job.bot_id)
                if bot_queues:
                    delivered = await bot_queues.update_message_by_media_id(
                        job.correspondent_id, job.guid, formatted.content
                    )
                    if delivered:
                        await self._remove_job(job, db)
            except Exception:
                logging.exception("MEDIA PROCESSOR: failed to deliver unhandled-exception error to queue")
