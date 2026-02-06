"""
Permission validation and user_id extraction from request paths.
"""

import re
import logging
from typing import Optional, Tuple, List


class PermissionValidator:
    """
    Validates permissions based on user role and path bot_id ownership.

    Rules:
    - Admin: Bypass all checks, access any resource
    - User: Can only access resources where extracted bot_id matches session owned_bots
    - Paths without bot_id: Admin-only
    """

    # Regex patterns for extracting bot_id from paths
    BOT_ID_PATTERNS = [
        r"/api/external/bots/(?P<bot_id>[^/]+)",  # /api/external/bots/{bot_id}
        r"/api/external/ui/bots/(?P<bot_id>[\w-]+)", # /api/external/ui/bots/{bot_id} (if UI path changes)
        r"/api/external/features/.*/(?P<bot_id>[^/]+)",  # /api/external/features/.../.../{bot_id}
    ]

    @staticmethod
    def validate_bot_id_safety(bot_id: str) -> bool:
        """
        Validate bot_id is safe (no path traversal).

        Args:
            bot_id: Bot identifier from path

        Returns:
            True if safe, False otherwise
        """
        # Reject path traversal attempts
        if ".." in bot_id or "/" in bot_id or "\\" in bot_id:
            logging.warning(f"GATEWAY: Rejected unsafe bot_id: {bot_id}")
            return False

        # Must match alphanumeric, underscore, hyphen only
        if not re.match(r"^[a-zA-Z0-9_-]+$", bot_id):
            logging.warning(f"GATEWAY: Rejected invalid bot_id format: {bot_id}")
            return False

        return True

    @classmethod
    def extract_bot_id_from_path(cls, path: str) -> Optional[str]:
        """
        Extract bot_id from request path using regex patterns.

        Args:
            path: Request path (e.g., /api/external/bots/my_bot)

        Returns:
            Extracted bot_id if found, None otherwise
        """
        for pattern in cls.BOT_ID_PATTERNS:
            match = re.search(pattern, path)
            if match:
                bot_id = match.group("bot_id")
                
                # Validate safety
                if cls.validate_bot_id_safety(bot_id):
                    return bot_id
                else:
                    # Unsafe bot_id found
                    return None

        # No bot_id found in path
        return None

    @classmethod
    def check_permission(
        cls,
        session_user_id: str,
        session_role: str,
        request_path: str,
        owned_bots: List[str] = [],
        method: str = "GET",
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user has permission to access path.

        Args:
            session_user_id: User ID from session (The Owner)
            session_role: User role from session (admin or user)
            request_path: Request path
            owned_bots: List of bot_ids owned by user
            method: HTTP method (e.g. GET, PUT)

        Returns:
            Tuple of (has_permission, extracted_bot_id)
            - has_permission: True if access allowed
            - extracted_bot_id: Bot ID extracted from path (None if not found)
        """
        # Admin bypass - full access
        if session_role == "admin":
            return True, cls.extract_bot_id_from_path(request_path)

        # Regular user - check bot_id ownership
        extracted_bot_id = cls.extract_bot_id_from_path(request_path)

        if extracted_bot_id is None:
            # Exception: List Bots endpoint is now accessible to regular users (filtered by gateway proxy)
            if request_path == "/api/external/bots" or request_path == "/api/external/bots/":
                 return True, None

            # Exception: Resources (Timezones, Languages) are public for authenticated users
            if request_path.startswith("/api/external/resources/"):
                 return True, None

            # No bot_id in path - admin-only endpoint
            logging.warning(
                f"GATEWAY: Owner {session_user_id} denied access to admin-only path: {request_path}"
            )
            return False, None

        # Check if extracted bot_id is in owned list
        if extracted_bot_id in owned_bots:
            
            # CRITICAL SECURITY: Legacy Endpoint Lockdown
            # Even if they own the bot_id, they CANNOT access the full admin API if we were to expose it.
            # But here we are mapping /api/external/bots -> /api/internal/bots.
            # We assume internal API is safe if ID matches.
            
            # Additional Check: Are they trying to access the root bot config DELETE/PUT via raw API?
            # We allow it if they own it (Proxy handles creation limit).
            
            return True, extracted_bot_id
        
        # Exception: /schema endpoint (if applicable for bots)
        if extracted_bot_id == "schema":
             return True, None

        # Exception: /status endpoint
        if extracted_bot_id == "status":
             return True, None
             
        # Exception: /validate/{bot_id} endpoint
        if "/ui/bots/validate/" in request_path:
             return True, None

        # Exception: PUT (Creation/Update)
        # We allow PUT for authenticated users even if they don't own it *yet* (New Bot Creation).
        # The backend/gateway will handle the "Don't Overwrite Others" check.
        if method == "PUT":
            return True, extracted_bot_id

        else:
            logging.warning(
                f"GATEWAY: Owner {session_user_id} denied access to Bot {extracted_bot_id}"
            )
            return False, extracted_bot_id
