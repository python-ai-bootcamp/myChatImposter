
import asyncio
import time
import random
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict

from config_models import PeriodicGroupTrackingConfig
from services.session_manager import SessionManager
from async_message_delivery_queue_manager import AsyncMessageDeliveryQueueManager, QueueMessageType
from .extractor import ActionItemExtractor
from .cron_window import CronWindowCalculator
from .history_service import GroupHistoryService

logger = logging.getLogger(__name__)

class GroupTrackingRunner:
    def __init__(self, chatbot_instances: Dict[str, SessionManager], history_service: GroupHistoryService, queue_manager: AsyncMessageDeliveryQueueManager, extractor: ActionItemExtractor, window_calculator: CronWindowCalculator):
        self.chatbot_instances = chatbot_instances
        self.history = history_service
        self.queue_manager = queue_manager
        self.extractor = extractor
        self.window_calculator = window_calculator

    async def run_tracking_cycle(self, user_id: str, config: PeriodicGroupTrackingConfig, timezone: str = "UTC"):
        """
        Executes a single tracking cycle for a group.
        Fetch -> Window -> Filter -> Save -> Extract -> Queue.
        """
        # Add jitter to prevent rate limiting if multiple groups trigger at the same cron time
        delay = random.uniform(0, 60)
        logger.info(f"Scheduled tracking for {user_id}/{config.groupIdentifier} starting in {delay:.2f}s")
        await asyncio.sleep(delay)
        
        logger.info(f"Starting tracking job for user {user_id}, group {config.groupIdentifier}")

        # Find the chatbot instance for this user
        target_instance = None
        for instance in self.chatbot_instances.values():
            if instance.bot_id == user_id:
                target_instance = instance
                break

        if not target_instance or not target_instance.provider_instance or not target_instance.provider_instance.is_connected:
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
        try:
             # Calculate window using separated service
             last_run_ts = await self.history.get_last_run(user_id, config.groupIdentifier)
            
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
        
        # Deduplication: Get recent message IDs from history to prevent overlap if timestamps update
        seen_message_ids = await self.history.get_recent_message_ids(user_id, config.groupIdentifier)
        logger.info(f"Loaded {len(seen_message_ids)} recent message IDs for deduplication.")

        for msg in messages:
            msg_ts = msg.get('originating_time')
            if not msg_ts:
                continue

            if last_run_ts < msg_ts <= now_ts:
                # Check for duplicate message
                provider_message_id = msg.get('provider_message_id')
                if provider_message_id in seen_message_ids:
                    logger.warning(f"Duplicate message {provider_message_id} skipped.")
                    continue
                seen_message_ids.add(provider_message_id)
                
                # Check if it's a bot message
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

        # Save to History Service
        await self.history.save_tracking_result(
            user_id=user_id,
            config_group_id=config.groupIdentifier,
            config_display_name=config.displayName,
            config_schedule=config.cronTrackingSchedule,
            messages=transformed_messages,
            start_ts=last_run_ts,
            end_ts=now_ts,
            alternate_identifiers_set=alternate_identifiers_set
        )

        logger.info(f"Completed tracking job for {user_id}/{config.groupIdentifier}. Saved {len(transformed_messages)} messages.")

        # Extract Action Items logic
        if not transformed_messages:
            logger.info(f"No messages in this period for {user_id}/{config.groupIdentifier}")
            return 
        else:
            try:
                # User Timezone for LLM Context
                try:
                    user_tz = ZoneInfo(timezone)
                except Exception:
                    logger.warning(f"Invalid timezone '{timezone}' for user {user_id}, using UTC")
                    user_tz = ZoneInfo("UTC")

                # Get user's LLM config and language preference
                llm_config = target_instance.config.configurations.llm_provider_config
                language_code = target_instance.config.configurations.user_details.language_code
                
                # Extract action items
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
                if self.queue_manager:
                    logger.info(f"Queuing {len(action_items)} items for {user_id}")
                    for item in action_items:
                        # Inject Group Name
                        item["group_display_name"] = config.displayName
                        
                        # Add to Queue
                        # Add to Queue
                        await self.queue_manager.add_item(
                            content=item,
                            message_type=QueueMessageType.ICS_ACTIONABLE_ITEM,
                            user_id=user_id,
                            provider_name="whatsAppBaileys" 
                        )
                else:
                    logger.error("AsyncMessageDeliveryQueueManager not initialized! Cannot send items.")

            except Exception as e:
                logger.error(f"Failed to process action items for user {user_id}: {e}")
