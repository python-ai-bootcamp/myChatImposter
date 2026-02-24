
import asyncio
import logging
import random
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter

from services.session_manager import SessionManager
from config_models import PeriodicGroupTrackingConfig
from async_message_delivery_queue_manager import AsyncMessageDeliveryQueueManager
from .history_service import GroupHistoryService
from .runner import GroupTrackingRunner
from .extractor import ActionItemExtractor
from .cron_window import CronWindowCalculator

# Initialize logger
logger = logging.getLogger(__name__)

class GroupTracker:
    def __init__(self, db: AsyncIOMotorDatabase, chatbot_instances: Dict[str, SessionManager], token_consumption_collection: AsyncIOMotorCollection, async_message_delivery_queue_manager: AsyncMessageDeliveryQueueManager = None):
        
        # Dependencies
        self.chatbot_instances = chatbot_instances
        self.async_message_delivery_queue_manager = async_message_delivery_queue_manager
        
        # Sub-Services
        self.history = GroupHistoryService(db)
        
        # Instantiate Runner's dependencies (Composition Root)
        extractor = ActionItemExtractor()
        window_calculator = CronWindowCalculator()
        
        self.runner = GroupTrackingRunner(
            chatbot_instances=self.chatbot_instances,
            history_service=self.history,
            queue_manager=self.async_message_delivery_queue_manager,
            extractor=extractor,
            window_calculator=window_calculator,
            token_consumption_collection=token_consumption_collection
        )
        
        # Scheduler
        self.scheduler = AsyncIOScheduler()
        self.jobs = {}

    def start(self):
        self.scheduler.start()
        logger.info("GroupTracker scheduler started.")

    def shutdown(self):
        self.scheduler.shutdown(wait=False)
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

    def stop_tracking_jobs(self, bot_id: str):
        """
        Stops all tracking jobs for a user WITHOUT deleting the data.
        Used for disconnects, reloads, and unlinks.
        """
        all_jobs = self.scheduler.get_jobs()
        prefix = f"{bot_id}_"
        
        for job in all_jobs:
            if job.id.startswith(prefix):
                try:
                    self.scheduler.remove_job(job.id)
                    logger.info(f"Stopped tracking job {job.id} for bot {bot_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove job {job.id}: {e}")
        
        # Sync self.jobs
        keys_to_remove = [k for k in self.jobs if k.startswith(prefix)]
        for k in keys_to_remove:
            del self.jobs[k]

    def update_jobs(self, bot_id: str, tracking_configs: list[PeriodicGroupTrackingConfig], timezone: str = "UTC", owner_user_id: str = None):
        # Remove existing jobs for this user by querying the scheduler directly
        # This ensures we catch any zombie jobs even if self.jobs is out of sync
        all_jobs = self.scheduler.get_jobs()
        prefix = f"{bot_id}_"
        
        for job in all_jobs:
            if job.id.startswith(prefix):
                try:
                    self.scheduler.remove_job(job.id)
                    logger.info(f"Removed tracking job {job.id} for bot {bot_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove job {job.id}: {e}")
        
        # Sync self.jobs (optional, but good for consistency)
        keys_to_remove = [k for k in self.jobs if k.startswith(prefix)]
        for k in keys_to_remove:
            del self.jobs[k]

        # Add new jobs
        for config in tracking_configs:
            job_id = f"{bot_id}_{config.groupIdentifier}"
            try:
                trigger = CronTrigger.from_crontab(config.cronTrackingSchedule, timezone=ZoneInfo(timezone))
                self.scheduler.add_job(
                    self.track_group_context,
                    trigger,
                    id=job_id,
                    args=[bot_id, owner_user_id, config, timezone],
                    replace_existing=True
                )
                self.jobs[job_id] = True
                logger.info(f"Added tracking job {job_id} with schedule {config.cronTrackingSchedule} for bot {bot_id} (owner: {owner_user_id})")
            except Exception as e:
                logger.error(f"Failed to add tracking job {job_id}: {e}")

        # Update provider cache policy
        max_interval = self._calculate_max_interval(tracking_configs)
        target_instance = None
        for instance in self.chatbot_instances.values():
            if instance.bot_id == bot_id:
                target_instance = instance
                break

        if target_instance and target_instance.provider_instance:
            target_instance.provider_instance.update_cache_policy(max_interval)

    async def track_group_context(self, bot_id: str, owner_user_id: str, config: PeriodicGroupTrackingConfig, timezone: str = "UTC"):
        # Delegate to Runner
        await self.runner.run_tracking_cycle(bot_id, owner_user_id, config, timezone)
