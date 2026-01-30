"""
Account lockout management for failed login attempts.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from motor.motor_asyncio import AsyncIOMotorCollection
from auth_models import AccountLockout


class AccountLockoutManager:
    """
    Manages account lockouts for failed login attempts.

    Rules:
    - 10 failed attempts within 10 minutes = 5 minute lockout
    - MongoDB persistence + in-memory cache
    - Automatic unlock after lockout expires
    """

    def __init__(
        self,
        account_lockouts_collection: AsyncIOMotorCollection,
        max_attempts: int = 10,
        attempt_window_minutes: int = 10,
        lockout_duration_minutes: int = 5,
    ):
        """
        Initialize AccountLockoutManager.

        Args:
            account_lockouts_collection: MongoDB collection for lockout data
            max_attempts: Maximum failed attempts before lockout (default 10)
            attempt_window_minutes: Time window for counting attempts (default 10)
            lockout_duration_minutes: Lockout duration (default 5)
        """
        self.collection = account_lockouts_collection
        self.max_attempts = max_attempts
        self.attempt_window = timedelta(minutes=attempt_window_minutes)
        self.lockout_duration = timedelta(minutes=lockout_duration_minutes)

        # In-memory cache: {user_id: (AccountLockout, cache_timestamp)}
        self.cache: Dict[str, tuple[AccountLockout, datetime]] = {}
        self.cache_ttl = timedelta(minutes=2)

    def _is_cache_valid(self, cache_timestamp: datetime) -> bool:
        """Check if cache entry is still valid."""
        return datetime.utcnow() - cache_timestamp < self.cache_ttl

    async def _get_lockout_record(self, user_id: str) -> Optional[AccountLockout]:
        """Get lockout record from cache or DB."""
        # Check cache
        if user_id in self.cache:
            lockout, cache_timestamp = self.cache[user_id]
            if self._is_cache_valid(cache_timestamp):
                return lockout

        # Fallback to DB
        doc = await self.collection.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            lockout = AccountLockout(**doc)
            # Add to cache
            self.cache[user_id] = (lockout, datetime.utcnow())
            return lockout

        return None

    async def check_lockout(self, user_id: str) -> Tuple[bool, Optional[datetime]]:
        """
        Check if user account is locked out.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (is_locked, locked_until)
            - is_locked: True if account is locked
            - locked_until: Lockout expiration time (None if not locked)
        """
        lockout = await self._get_lockout_record(user_id)

        if not lockout:
            return False, None

        now = datetime.utcnow()

        # Check if lockout expired
        if lockout.locked_until and lockout.locked_until > now:
            logging.warning(
                f"GATEWAY: Account {user_id} is locked until {lockout.locked_until}"
            )
            return True, lockout.locked_until

        # Check if we need to reset old attempts (outside attempt window)
        if lockout.last_attempt and (now - lockout.last_attempt) > self.attempt_window:
            # Reset attempt counter
            await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"failed_attempts": 0, "locked_until": None}},
            )
            # Update cache
            if user_id in self.cache:
                del self.cache[user_id]
            return False, None

        return False, None

    async def record_failed_attempt(self, user_id: str) -> Tuple[bool, Optional[datetime]]:
        """
        Record failed login attempt and potentially lock account.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (is_now_locked, locked_until)
            - is_now_locked: True if account was just locked
            - locked_until: Lockout expiration time (None if not locked)
        """
        now = datetime.utcnow()
        lockout = await self._get_lockout_record(user_id)

        if lockout:
            # Check if attempts are within window
            if (now - lockout.last_attempt) > self.attempt_window:
                # Reset counter - attempts too old
                new_attempts = 1
            else:
                new_attempts = lockout.failed_attempts + 1

            # Check if should lock account
            locked_until = None
            if new_attempts >= self.max_attempts:
                locked_until = now + self.lockout_duration
                logging.warning(
                    f"GATEWAY: Locking account {user_id} until {locked_until} "
                    f"({new_attempts} failed attempts)"
                )

            # Update existing record
            await self.collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "failed_attempts": new_attempts,
                        "last_attempt": now,
                        "locked_until": locked_until,
                    }
                },
            )

            # Update cache
            if user_id in self.cache:
                del self.cache[user_id]

            return locked_until is not None, locked_until
        else:
            # Create new lockout record
            new_lockout = AccountLockout(
                user_id=user_id,
                ip_address=None,
                failed_attempts=1,
                locked_until=None,
                last_attempt=now,
            )

            await self.collection.insert_one(new_lockout.model_dump())

            # Add to cache
            self.cache[user_id] = (new_lockout, now)

            logging.debug(f"GATEWAY: Recorded first failed attempt for {user_id}")
            return False, None

    async def clear_lockout(self, user_id: str):
        """
        Clear lockout after successful login.

        Args:
            user_id: User identifier
        """
        await self.collection.delete_one({"user_id": user_id})

        # Remove from cache
        if user_id in self.cache:
            del self.cache[user_id]

        logging.info(f"GATEWAY: Cleared lockout for {user_id}")

    async def unlock_account(self, user_id: str):
        """
        Manually unlock account (admin action).

        Args:
            user_id: User identifier
        """
        await self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"failed_attempts": 0, "locked_until": None}},
        )

        # Remove from cache
        if user_id in self.cache:
            del self.cache[user_id]

        logging.info(f"GATEWAY: Manually unlocked account {user_id}")

    def clear_cache(self):
        """Clear in-memory cache (useful for testing)."""
        self.cache.clear()
        logging.info("GATEWAY: Account lockout cache cleared")
