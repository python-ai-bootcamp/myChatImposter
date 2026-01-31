"""
Gateway state management and MongoDB connections.
"""

import logging
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from infrastructure import db_schema


class GatewayStateManager:
    """
    Singleton manager for gateway state and MongoDB connections.
    """

    _instance = None

    def __init__(self):
        # MongoDB async client
        self.mongo_client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

        # Authentication collections
        self.sessions_collection: Optional[AsyncIOMotorCollection] = None
        self.stale_sessions_collection: Optional[AsyncIOMotorCollection] = None
        self.credentials_collection: Optional[AsyncIOMotorCollection] = None
        self.audit_logs_collection: Optional[AsyncIOMotorCollection] = None
        self.account_lockouts_collection: Optional[AsyncIOMotorCollection] = None

        # Configuration
        self.backend_url: str = os.getenv("BACKEND_URL", "http://backend:8000")

    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = GatewayStateManager()
        return cls._instance

    async def initialize_mongodb(self, mongodb_url: str):
        """
        Initialize MongoDB connection and create indexes.

        Args:
            mongodb_url: MongoDB connection string
        """
        logging.info(f"GATEWAY: Connecting to MongoDB at {mongodb_url}")
        self.mongo_client = AsyncIOMotorClient(
            mongodb_url, serverSelectionTimeoutMS=5000
        )

        # Test connection
        await self.mongo_client.admin.command("ismaster")

        self.db = self.mongo_client.get_database("chat_manager")
        self.sessions_collection = self.db.get_collection(db_schema.COLLECTION_SESSIONS)
        self.stale_sessions_collection = self.db.get_collection(db_schema.COLLECTION_STALE_SESSIONS)
        self.credentials_collection = self.db.get_collection(db_schema.COLLECTION_CREDENTIALS)
        self.audit_logs_collection = self.db.get_collection(db_schema.COLLECTION_AUDIT_LOGS)
        self.account_lockouts_collection = self.db.get_collection(db_schema.COLLECTION_ACCOUNT_LOCKOUTS)

        # Index creation is handled by the Backend (GlobalStateManager)
        # Gateway assumes schema is already established.
        logging.info("GATEWAY: Successfully connected to MongoDB.")

    async def shutdown(self):
        """Cleanup resources on shutdown."""
        if self.mongo_client:
            self.mongo_client.close()
            logging.info("GATEWAY: MongoDB connection closed.")


# Singleton accessor
gateway_state = GatewayStateManager.get_instance()
