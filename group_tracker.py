import asyncio
import time
import json
import importlib
import inspect
import random
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pymongo import MongoClient
from croniter import croniter
import logging
from zoneinfo import ZoneInfo

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from chatbot_manager import ChatbotInstance
from config_models import PeriodicGroupTrackingConfig, LLMProviderConfig
from chat_providers.whatsAppBaileyes import WhatsAppBaileysProvider # DEPRECATED: Removed direct usage
# But wait, we can't remove the line if we modify it, just commenting out or removing completely.
# Let's remove it completely.
from llm_providers.base import BaseLlmProvider
from async_message_delivery_queue_manager import AsyncMessageDeliveryQueueManager, QueueMessageType
from services.action_item_extractor import ActionItemExtractor
from services.cron_window_calculator import CronWindowCalculator


# Initialize logger
logger = logging.getLogger(__name__)

class GroupTracker:
    def __init__(self, mongo_url: str, chatbot_instances: dict[str, ChatbotInstance], async_message_delivery_queue_manager: AsyncMessageDeliveryQueueManager = None):
        self.mongo_client = MongoClient(mongo_url)
        self.db = self.mongo_client['chat_manager']
        self.tracked_groups_collection = self.db['tracked_groups']
        self.tracked_group_periods_collection = self.db['tracked_group_periods']
        self.tracking_state_collection = self.db['group_tracking_state']
        self.chatbot_instances = chatbot_instances
        self.async_message_delivery_queue_manager = async_message_delivery_queue_manager  # Store the queue manager
        self.async_message_delivery_queue_manager = async_message_delivery_queue_manager  # Store the queue manager
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}
        self.extractor = ActionItemExtractor()
        self.window_calculator = CronWindowCalculator()


    def start(self):
        self.scheduler.start()
        logger.info("GroupTracker scheduler started.")

    def shutdown(self):
        self.scheduler.shutdown()
        logger.info("GroupTracker scheduler shutdown.")

    def _calculate_max_interval(self, configs: list[PeriodicGroupTrackingConfig]) -> int:
        max_interval = 0
        now_dt = datetime.now()
        for config in configs:
            try:
                # We calculate the interval between two potential future executions to estimate the period.
                # Note: Cron intervals can vary (e.g. months). We take a sample.
                iter = croniter(config.cronTrackingSchedule, now_dt)
                next_1 = iter.get_next(datetime)
                next_2 = iter.get_next(datetime)
                interval = (next_2 - next_1).total_seconds()
                if interval > max_interval:
                    max_interval = interval
            except Exception:
                pass

        if max_interval > 0:
            return int(max_interval) + 900 # Add 15 minutes buffer
        return 0




    def stop_tracking_jobs(self, user_id: str):
        """
        Stops all tracking jobs for a user WITHOUT deleting the data.
        Used for disconnects, reloads, and unlinks.
        """
        all_jobs = self.scheduler.get_jobs()
        prefix = f"{user_id}_"
        
        for job in all_jobs:
            if job.id.startswith(prefix):
                try:
                    self.scheduler.remove_job(job.id)
                    logger.info(f"Stopped tracking job {job.id} for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove job {job.id}: {e}")
        
        # Sync self.jobs
        keys_to_remove = [k for k in self.jobs if k.startswith(prefix)]
        for k in keys_to_remove:
            del self.jobs[k]

    def update_jobs(self, user_id: str, tracking_configs: list[PeriodicGroupTrackingConfig], timezone: str = "UTC"):
        # Remove existing jobs for this user by querying the scheduler directly
        # This ensures we catch any zombie jobs even if self.jobs is out of sync
        all_jobs = self.scheduler.get_jobs()
        prefix = f"{user_id}_"
        
        for job in all_jobs:
            if job.id.startswith(prefix):
                try:
                    self.scheduler.remove_job(job.id)
                    logger.info(f"Removed tracking job {job.id} for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove job {job.id}: {e}")
        
        # Sync self.jobs (optional, but good for consistency)
        keys_to_remove = [k for k in self.jobs if k.startswith(prefix)]
        for k in keys_to_remove:
            del self.jobs[k]

        # Clean up stale groups from MongoDB logic REMOVED.
        # We now rely on explicit DELETE API calls to remove data.
        # This prevents accidental data loss during config reloads/glitches.

        # Add new jobs
        for config in tracking_configs:
            job_id = f"{user_id}_{config.groupIdentifier}"
            try:
                trigger = CronTrigger.from_crontab(config.cronTrackingSchedule, timezone=ZoneInfo(timezone))
                self.scheduler.add_job(
                    self.track_group_context,
                    trigger,
                    id=job_id,
                    args=[user_id, config, timezone],
                    replace_existing=True
                )
                self.jobs[job_id] = True
                logger.info(f"Added tracking job {job_id} with schedule {config.cronTrackingSchedule}")
            except Exception as e:
                logger.error(f"Failed to add tracking job {job_id}: {e}")

        # Update provider cache policy
        # NOTE: Polymorphic call. Ensure all providers have this method (defined in BaseChatProvider).
        max_interval = self._calculate_max_interval(tracking_configs)
        target_instance = None
        for instance in self.chatbot_instances.values():
            if instance.user_id == user_id:
                target_instance = instance
                break

        if target_instance and target_instance.provider_instance:
            target_instance.provider_instance.update_cache_policy(max_interval)

    async def track_group_context(self, user_id: str, config: PeriodicGroupTrackingConfig, timezone: str = "UTC"):
        # Add jitter to prevent rate limiting if multiple groups trigger at the same cron time
        delay = random.uniform(0, 60)
        logger.info(f"Scheduled tracking for {user_id}/{config.groupIdentifier} starting in {delay:.2f}s")
        await asyncio.sleep(delay)
        
        logger.info(f"Starting tracking job for user {user_id}, group {config.groupIdentifier}")

        # Find the chatbot instance for this user
        target_instance = None
        for instance in self.chatbot_instances.values():
            if instance.user_id == user_id:
                target_instance = instance
                break

        if not target_instance or not target_instance.provider_instance.is_connected:
            logger.error(f"Chatbot not active or invalid provider for user {user_id}")
            return

        # Fetch messages
        try:
            # Polymorphic call
            messages = await target_instance.provider_instance.fetch_historic_messages(config.groupIdentifier, limit=500)
            if messages is None:
                 logger.error(f"Fetch failed for {user_id}/{config.groupIdentifier} (returned None). Aborting job to prevent data loss. State will NOT be updated.")
                 return # Abort without updating state, allowing retry next time
        except Exception as e:
             logger.error(f"Failed to fetch historic messages for {user_id}/{config.groupIdentifier}: {e}")
             return

        # Determine time window
        # We calculate the time window strictly based on the cron schedule to avoid
        # ingesting stale data (e.g. after downtime) or duplicate data.
        # The window is [previous_cron_time, current_cron_time].

        try:
             # Calculate window using separated service
             last_run_ts = None
             state_key = {'user_id': user_id, 'group_id': config.groupIdentifier}
             state_doc = self.tracking_state_collection.find_one(state_key)
             if state_doc:
                 last_run_ts = state_doc.get('last_run_ts')
            
             current_cron_start_dt, current_cron_end_dt = self.window_calculator.calculate_window(
                 cron_expression=config.cronTrackingSchedule,
                 timezone=timezone,
                 now_dt=datetime.now(ZoneInfo("UTC")), 
                 last_run_ts=last_run_ts
             )

             if not current_cron_start_dt or not current_cron_end_dt:
                 logger.error(f'Failed to calculate window for {user_id}/{config.groupIdentifier}. Aborting.')
                 return

             now_ts = int(current_cron_end_dt.timestamp() * 1000)
             last_run_ts = int(current_cron_start_dt.timestamp() * 1000)

             logger.info(f'Tracking job for {user_id}/{config.groupIdentifier}: Window calculated as {current_cron_start_dt} -> {current_cron_end_dt}')
        except Exception as e:
            logger.error(f'Failed to calculate cron window for {user_id}/{config.groupIdentifier}: {e}. Aborting.')
            return


        # Filter and Transform
        transformed_messages = []
        alternate_identifiers_set = set()

        for msg in messages:
            msg_ts = msg.get('originating_time')
            if not msg_ts:
                continue

            if last_run_ts < msg_ts <= now_ts:
                # Check if it's a bot message
                provider_message_id = msg.get('provider_message_id')
                is_bot = target_instance.provider_instance.is_bot_message(provider_message_id)

                if is_bot:
                    sender_data = {
                        "identifier": f"bot_{user_id}",
                        "display_name": f"Bot ({user_id})",
                        "alternate_identifiers": msg.get('actual_sender', {}).get('alternate_identifiers', [])
                    }
                else:
                    sender_data = {
                        "identifier": msg.get('sender'),
                        "display_name": msg.get('display_name'),
                        "alternate_identifiers": msg.get('alternate_identifiers', [])
                    }

                # Collect group alternates if available in msg
                if msg.get('group'):
                    for alt in msg['group'].get('alternate_identifiers', []):
                        alternate_identifiers_set.add(alt)

                transformed_msg = {
                    "sender": sender_data,
                    "message": msg.get('message'),
                    "accepted_time": int(time.time() * 1000),
                    "originating_time": msg_ts,
                    "provider_message_id": provider_message_id
                }
                transformed_messages.append(transformed_msg)

        # Sort messages by originating_time
        transformed_messages.sort(key=lambda x: x['originating_time'])

        # Upsert Group Metadata
        alternate_identifiers_set.add(config.groupIdentifier)
        alternate_identifiers_set.add(config.displayName)

        self.tracked_groups_collection.update_one(
            {"user_id": user_id, "group_id": config.groupIdentifier},
            {"$set": {
                "user_id": user_id,
                "group_id": config.groupIdentifier,
                "display_name": config.displayName,
                "alternate_identifiers": list(alternate_identifiers_set),
                "crontab_triggering_expression": config.cronTrackingSchedule
            }},
            upsert=True
        )

        # Insert Period Document
        period_doc = {
            "user_id": user_id,
            "tracked_group_unique_identifier": config.groupIdentifier,
            "periodStart": last_run_ts,
            "periodEnd": now_ts,
            "messageCount": len(transformed_messages),
            "createdAt": datetime.utcnow(),
            "messages": transformed_messages
        }
        self.tracked_group_periods_collection.insert_one(period_doc)

        # Update last run state
        # We store the end of the current window as the last run time.
        state_key = {"user_id": user_id, "group_id": config.groupIdentifier}
        self.tracking_state_collection.update_one(
            state_key,
            {"$set": {"last_run_ts": now_ts}},
            upsert=True
        )

        logger.info(f"Completed tracking job for {user_id}/{config.groupIdentifier}. Saved {len(transformed_messages)} messages.")

        # Send digest notification to user (message to self)
        # Use user's configured timezone for the timestamp
        try:
            user_tz = ZoneInfo(timezone)
        except Exception:
            logger.warning(f"Invalid timezone '{timezone}' for user {user_id}, using UTC")
            user_tz = ZoneInfo("UTC")
        
        now = datetime.now(user_tz)
        digest_message = f"{now.strftime('%Y-%m-%d')} {now.strftime('%H:%M:%S')}: Tracked Group {config.displayName} Digest"
        
        # Extract action items if there are messages
        action_items_output = ""
        
        if not transformed_messages:
            logger.info(f"No messages in this period for {user_id}/{config.groupIdentifier}")
            # Optional: Send "No messages" digest? Current logic sends only if items found or if we want to confirm emptiness.
            # User wants "Actionable Items". If none, maybe silent? 
            # Original code sent "\n\nNo messages in this period"
            # Let's keep silence or minimal log for now, as we moved to "Per Item" delivery. 
            # Attempting to send "No items" as a single message might be annoying if frequent.
            return 
        else:
            try:
                # Get user's LLM config and language preference
                llm_config = target_instance.config.configurations.llm_provider_config
                language_code = target_instance.config.configurations.user_details.language_code
                
                # Extract action items using the new service
                # This returns a list of action item dicts directly (or empty list)
                action_items = await self.extractor.extract(
                    messages=transformed_messages,
                    llm_config=llm_config,
                    user_id=user_id,
                    timezone=user_tz,
                    group_id=config.groupIdentifier,
                    language_code=language_code
                )
                
                if not action_items:
                     logger.info(f"No actionable items found by LLM for {user_id}/{config.groupIdentifier}")
                     return

                # Send items to Queue
                if self.async_message_delivery_queue_manager:
                    logger.info(f"Queuing {len(action_items)} items for {user_id}")
                    for item in action_items:
                        # Inject Group Name
                        item["group_display_name"] = config.displayName
                        
                        # Add to Queue
                        self.async_message_delivery_queue_manager.add_item(
                            content=item,
                            message_type=QueueMessageType.ICS_ACTIONABLE_ITEM,
                            user_id=user_id,
                            provider_name="whatsapp_baileys" # Currently hardcoded, could be dynamic
                        )
                else:
                    logger.error("AsyncMessageDeliveryQueueManager not initialized! Cannot send items.")

            except Exception as e:
                logger.error(f"Failed to process action items for user {user_id}: {e}")

    def _build_period_query(self, user_id, group_id, time_from=None, time_until=None):
        query = {
            "user_id": user_id,
            "tracked_group_unique_identifier": group_id
        }

        if time_from is not None:
            query["periodStart"] = {"$gt": time_from}
        if time_until is not None:
            query["periodEnd"] = {"$lt": time_until}

        return query

    def _build_group_response(self, group_meta, last_periods: int, time_from=None, time_until=None):
        user_id = group_meta['user_id']
        group_id = group_meta['group_id']

        query = self._build_period_query(user_id, group_id, time_from, time_until)
        cursor = self.tracked_group_periods_collection.find(query).sort("periodEnd", -1)

        if last_periods > 0:
            cursor = cursor.limit(last_periods)

        periods = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            if isinstance(doc.get('createdAt'), datetime):
                doc['createdAt'] = doc['createdAt'].isoformat()
            periods.append(doc)

        return {
            "group": {
                "identifier": group_id,
                "display_name": group_meta['display_name'],
                "alternate_identifiers": group_meta.get('alternate_identifiers', [])
            },
            "periods": periods
        }

    def get_group_messages(self, user_id: str, group_id: str, last_periods: int = 0, time_from: int = None, time_until: int = None):
        # Fetch group metadata
        group_meta = self.tracked_groups_collection.find_one({"user_id": user_id, "group_id": group_id})
        if not group_meta:
            return None
        return self._build_group_response(group_meta, last_periods, time_from, time_until)

    def get_all_user_messages(self, user_id: str, last_periods: int = 0, time_from: int = None, time_until: int = None):
        # Fetch all groups for user
        groups_cursor = self.tracked_groups_collection.find({"user_id": user_id})

        results = []
        for group_meta in groups_cursor:
            results.append(self._build_group_response(group_meta, last_periods, time_from, time_until))

        return results

    def delete_group_messages(self, user_id: str, group_id: str, last_periods: int = 0, time_from: int = None, time_until: int = None):
        query = self._build_period_query(user_id, group_id, time_from, time_until)

        if last_periods > 0:
            # Fetch IDs to delete (most recent N matching filters)
            cursor = self.tracked_group_periods_collection.find(query, {"_id": 1}).sort("periodEnd", -1).limit(last_periods)
            ids = [doc["_id"] for doc in cursor]
            if not ids:
                return 0
            result = self.tracked_group_periods_collection.delete_many({"_id": {"$in": ids}})
            return result.deleted_count
        else:
            result = self.tracked_group_periods_collection.delete_many(query)
            return result.deleted_count

    def delete_all_user_messages(self, user_id: str, last_periods: int = 0, time_from: int = None, time_until: int = None):
        total_deleted = 0
        groups_cursor = self.tracked_groups_collection.find({"user_id": user_id})
        for group_meta in groups_cursor:
            deleted = self.delete_group_messages(user_id, group_meta['group_id'], last_periods, time_from, time_until)
            total_deleted += deleted

        return total_deleted
