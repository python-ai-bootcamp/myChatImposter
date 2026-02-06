"""
BotLifecycleService: Handles bot connection/disconnection lifecycle events.
Extracted from routers/bot_management.py to separate business logic from routing.
"""
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from dependencies import GlobalStateManager

from config_models import BotConfiguration


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
            await self.global_state.async_message_delivery_queue_manager.move_user_to_active(bot_id)
            logging.info(f"LIFECYCLE: Bot {bot_id} connected. Moved items to ACTIVE queue.")

        # 2. Start Group Tracking (Late Binding)
        if self.global_state.group_tracker:
            try:
                # Fetch config to know what to track
                config_dict = await self._get_bot_config(bot_id)

                if config_dict:
                    config = BotConfiguration.model_validate(config_dict)

                    if config.features.periodic_group_tracking.enabled:
                        self.global_state.group_tracker.update_jobs(
                            bot_id,
                            config.features.periodic_group_tracking.tracked_groups,
                            config.configurations.user_details.timezone
                        )
                    else:
                        self.global_state.group_tracker.update_jobs(bot_id, [])
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
