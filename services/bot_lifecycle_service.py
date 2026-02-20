"""
BotLifecycleService: Handles bot connection/disconnection lifecycle events.
Extracted from routers/bot_management.py to separate business logic from routing.
"""
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from dependencies import GlobalStateManager

from config_models import BotConfiguration
import asyncio
import uuid
from services.session_manager import SessionManager
from services.ingestion_service import IngestionService
from features.automatic_bot_reply.service import AutomaticBotReplyService
from features.kid_phone_safety_tracking.service import KidPhoneSafetyService


class BotLifecycleService:
    """
    Service that handles bot lifecycle events (connection status changes).

    Responsibilities:
    - Moving messages between holding/active queues on connect/disconnect
    - Starting/stopping group tracking jobs
    """

    def __init__(self, global_state: "GlobalStateManager"):
        self.global_state = global_state

    async def on_bot_connected(self, bot_id: str):
        """
        Handle bot connection event.
        - Move queued messages from holding to active
        - Start group tracking jobs if enabled
        """
        # Guard: Skip if bot already has active tracking jobs (avoid duplicate setup during reconnects)
        if self.global_state.group_tracker:
            existing_jobs = [
                job for job in self.global_state.group_tracker.scheduler.get_jobs()
                if job.id.startswith(f"{bot_id}_")
            ]
            if existing_jobs:
                logging.debug(
                    f"LIFECYCLE: Bot {bot_id} already has {len(existing_jobs)} tracking jobs, "
                    "skipping duplicate setup."
                )
                return

        # 1. Move items to Active Queue
        if self.global_state.async_message_delivery_queue_manager:
            await self.global_state.async_message_delivery_queue_manager.move_bot_to_active(bot_id)
            logging.info(f"LIFECYCLE: Bot {bot_id} connected. Moved items to ACTIVE queue.")

        # 2. Start Group Tracking (Late Binding)
        if self.global_state.group_tracker:
            try:
                # Fetch config to know what to track
                config_dict = await self._get_bot_config(bot_id)

                if config_dict:
                    config = BotConfiguration.model_validate(config_dict)
                    
                    # Determine Owner
                    owner_user_id = None
                    if self.global_state.credentials_collection is not None:
                         # Find credential that owns this configuration
                         owner_doc = await self.global_state.credentials_collection.find_one(
                             {"owned_bots": bot_id},
                             {"user_id": 1}
                         )
                         if owner_doc:
                             owner_user_id = owner_doc.get("user_id")

                    if config.features.periodic_group_tracking.enabled:
                        self.global_state.group_tracker.update_jobs(
                            bot_id,
                            config.features.periodic_group_tracking.tracked_groups,
                            config.configurations.user_details.timezone,
                            owner_user_id=owner_user_id
                        )
                    else:
                        self.global_state.group_tracker.update_jobs(bot_id, [], owner_user_id=owner_user_id)
            except Exception as e:
                logging.error(f"LIFECYCLE: Failed to start tracking for {bot_id}: {e}")
    
    async def on_bot_disconnected(self, bot_id: str):
        """
        Handle bot disconnection event.
        - Stop group tracking jobs (Safe Pause)
        """
        if self.global_state.group_tracker:
            logging.info(f"LIFECYCLE: Bot {bot_id} disconnected. Pausing tracking jobs.")
            self.global_state.group_tracker.stop_tracking_jobs(bot_id)
    
    async def _get_bot_config(self, bot_id: str) -> Optional[dict]:
        """Helper to retrieve bot configuration from DB."""
        try:
            db_config = await self.global_state.configurations_collection.find_one(
                {"config_data.bot_id": bot_id}
            )
            
            if not db_config:
                return None
            
            config_data = db_config.get("config_data")
            if isinstance(config_data, dict):
                return config_data
            return None
        except Exception as e:
            logging.error(f"LIFECYCLE: Error retrieving config for {bot_id}: {e}")
            return None
    
    def create_status_change_callback(self):
        """
        Returns an async callback function suitable for passing to ChatbotInstance.
        This allows the router to remain thin while this service handles the logic.
        """
        async def callback(uid: str, status: str):
            if status == 'connected':
                await self.on_bot_connected(uid)
            elif status == 'disconnected':
                await self.on_bot_disconnected(uid)
        return callback

    async def delete_bot_data(self, bot_id: str) -> bool:
        """
        Delete all data associated with a bot configuration.
        - Stops active instance
        - Clears queues
        - Stops tracking jobs
        - Deletes configuration from DB

        Returns:
            True if deletion was successful (or config not found), False on error.
        """
        try:
            # 1. Stop Tracking Jobs
            if self.global_state.group_tracker:
                 logging.info(f"LIFECYCLE: Stopping tracking jobs for {bot_id}")
                 self.global_state.group_tracker.update_jobs(bot_id, [])

            # 2. Stop Active Instance
            if bot_id in self.global_state.active_bots:
                instance_id = self.global_state.active_bots[bot_id]
                instance = self.global_state.chatbot_instances.get(instance_id)
                if instance:
                    logging.info(f"LIFECYCLE: Stopping instance for {bot_id} before delete.")
                    await instance.stop(cleanup_session=True)
                    self.global_state.remove_active_bot(bot_id)
            
            # 3. Cleanup Queues (Move to Holding)
            if self.global_state.async_message_delivery_queue_manager:
                 await self.global_state.async_message_delivery_queue_manager.move_bot_to_holding(bot_id)

            # 4. Delete Configuration DO NOT DELETE CREDENTIALS HERE
            query = {"config_data.bot_id": bot_id}
            result = await self.global_state.configurations_collection.delete_one(query)
            
            if result.deleted_count > 0:
                logging.info(f"LIFECYCLE: Deleted configuration for {bot_id}.")
                return True
            else:
                logging.warning(f"LIFECYCLE: Configuration for {bot_id} not found during delete.")
                return False

        except Exception as e:
            logging.error(f"LIFECYCLE: Error deleting bot data for {bot_id}: {e}")
            raise e

    async def create_bot_session(self, config: BotConfiguration) -> SessionManager:
        """
        Create and configure a SessionManager with all services and features.
        Replicates logic from bot_management._setup_session.
        """
        loop = asyncio.get_running_loop()
        
        # Determine Owner
        owner_user_id = None
        if self.global_state.credentials_collection is not None:
            # Find credential that owns this configuration
            owner_doc = await self.global_state.credentials_collection.find_one(
                {"owned_bots": config.bot_id},
                {"user_id": 1}
            )
            if owner_doc:
                owner_user_id = owner_doc.get("user_id")
        
        instance = SessionManager(
            config=config,
            on_session_end=self.global_state.remove_active_bot,
            queues_collection=self.global_state.queues_collection,
            main_loop=loop,
            on_status_change=self.create_status_change_callback(),
            owner_user_id=owner_user_id
        )
        
        try:
            # 1. Ingestion Service
            if self.global_state.queues_collection is not None:
                ingester = IngestionService(instance, self.global_state.queues_collection)
                ingester.start()
                instance.register_service(ingester)

            # 2. Features Subscription
            if config.features.automatic_bot_reply.enabled:
                bot_service = AutomaticBotReplyService(instance)
                instance.register_message_handler(bot_service.handle_message)
                instance.register_feature("automatic_bot_reply", bot_service)
            
            if config.features.kid_phone_safety_tracking.enabled:
                kid_service = KidPhoneSafetyService(instance)
                instance.register_message_handler(kid_service.handle_message)
                instance.register_feature("kid_phone_safety_tracking", kid_service)
                
            return instance
            
        except Exception as e:
            logging.error(f"LIFECYCLE: Error setting up session for {config.bot_id}: {e}")
            await instance.stop()
            raise e

    async def start_bot(self, bot_id: str):
        """
        Start a specific bot by ID.
        """
        if bot_id in self.global_state.active_bots:
            logging.info(f"LIFECYCLE: Bot {bot_id} already active. Skipping start.")
            return

        config_dict = await self._get_bot_config(bot_id)
        if not config_dict:
            logging.error(f"LIFECYCLE: Config not found for {bot_id}. Cannot start.")
            return

        try:
            config = BotConfiguration.model_validate(config_dict)
            
            # Start Instance
            instance_id = str(uuid.uuid4())
            logging.info(f"LIFECYCLE: Starting bot {bot_id} (Instance {instance_id})")
            
            instance = await self.create_bot_session(config)

            self.global_state.chatbot_instances[instance_id] = instance
            await instance.start()
            self.global_state.active_bots[bot_id] = instance_id
            
            # Clear tracking jobs in case relevant
            if self.global_state.group_tracker:
                 self.global_state.group_tracker.update_jobs(bot_id, [])

        except Exception as e:
            logging.error(f"LIFECYCLE: Failed to start bot {bot_id}: {e}")
            if bot_id in self.global_state.active_bots:
                self.global_state.remove_active_bot(bot_id)

    async def stop_bot(self, bot_id: str, cleanup_session: bool = True):
        """
        Stop a specific bot by ID.
        :param bot_id: The ID of the bot to stop.
        :param cleanup_session: If True, deletes session credentials. If False, keeps them (Soft Stop).
        """
        if bot_id not in self.global_state.active_bots:
            return

        logging.info(f"LIFECYCLE: Stopping bot {bot_id}")
        instance_id = self.global_state.active_bots[bot_id]
        instance = self.global_state.chatbot_instances.get(instance_id)

        try:
            if instance:
                await instance.stop(cleanup_session=cleanup_session)
            
            self.global_state.remove_active_bot(bot_id)
            
            if self.global_state.async_message_delivery_queue_manager:
                 await self.global_state.async_message_delivery_queue_manager.move_user_to_holding(bot_id)
            if self.global_state.group_tracker:
                 self.global_state.group_tracker.stop_tracking_jobs(bot_id)
                 
        except Exception as e:
            logging.error(f"LIFECYCLE: Error stopping bot {bot_id}: {e}")
