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

    def _format_messages(self, messages: list) -> str:
        lines = []
        for msg in messages:
            sender = msg.get('display_name') or msg.get('sender', 'Unknown')
            text = msg.get('message', '')
            # Format: "Sender: Message"
            lines.append(f"{sender}: {text}")
        return "\n".join(lines)

    async def track_group_context(self, user_id: str, config: PeriodicGroupTrackingConfig):
        logger.info(f"Starting tracking job for user {user_id}, group {config.groupIdentifier}")

        # Find the chatbot instance for this user
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
        # If no previous run, default to 24 hours ago
        last_run_ts = state['last_run_ts'] if state else (now_ts - 24 * 60 * 60 * 1000)

        # Fetch messages (fetching slightly more to ensure coverage)
        try:
            messages = await target_instance.provider_instance.fetch_historic_messages(config.groupIdentifier, limit=500)
        except Exception as e:
             logger.error(f"Failed to fetch historic messages for {user_id}/{config.groupIdentifier}: {e}")
             return

        # Filter messages by time window: last_run_ts < msg.originating_time <= now_ts
        filtered_messages = []
        for msg in messages:
            msg_ts = msg.get('originating_time')
            if not msg_ts:
                continue

            if last_run_ts < msg_ts <= now_ts:
                filtered_messages.append(msg)

        # Generate context string
        group_context_str = self._format_messages(filtered_messages)

        # Create context object
        context_object = {
            "user_id": user_id,
            "group_id": config.groupIdentifier,
            "group_name": config.displayName,
            "period_start": last_run_ts,
            "period_end": now_ts,
            "group_context": group_context_str,
            "messages": filtered_messages, # Storing raw messages as requested
            "message_count": len(filtered_messages),
            "created_at": datetime.utcnow()
        }

        # Save to DB
        self.tracked_contexts_collection.insert_one(context_object)

        # Update last run state
        self.tracking_state_collection.update_one(
            state_key,
            {"$set": {"last_run_ts": now_ts}},
            upsert=True
        )

        logger.info(f"Completed tracking job for {user_id}/{config.groupIdentifier}. Generated context with {len(filtered_messages)} messages.")

    def get_tracked_contexts(self, user_id: str, last_periods: int = 0):
        # The user requested: "list with objects which are {groupIdentifier:<STR>,groupContext:<STR>}"
        query = {"user_id": user_id}
        # Sort by most recent first
        cursor = self.tracked_contexts_collection.find(query).sort("period_end", -1)

        if last_periods > 0:
            cursor = cursor.limit(last_periods)

        results = []
        for doc in cursor:
            results.append({
                "groupIdentifier": doc['group_id'],
                "displayName": doc.get('group_name'),
                "groupContext": doc['group_context'],
                "periodStart": doc['period_start'],
                "periodEnd": doc['period_end'],
                "messageCount": doc['message_count'],
                "createdAt": doc['created_at'].isoformat() if isinstance(doc.get('created_at'), datetime) else doc.get('created_at')
            })

        return results
