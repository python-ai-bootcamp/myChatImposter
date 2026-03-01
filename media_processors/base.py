import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Any, Callable, Dict, List

from infrastructure.models import MediaProcessingJob, ProcessingResult


class BaseMediaProcessor(ABC):
    def __init__(self, handled_mime_types: List[str], processing_timeout: float = 60.0):
        self.handled_mime_types = handled_mime_types
        self.processing_timeout = processing_timeout

    async def process_job(self, job: MediaProcessingJob, get_bot_queues: Callable[[str], Any], db):
        """Full shared lifecycle — called by the worker pool for each job."""
        file_path = os.path.join("media_store", "pending_media", job.guid)
        try:
            # 1. ACTUAL CONVERSION (Externally Guarded by Centralized Timeout)
            try:
                result = await asyncio.wait_for(
                    self.process_media(file_path, job.mime_type, job.placeholder_message.content, job.media_metadata),
                    timeout=self.processing_timeout,
                )
            except asyncio.TimeoutError:
                result = ProcessingResult(
                    content="[Processing timed out]",
                    failed_reason=f"TIMEOUT: processing exceeded {self.processing_timeout}s",
                )

            # 2. PERSISTENCE (Persistence-First — applies to ALL outcomes, success or failure)
            # On success: result goes to _jobs or _holding as status=completed for delivery/reaping.
            # On failure: same — error text is the result, stays in _holding for reaping on reconnect.
            persisted = await self._persist_result_first(job, result, db)
            if not persisted:
                return  # Job was already swept by cleanup — no further action

            # 3. ARCHIVE TO FAILED (operator inspection only — does not affect delivery flow)
            # A copy is inserted into _failed so operators can investigate. It is never read back
            # by any recovery mechanism — delivery is handled exclusively via the _holding reaping path.
            if result.failed_reason:
                await self._archive_to_failed(job, result, db)

            # 4. BEST-EFFORT DIRECT DELIVERY (bot is active)
            bot_queues = get_bot_queues(job.bot_id)
            if bot_queues:
                delivered = await bot_queues.update_message_by_media_id(
                    job.correspondent_id, job.guid, result.content
                )
                if delivered:
                    # Delivered — remove the job from active/holding (mission complete)
                    await self._remove_job(job, db)
                else:
                    # Placeholder not found in the queue (queue was reset) — unrecoverable without a placeholder
                    logging.warning(
                        f"MEDIA PROCESSOR: Placeholder not found for GUID {job.guid} while bot is active; "
                        "removing job as unrecoverable."
                    )
                    await self._remove_job(job, db)

            # If bot is NOT active: job stays in _holding as status=completed.
            # When the bot eventually reconnects, the normal reaping path (on_bot_connected →
            # _reap_completed_jobs_atomically) will find it, inject the placeholder, deliver, and delete it.

        except Exception as e:
            logging.exception("MEDIA PROCESSOR: unhandled exception")
            await self._handle_unhandled_exception(job, db, str(e))
        finally:
            # GUARANTEE: The media file is always removed from the shared terrain
            self._delete_media_file(file_path)

    @abstractmethod
    async def process_media(self, file_path: str, mime_type: str, caption: str, media_metadata: Dict[str, Any]) -> ProcessingResult:
        """Subclass implements ONLY this: actual AI/conversion logic."""
        ...

    # --- Inherited Concrete Methods ---

    async def _persist_result_first(self, job: MediaProcessingJob, result: ProcessingResult, db) -> bool:
        """Durable state anchor: updates status to completed in active/holding collections.
        Works identically for success and failure outcomes."""
        update = {"$set": {"status": "completed", "result": result.content}}
        active_result = await db["media_processing_jobs"].update_one({"_id": job.job_id}, update)
        if active_result.modified_count > 0:
            return True
        holding_result = await db["media_processing_jobs_holding"].update_one({"_id": job.job_id}, update)
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
            "media_metadata": job.media_metadata,
            "created_at": getattr(job, "created_at", None),
        }
        await db["media_processing_jobs_failed"].insert_one(doc)

    async def _remove_job(self, job: MediaProcessingJob, db):
        """Clears the job from active and holding collections after delivery."""
        await db["media_processing_jobs"].delete_one({"_id": job.job_id})
        await db["media_processing_jobs_holding"].delete_one({"_id": job.job_id})

    async def _handle_unhandled_exception(self, job: MediaProcessingJob, db, error: str):
        """Safety net: persists an error result and archives to _failed for operator investigation."""
        result = ProcessingResult(content="[Media processing failed]", failed_reason=error)
        persisted = await self._persist_result_first(job, result, db)
        if persisted:
            await self._archive_to_failed(job, result, db)

    def _delete_media_file(self, file_path: str):
        """Guaranteed cleanup of the shared media staging volume."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
