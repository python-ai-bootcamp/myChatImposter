import logging
import os
from typing import Dict, Optional, TYPE_CHECKING
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

if TYPE_CHECKING:
    from chatbot_manager import ChatbotInstance
    from group_tracker import GroupTracker
    from async_message_delivery_queue_manager import AsyncMessageDeliveryQueueManager

class GlobalStateManager:
    _instance = None

    def __init__(self):
        # MongoDB
        self.mongo_client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.configurations_collection: Optional[Collection] = None
        self.queues_collection: Optional[Collection] = None
        self.baileys_sessions_collection: Optional[Collection] = None

        # State storage
        self.chatbot_instances: Dict[str, 'ChatbotInstance'] = {}
        self.active_users: Dict[str, str] = {}  # Maps user_id to instance_id
        
        # Managers
        self.group_tracker: Optional['GroupTracker'] = None
        self.async_message_delivery_queue_manager: Optional['AsyncMessageDeliveryQueueManager'] = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = GlobalStateManager()
        return cls._instance

    def initialize_mongodb(self, mongodb_url: str):
        logging.info(f"API: Connecting to MongoDB at {mongodb_url}")
        self.mongo_client = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
        # Force connection check
        self.mongo_client.admin.command('ismaster')
        
        self.db = self.mongo_client.get_database("chat_manager")
        self.configurations_collection = self.db.get_collection("configurations")
        self.queues_collection = self.db.get_collection("queues")
        self.baileys_sessions_collection = self.db.get_collection("baileys_sessions")
        
        # Ensure indexes
        try:
            self.configurations_collection.create_index("config_data.user_id", unique=True)
            logging.info("API: Ensured unique index exists for 'config_data.user_id'.")
        except Exception as e:
            logging.warning(f"API: Could not create unique index: {e}")

        logging.info("API: Successfully connected to MongoDB.")

    def get_chatbot_instance_by_user(self, user_id: str) -> Optional['ChatbotInstance']:
        if user_id in self.active_users:
            instance_id = self.active_users[user_id]
            return self.chatbot_instances.get(instance_id)
        return None

    def remove_active_user(self, user_id: str):
        """Callback to remove a user from the active list and clean up instance."""
        if user_id in self.active_users:
            instance_id = self.active_users[user_id]
            logging.info(f"API: Session ended for user '{user_id}'. Removing from active list.")
            del self.active_users[user_id]
            if instance_id in self.chatbot_instances:
                del self.chatbot_instances[instance_id]
        else:
            logging.warning(f"API: Tried to remove non-existent user '{user_id}' from active list.")

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
