"""
Permission validation and user_id extraction from request paths.
"""

import re
import logging
from typing import Optional, Tuple


class PermissionValidator:
    """
    Validates permissions based on user role and path user_id ownership.

    Rules:
    - Admin: Bypass all checks, access any resource
    - User: Can only access resources where extracted user_id matches session user_id
    - Paths without user_id: Admin-only
    """

    # Regex patterns for extracting user_id from paths
    USER_ID_PATTERNS = [
        r"/api/external/users/(?P<user_id>[^/]+)",  # /api/external/users/{user_id}
        r"/api/external/features/.*/(?P<user_id>[^/]+)",  # /api/external/features/.../.../{user_id}
    ]

    @staticmethod
    def validate_user_id_safety(user_id: str) -> bool:
        """
        Validate user_id is safe (no path traversal).

        Args:
            user_id: User identifier from path

        Returns:
            True if safe, False otherwise
        """
        # Reject path traversal attempts
        if ".." in user_id or "/" in user_id or "\\" in user_id:
            logging.warning(f"GATEWAY: Rejected unsafe user_id: {user_id}")
            return False

        # Must match alphanumeric, underscore, hyphen only
        if not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
            logging.warning(f"GATEWAY: Rejected invalid user_id format: {user_id}")
            return False

        return True

    @classmethod
    def extract_user_id_from_path(cls, path: str) -> Optional[str]:
        """
        Extract user_id from request path using regex patterns.

        Args:
            path: Request path (e.g., /api/external/users/john_doe)

        Returns:
            Extracted user_id if found, None otherwise
        """
        for pattern in cls.USER_ID_PATTERNS:
            match = re.search(pattern, path)
            if match:
                user_id = match.group("user_id")
                # Validate safety
                if cls.validate_user_id_safety(user_id):
                    return user_id
                else:
                    # Unsafe user_id found
                    return None

        # No user_id found in path
        return None

    @classmethod
    def check_permission(
        cls, session_user_id: str, session_role: str, request_path: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user has permission to access path.

        Args:
            session_user_id: User ID from session
            session_role: User role from session (admin or user)
            request_path: Request path

        Returns:
            Tuple of (has_permission, extracted_user_id)
            - has_permission: True if access allowed
            - extracted_user_id: User ID extracted from path (None if not found)
        """
        # Special case: /me refers to current user (always allowed)
        if "/me/" in request_path or request_path.endswith("/me"):
            logging.debug(f"GATEWAY: /me endpoint accessed by {session_user_id}")
            return True, session_user_id

        # Admin bypass - full access
        if session_role == "admin":
            return True, cls.extract_user_id_from_path(request_path)

        # Regular user - check user_id ownership
        extracted_user_id = cls.extract_user_id_from_path(request_path)

        if extracted_user_id is None:
            # No user_id in path - admin-only endpoint
            logging.warning(
                f"GATEWAY: User {session_user_id} denied access to admin-only path: {request_path}"
            )
            return False, None

        # Check if extracted user_id matches session user_id
        if extracted_user_id == session_user_id:
            return True, extracted_user_id
        else:
            logging.warning(
                f"GATEWAY: User {session_user_id} denied access to {extracted_user_id}'s resources"
            )
            return False, extracted_user_id
