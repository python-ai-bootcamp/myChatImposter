"""
User authentication service.

Handles password hashing, validation, and credential management using bcrypt.
"""

import bcrypt
import re
from typing import Optional, Tuple, List
from motor.motor_asyncio import AsyncIOMotorCollection
from auth_models import UserAuthCredentials


class UserAuthService:
    """
    Service for managing user authentication credentials and password validation.

    Uses bcrypt for password hashing with 12 rounds (2^12 iterations).
    """

    def __init__(self, credentials_collection: AsyncIOMotorCollection):
        """
        Initialize UserAuthService.

        Args:
            credentials_collection: MongoDB collection for storing credentials
        """
        self.credentials_collection = credentials_collection

    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password meets security requirements.

        Rules:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character/symbol

        Args:
            password: Plain text password to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if password meets all requirements
            - error_message: Empty string if valid, descriptive error if not
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"

        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"

        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password):
            return False, "Password must contain at least one special character/symbol"

        return True, ""

    @staticmethod
    def validate_user_id_safety(user_id: str) -> Tuple[bool, str]:
        """
        Validate user_id is safe (no path traversal or injection attacks).

        Args:
            user_id: User identifier to validate

        Returns:
            Tuple of (is_safe, error_message)
        """
        # Check for path traversal attempts
        if ".." in user_id or "/" in user_id or "\\" in user_id:
            return False, "user_id contains invalid path characters"

        # Must match alphanumeric, underscore, hyphen only
        if not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
            return False, "user_id must contain only alphanumeric characters, underscores, or hyphens"

        return True, ""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt with 12 rounds.

        Args:
            password: Plain text password

        Returns:
            Bcrypt hashed password (includes salt)
        """
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)
        return password_hash.decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify password against bcrypt hash.

        Args:
            password: Plain text password
            password_hash: Bcrypt hashed password

        Returns:
            True if password matches hash, False otherwise
        """
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    async def create_credentials(
        self, user_id: str, password: str, role: str
    ) -> Tuple[bool, str]:
        """
        Create new user credentials after validation.

        Args:
            user_id: User identifier
            password: Plain text password
            role: User role ("admin" or "user")

        Returns:
            Tuple of (success, message)
        """
        # Validate user_id safety
        is_safe, error_msg = self.validate_user_id_safety(user_id)
        if not is_safe:
            return False, error_msg

        # Validate password strength
        is_valid, error_msg = self.validate_password_strength(password)
        if not is_valid:
            return False, error_msg

        # Check if user already exists
        existing = await self.credentials_collection.find_one({"user_id": user_id})
        if existing:
            return False, f"User '{user_id}' already exists"

        # Hash password and create credentials
        password_hash = self.hash_password(password)
        credentials = UserAuthCredentials(
            user_id=user_id, password_hash=password_hash, role=role
        )

        # Insert into MongoDB
        await self.credentials_collection.insert_one(credentials.model_dump())
        return True, f"User '{user_id}' created successfully"

    async def get_credentials(self, user_id: str) -> Optional[UserAuthCredentials]:
        """
        Retrieve user credentials by user_id.

        Args:
            user_id: User identifier

        Returns:
            UserAuthCredentials if found, None otherwise
        """
        doc = await self.credentials_collection.find_one({"user_id": user_id})
        if doc:
            # Remove MongoDB's _id field
            doc.pop("_id", None)
            return UserAuthCredentials(**doc)
        return None

    async def update_password(
        self, user_id: str, new_password: str
    ) -> Tuple[bool, str]:
        """
        Update user password after validation.

        Args:
            user_id: User identifier
            new_password: New plain text password

        Returns:
            Tuple of (success, message)
        """
        # Validate password strength
        is_valid, error_msg = self.validate_password_strength(new_password)
        if not is_valid:
            return False, error_msg

        # Check if user exists
        existing = await self.credentials_collection.find_one({"user_id": user_id})
        if not existing:
            return False, f"User '{user_id}' not found"

        # Hash new password and update
        password_hash = self.hash_password(new_password)
        result = await self.credentials_collection.update_one(
            {"user_id": user_id}, {"$set": {"password_hash": password_hash}}
        )

        if result.modified_count > 0:
            return True, "Password updated successfully"
        return False, "Password update failed"

    async def delete_credentials(self, user_id: str) -> Tuple[bool, str]:
        """
        Delete user credentials.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (success, message)
        """
        result = await self.credentials_collection.delete_one({"user_id": user_id})
        if result.deleted_count > 0:
            return True, f"User '{user_id}' deleted successfully"
        return False, f"User '{user_id}' not found"

    async def authenticate(self, user_id: str, password: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Authenticate user credentials.

        Args:
            user_id: User identifier
            password: Plain text password

        Returns:
            Tuple of (success, role, owned_user_configurations)
            - success: True if authentication successful
            - role: User role if successful, None otherwise
            - owned_user_configurations: List of owned configurations if successful, empty list otherwise
        """
        credentials = await self.get_credentials(user_id)
        if not credentials:
            return False, None, []

        if self.verify_password(password, credentials.password_hash):
            return True, credentials.role, credentials.owned_user_configurations if hasattr(credentials, 'owned_user_configurations') else []

        return False, None, []

    async def add_owned_configuration(self, user_id: str, config_id: str) -> bool:
        """
        Add a configuration ID to the user's owned list.
        Atomic update to prevent race conditions.
        """
        result = await self.credentials_collection.update_one(
            {"user_id": user_id},
            {"$addToSet": {"owned_user_configurations": config_id}}
        )
        return result.modified_count > 0 or result.matched_count > 0

