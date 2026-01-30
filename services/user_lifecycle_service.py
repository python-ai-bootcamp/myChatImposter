"""
UserLifecycleService: Handles user connection/disconnection lifecycle events.
Extracted from routers/user_management.py to separate business logic from routing.
"""
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from dependencies import GlobalStateManager

from config_models import UserConfiguration


class UserLifecycleService:
    """
    Service that handles user lifecycle events (connection status changes).

    Responsibilities:
    - Moving messages between holding/active queues on connect/disconnect
    - Starting/stopping group tracking jobs
    """

    def __init__(self, global_state: "GlobalStateManager"):
        self.global_state = global_state

    async def on_user_connected(self, user_id: str):
        """
        Handle user connection event.
        - Move queued messages from holding to active
        - Start group tracking jobs if enabled
        """
        # Guard: Skip if user already has active tracking jobs (avoid duplicate setup during reconnects)
        if self.global_state.group_tracker:
            existing_jobs = [
                job for job in self.global_state.group_tracker.scheduler.get_jobs()
                if job.id.startswith(f"{user_id}_")
            ]
            if existing_jobs:
                logging.debug(
                    f"LIFECYCLE: User {user_id} already has {len(existing_jobs)} tracking jobs, "
                    "skipping duplicate setup."
                )
                return

        # 1. Move items to Active Queue
        if self.global_state.async_message_delivery_queue_manager:
            self.global_state.async_message_delivery_queue_manager.move_user_to_active(user_id)
            logging.info(f"LIFECYCLE: User {user_id} connected. Moved items to ACTIVE queue.")

        # 2. Start Group Tracking (Late Binding)
        if self.global_state.group_tracker:
            try:
                # Fetch config to know what to track
                config_dict = await self._get_user_config(user_id)

                if config_dict:
                    config = UserConfiguration.model_validate(config_dict)

                    if config.features.periodic_group_tracking.enabled:
                        self.global_state.group_tracker.update_jobs(
                            user_id,
                            config.features.periodic_group_tracking.tracked_groups,
                            config.configurations.user_details.timezone
                        )
                    else:
                        self.global_state.group_tracker.update_jobs(user_id, [])
            except Exception as e:
                logging.error(f"LIFECYCLE: Failed to start tracking for {user_id}: {e}")
    
    async def on_user_disconnected(self, user_id: str):
        """
        Handle user disconnection event.
        - Stop group tracking jobs (Safe Pause)
        """
        if self.global_state.group_tracker:
            logging.info(f"LIFECYCLE: User {user_id} disconnected. Pausing tracking jobs.")
            self.global_state.group_tracker.stop_tracking_jobs(user_id)
    
    async def _get_user_config(self, user_id: str) -> Optional[dict]:
        """Helper to retrieve user configuration from DB."""
        from fastapi.concurrency import run_in_threadpool
        
        try:
            db_config = await run_in_threadpool(
                self.global_state.configurations_collection.find_one, 
                {"config_data.user_id": user_id}
            )
            
            if not db_config:
                return None
            
            config_data = db_config.get("config_data")
            if isinstance(config_data, dict):
                return config_data
            return None
        except Exception as e:
            logging.error(f"LIFECYCLE: Error retrieving config for {user_id}: {e}")
            return None
    
    def create_status_change_callback(self):
        """
        Returns an async callback function suitable for passing to ChatbotInstance.
        This allows the router to remain thin while this service handles the logic.
        """
        async def callback(uid: str, status: str):
            if status == 'connected':
                await self.on_user_connected(uid)
            elif status == 'disconnected':
                await self.on_user_disconnected(uid)
        return callback
