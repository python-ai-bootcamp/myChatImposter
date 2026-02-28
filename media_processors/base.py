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
        file_path = os.path.join("media_store", "pending_media", job.guid)
        try:
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

            if result.failed_reason:
                await self._move_to_failed(job, result, db)
            else:
                persisted = await self._persist_result_first(job, result, db)
                if not persisted:
                    return

            bot_queues = get_bot_queues(job.bot_id)
            if bot_queues:
                delivered = await bot_queues.update_message_by_media_id(job.correspondent_id, job.guid, result.content)
                if delivered and result.failed_reason:
                    await db["media_processing_jobs_failed"].update_many(
                        {
                            "bot_id": job.bot_id,
                            "correspondent_id": job.correspondent_id,
                            "guid": job.guid,
                            "pending_user_delivery": True,
                        },
                        {"$set": {"pending_user_delivery": False}},
                    )
                if delivered and not result.failed_reason:
                    await self._remove_job(job, db)
                if not delivered and not result.failed_reason:
                    logging.warning(
                        f"MEDIA PROCESSOR: Placeholder not found for GUID {job.guid} while bot is active; removing completed job as unrecoverable."
                    )
                    await self._remove_job(job, db)
        except Exception as e:
            logging.exception("MEDIA PROCESSOR: unhandled exception")
            await self._handle_unhandled_exception(job, db, str(e))
        finally:
            self._delete_media_file(file_path)

    @abstractmethod
    async def process_media(self, file_path: str, mime_type: str, caption: str, media_metadata: Dict[str, Any]) -> ProcessingResult:
        ...

    async def _persist_result_first(self, job: MediaProcessingJob, result: ProcessingResult, db) -> bool:
        update = {"$set": {"status": "completed", "result": result.content}}
        active_result = await db["media_processing_jobs"].update_one({"_id": job.job_id}, update)
        if active_result.modified_count > 0:
            return True
        holding_result = await db["media_processing_jobs_holding"].update_one({"_id": job.job_id}, update)
        if holding_result.modified_count > 0:
            return True
        logging.warning(f"MEDIA PROCESSOR: Job record missing for GUID {job.guid}. Task result abandoned.")
        return False

    async def _move_to_failed(self, job: MediaProcessingJob, result: ProcessingResult, db):
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
            "pending_user_delivery": True,
        }
        await db["media_processing_jobs_failed"].insert_one(doc)
        await self._remove_job(job, db)

    async def _remove_job(self, job: MediaProcessingJob, db):
        await db["media_processing_jobs"].delete_one({"_id": job.job_id})
        await db["media_processing_jobs_holding"].delete_one({"_id": job.job_id})

    async def _handle_unhandled_exception(self, job: MediaProcessingJob, db, error: str):
        result = ProcessingResult(content="[Media processing failed]", failed_reason=error)
        await self._move_to_failed(job, result, db)

    def _delete_media_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
