"""
Permission validation and user_id extraction from request paths.
"""

import re
import logging
from typing import Optional, Tuple, List


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
        r"/api/external/ui/users/(?P<user_id>[\w-]+)", # /api/external/ui/users/{user_id}
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
        cls,
        session_user_id: str,
        session_role: str,
        request_path: str,
        owned_configurations: List[str] = [],
        method: str = "GET",
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user has permission to access path.

        Args:
            session_user_id: User ID from session
            session_role: User role from session (admin or user)
            request_path: Request path
            owned_configurations: List of configs owned by user
            method: HTTP method (e.g. GET, PUT)

        Returns:
            Tuple of (has_permission, extracted_user_id)
            - has_permission: True if access allowed
            - extracted_user_id: User ID extracted from path (None if not found)
        """
        # Admin bypass - full access
        if session_role == "admin":
            return True, cls.extract_user_id_from_path(request_path)

        # Regular user - check user_id ownership
        extracted_user_id = cls.extract_user_id_from_path(request_path)

        if extracted_user_id is None:
            # Exception: List Users endpoint is now accessible to regular users (filtered by gateway proxy)
            if request_path == "/api/external/users" or request_path == "/api/external/users/":
                 return True, None

            # Exception: Resources (Timezones, Languages) are public for authenticated users
            if request_path.startswith("/api/external/resources/"):
                 return True, None

            # No user_id in path - admin-only endpoint
            logging.warning(
                f"GATEWAY: User {session_user_id} denied access to admin-only path: {request_path}"
            )
            return False, None

        # Check if extracted user_id matches session user_id or is in owned list
        if extracted_user_id == session_user_id or extracted_user_id in owned_configurations:
            
            # CRITICAL SECURITY: Legacy Endpoint Lockdown
            # Even if they own the user_id, they CANNOT access the full admin API.
            # Only Admins can access the ROOT resource /api/external/users/{id}
            # Sub-resources like /info, /groups, /actions are ALLOWED for owners.
            
            # Construct the restricted root path
            root_resource_path = f"/api/external/users/{extracted_user_id}"
            
            # Check if the request is targeting the root resource exactly (ignoring trailing slash)
            if request_path.rstrip("/") == root_resource_path:
                 logging.warning(
                     f"GATEWAY: Regular User {session_user_id} denied access to ADMIN ROOT: {request_path}"
                 )
                 return False, extracted_user_id
            
            # If it's a sub-resource (e.g. /info), we allow it because they passed the ownership check above.
            return True, extracted_user_id
        
        # Exception: /schema endpoint
        # The regex extracts "schema" as user_id. We allow this for everyone.
        if extracted_user_id == "schema":
             return True, None # None means no specific user context needed downstream

        # Exception: /status endpoint
        # The regex extracts "status" as user_id. We allow this for everyone (filtered by gateway).
        if extracted_user_id == "status":
             return True, None

        # Exception: /validate/{user_id} endpoint
        # The regex extracts "validate" first, but we need to allow the full validate path.
        if "/ui/users/validate/" in request_path:
             return True, None

        # Exception: PUT (Creation/Update)
        # We allow PUT for authenticated users even if they don't own it *yet*.
        # The backend/gateway will handle the "Don't Overwrite Others" check.
        # But we need to allow it to pass this validator.
        if method == "PUT":
            return True, extracted_user_id

        else:
            logging.warning(
                f"GATEWAY: User {session_user_id} denied access to {extracted_user_id}'s resources"
            )
            return False, extracted_user_id
