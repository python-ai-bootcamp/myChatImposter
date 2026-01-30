"""
Gateway state management and MongoDB connections.
"""

import logging
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection


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
        self.sessions_collection = self.db.get_collection("authenticated_sessions")
        self.stale_sessions_collection = self.db.get_collection(
            "stale_authenticated_sessions"
        )
        self.credentials_collection = self.db.get_collection("user_auth_credentials")
        self.audit_logs_collection = self.db.get_collection("audit_logs")
        self.account_lockouts_collection = self.db.get_collection("account_lockouts")

        # Create indexes
        try:
            # Sessions: unique session_id, index on user_id, TTL on expires_at
            await self.sessions_collection.create_index("session_id", unique=True)
            await self.sessions_collection.create_index("user_id")
            await self.sessions_collection.create_index(
                "expires_at", expireAfterSeconds=0
            )
            logging.info("GATEWAY: Created indexes for authenticated_sessions.")

            # Credentials: unique user_id
            await self.credentials_collection.create_index("user_id", unique=True)
            logging.info("GATEWAY: Created indexes for user_auth_credentials.")

            # Audit logs: TTL (30 days), indexes on user_id and event_type
            await self.audit_logs_collection.create_index(
                "timestamp", expireAfterSeconds=2592000
            )
            await self.audit_logs_collection.create_index("user_id")
            await self.audit_logs_collection.create_index("event_type")
            logging.info("GATEWAY: Created indexes for audit_logs with 30-day TTL.")

            # Account lockouts: unique user_id, index on ip_address, TTL on locked_until
            await self.account_lockouts_collection.create_index(
                "user_id", unique=True, sparse=True
            )
            await self.account_lockouts_collection.create_index("ip_address", sparse=True)
            await self.account_lockouts_collection.create_index(
                "locked_until", expireAfterSeconds=0, sparse=True
            )
            logging.info("GATEWAY: Created indexes for account_lockouts.")
        except Exception as e:
            logging.warning(f"GATEWAY: Could not create indexes: {e}")

        logging.info("GATEWAY: Successfully connected to MongoDB.")

    async def shutdown(self):
        """Cleanup resources on shutdown."""
        if self.mongo_client:
            self.mongo_client.close()
            logging.info("GATEWAY: MongoDB connection closed.")


# Singleton accessor
gateway_state = GatewayStateManager.get_instance()
