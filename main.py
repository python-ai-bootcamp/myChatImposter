
import logging
import sys
import os
import asyncio
from fastapi import FastAPI
from dependencies import GlobalStateManager
from async_message_delivery_queue_manager import AsyncMessageDeliveryQueueManager
from services.session_manager import SessionManager
from features.periodic_group_tracking.service import GroupTracker
from services.user_lifecycle_service import UserLifecycleService

# Import Routers
from routers import user_management
from routers.features import automatic_bot_reply, periodic_group_tracking
from routers import async_message_delivery_queue
from routers import resources

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
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI()

# Global State Access
global_state = GlobalStateManager.get_instance()

@app.on_event("startup")
async def startup_event():
    """
    Initialize global state, DB, and managers.
    """
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017/")
    
    # 1. Initialize MongoDB
    global_state.initialize_mongodb(mongodb_url)
    
    try:
        # 2. Initialize AsyncMessageDeliveryQueueManager
        global_state.async_message_delivery_queue_manager = AsyncMessageDeliveryQueueManager(mongodb_url, global_state.chatbot_instances)
        
        # Lifecycle: Move all items to Holding Queue on Startup
        global_state.async_message_delivery_queue_manager.move_all_to_holding()
        
        await global_state.async_message_delivery_queue_manager.start_consumer()
        
        # 3. Initialize GroupTracker
        global_state.group_tracker = GroupTracker(mongodb_url, global_state.chatbot_instances, global_state.async_message_delivery_queue_manager)
        global_state.group_tracker.start()
        
        # 4. Initialize UserLifecycleService
        global_state.user_lifecycle_service = UserLifecycleService(global_state)
        
    except Exception as e:
        logging.error(f"API: Startup initialization failed: {e}")
        # We might want to exit or continue with limited functionality

@app.on_event("shutdown")
async def shutdown_event():
    """
    Gracefully shut down components.
    """
    logging.info("API: Server is shutting down. Stopping all chatbot instances...")
    
    # Stop Chatbot Instances
    # iterate list(items) to copy keys
    for instance_id, instance in list(global_state.chatbot_instances.items()):
        logging.info(f"API: Stopping instance {instance_id} (No cleanup)...")
        await instance.stop(cleanup_session=False)
        # Remove from active maps
        global_state.remove_active_user(instance.user_id)
        
    global_state.chatbot_instances.clear()
    
    # Shutdown GroupTracker
    global_state.shutdown()
    
    # Shutdown Queue Manager (Specific)
    if global_state.async_message_delivery_queue_manager:
        await global_state.async_message_delivery_queue_manager.stop_consumer()

# Include Routers
app.include_router(user_management.router)
app.include_router(automatic_bot_reply.router)
app.include_router(periodic_group_tracking.router)
app.include_router(async_message_delivery_queue.router)
app.include_router(resources.router)

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

if __name__ == "__main__":
    import uvicorn
    # Use environment variable for port or default to 8000
    port = int(os.environ.get("PORT", 8000))
    # Run uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
