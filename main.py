
import logging
import sys
import os
import asyncio
from fastapi import FastAPI
from dependencies import GlobalStateManager
from async_message_delivery_queue_manager import AsyncMessageDeliveryQueueManager
from services.session_manager import SessionManager
from features.periodic_group_tracking.service import GroupTracker
from services.bot_lifecycle_service import BotLifecycleService
from utils.json_encoder import CustomJSONResponse

# Import Routers
# Import Routers
from routers import bot_management
from routers.features import automatic_bot_reply, periodic_group_tracking
from routers import async_message_delivery_queue
from routers import resources
from routers import bot_ui
from routers import user_management # [NEW]


# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s]::%(levelname)s::%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Suppress uvicorn access logger
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("uvicorn").propagate = False
logging.getLogger("httpx").setLevel(logging.WARNING)

from contextlib import asynccontextmanager

# Global State Access
global_state = GlobalStateManager.get_instance()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI application.
    Handles startup configuration and shutdown cleanup.
    """
    # --- STARTUP LOGIC ---
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017/")
    
    # 1. Initialize MongoDB
    await global_state.initialize_mongodb(mongodb_url)
    
    try:
        # 2. Initialize AsyncMessageDeliveryQueueManager
        # Now pass shared DB object
        global_state.async_message_delivery_queue_manager = AsyncMessageDeliveryQueueManager(global_state.db, global_state.chatbot_instances)
        # Ensure indexes (if manual init is preferred, or rely on shared schema if moved there)
        # For now, explicit await init
        await global_state.async_message_delivery_queue_manager.initialize_indexes()
        
        # Lifecycle: Move all items to Holding Queue on Startup
        await global_state.async_message_delivery_queue_manager.move_all_to_holding()
        
        await global_state.async_message_delivery_queue_manager.start_consumer()
        
        # 3. Initialize GroupTracker
        global_state.group_tracker = GroupTracker(global_state.db, global_state.chatbot_instances, global_state.async_message_delivery_queue_manager)
        global_state.group_tracker.start()
        
        # 4a. Initialize UserAuthService (Needed by User Management)
        from services.user_auth_service import UserAuthService
        global_state.auth_service = UserAuthService(global_state.credentials_collection)

        # 4. Initialize BotLifecycleService
        global_state.bot_lifecycle_service = BotLifecycleService(global_state)
        
        # 5. Initialize SessionMaintenanceService & Schedule
        from features.session_maintenance.service import SessionMaintenanceService
        global_state.session_maintenance = SessionMaintenanceService(global_state.db)
        
        # We can reuse the GroupTracker's scheduler for simplicity, or add a general one.
        # GroupTracker scheduler is available at global_state.group_tracker.scheduler
        if global_state.group_tracker and global_state.group_tracker.scheduler:
             logging.info("API: Scheduling recurring session maintenance (Every 1 hour).")
             global_state.group_tracker.scheduler.add_job(
                 global_state.session_maintenance.run_global_maintenance,
                 'interval', 
                 hours=1,
                 id='session_maintenance_global',
                 replace_existing=True
             )
        else:
             logging.warning("API: Could not schedule session maintenance - Scheduler not available.")

    except Exception as e:
        logging.error(f"API: Startup initialization failed: {e}")
        # We might want to exit or continue with limited functionality

    try:
        yield
    finally:
        # --- SHUTDOWN LOGIC ---
        logging.info("API: Server is shutting down. Stopping all chatbot instances...")
        
        # Stop Chatbot Instances
        # iterate list(items) to copy keys
        for instance_id, instance in list(global_state.chatbot_instances.items()):
            logging.info(f"API: Stopping instance {instance_id} (No cleanup)...")
            await instance.stop(cleanup_session=False)
            # Remove from active maps
            global_state.remove_active_bot(instance.bot_id)
            
        global_state.chatbot_instances.clear()
        
        # Shutdown GroupTracker
        global_state.shutdown()
        
        # Shutdown Queue Manager (Specific)
        if global_state.async_message_delivery_queue_manager:
            await global_state.async_message_delivery_queue_manager.stop_consumer()

app = FastAPI(lifespan=lifespan, default_response_class=CustomJSONResponse)

# Include Routers
app.include_router(bot_management.router)
app.include_router(automatic_bot_reply.router)
app.include_router(periodic_group_tracking.router)
app.include_router(async_message_delivery_queue.router)
app.include_router(resources.router)
app.include_router(bot_ui.router)
app.include_router(user_management.router) # [NEW]


@app.middleware("http")
async def log_requests(request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logging.info(f'{request.client.host}:{request.client.port} - "{request.method} {request.url.path} HTTP/{request.scope["http_version"]}" {response.status_code} ({process_time:.2f}ms)')
    return response

# Root endpoint check
@app.get("/")
async def root():
    return {"message": "Chatbot Manager API Running"}

# Health check endpoint (no auth required — accessed internally by gateway)
@app.get("/health")
async def health():
    """Backend health check endpoint."""
    return {"status": "backend_ok"}

if __name__ == "__main__":
    import uvicorn
    # Use environment variable for port or default to 8000
    port = int(os.environ.get("PORT", 8000))
    # Run uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
