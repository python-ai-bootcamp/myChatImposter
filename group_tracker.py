import asyncio
import time
import json
import importlib
import inspect
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
from chat_providers.whatsAppBaileyes import WhatsAppBaileysProvider
from llm_providers.base import BaseLlmProvider

# Initialize logger
logger = logging.getLogger(__name__)

class GroupTracker:
    def __init__(self, mongo_url: str, chatbot_instances: dict[str, ChatbotInstance]):
        self.mongo_client = MongoClient(mongo_url)
        self.db = self.mongo_client['chat_manager']
        self.tracked_groups_collection = self.db['tracked_groups']
        self.tracked_group_periods_collection = self.db['tracked_group_periods']
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

    def _find_provider_class(self, module, base_class):
        """Finds a class in the module that is a subclass of the base_class."""
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, base_class) and obj is not base_class:
                return obj
        return None

    def _build_llm_input_json(self, messages: list, timezone: ZoneInfo) -> str:
        """
        Builds a JSON array of messages formatted for LLM input.
        Each message has: when (timestamp in user's timezone), sender (display name), content.
        """
        formatted_messages = []
        for msg in messages:
            originating_time_ms = msg.get('originating_time', 0)
            originating_dt = datetime.fromtimestamp(originating_time_ms / 1000, tz=timezone)
            formatted_msg = {
                "when": originating_dt.strftime('%Y-%m-%d %H:%M'),
                "sender": msg.get('sender', {}).get('display_name', 'Unknown'),
                "content": msg.get('message', '')
            }
            formatted_messages.append(formatted_msg)
        return json.dumps(formatted_messages, indent=2, ensure_ascii=False)

    async def _extract_action_items(self, messages_json: str, llm_config: LLMProviderConfig, user_id: str, group_id: str = "", language_code: str = "en") -> str:
        """
        Uses LLM to extract action items from group messages.
        Returns the raw LLM output string.
        
        Args:
            messages_json: JSON string of messages to analyze
            llm_config: LLM provider configuration
            user_id: User identifier
            group_id: Group identifier for recording purposes
            language_code: ISO 639-1 language code for response language
        """
        from llm_providers.recorder import LLMRecorder
        
        # System prompt with language placeholder - uses LangChain template syntax
        # Curly braces for JSON are escaped with {{ and }}
        system_prompt_template = """IMPORTANT: task_title and task_description must be written in a language with ISO 639-1 language code {language_code}.
You are a helpful assistant. 
each time you get a chat group message correspondence you extract from it all of the possible action items in the group correspondence and prepare a summary of it.
the summary of action items is a json array, with objects, each object representing an action item and must include the following details:
[{{
"relevant_task_messages":<an array of messages that are relevant to this specific action item of format RELEVANT_TASK_MESSAGE>,
"text_deadline": <string representing the sender quoted deadline of this action item, if available>,
"timestamp_deadline": <string representing the sender quoted deadline of this action item, but translated to timestamp string. if deadline was given originally as relative time (for example 'next week' or 'next wednsday') translate it relative to the time message with deadline was originally sent. if the deadline has not specific hour please set it to 12:00:00 noon at that designated day>,
"task_title": <a concise description of the task phrased as short as possible as a title>,
"task_description": <a concise description of the task to be done with details, if task spans more than a single message, aggragate the information from all messages that are part of this task>
}},...] 

RELEVANT_TASK_MESSAGE is an object of format:
{{
    "originating_time": <string representing the time in which the message was sent>,
    "sender": <string representing the sender of the message>,
    "content": <the content of the message>
}}
"""
        
        # Setup recorder if enabled
        record_enabled = llm_config.provider_config.record_llm_interactions
        recorder = None
        epoch_ts = None
        if record_enabled:
            recorder = LLMRecorder(user_id, "periodic_group_tracking", group_id)
            epoch_ts = recorder.start_recording()
            # Format prompt for recording - substitute language_code variable
            formatted_prompt = system_prompt_template.replace("{language_code}", language_code)
            recorder.record_prompt(formatted_prompt, messages_json, epoch_ts=epoch_ts)
        
        try:
            # Dynamically load the LLM provider
            llm_provider_name = llm_config.provider_name
            llm_provider_module = importlib.import_module(f"llm_providers.{llm_provider_name}")
            LlmProviderClass = self._find_provider_class(llm_provider_module, BaseLlmProvider)
            
            if not LlmProviderClass:
                logger.error(f"Could not find LLM provider class for {llm_provider_name}")
                return "[Error: LLM provider not found]"
            
            llm_provider = LlmProviderClass(config=llm_config, user_id=f"action_items_{user_id}")
            llm = llm_provider.get_llm()
            
            # Create the prompt and chain - language_code passed as template variable
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt_template),
                ("human", "{input}")
            ])
            
            chain = prompt | llm | StrOutputParser()
            
            # Invoke the chain with all template variables
            logger.info(f"Invoking LLM for action items extraction for user {user_id}")
            result = await chain.ainvoke({"input": messages_json, "language_code": language_code})
            logger.info(f"LLM action items extraction completed for user {user_id}")
            
            # Record response if enabled
            if recorder and epoch_ts:
                recorder.record_response(result, epoch_ts=epoch_ts)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract action items for user {user_id}: {e}")
            error_msg = f"[Error extracting action items: {e}]"
            
            # Record error as response if enabled
            if recorder and epoch_ts:
                recorder.record_response(error_msg, epoch_ts=epoch_ts)
            
            return error_msg

    def update_jobs(self, user_id: str, tracking_configs: list[PeriodicGroupTrackingConfig], timezone: str = "UTC"):
        # Remove existing jobs for this user
        jobs_to_remove = [job_id for job_id in self.jobs if job_id.startswith(f"{user_id}_")]
        for job_id in jobs_to_remove:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            del self.jobs[job_id]

        # Clean up stale groups from MongoDB that are no longer in the config
        current_group_ids = {config.groupIdentifier for config in tracking_configs}
        existing_groups = self.tracked_groups_collection.find({"user_id": user_id}, {"group_id": 1})
        for group_doc in existing_groups:
            group_id = group_doc.get("group_id")
            if group_id and group_id not in current_group_ids:
                # Delete group metadata
                self.tracked_groups_collection.delete_one({"user_id": user_id, "group_id": group_id})
                # Delete associated periods
                self.tracked_group_periods_collection.delete_many({"user_id": user_id, "tracked_group_unique_identifier": group_id})
                # Delete tracking state
                self.tracking_state_collection.delete_one({"user_id": user_id, "group_id": group_id})
                logger.info(f"Cleaned up stale tracked group {group_id} for user {user_id}")

        # Add new jobs
        for config in tracking_configs:
            job_id = f"{user_id}_{config.groupIdentifier}"
            try:
                trigger = CronTrigger.from_crontab(config.cronTrackingSchedule)
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
        max_interval = self._calculate_max_interval(tracking_configs)
        target_instance = None
        for instance in self.chatbot_instances.values():
            if instance.user_id == user_id:
                target_instance = instance
                break

        if target_instance and isinstance(target_instance.provider_instance, WhatsAppBaileysProvider):
            target_instance.provider_instance.update_cache_policy(max_interval)

    async def track_group_context(self, user_id: str, config: PeriodicGroupTrackingConfig, timezone: str = "UTC"):
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

        # Fetch messages
        try:
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
            now_ts_raw = time.time()
            now_dt = datetime.fromtimestamp(now_ts_raw)
            # Add a small buffer to ensure that if we run exactly on the second, we still catch the current slot.
            safe_now_dt = now_dt + timedelta(seconds=1)

            iter = croniter(config.cronTrackingSchedule, safe_now_dt)
            current_cron_end_dt = iter.get_prev(datetime)
            current_cron_start_dt = iter.get_prev(datetime)

            now_ts = int(current_cron_end_dt.timestamp() * 1000)
            last_run_ts = int(current_cron_start_dt.timestamp() * 1000)

            logger.info(f"Tracking job for {user_id}/{config.groupIdentifier}: Window calculated as {current_cron_start_dt} -> {current_cron_end_dt}")
        except Exception as e:
            logger.error(f"Failed to calculate cron window for {user_id}/{config.groupIdentifier}: {e}. Aborting.")
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
            action_items_output = "\n\nNo messages in this period"
        else:
            try:
                # Get user's LLM config and language preference
                llm_config = target_instance.config.configurations.llm_provider_config
                language_code = target_instance.config.configurations.user_details.language_code
                
                # Build the JSON input for LLM
                messages_json = self._build_llm_input_json(transformed_messages, user_tz)
                logger.info(f"Built LLM input JSON with {len(transformed_messages)} messages for user {user_id}")
                
                # Extract action items
                action_items_output = await self._extract_action_items(
                    messages_json, 
                    llm_config, 
                    user_id,
                    group_id=config.groupIdentifier,
                    language_code=language_code
                )
                action_items_output = f"\n\n{action_items_output}"
                
            except Exception as e:
                logger.error(f"Failed to extract action items for user {user_id}: {e}")
                action_items_output = f"\n\n[Error extracting action items: {e}]"
        
        # Append action items to digest message
        digest_message = digest_message + action_items_output
        
        # Use the user's actual WhatsApp JID for sending message to self
        recipient_jid = target_instance.provider_instance.user_jid
        if not recipient_jid:
            logger.warning(f"User JID not available for {user_id}, cannot send digest notification")
        else:
            try:
                await target_instance.provider_instance.sendMessage(recipient_jid, digest_message)
                logger.info(f"Sent digest notification to user {user_id} (JID: {recipient_jid}, TZ: {timezone})")
            except Exception as e:
                logger.error(f"Failed to send digest notification to user {user_id}: {e}")

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
