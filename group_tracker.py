import asyncio
import time
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pymongo import MongoClient
import logging

from chatbot_manager import ChatbotInstance
from config_models import PeriodicGroupTrackingConfig
from chat_providers.whatsAppBaileyes import WhatsAppBaileysProvider

# Initialize logger
logger = logging.getLogger(__name__)

class GroupTracker:
    def __init__(self, mongo_url: str, chatbot_instances: dict[str, ChatbotInstance]):
        self.mongo_client = MongoClient(mongo_url)
        self.db = self.mongo_client['chat_manager']
        self.tracked_contexts_collection = self.db['tracked_group_contexts']
        self.tracking_state_collection = self.db['group_tracking_state']
        self.chatbot_instances = chatbot_instances
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}

    def start(self):
        self.scheduler.start()
        logger.info("GroupTracker scheduler started.")

    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("GroupTracker scheduler shutdown.")

    def update_jobs(self, user_id: str, tracking_configs: list[PeriodicGroupTrackingConfig]):
        # Remove existing jobs for this user
        jobs_to_remove = [job_id for job_id in self.jobs if job_id.startswith(f"{user_id}_")]
        for job_id in jobs_to_remove:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            del self.jobs[job_id]

        # Add new jobs
        for config in tracking_configs:
            job_id = f"{user_id}_{config.groupIdentifier}"
            try:
                trigger = CronTrigger.from_crontab(config.cronTrackingSchedule)
                self.scheduler.add_job(
                    self.track_group_context,
                    trigger,
                    id=job_id,
                    args=[user_id, config],
                    replace_existing=True
                )
                self.jobs[job_id] = True
                logger.info(f"Added tracking job {job_id} with schedule {config.cronTrackingSchedule}")
            except Exception as e:
                logger.error(f"Failed to add tracking job {job_id}: {e}")

    async def track_group_context(self, user_id: str, config: PeriodicGroupTrackingConfig):
        logger.info(f"Starting tracking job for user {user_id}, group {config.groupIdentifier}")

        chatbot = self.chatbot_instances.get(user_id)
        # Note: We rely on the chatbot instance being keyed by user_id in the main app map?
        # Actually in main.py `chatbot_instances` is keyed by instance_id (uuid), and `active_users` maps user_id -> instance_id.
        # But `GroupTracker` receives `chatbot_instances` reference.
        # We need `active_users` map as well to lookup the instance.
        # Wait, my previous implementation of GroupTracker took `chatbot_instances` (dict).
        # In `main.py`, I passed `chatbot_instances` which is `instance_id -> instance`.
        # I need to fix `GroupTracker` to handle this lookup or pass `active_users` too.

        # FIX: I will pass `active_users` to GroupTracker or handle the lookup differently.
        # Since I can't easily change the constructor signature without changing main.py again (which implies more risk),
        # I will iterate `chatbot_instances` to find the one with matching `user_id`.

        target_instance = None
        for instance in self.chatbot_instances.values():
            if instance.user_id == user_id:
                target_instance = instance
                break

        if not target_instance or not isinstance(target_instance.provider_instance, WhatsAppBaileysProvider):
            logger.error(f"Chatbot not active or invalid provider for user {user_id}")
            return

        # Get last run time
        state_key = {"user_id": user_id, "group_id": config.groupIdentifier}
        state = self.tracking_state_collection.find_one(state_key)

        now_ts = int(time.time() * 1000)
        last_run_ts = state['last_run_ts'] if state else (now_ts - 24 * 60 * 60 * 1000) # Default to 24h ago

        # Fetch messages
        messages = await target_instance.provider_instance.fetch_historic_messages(config.groupIdentifier, limit=500)

        # Filter messages by time window: last_run_ts < msg.originating_time <= now_ts
        filtered_messages = []
        for msg in messages:
            msg_ts = msg.get('originating_time')
            if not msg_ts:
                # Fallback: parse timestamp string if originating_time is missing?
                # server.js sends ISO string in 'timestamp', and numeric in 'originating_time' (if I added it correctly).
                # Let's trust originating_time.
                continue

            if last_run_ts < msg_ts <= now_ts:
                filtered_messages.append(msg)

        # Create period object
        period_object = {
            "user_id": user_id,
            "group_id": config.groupIdentifier,
            "group_name": config.displayName,
            "period_start": last_run_ts,
            "period_end": now_ts,
            "messages": filtered_messages,
            "created_at": datetime.utcnow()
        }

        # Save to DB
        self.tracked_contexts_collection.insert_one(period_object)

        # Update last run state
        self.tracking_state_collection.update_one(
            state_key,
            {"$set": {"last_run_ts": now_ts}},
            upsert=True
        )

        logger.info(f"Completed tracking job for {user_id}/{config.groupIdentifier}. Saved {len(filtered_messages)} messages.")

    def get_tracked_contexts(self, user_id: str, last_periods: int = 0):
        query = {"user_id": user_id}
        cursor = self.tracked_contexts_collection.find(query).sort("period_end", -1)

        if last_periods > 0:
            cursor = cursor.limit(last_periods)

        results = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            results.append(doc)

        return results
