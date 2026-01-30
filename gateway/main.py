"""
Gateway service main application.

Provides:
- Session-based authentication
- Permission validation
- Request proxying to backend
- Audit logging
- Rate limiting
- Account lockout
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from gateway.dependencies import gateway_state
from gateway.session_manager import SessionManager
from gateway.rate_limiter import RateLimiter
from gateway.account_lockout import AccountLockoutManager
from gateway.audit_logger import AuditLogger
from gateway.middleware import AuthenticationMiddleware, RequestSizeLimitMiddleware
from gateway.routers import auth, proxy
from services.user_auth_service import UserAuthService


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# Background task flags
cleanup_task = None
lockout_cleanup_task = None
shutdown_event = asyncio.Event()


async def cleanup_old_data():
    """
    Background task to clean up old audit logs and stale sessions.

    Runs every 24 hours.
    """
    while not shutdown_event.is_set():
        try:
            # Wait 24 hours (or until shutdown)
            await asyncio.wait_for(shutdown_event.wait(), timeout=86400)
        except asyncio.TimeoutError:
            # Timeout means 24 hours passed, proceed with cleanup
            logger.info("GATEWAY: Running scheduled cleanup task")

            try:
                # Clean up audit logs older than 30 days (TTL index handles this automatically)
                # Clean up stale sessions older than 30 days
                cutoff = datetime.utcnow() - timedelta(days=30)
                result = await gateway_state.stale_sessions_collection.delete_many(
                    {"invalidated_at": {"$lt": cutoff}}
                )
                logger.info(
                    f"GATEWAY: Cleaned up {result.deleted_count} old stale sessions"
                )

            except Exception as e:
                logger.error(f"GATEWAY: Error during cleanup task: {e}")


async def cleanup_expired_lockouts():
    """
    Background task to clean up expired account lockouts.

    Runs every hour.
    """
    while not shutdown_event.is_set():
        try:
            # Wait 1 hour (or until shutdown)
            await asyncio.wait_for(shutdown_event.wait(), timeout=3600)
        except asyncio.TimeoutError:
            # Timeout means 1 hour passed, proceed with cleanup
            logger.info("GATEWAY: Running lockout cleanup task")

            try:
                # Remove expired lockouts
                now = datetime.utcnow()
                result = await gateway_state.account_lockouts_collection.delete_many(
                    {
                        "locked_until": {"$lt": now, "$ne": None}
                    }
                )
                logger.info(
                    f"GATEWAY: Cleaned up {result.deleted_count} expired account lockouts"
                )

            except Exception as e:
                logger.error(f"GATEWAY: Error during lockout cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup:
    1. Connect to MongoDB
    2. Initialize services
    3. Start background tasks

    Shutdown:
    1. Stop background tasks
    2. Close MongoDB connection
    """
    global cleanup_task, lockout_cleanup_task

    # Startup
    logger.info("GATEWAY: Starting up...")

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")

    # Initialize MongoDB
    await gateway_state.initialize_mongodb(mongodb_url)

    # Initialize services
    session_manager = SessionManager(
        sessions_collection=gateway_state.sessions_collection,
        stale_sessions_collection=gateway_state.stale_sessions_collection,
    )

    rate_limiter = RateLimiter(max_attempts=10, window_seconds=60)

    lockout_manager = AccountLockoutManager(
        account_lockouts_collection=gateway_state.account_lockouts_collection,
        max_attempts=10,
        attempt_window_minutes=10,
        lockout_duration_minutes=5,
    )

    audit_logger = AuditLogger(
        audit_logs_collection=gateway_state.audit_logs_collection
    )

    auth_service = UserAuthService(
        credentials_collection=gateway_state.credentials_collection
    )

    # Initialize auth router with services
    auth.initialize_auth_router(
        sm=session_manager,
        rl=rate_limiter,
        lm=lockout_manager,
        al=audit_logger,
        aus=auth_service,
    )

    # Add middleware (order matters - last added runs first)
    app.add_middleware(
        AuthenticationMiddleware,
        session_manager=session_manager,
        audit_logger=audit_logger,
    )
    app.add_middleware(RequestSizeLimitMiddleware)

    # Start background tasks
    cleanup_task = asyncio.create_task(cleanup_old_data())
    lockout_cleanup_task = asyncio.create_task(cleanup_expired_lockouts())

    logger.info("GATEWAY: Initialization complete")

    yield

    # Shutdown
    logger.info("GATEWAY: Shutting down...")

    # Stop background tasks
    shutdown_event.set()
    if cleanup_task:
        cleanup_task.cancel()
    if lockout_cleanup_task:
        lockout_cleanup_task.cancel()

    # Close MongoDB
    await gateway_state.shutdown()

    logger.info("GATEWAY: Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Gateway Service",
    description="Authentication and request proxying gateway",
    version="1.0.0",
    lifespan=lifespan,
)


# Include routers
app.include_router(auth.router)
app.include_router(proxy.router)


# Root endpoint
@app.get("/")
async def root():
    """Gateway service root endpoint."""
    return {
        "service": "gateway",
        "status": "running",
        "version": "1.0.0",
    }


# Health check
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Error handler for 404
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("GATEWAY_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
