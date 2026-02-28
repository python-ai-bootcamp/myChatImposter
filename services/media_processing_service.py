import asyncio
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional

from pymongo import ReturnDocument

from infrastructure.models import MediaProcessingJob
from media_processors.factory import get_processor_class
from queue_manager import Group, Message, Sender


DEFAULT_POOL_DEFINITIONS = [
    {"mimeTypes": ["audio/ogg", "audio/mpeg"], "processorClass": "AudioTranscriptionProcessor", "concurrentProcessingPoolSize": 2, "processingTimeoutSeconds": 300},
    {"mimeTypes": ["video/mp4", "video/webm"], "processorClass": "VideoDescriptionProcessor", "concurrentProcessingPoolSize": 1, "processingTimeoutSeconds": 600},
    {"mimeTypes": ["image/jpeg", "image/png", "image/webp"], "processorClass": "ImageVisionProcessor", "concurrentProcessingPoolSize": 3, "processingTimeoutSeconds": 120},
    {"mimeTypes": ["application/pdf", "text/plain"], "processorClass": "DocumentProcessor", "concurrentProcessingPoolSize": 2, "processingTimeoutSeconds": 120},
    {"mimeTypes": ["media_corrupt_image", "media_corrupt_audio", "media_corrupt_video", "media_corrupt_document", "media_corrupt_sticker"], "processorClass": "CorruptMediaProcessor", "concurrentProcessingPoolSize": 1, "processingTimeoutSeconds": 10},
    {"mimeTypes": [], "processorClass": "UnsupportedMediaProcessor", "concurrentProcessingPoolSize": 1, "processingTimeoutSeconds": 10},
]


class MediaProcessingService:
    def __init__(
        self,
        db,
        get_bot_queues: Callable[[str], Any],
        get_active_bot_ids: Callable[[], List[str]],
    ):
        self.db = db
        self.get_bot_queues = get_bot_queues
        self.get_active_bot_ids = get_active_bot_ids
        self.active_collection = db["media_processing_jobs"]
        self.holding_collection = db["media_processing_jobs_holding"]
        self.failed_collection = db["media_processing_jobs_failed"]
        self.running = False
        self.worker_tasks: List[asyncio.Task] = []
        self.cleanup_task: Optional[asyncio.Task] = None
        self.pool_definitions = []

    async def initialize(self):
        await self._ensure_configuration_templates()
        await self._global_startup_recovery()
        await self._load_pool_definitions()

    async def start(self):
        if self.running:
            return
        await self.initialize()
        self.running = True
        for pool_definition in self.pool_definitions:
            for worker_index in range(pool_definition["concurrentProcessingPoolSize"]):
                worker_id = f"{pool_definition['processorClass']}-{worker_index}"
                task = asyncio.create_task(self._worker_loop(worker_id, pool_definition))
                self.worker_tasks.append(task)
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logging.info("MEDIA SERVICE: started.")

    async def stop(self):
        self.running = False
        for task in self.worker_tasks:
            task.cancel()
        for task in self.worker_tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.worker_tasks.clear()
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
        logging.info("MEDIA SERVICE: stopped.")

    async def on_bot_connected(self, bot_id: str):
        bot_queues = self.get_bot_queues(bot_id)
        if not bot_queues:
            return
        await self._reap_completed_jobs_atomically(bot_id, bot_queues)
        await self._promote_incomplete_jobs_atomically(bot_id, bot_queues)
        await self._reap_failed_notifications(bot_id, bot_queues)

    async def on_bot_disconnected(self, bot_id: str):
        docs = []
        async for doc in self.active_collection.find({"bot_id": bot_id}):
            docs.append(doc)
        if docs:
            await self.holding_collection.insert_many(docs)
            await self.active_collection.delete_many({"bot_id": bot_id})

    async def _load_pool_definitions(self):
        config_doc = await self.db["bot_configurations"].find_one({"_id": "_mediaProcessorDefinitions"})
        definitions = config_doc.get("definitions") if config_doc else None
        if not definitions:
            definitions = DEFAULT_POOL_DEFINITIONS
        catch_all_count = sum(1 for definition in definitions if not definition.get("mimeTypes"))
        if catch_all_count != 1:
            logging.warning(
                "MEDIA SERVICE: invalid processor definitions (expected exactly one catch-all). Falling back to defaults."
            )
            definitions = DEFAULT_POOL_DEFINITIONS
        self.pool_definitions = definitions

    async def _ensure_configuration_templates(self):
        # Keep existing documents untouched; create only if missing.
        bot_cfg_doc = await self.db["bot_configurations"].find_one({"_id": "_mediaProcessorDefinitions"})
        if bot_cfg_doc is None:
            try:
                await self.db["bot_configurations"].insert_one(
                    {
                        "_id": "_mediaProcessorDefinitions",
                        "definitions": DEFAULT_POOL_DEFINITIONS,
                        "created_at": int(time.time() * 1000),
                    }
                )
            except Exception:
                logging.exception("MEDIA SERVICE: failed creating _mediaProcessorDefinitions template")

        global_cfg_doc = await self.db["configurations"].find_one({"_id": "_multimedia_message_support"})
        if global_cfg_doc is None:
            try:
                await self.db["configurations"].insert_one(
                    {
                        "_id": "_multimedia_message_support",
                        "media_storage_quota_gb_default": 25,
                        "processor_definitions_ref": "_mediaProcessorDefinitions",
                        "created_at": int(time.time() * 1000),
                    }
                )
            except Exception:
                logging.exception("MEDIA SERVICE: failed creating _multimedia_message_support template")

    async def _global_startup_recovery(self):
        docs = []
        async for doc in self.active_collection.find({}):
            docs.append(doc)
        if docs:
            await self.holding_collection.insert_many(docs)
            await self.active_collection.delete_many({})
        await self.holding_collection.update_many({"status": "processing"}, {"$set": {"status": "pending"}})

    async def _worker_loop(self, worker_id: str, pool_definition: Dict[str, Any]):
        processor_class = get_processor_class(pool_definition["processorClass"])
        processor = processor_class(pool_definition["mimeTypes"], pool_definition.get("processingTimeoutSeconds", 60))
        last_bot_id = None

        while self.running:
            try:
                job_doc = await self._claim_job(worker_id, pool_definition["mimeTypes"], last_bot_id)
                pending_query = {"status": "pending"}
                if pool_definition["mimeTypes"]:
                    pending_query["mime_type"] = {"$in": pool_definition["mimeTypes"]}
                depth = await self.active_collection.count_documents(pending_query)
                logging.info(
                    f"MEDIA SERVICE: pool={pool_definition['processorClass']} pending_depth={depth}"
                )
                if not job_doc:
                    await asyncio.sleep(0.5)
                    continue
                last_bot_id = job_doc.get("bot_id")
                job = self._doc_to_job(job_doc)
                await processor.process_job(job, self.get_bot_queues, self.db)
            except asyncio.CancelledError:
                break
            except Exception:
                logging.exception("MEDIA SERVICE: worker loop failure")
                await asyncio.sleep(1)

    async def _claim_job(self, worker_id: str, mime_types: List[str], last_bot_id: Optional[str]):
        base_query = {"status": "pending"}
        if mime_types:
            base_query["mime_type"] = {"$in": mime_types}

        fairness_query = dict(base_query)
        if last_bot_id:
            fairness_query["bot_id"] = {"$ne": last_bot_id}
        update = {"$set": {"status": "processing", "worker_id": worker_id}}

        doc = await self.active_collection.find_one_and_update(
            fairness_query,
            update,
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if doc:
            return doc

        return await self.active_collection.find_one_and_update(
            base_query,
            update,
            sort=[("created_at", 1)],
            return_document=ReturnDocument.AFTER,
        )

    def _doc_to_job(self, doc: Dict[str, Any]) -> MediaProcessingJob:
        placeholder_doc = doc.get("placeholder_message", {})
        sender_doc = placeholder_doc.get("sender", {})
        group_doc = placeholder_doc.get("group")
        sender = Sender(
            identifier=sender_doc.get("identifier", "unknown"),
            display_name=sender_doc.get("display_name", "unknown"),
            alternate_identifiers=sender_doc.get("alternate_identifiers", []),
        )
        group = None
        if group_doc:
            group = Group(
                identifier=group_doc["identifier"],
                display_name=group_doc["display_name"],
                alternate_identifiers=group_doc.get("alternate_identifiers", []),
            )
        placeholder = Message(
            id=placeholder_doc.get("id", 0),
            content=placeholder_doc.get("content", ""),
            sender=sender,
            source=placeholder_doc.get("source", "user"),
            accepted_time=placeholder_doc.get("accepted_time", int(time.time() * 1000)),
            message_size=placeholder_doc.get("message_size", 0),
            originating_time=placeholder_doc.get("originating_time"),
            group=group,
            provider_message_id=placeholder_doc.get("provider_message_id"),
            media_processing_id=placeholder_doc.get("media_processing_id"),
        )
        return MediaProcessingJob(
            job_id=doc["_id"],
            bot_id=doc["bot_id"],
            correspondent_id=doc["correspondent_id"],
            placeholder_message=placeholder,
            guid=doc["guid"],
            mime_type=doc["mime_type"],
            status=doc["status"],
            original_filename=doc.get("original_filename"),
            media_metadata=doc.get("media_metadata", {}),
            result=doc.get("result"),
            error=doc.get("error"),
        )

    async def _reap_completed_jobs_atomically(self, bot_id: str, bot_queues):
        while True:
            doc = await self.holding_collection.find_one_and_delete(
                {
                    "bot_id": bot_id,
                    "status": "completed",
                    "result": {"$exists": True},
                },
                sort=[("created_at", 1)],
            )
            if not doc:
                break
            job = self._doc_to_job(doc)
            updated = await bot_queues.update_message_by_media_id(job.correspondent_id, job.guid, doc["result"])
            if not updated:
                await bot_queues.inject_placeholder(job.correspondent_id, job.placeholder_message)
                await bot_queues.update_message_by_media_id(job.correspondent_id, job.guid, doc["result"])

    async def _promote_incomplete_jobs_atomically(self, bot_id: str, bot_queues):
        while True:
            doc = await self.holding_collection.find_one_and_delete(
                {
                    "bot_id": bot_id,
                    "$or": [
                        {"status": {"$in": ["pending", "processing"]}},
                        {"status": "completed", "result": {"$exists": False}},
                    ],
                },
                sort=[("created_at", 1)],
            )
            if not doc:
                break
            job = self._doc_to_job(doc)
            has_placeholder = await bot_queues.has_media_processing_id(job.correspondent_id, job.guid)
            if not has_placeholder:
                await bot_queues.inject_placeholder(job.correspondent_id, job.placeholder_message)
            promoted = dict(doc)
            promoted.pop("_id", None)
            promoted["status"] = "pending"
            await self.active_collection.insert_one(promoted)

    async def _reap_failed_notifications(self, bot_id: str, bot_queues):
        while True:
            doc = await self.failed_collection.find_one_and_update(
                {
                    "bot_id": bot_id,
                    "pending_user_delivery": True,
                    "result": {"$exists": True},
                },
                {"$set": {"pending_user_delivery": False}},
                sort=[("created_at", 1)],
                return_document=ReturnDocument.AFTER,
            )
            if not doc:
                break
            job = self._doc_to_job(doc)
            updated = await bot_queues.update_message_by_media_id(job.correspondent_id, job.guid, doc["result"])
            if not updated:
                await bot_queues.inject_placeholder(job.correspondent_id, job.placeholder_message)
                await bot_queues.update_message_by_media_id(job.correspondent_id, job.guid, doc["result"])

    async def _cleanup_loop(self):
        while self.running:
            try:
                await self.run_janitorial_cleanup()
            except asyncio.CancelledError:
                break
            except Exception:
                logging.exception("MEDIA SERVICE: janitorial cleanup failed")
            await asyncio.sleep(3600)

    async def run_janitorial_cleanup(self):
        cutoff_ms = int(time.time() * 1000) - (3 * 60 * 60 * 1000)
        await self._cleanup_stale_in_memory_placeholders(cutoff_ms)
        await self._cleanup_stale_db_jobs(cutoff_ms)
        await self._cleanup_orphan_files()

    async def _cleanup_stale_in_memory_placeholders(self, cutoff_ms: int):
        for bot_id in self.get_active_bot_ids():
            bot_queues = self.get_bot_queues(bot_id)
            if not bot_queues:
                continue
            for queue in bot_queues.get_all_queues():
                for message in queue.get_messages():
                    if not message.media_processing_id:
                        continue
                    if message.accepted_time > cutoff_ms:
                        continue
                    await bot_queues.update_message_by_media_id(
                        queue.correspondent_id,
                        message.media_processing_id,
                        "[Media processing failed: stale placeholder cleanup]",
                    )
                    await self._move_matching_jobs_to_failed(bot_id, message.media_processing_id, "stale placeholder cleanup")

    async def _cleanup_stale_db_jobs(self, cutoff_ms: int):
        for collection_name in ["media_processing_jobs", "media_processing_jobs_holding"]:
            cursor = self.db[collection_name].find({"created_at": {"$lt": cutoff_ms}})
            async for doc in cursor:
                await self._archive_failed_doc(doc, "stale db job cleanup")
                await self.db[collection_name].delete_one({"_id": doc["_id"]})
                self._delete_media_file(doc.get("guid"))

    async def _cleanup_orphan_files(self):
        media_dir = os.path.join("media_store", "pending_media")
        if not os.path.isdir(media_dir):
            return
        known_guids = set()
        async for doc in self.active_collection.find({}, {"guid": 1}):
            known_guids.add(doc["guid"])
        async for doc in self.holding_collection.find({}, {"guid": 1}):
            known_guids.add(doc["guid"])

        now = time.time()
        for file_name in os.listdir(media_dir):
            file_path = os.path.join(media_dir, file_name)
            if not os.path.isfile(file_path):
                continue
            if file_name in known_guids:
                continue
            if now - os.path.getmtime(file_path) < 4 * 60 * 60:
                continue
            try:
                os.remove(file_path)
            except Exception:
                pass

    async def _move_matching_jobs_to_failed(self, bot_id: str, guid: str, error: str):
        for collection_name in ["media_processing_jobs", "media_processing_jobs_holding"]:
            cursor = self.db[collection_name].find({"bot_id": bot_id, "guid": guid})
            async for doc in cursor:
                await self._archive_failed_doc(doc, error)
                await self.db[collection_name].delete_one({"_id": doc["_id"]})
                self._delete_media_file(guid)

    async def _archive_failed_doc(self, doc: Dict[str, Any], error: str):
        failed_doc = dict(doc)
        failed_doc.pop("_id", None)
        failed_doc["status"] = "failed"
        failed_doc["error"] = error
        await self.failed_collection.insert_one(failed_doc)

    def _delete_media_file(self, guid: Optional[str]):
        if not guid:
            return
        file_path = os.path.join("media_store", "pending_media", guid)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
