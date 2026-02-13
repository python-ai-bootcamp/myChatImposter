"""
Authentication endpoints for login and logout.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from auth_models import LoginRequest, LoginResponse
from gateway.dependencies import gateway_state
from gateway.session_manager import SessionManager
from gateway.rate_limiter import RateLimiter
from gateway.account_lockout import AccountLockoutManager
from gateway.audit_logger import AuditLogger
from services.user_auth_service import UserAuthService


router = APIRouter(prefix="/api/external/auth", tags=["Authentication"])

# Initialize services (will be set in main.py)
session_manager: SessionManager = None
rate_limiter: RateLimiter = None
lockout_manager: AccountLockoutManager = None
audit_logger: AuditLogger = None
auth_service: UserAuthService = None


def initialize_auth_router(
    sm: SessionManager,
    rl: RateLimiter,
    lm: AccountLockoutManager,
    al: AuditLogger,
    aus: UserAuthService,
):
    """
    Initialize router with service instances.

    Called from main.py during startup.
    """
    global session_manager, rate_limiter, lockout_manager, audit_logger, auth_service
    session_manager = sm
    rate_limiter = rl
    lockout_manager = lm
    audit_logger = al
    auth_service = aus


@router.post("/login", response_model=LoginResponse)
async def login(login_request: LoginRequest, request: Request, response: Response):
    """
    Authenticate user and create session.

    Security checks:
    1. Rate limiting (10 attempts/min per IP)
    2. Account lockout (10 failed attempts = 5min lock)
    3. Password validation via bcrypt
    4. Audit logging

    Returns session cookie on success.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Check rate limit
    allowed, retry_after = rate_limiter.check_rate_limit(ip_address)
    if not allowed:
        logging.warning(
            f"GATEWAY: Rate limit exceeded for IP {ip_address} (retry after {retry_after}s)"
        )
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many login attempts. Please try again later.",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    # Check account lockout
    is_locked, locked_until = await lockout_manager.check_lockout(login_request.user_id)
    if is_locked:
        retry_after = int((locked_until - datetime.utcnow()).total_seconds())
        logging.warning(
            f"GATEWAY: Account {login_request.user_id} is locked until {locked_until}"
        )

        return JSONResponse(
            status_code=423,
            content={
                "detail": "Account is temporarily locked due to multiple failed login attempts.",
                "locked_until": locked_until.isoformat(),
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    # Record rate limit attempt
    rate_limiter.record_attempt(ip_address)

    # Authenticate
    success, role, owned_bots, max_config_limit, max_feature_limit = await auth_service.authenticate(
        login_request.user_id, login_request.password
    )

    if not success:
        # Record failed attempt
        is_now_locked, locked_until = await lockout_manager.record_failed_attempt(
            login_request.user_id
        )

        # Log failed attempt
        await audit_logger.log_login_failed(
            user_id=login_request.user_id,
            reason="invalid_credentials",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # If account just got locked, log it
        if is_now_locked:
            await audit_logger.log_account_locked(
                user_id=login_request.user_id,
                failed_attempts=lockout_manager.max_attempts,
                locked_until=locked_until,
                ip_address=ip_address,
            )

            retry_after = int((locked_until - datetime.utcnow()).total_seconds())
            return JSONResponse(
                status_code=423,
                content={
                    "detail": "Account locked due to multiple failed login attempts.",
                    "locked_until": locked_until.isoformat(),
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return LoginResponse(
            success=False,
            message="Invalid credentials",
        )

    # Clear lockout on successful login
    await lockout_manager.clear_lockout(login_request.user_id)

    # Reset rate limit for this IP
    rate_limiter.reset_ip(ip_address)

    # Create session
    session = await session_manager.create_session(
        user_id=login_request.user_id,
        role=role,
        owned_bots=owned_bots,
        max_user_configuration_limit=max_config_limit,
        max_feature_limit=max_feature_limit,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Log successful login
    await audit_logger.log_login_success(
        user_id=login_request.user_id,
        role=role,
        session_id=session.session_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Set session cookie (HTTPOnly, SameSite=Lax for CSRF protection)
    response.set_cookie(
        key="session_id",
        value=session.session_id,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 hours
        # secure=True,  # Enable in production with HTTPS
    )

    logging.info(f"GATEWAY: User {login_request.user_id} logged in successfully")

    # Fetch full user details for response
    user_creds = await auth_service.get_credentials(login_request.user_id)
    first_name = user_creds.first_name if user_creds else None
    last_name = user_creds.last_name if user_creds else None
    language_code = user_creds.language if user_creds else "en"

    return LoginResponse(
        success=True,
        message="Login successful",
        user_id=session.user_id,
        role=session.role,
        session_id=session.session_id,
        first_name=first_name,
        last_name=last_name,
        language_code=language_code
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    Logout user and invalidate session.

    Returns 200 even if no session (idempotent).
    """
    session_id = request.cookies.get("session_id")

    if session_id:
        session = await session_manager.get_session(session_id)

        if session:
            # Log logout
            await audit_logger.log_logout(
                user_id=session.user_id,
                session_id=session_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
            )

            # Invalidate session
            await session_manager.invalidate_session(session_id, reason="logout")

            logging.info(f"GATEWAY: User {session.user_id} logged out")

    # Clear session cookie
    response.delete_cookie(key="session_id")

    return {"success": True, "message": "Logout successful"}


@router.get("/validate")
async def validate_session(request: Request):
    """
    Lightweight session validation.
    Returns {valid: true} if session is active, or 401 if expired/invalid.
    Used by ProtectedRoute to gate access without fetching full user data.
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="No session")

    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return {"valid": True}
