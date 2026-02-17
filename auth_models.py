"""
Authentication and authorization data models.

This module defines Pydantic models for user authentication, session management,
audit logging, and account lockout functionality.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
import re


class UserAuthCredentials(BaseModel):
    """
    User authentication credentials stored in MongoDB.

    Attributes:
        user_id: Unique user identifier (alphanumeric, underscore, hyphen only)
        password_hash: Bcrypt hashed password with salt (12 rounds)
        role: User role (admin or user)
    """
    user_id: str = Field(..., description="Unique user identifier")
    password_hash: str = Field(..., description="Bcrypt hashed password")
    role: Literal["admin", "user"] = Field(..., description="User role")
    owned_bots: list[str] = Field(default_factory=list, description="List of bot_ids this user owns")
    max_user_configuration_limit: int = Field(default=5, description="Max number of owned configurations")
    max_feature_limit: int = Field(default=5, description="Max number of enabled features per configuration")
    
    # New Fields
    first_name: str = Field(default="Unknown", description="User first name")
    last_name: str = Field(default="User", description="User last name")
    phone_number: str = Field(default="", description="User phone number (E.164)")
    email: str = Field(default="", description="User email address")
    gov_id: str = Field(default="", description="Government ID")
    country_value: str = Field(default="US", description="Country code (ISO 3166-1 alpha-2)")
    language: str = Field(default="en", description="Language code (ISO 639-1)")

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id contains only alphanumeric, underscore, or hyphen."""
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "user_id must contain only alphanumeric characters, underscores, or hyphens"
            )
        return v

class UserResponse(BaseModel):
    """
    User details returned to API clients (excludes password_hash).
    """
    user_id: str = Field(..., description="Unique user identifier")
    role: Literal["admin", "user"] = Field(..., description="User role")
    owned_bots: list[str] = Field(default_factory=list, description="List of bot_ids this user owns")
    max_user_configuration_limit: int = Field(default=5, description="Max number of owned configurations")
    max_feature_limit: int = Field(default=5, description="Max number of enabled features per configuration")
    
    first_name: str = Field(default="Unknown", description="User first name")
    last_name: str = Field(default="User", description="User last name")
    phone_number: str = Field(default="", description="User phone number (E.164)")
    email: str = Field(default="", description="User email address")
    gov_id: str = Field(default="", description="Government ID")
    country_value: str = Field(default="US", description="Country code (ISO 3166-1 alpha-2)")
    language: str = Field(default="en", description="Language code (ISO 639-1)")

class UserRestrictedResponse(BaseModel):
    """
    Restricted user details for non-admins (excludes role and limits).
    """
    user_id: str = Field(..., description="Unique user identifier")
    # Exclude role, limits
    owned_bots: list[str] = Field(default_factory=list, description="List of bot_ids this user owns")
    
    first_name: str = Field(default="Unknown", description="User first name")
    last_name: str = Field(default="User", description="User last name")
    phone_number: str = Field(default="", description="User phone number (E.164)")
    email: str = Field(default="", description="User email address")
    gov_id: str = Field(default="", description="Government ID")
    country_value: str = Field(default="US", description="Country code (ISO 3166-1 alpha-2)")
    language: str = Field(default="en", description="Language code (ISO 639-1)")

class SessionData(BaseModel):
    """
    Active user session data.

    Attributes:
        session_id: UUID4 session identifier
        user_id: Associated user identifier
        role: User role for permission checks
        created_at: Session creation timestamp
        last_accessed: Last activity timestamp (for heartbeat tracking)
        expires_at: Absolute expiration (24h from creation)
        ip_address: Optional client IP address for audit
        user_agent: Optional client user agent for audit
        max_user_configuration_limit: Max number of owned configurations
        max_feature_limit: Max number of enabled features per configuration
    """
    session_id: str = Field(..., description="UUID4 session identifier")
    user_id: str = Field(..., description="Associated user identifier")
    role: Literal["admin", "user"] = Field(..., description="User role")
    owned_bots: list[str] = Field(default_factory=list, description="List of bot_ids this user owns")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_accessed: datetime = Field(..., description="Last activity timestamp")
    expires_at: datetime = Field(..., description="Session expiration (24h absolute)")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    max_user_configuration_limit: int = Field(default=5, description="Max number of owned configurations")
    max_feature_limit: int = Field(default=5, description="Max number of enabled features per configuration")


class StaleSession(BaseModel):
    """
    Stale/invalidated session moved to archive collection.
    Inherits all fields from SessionData plus invalidation metadata.
    """
    session_id: str
    user_id: str
    role: Literal["admin", "user"]
    owned_bots: list[str] = Field(default_factory=list, description="List of bot_ids this user owns")
    created_at: datetime
    last_accessed: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    invalidated_at: datetime = Field(..., description="When session was invalidated")
    reason: str = Field(..., description="Reason for invalidation (logout, expired, etc.)")


class LoginRequest(BaseModel):
    """
    Login request payload.

    Attributes:
        user_id: User identifier
        password: Plain text password (will be hashed for comparison)
    """
    user_id: str = Field(..., description="User identifier")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    """
    Login response payload.

    Attributes:
        success: Whether login was successful
        message: Human-readable message
        user_id: User identifier (only on success)
        role: User role (only on success)
        session_id: Session identifier (only on success, for debugging)
        first_name: User first name
        last_name: User last name
        language_code: User language code
    """
    success: bool = Field(..., description="Login success status")
    message: str = Field(..., description="Response message")
    user_id: Optional[str] = Field(None, description="User identifier")
    role: Optional[Literal["admin", "user"]] = Field(None, description="User role")
    session_id: Optional[str] = Field(None, description="Session identifier")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    language_code: Optional[str] = Field(None, description="User language code")


class AuditLog(BaseModel):
    """
    Security audit log entry.

    Attributes:
        timestamp: Event timestamp
        event_type: Type of security event
        user_id: Associated user (optional, e.g., failed login may not have valid user)
        ip_address: Client IP address
        user_agent: Client user agent
        details: Additional event-specific details
    """
    timestamp: datetime = Field(..., description="Event timestamp")
    event_type: Literal[
        "login_success",
        "login_failed",
        "permission_denied",
        "logout",
        "account_locked",
        "account_unlocked",
        "user_created",
        "user_updated",
        "user_updated_full",
        "user_deleted",
        "password_reset"
    ] = Field(..., description="Security event type")
    user_id: Optional[str] = Field(None, description="Associated user identifier")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    details: dict = Field(default_factory=dict, description="Event-specific details")


class AccountLockout(BaseModel):
    """
    Account lockout tracking for failed login attempts.

    Attributes:
        user_id: User identifier being tracked
        ip_address: Optional IP address tracking (for IP-based lockout)
        failed_attempts: Number of failed attempts
        locked_until: When lockout expires (null if not locked)
        last_attempt: Timestamp of most recent failed attempt
    """
    user_id: Optional[str] = Field(None, description="User identifier")
    ip_address: Optional[str] = Field(None, description="IP address")
    failed_attempts: int = Field(0, description="Number of failed login attempts")
    locked_until: Optional[datetime] = Field(None, description="Lockout expiration timestamp")
    last_attempt: datetime = Field(..., description="Most recent failed attempt timestamp")
