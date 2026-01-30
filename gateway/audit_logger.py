"""
Security audit logging to MongoDB.
"""

import logging
from datetime import datetime
from typing import Optional, Literal
from motor.motor_asyncio import AsyncIOMotorCollection
from auth_models import AuditLog


class AuditLogger:
    """
    Logs security events to MongoDB with 30-day auto-cleanup via TTL index.

    Event types:
    - login_success: Successful login
    - login_failed: Failed login attempt
    - permission_denied: Access denied (403)
    - logout: User logout
    - account_locked: Account locked due to failed attempts
    - account_unlocked: Account manually unlocked
    """

    def __init__(self, audit_logs_collection: AsyncIOMotorCollection):
        """
        Initialize AuditLogger.

        Args:
            audit_logs_collection: MongoDB collection with 30-day TTL index
        """
        self.collection = audit_logs_collection

    async def log_event(
        self,
        event_type: Literal[
            "login_success",
            "login_failed",
            "permission_denied",
            "logout",
            "account_locked",
            "account_unlocked",
        ],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        """
        Log security event to MongoDB.

        Args:
            event_type: Type of security event
            user_id: User identifier (optional for failed login)
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event-specific details
        """
        audit_log = AuditLog(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )

        await self.collection.insert_one(audit_log.model_dump())

        logging.info(
            f"GATEWAY: Audit log - {event_type} for user {user_id or 'unknown'} "
            f"from IP {ip_address or 'unknown'}"
        )

    async def log_login_success(
        self,
        user_id: str,
        role: str,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log successful login."""
        await self.log_event(
            event_type="login_success",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"role": role, "session_id": session_id},
        )

    async def log_login_failed(
        self,
        user_id: str,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log failed login attempt."""
        await self.log_event(
            event_type="login_failed",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"reason": reason},
        )

    async def log_permission_denied(
        self,
        user_id: str,
        role: str,
        requested_path: str,
        extracted_user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log permission denied (403)."""
        await self.log_event(
            event_type="permission_denied",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "role": role,
                "requested_path": requested_path,
                "extracted_user_id": extracted_user_id,
            },
        )

    async def log_logout(
        self,
        user_id: str,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log user logout."""
        await self.log_event(
            event_type="logout",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"session_id": session_id},
        )

    async def log_account_locked(
        self,
        user_id: str,
        failed_attempts: int,
        locked_until: datetime,
        ip_address: Optional[str] = None,
    ):
        """Log account lockout."""
        await self.log_event(
            event_type="account_locked",
            user_id=user_id,
            ip_address=ip_address,
            details={
                "failed_attempts": failed_attempts,
                "locked_until": locked_until.isoformat(),
            },
        )

    async def log_account_unlocked(
        self,
        user_id: str,
        admin_id: str,
        ip_address: Optional[str] = None,
    ):
        """Log manual account unlock (admin action)."""
        await self.log_event(
            event_type="account_unlocked",
            user_id=user_id,
            ip_address=ip_address,
            details={"unlocked_by": admin_id},
        )
