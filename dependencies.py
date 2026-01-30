import logging
import os
from typing import Dict, Optional, TYPE_CHECKING
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

if TYPE_CHECKING:
    from services.session_manager import SessionManager
    from features.periodic_group_tracking.service import GroupTracker
    from async_message_delivery_queue_manager import AsyncMessageDeliveryQueueManager
    from services.user_lifecycle_service import UserLifecycleService

class GlobalStateManager:
    _instance = None

    def __init__(self):
        # MongoDB
        self.mongo_client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.configurations_collection: Optional[Collection] = None
        self.queues_collection: Optional[Collection] = None
        self.baileys_sessions_collection: Optional[Collection] = None

        # Authentication collections
        self.sessions_collection: Optional[Collection] = None
        self.stale_sessions_collection: Optional[Collection] = None
        self.credentials_collection: Optional[Collection] = None
        self.audit_logs_collection: Optional[Collection] = None
        self.account_lockouts_collection: Optional[Collection] = None

        # State storage
        self.chatbot_instances: Dict[str, 'SessionManager'] = {}
        self.active_users: Dict[str, str] = {}  # Maps user_id to instance_id
        
        # Managers
        self.group_tracker: Optional['GroupTracker'] = None
        self.async_message_delivery_queue_manager: Optional['AsyncMessageDeliveryQueueManager'] = None
        self.user_lifecycle_service: Optional['UserLifecycleService'] = None

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

        # Authentication collections
        self.sessions_collection = self.db.get_collection("authenticated_sessions")
        self.stale_sessions_collection = self.db.get_collection("stale_authenticated_sessions")
        self.credentials_collection = self.db.get_collection("user_auth_credentials")
        self.audit_logs_collection = self.db.get_collection("audit_logs")
        self.account_lockouts_collection = self.db.get_collection("account_lockouts")

        # Ensure indexes
        try:
            self.configurations_collection.create_index("config_data.user_id", unique=True)
            logging.info("API: Ensured unique index exists for 'config_data.user_id'.")
        except Exception as e:
            logging.warning(f"API: Could not create unique index: {e}")

        # Authentication indexes
        try:
            # Sessions: unique session_id, index on user_id, TTL on expires_at
            self.sessions_collection.create_index("session_id", unique=True)
            self.sessions_collection.create_index("user_id")
            self.sessions_collection.create_index("expires_at", expireAfterSeconds=0)
            logging.info("API: Created indexes for authenticated_sessions collection.")

            # Credentials: unique user_id
            self.credentials_collection.create_index("user_id", unique=True)
            logging.info("API: Created unique index for user_auth_credentials collection.")

            # Audit logs: TTL index (30 days = 2592000 seconds), indexes on user_id and event_type
            self.audit_logs_collection.create_index("timestamp", expireAfterSeconds=2592000)
            self.audit_logs_collection.create_index("user_id")
            self.audit_logs_collection.create_index("event_type")
            logging.info("API: Created indexes for audit_logs collection with 30-day TTL.")

            # Account lockouts: unique user_id, index on ip_address, TTL on locked_until
            self.account_lockouts_collection.create_index("user_id", unique=True, sparse=True)
            self.account_lockouts_collection.create_index("ip_address", sparse=True)
            self.account_lockouts_collection.create_index("locked_until", expireAfterSeconds=0, sparse=True)
            logging.info("API: Created indexes for account_lockouts collection.")
        except Exception as e:
            logging.warning(f"API: Could not create authentication indexes: {e}")

        logging.info("API: Successfully connected to MongoDB.")

    def get_chatbot_instance_by_user(self, user_id: str) -> Optional['SessionManager']:
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
