import asyncio
import logging
from dataclasses import asdict
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorCollection

from queue_manager import Message
from services.session_manager import SessionManager

class IngestionService:
    """
    Background service that archives messages from User Queues to MongoDB.
    """
    def __init__(self, session_manager: SessionManager, queues_collection: AsyncIOMotorCollection):
        self.session_manager = session_manager
        self.bot_id = session_manager.bot_id
        # We need provider name, likely available in session_manager.provider_instance?
        # Or from config. 
        # Using config is safer as provider instance might be re-initialized? 
        # But session_manager holds the config too.
        self.provider_name = session_manager.config.configurations.chat_provider_config.provider_name
        self.queues_collection = queues_collection
        self.main_loop = session_manager.main_loop
        
        self._stop_event = asyncio.Event()
        self._task = None

    async def _run(self):
        """The main async loop for the ingester."""
        logging.info(f"INGESTION ({self.bot_id}): Starting up.")
        while not self._stop_event.is_set():
            any_message_processed = False
            
            # Access queues via SessionManager
            if not self.session_manager.user_queues_manager:
                 # Should not happen if session started
                 await asyncio.sleep(1)
                 continue

            all_queues = self.session_manager.user_queues_manager.get_all_queues()

            for queue in all_queues:
                while True:
                    message = queue.pop_message()
                    if not message:
                        break

                    any_message_processed = True
                    try:
                        message_doc = asdict(message)
                        message_doc['bot_id'] = self.bot_id
                        message_doc['provider_name'] = self.provider_name
                        message_doc['correspondent_id'] = queue.correspondent_id

                        # Run the blocking DB call in a separate thread
                        await self.queues_collection.insert_one(message_doc)

                        logging.info(f"INGESTION ({self.bot_id}/{queue.correspondent_id}): Persisted message {message.id}.")
                    except Exception as e:
                        logging.error(f"INGESTION ({self.bot_id}/{queue.correspondent_id}): Failed to save message {message.id}: {e}")

            if not any_message_processed:
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass

        logging.info(f"INGESTION ({self.bot_id}): Shutting down.")

    def start(self):
        """Starts the ingester task."""
        if not self._task and self.main_loop:
            self._task = self.main_loop.create_task(self._run())

    async def stop(self):
        """Signals the ingester task to stop and waits for it to finish."""
        if self._task:
            self._stop_event.set()
            await self._task
            self._task = None
