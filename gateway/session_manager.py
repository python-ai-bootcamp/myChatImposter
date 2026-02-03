"""
Session management with MongoDB persistence and in-memory caching.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from motor.motor_asyncio import AsyncIOMotorCollection
from auth_models import SessionData, StaleSession


class SessionManager:
    """
    Manages user sessions with in-memory cache and MongoDB persistence.

    Cache TTL: 5 minutes (sessions accessed frequently stay in cache)
    Session expiration: 24 hours absolute (not sliding)
    """

    def __init__(
        self,
        sessions_collection: AsyncIOMotorCollection,
        stale_sessions_collection: AsyncIOMotorCollection,
    ):
        """
        Initialize SessionManager.

        Args:
            sessions_collection: MongoDB collection for active sessions
            stale_sessions_collection: MongoDB collection for stale/invalidated sessions
        """
        self.sessions_collection = sessions_collection
        self.stale_sessions_collection = stale_sessions_collection

        # In-memory cache: {session_id: (SessionData, cache_timestamp)}
        self.cache: Dict[str, tuple[SessionData, datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)

    def _is_cache_valid(self, cache_timestamp: datetime) -> bool:
        """Check if cache entry is still valid."""
        return datetime.utcnow() - cache_timestamp < self.cache_ttl

    async def create_session(
        self,
        user_id: str,
        role: str,
        owned_user_configurations: List[str] = [],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> SessionData:
        """
        Create new session in DB and cache.

        Args:
            user_id: User identifier
            role: User role (admin or user)
            ip_address: Optional client IP
            user_agent: Optional client user agent

        Returns:
            Created SessionData
        """
        now = datetime.utcnow()
        session_id = str(uuid.uuid4())

        session = SessionData(
            session_id=session_id,
            user_id=user_id,
            role=role,
            owned_user_configurations=owned_user_configurations,
            created_at=now,
            last_accessed=now,
            expires_at=now + timedelta(hours=24),  # 24h absolute expiration
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Insert into MongoDB
        await self.sessions_collection.insert_one(session.model_dump())

        # Add to cache
        self.cache[session_id] = (session, now)

        logging.info(f"GATEWAY: Created session {session_id} for user {user_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Retrieve session from cache or DB.

        Args:
            session_id: Session identifier

        Returns:
            SessionData if found and valid, None otherwise
        """
        # Check cache first
        if session_id in self.cache:
            session, cache_timestamp = self.cache[session_id]
            if self._is_cache_valid(cache_timestamp):
                # Check if session expired
                if datetime.utcnow() < session.expires_at:
                    return session
                else:
                    # Session expired, remove from cache
                    del self.cache[session_id]
                    logging.info(f"GATEWAY: Session {session_id} expired (from cache)")
                    return None

        # Fallback to DB
        doc = await self.sessions_collection.find_one({"session_id": session_id})
        if doc:
            doc.pop("_id", None)
            session = SessionData(**doc)

            # Check if expired
            if datetime.utcnow() < session.expires_at:
                # Add to cache
                self.cache[session_id] = (session, datetime.utcnow())
                return session
            else:
                logging.info(f"GATEWAY: Session {session_id} expired (from DB)")
                return None

        return None

    async def update_last_accessed(self, session_id: str) -> bool:
        """
        Update last_accessed timestamp for heartbeat tracking.
        Does NOT extend expiration (24h absolute expiration).

        Args:
            session_id: Session identifier

        Returns:
            True if updated successfully, False otherwise
        """
        now = datetime.utcnow()

        # Update in DB
        result = await self.sessions_collection.update_one(
            {"session_id": session_id}, {"$set": {"last_accessed": now}}
        )

        # Update in cache if present
        if session_id in self.cache:
            session, cache_timestamp = self.cache[session_id]
            session.last_accessed = now
            self.cache[session_id] = (session, cache_timestamp)

        return result.modified_count > 0

    async def invalidate_session(
        self, session_id: str, reason: str = "logout"
    ) -> bool:
        """
        Invalidate session, move to stale collection, and remove from cache.

        Args:
            session_id: Session identifier
            reason: Reason for invalidation (logout, expired, etc.)

        Returns:
            True if invalidated successfully, False otherwise
        """
        # Get session before deletion
        session = await self.get_session(session_id)
        if not session:
            return False

        # Create stale session record
        stale = StaleSession(
            session_id=session.session_id,
            user_id=session.user_id,
            role=session.role,
            created_at=session.created_at,
            last_accessed=session.last_accessed,
            expires_at=session.expires_at,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
            invalidated_at=datetime.utcnow(),
            reason=reason,
        )

        # Move to stale collection
        await self.stale_sessions_collection.insert_one(stale.model_dump())

        # Delete from active sessions
        await self.sessions_collection.delete_one({"session_id": session_id})

        # Remove from cache
        if session_id in self.cache:
            del self.cache[session_id]

        logging.info(
            f"GATEWAY: Invalidated session {session_id} for user {session.user_id} (reason: {reason})"
        )
        return True

    async def get_user_sessions(self, user_id: str) -> list[SessionData]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of active SessionData for the user
        """
        cursor = self.sessions_collection.find({"user_id": user_id})
        sessions = []

        async for doc in cursor:
            doc.pop("_id", None)
            session = SessionData(**doc)
            # Only return non-expired sessions
            if datetime.utcnow() < session.expires_at:
                sessions.append(session)

        return sessions

    async def invalidate_all_user_sessions(self, user_id: str, reason: str = "logout_all") -> int:
        """
        Invalidate all sessions for a user.

        Args:
            user_id: User identifier
            reason: Reason for invalidation

        Returns:
            Number of sessions invalidated
        """
        sessions = await self.get_user_sessions(user_id)
        count = 0

        for session in sessions:
            if await self.invalidate_session(session.session_id, reason):
                count += 1

        return count

    async def add_owned_configuration(self, session_id: str, config_id: str) -> bool:
        """
        Update session with new owned configuration (DB + Cache).
        """
        # Update DB
        await self.sessions_collection.update_one(
            {"session_id": session_id},
            {"$addToSet": {"owned_user_configurations": config_id}}
        )

        # Update Cache
        if session_id in self.cache:
            session, timestamp = self.cache[session_id]
            if config_id not in session.owned_user_configurations:
                session.owned_user_configurations.append(config_id)
                self.cache[session_id] = (session, timestamp)
        
        return True

    def clear_cache(self):
        """Clear in-memory cache (useful for testing)."""
        self.cache.clear()
        logging.info("GATEWAY: Session cache cleared")

