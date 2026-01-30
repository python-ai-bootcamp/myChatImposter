"""
Gateway middleware for authentication and request validation.
"""

import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from gateway.session_manager import SessionManager
from gateway.permission_validator import PermissionValidator
from gateway.audit_logger import AuditLogger


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for session validation and permission checking.

    Whitelist:
    - / (root)
    - /api/external/auth/login
    - /api/external/auth/logout
    - /docs, /openapi.json (API documentation)
    - /health (health check)

    For all other paths:
    1. Check session cookie
    2. Validate session
    3. Check permissions
    4. Attach session to request.state
    """

    # Paths that don't require authentication
    WHITELIST = [
        "/",
        "/api/external/auth/login",
        "/api/external/auth/logout",
        "/docs",
        "/openapi.json",
        "/health",
    ]

    def __init__(
        self,
        app,
        session_manager: SessionManager,
        audit_logger: AuditLogger,
    ):
        """
        Initialize AuthenticationMiddleware.

        Args:
            app: FastAPI application
            session_manager: SessionManager instance
            audit_logger: AuditLogger instance
        """
        super().__init__(app)
        self.session_manager = session_manager
        self.audit_logger = audit_logger

    async def dispatch(self, request: Request, call_next):
        """Process request through authentication and permission checks."""
        path = request.url.path

        # Whitelist check
        if path in self.WHITELIST:
            return await call_next(request)

        # Get session cookie
        session_id = request.cookies.get("session_id")

        if not session_id:
            logging.warning(f"GATEWAY: No session cookie for path: {path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required"},
            )

        # Validate session
        session = await self.session_manager.get_session(session_id)

        if not session:
            logging.warning(f"GATEWAY: Invalid/expired session: {session_id}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired session"},
            )

        # Update last_accessed (heartbeat)
        await self.session_manager.update_last_accessed(session_id)

        # Check permissions
        has_permission, extracted_user_id = PermissionValidator.check_permission(
            session_user_id=session.user_id,
            session_role=session.role,
            request_path=path,
        )

        if not has_permission:
            # Log permission denied
            await self.audit_logger.log_permission_denied(
                user_id=session.user_id,
                role=session.role,
                requested_path=path,
                extracted_user_id=extracted_user_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            return JSONResponse(
                status_code=403,
                content={"detail": "Permission denied"},
            )

        # Attach session to request state
        request.state.session = session

        # Forward request
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce request body size limits.

    Limits:
    - Maximum body size: 80KB (80,000 characters)
    - Applies to POST, PUT, PATCH requests
    """

    MAX_BODY_SIZE = 80000  # 80KB

    async def dispatch(self, request: Request, call_next):
        """Check request body size before processing."""
        # Only check methods with bodies
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")

            if content_length:
                content_length = int(content_length)

                if content_length > self.MAX_BODY_SIZE:
                    logging.warning(
                        f"GATEWAY: Request body too large: {content_length} bytes "
                        f"(max {self.MAX_BODY_SIZE} bytes)"
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body too large (max {self.MAX_BODY_SIZE} bytes)"
                        },
                    )

        return await call_next(request)
