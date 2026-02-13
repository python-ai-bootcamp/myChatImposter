import logging
import os
from typing import Dict, Optional, TYPE_CHECKING
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from infrastructure import db_schema

if TYPE_CHECKING:
    from services.session_manager import SessionManager
    from features.periodic_group_tracking.service import GroupTracker
    from async_message_delivery_queue_manager import AsyncMessageDeliveryQueueManager
    from services.bot_lifecycle_service import BotLifecycleService

class GlobalStateManager:
    _instance = None

    def __init__(self):
        # MongoDB
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.configurations_collection: Optional[AsyncIOMotorCollection] = None
        self.queues_collection: Optional[AsyncIOMotorCollection] = None
        self.baileys_sessions_collection: Optional[AsyncIOMotorCollection] = None

        # Authentication collections
        self.sessions_collection: Optional[AsyncIOMotorCollection] = None
        self.stale_sessions_collection: Optional[AsyncIOMotorCollection] = None
        self.credentials_collection: Optional[AsyncIOMotorCollection] = None
        self.audit_logs_collection: Optional[AsyncIOMotorCollection] = None
        self.account_lockouts_collection: Optional[AsyncIOMotorCollection] = None
        
        # Telemetry
        self.token_consumption_collection: Optional[AsyncIOMotorCollection] = None

        # State storage
        self.chatbot_instances: Dict[str, 'SessionManager'] = {}
        self.active_bots: Dict[str, str] = {}  # Maps bot_id to instance_id
        
        # Managers
        self.group_tracker: Optional['GroupTracker'] = None
        self.async_message_delivery_queue_manager: Optional['AsyncMessageDeliveryQueueManager'] = None
        self.bot_lifecycle_service: Optional['BotLifecycleService'] = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = GlobalStateManager()
        return cls._instance

    async def initialize_mongodb(self, mongodb_url: str):
        logging.info(f"API: Connecting to MongoDB at {mongodb_url}")
        self.mongo_client = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=5000)
        # Force connection check
        await self.mongo_client.admin.command('ismaster')
        
        self.db = self.mongo_client.get_database("chat_manager")
        self.configurations_collection = self.db.get_collection(db_schema.COLLECTION_BOT_CONFIGURATIONS)
        self.queues_collection = self.db.get_collection(db_schema.COLLECTION_QUEUES)
        self.baileys_sessions_collection = self.db.get_collection(db_schema.COLLECTION_BAILEYS_SESSIONS)

        # Authentication collections
        self.sessions_collection = self.db.get_collection(db_schema.COLLECTION_SESSIONS)
        self.stale_sessions_collection = self.db.get_collection(db_schema.COLLECTION_STALE_SESSIONS)
        self.credentials_collection = self.db.get_collection(db_schema.COLLECTION_CREDENTIALS)
        self.audit_logs_collection = self.db.get_collection(db_schema.COLLECTION_AUDIT_LOGS)
        self.account_lockouts_collection = self.db.get_collection(db_schema.COLLECTION_ACCOUNT_LOCKOUTS)

        # Telemetry
        self.token_consumption_collection = self.db.get_collection(db_schema.COLLECTION_TOKEN_CONSUMPTION)

        # Ensure indexes (Centralized)
        await db_schema.create_indexes(self.db)

        logging.info("API: Successfully connected to MongoDB.")

    def get_chatbot_instance_by_bot(self, bot_id: str) -> Optional['SessionManager']:
        if bot_id in self.active_bots:
            instance_id = self.active_bots[bot_id]
            return self.chatbot_instances.get(instance_id)
        return None

    def remove_active_bot(self, bot_id: str):
        """Callback to remove a bot from the active list and clean up instance."""
        if bot_id in self.active_bots:
            instance_id = self.active_bots[bot_id]
            logging.info(f"API: Session ended for bot '{bot_id}'. Removing from active list.")
            del self.active_bots[bot_id]
            if instance_id in self.chatbot_instances:
                del self.chatbot_instances[instance_id]
        else:
            logging.warning(f"API: Tried to remove non-existent bot '{bot_id}' from active list.")

    def shutdown(self):
        """Cleanup resources on shutdown."""
        if self.group_tracker:
            self.group_tracker.shutdown()
        
        # Note: ActionableQueueManager shutdown is async, might need handling in main loop or here if we make this async
        # For now, we'll expose the manager to be stopped by the async shutdown event in main

        if self.mongo_client:
            self.mongo_client.close()
            logging.info("API: MongoDB connection closed.")

# Singleton accessor
global_state = GlobalStateManager.get_instance()

def get_global_state() -> GlobalStateManager:
    """FastAPI Dependency to get the global state manager."""
    return GlobalStateManager.get_instance()
