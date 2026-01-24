import uuid
import threading
import sys
import logging
import time
import os
import json
import asyncio
from pathlib import Path
import dataclasses
from fastapi import FastAPI, HTTPException, Body, Request, Response, Query
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from typing import Dict, Any, List, Union
from uvicorn.config import LOGGING_CONFIG
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from chatbot_manager import ChatbotInstance
from group_tracker import GroupTracker
from config_models import UserConfiguration, PeriodicGroupTrackingConfig
from actionable_items_message_delivery_queue_manager import ActionableItemsDeliveryQueueManager

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s]::%(levelname)s::%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Suppress the default uvicorn access logger
access_logger = logging.getLogger("uvicorn.access")
access_logger.disabled = True
# Keep the default uvicorn logger for startup/shutdown messages
default_logger = logging.getLogger("uvicorn")
default_logger.propagate = False 

app = FastAPI()

# MongoDB Client
mongo_client: MongoClient = None
db = None
configurations_collection = None
queues_collection = None
baileys_sessions_collection = None

# In-memory storage for chatbot instances
chatbot_instances: Dict[str, ChatbotInstance] = {}
active_users: Dict[str, str] = {} # Maps user_id to instance_id
group_tracker: GroupTracker = None
actionable_queue_manager: ActionableItemsDeliveryQueueManager = None

@app.on_event("startup")
async def startup_event():
    """
    Connect to MongoDB and create a unique index on startup.
    """
    global mongo_client, db, configurations_collection, queues_collection, baileys_sessions_collection, group_tracker, actionable_queue_manager
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017/")
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017/")
    logging.info(f"API: Connecting to MongoDB at {mongodb_url}")

    try:
        mongo_client = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ismaster')
        db = mongo_client.get_database("chat_manager")
        configurations_collection = db.get_collection("configurations")
        queues_collection = db.get_collection("queues")
        baileys_sessions_collection = db.get_collection("baileys_sessions")

        try:
            # This index is on the user_id field *within* the config_data object.
            configurations_collection.create_index("config_data.user_id", unique=True)
            logging.info("API: Ensured unique index exists for 'config_data.user_id'.")
        except Exception as index_e:
            logging.warning(f"API: Could not create unique index, it may already exist or there's a data issue: {index_e}")

        logging.info("API: Successfully connected to MongoDB.")

        # Initialize ActionableItemsDeliveryQueueManager
        actionable_queue_manager = ActionableItemsDeliveryQueueManager(mongodb_url, chatbot_instances)
        
        # Lifecycle: Move all items to Holding Queue on Startup
        actionable_queue_manager.move_all_to_holding()
        
        await actionable_queue_manager.start_consumer()

        # Initialize GroupTracker with queue manager
        group_tracker = GroupTracker(mongodb_url, chatbot_instances, actionable_queue_manager)
        group_tracker.start()

    except Exception as e:
        logging.error(f"API: Could not connect to MongoDB: {e}")
        mongo_client = None

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    A middleware to log incoming requests in a format similar to uvicorn's,
    but using our custom timestamped logger.
    """
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000

    # Recreate a uvicorn-like access log, but with our timestamp
    logging.info(f'{request.client.host}:{request.client.port} - "{request.method} {request.url.path} HTTP/{request.scope["http_version"]}" {response.status_code} ({process_time:.2f}ms)')

    return response


def remove_active_user(user_id: str):
    """Callback function to remove a user from the active list."""
    if user_id in active_users:
        instance_id = active_users[user_id]
        logging.info(f"API: Session ended for user '{user_id}'. Removing from active list.")
        del active_users[user_id]
        if instance_id in chatbot_instances:
            # Also remove the main instance object to free memory
            del chatbot_instances[instance_id]
    else:
        logging.warning(f"API: Tried to remove non-existent user '{user_id}' from active list.")

@app.get("/api/configurations")
async def get_configuration_user_ids():
    """
    Returns a list of all configuration user_ids from the database.
    """
    if configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")
    try:
        user_ids = []
        # Query for documents where config_data is an object, and for documents where it's an array.
        # This is more robust than trying to handle it in Python code.
        cursor = configurations_collection.find({}, {"config_data.user_id": 1, "_id": 0})
        for doc in cursor:
            config_data = doc.get("config_data", {})
            if isinstance(config_data, list) and config_data:
                user_id = config_data[0].get("user_id")
                if user_id:
                    user_ids.append(user_id)
            elif isinstance(config_data, dict):
                user_id = config_data.get("user_id")
                if user_id:
                    user_ids.append(user_id)

        return {"user_ids": user_ids}
    except Exception as e:
        logging.error(f"API: Could not list user_ids from DB: {e}")
        raise HTTPException(status_code=500, detail="Could not list user_ids.")


@app.get("/api/configurations/schema", response_model=Dict[str, Any])
async def get_configuration_schema():
    """
    Returns the JSON Schema for the UserConfiguration model, with modifications
    for better frontend rendering.
    """
    schema = UserConfiguration.model_json_schema()
    defs_key = '$defs' if '$defs' in schema else 'definitions'

    # llm_provider_config is now mandatory, no dropdown needed

    # To fix the conditional API key, we will restructure the entire LLMProviderSettings schema.
    # Instead of using dependencies, we will define two distinct objects in a oneOf.
    if defs_key in schema and 'LLMProviderSettings' in schema[defs_key]:
        llm_settings_schema = schema[defs_key]['LLMProviderSettings']

        # Get the original properties, remove the ones we are making conditional
        original_properties = llm_settings_schema.get('properties', {}).copy()
        original_properties.pop('api_key_source', None)
        original_properties.pop('api_key', None)

        # Define the two distinct schemas
        schema_from_env = {
            "title": "API Key From Environment",
            "properties": {
                "api_key_source": {"const": "environment"},
                **original_properties
            }
        }

        schema_explicit_key = {
            "title": "API Key From User Input",
            "properties": {
                "api_key_source": {"const": "explicit"},
                "api_key": {"type": "string", "title": "API Key", "minLength": 1},
                **original_properties
            },
            "required": ["api_key"]
        }

        # Overwrite the LLMProviderSettings definition with our new oneOf structure
        schema[defs_key]['LLMProviderSettings'] = {
            "oneOf": [
                schema_from_env,
                schema_explicit_key
            ]
        }

    # Patch reasoning_effort anyOf titles to show "Defined" / "Undefined"
    if defs_key in schema and 'LLMProviderSettings' in schema[defs_key]:
        llm_settings = schema[defs_key]['LLMProviderSettings']
        # After our restructuring, LLMProviderSettings is a oneOf of two branches
        if 'oneOf' in llm_settings:
            for branch in llm_settings['oneOf']:
                if 'properties' in branch and 'reasoning_effort' in branch['properties']:
                    re = branch['properties']['reasoning_effort']
                    if 'anyOf' in re:
                        for option in re['anyOf']:
                            # The string option (enum)
                            if option.get('type') == 'string' or 'enum' in option:
                                option['title'] = 'Defined'
                                option['default'] = 'minimal'
                            # The null option
                            elif option.get('type') == 'null':
                                option['title'] = 'Undefined'

    return schema


@app.get("/api/configurations/status")
async def get_all_configurations_status():
    """
    Returns a list of all configs from the DB along with their current session status.
    Validates each config against the UserConfiguration model.
    """
    if configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    statuses = []
    try:
        db_configs = list(configurations_collection.find({}))
        for db_config in db_configs:
            config_data = db_config.get("config_data")
            user_id_from_config = None
            try:
                if not config_data:
                    raise ValueError("Configuration data is missing.")

                if isinstance(config_data, list) and config_data:
                    config_to_validate = config_data[0]
                elif isinstance(config_data, dict):
                    config_to_validate = config_data
                else:
                    raise ValueError("Configuration data is empty or has an unsupported format.")

                config = UserConfiguration.model_validate(config_to_validate)
                user_id_from_config = config.user_id

                # Check if session is authenticated in MongoDB
                is_authenticated = False
                try:
                    if baileys_sessions_collection is not None:
                         auth_doc = await run_in_threadpool(baileys_sessions_collection.find_one, {"_id": f"{user_id_from_config}-creds"})
                         
                         if auth_doc:
                             is_authenticated = True
                    else:
                        logging.warning("API: baileys_sessions_collection is None during status check.")
                except Exception as auth_e:
                    logging.warning(f"API: Error checking auth status for {user_id_from_config}: {auth_e}")
                
                # Check for active session
                if user_id_from_config in active_users:
                    instance_id = active_users[user_id_from_config]
                    instance = chatbot_instances.get(instance_id)
                    status_info = await instance.get_status() if instance else {"status": "error"}
                    statuses.append({
                        "user_id": user_id_from_config, 
                        "status": status_info.get('status', 'unknown'),
                        "authenticated": is_authenticated
                    })
                else:
                    statuses.append({
                        "user_id": user_id_from_config, 
                        "status": "disconnected",
                        "authenticated": is_authenticated
                    })

            except Exception as e:
                uid = "unknown"
                if isinstance(config_data, list) and config_data and isinstance(config_data[0], dict):
                    uid = config_data[0].get('user_id', 'unknown')
                elif isinstance(config_data, dict):
                    uid = config_data.get('user_id', 'unknown')

                logging.warning(f"API: Could not process config for user_id '{uid}': {e}")
                statuses.append({"user_id": uid, "status": "invalid_config", "authenticated": False})
                continue

        return {"configurations": statuses}
    except Exception as e:
        logging.error(f"API: Could not get configuration statuses from DB: {e}")
        raise HTTPException(status_code=500, detail="Could not get configuration statuses.")


@app.get("/api/configurations/{user_id}")
async def get_configuration_by_user_id(user_id: str):
    """
    Returns the content of a specific configuration from the database by user_id.
    """
    if configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    try:
        db_config = configurations_collection.find_one({"config_data.user_id": user_id})
        if not db_config:
            db_config = configurations_collection.find_one({"config_data.0.user_id": user_id})

        if not db_config:
            raise HTTPException(status_code=404, detail="Configuration not found.")

        return JSONResponse(content=db_config.get("config_data"))
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"API: Could not retrieve config for user_id '{user_id}' from DB: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve configuration.")


@app.put("/api/configurations/{user_id}")
async def save_configuration_by_user_id(user_id: str, config: Union[UserConfiguration, List[UserConfiguration]] = Body(...)):
    """
    Saves/updates a configuration to the database, identified by its user_id.
    """
    if configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    try:
        if isinstance(config, list):
            json_data = [item.model_dump(exclude_unset=True) for item in config]
            if not json_data or json_data[0].get("user_id") != user_id:
                raise HTTPException(status_code=400, detail="User ID in URL and body do not match.")
        else:
            json_data = config.model_dump(exclude_unset=True)
            if json_data.get("user_id") != user_id:
                raise HTTPException(status_code=400, detail="User ID in URL and body do not match.")

        db_document = { "config_data": json_data }

        # Use update_one with upsert=True based on the user_id within the config_data
        # This handles both object and array-of-one-object cases.
        query = {
            "$or": [
                {"config_data.user_id": user_id},
                {"config_data.0.user_id": user_id}
            ]
        }
        configurations_collection.update_one(query, {"$set": db_document}, upsert=True)

        logging.info(f"API: Successfully saved configuration for user_id '{user_id}' to DB.")
        return {"status": "success", "user_id": user_id}
    except DuplicateKeyError:
        logging.error(f"API: Duplicate key error for user_id '{user_id}'.")
        raise HTTPException(status_code=409, detail=f"A configuration with user_id '{user_id}' already exists.")
    except Exception as e:
        logging.error(f"API: Could not save configuration for user_id '{user_id}' to DB: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save configuration: {e}")


@app.delete("/api/configurations/{user_id}")
async def delete_configuration_by_user_id(user_id: str):
    """
    Deletes a specific configuration from the database by user_id.
    """
    if configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    try:
        query = {
            "$or": [
                {"config_data.user_id": user_id},
                {"config_data.0.user_id": user_id}
            ]
        }

        # Shutdown active instance if exists
        if user_id in active_users:
            instance_id = active_users[user_id]
            if instance_id in chatbot_instances:
                logging.info(f"API: Stopping active instance for {user_id} before configuration deletion (Cleanup=True).")
                try:
                    await chatbot_instances[instance_id].stop(cleanup_session=True)
                except Exception as e:
                    logging.error(f"API: Failed to stop instance for {user_id}: {e}")
                
                # Force remove from maps immediately
                if user_id in active_users:
                   del active_users[user_id]
                if instance_id in chatbot_instances:
                   del chatbot_instances[instance_id]

        result = configurations_collection.delete_one(query)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Configuration not found.")

        logging.info(f"API: Successfully deleted configuration for user_id '{user_id}' from DB.")
        return {"status": "success", "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"API: Could not delete configuration for user_id '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Could not delete configuration: {e}")


@app.put("/chatbot")
async def create_chatbot(config: UserConfiguration = Body(...)):
    """
    Creates and starts a new chatbot instance based on the provided configuration.
    Returns a JSON object with the result.
    """
    instance_id = str(uuid.uuid4())
    user_id = config.user_id

    # Listener to handle queue movement on connection
    async def status_change_listener(uid: str, status: str):
        if status == 'connected':
             if actionable_queue_manager:
                 actionable_queue_manager.move_user_to_active(uid)
                 logging.info(f"EVENT: User {uid} connected. Moved items to ACTIVE queue.")

    if user_id in active_users:
        # Check if the existing session is effectively dead
        existing_instance_id = active_users[user_id]
        existing_instance = chatbot_instances.get(existing_instance_id)

        try:
            status = await existing_instance.get_status() if existing_instance else {"status": "error"}
            if status.get("status") == "disconnected" or status.get("status") == "error":
                logging.warning(f"API: Found existing 'disconnected' session for user '{user_id}'. Cleaning up to allow new link.")
                if existing_instance:
                    await existing_instance.stop(cleanup_session=False) 
                # Remove from active_users so we can proceed
                if user_id in active_users:
                    del active_users[user_id]
            else:
                error_message = f"Conflict: An active session for user_id '{user_id}' already exists (Status: {status.get('status')})."
                logging.warning(f"API: {error_message}")
                raise HTTPException(status_code=409, detail=error_message)
        except Exception as e:
            # If we fail to check status, assume it's stuck and fail safe? Or block?
            # Let's block to be safe, but log it.
            logging.error(f"API: Failed to check status of conflicting session for '{user_id}': {e}")
            raise HTTPException(status_code=409, detail=f"Conflict: Active session exists and status check failed: {e}")

    logging.info(f"API: Received request to create instance {instance_id} for user {user_id}")

    try:
        loop = asyncio.get_running_loop()
        instance = ChatbotInstance(config=config, on_session_end=remove_active_user, queues_collection=queues_collection, main_loop=loop, on_status_change=status_change_listener)
        chatbot_instances[instance_id] = instance
        await instance.start()

        # Add the new instance to our active user tracking
        active_users[user_id] = instance_id

        logging.info(f"API: Instance {instance_id} for user '{user_id}' is starting in the background.")

        # Update group tracker with new config (only if enabled)
        if group_tracker:
            if config.features.periodic_group_tracking.enabled:
                group_tracker.update_jobs(user_id, config.features.periodic_group_tracking.tracked_groups, config.configurations.user_details.timezone)
            else:
                group_tracker.update_jobs(user_id, [])  # Clear jobs when disabled
        
        # Lifecycle: Queue activation is now handled by status_change_listener upon 'connected' event.
        # No immediate move to active queue here.

        return {
            "successful": [{
                "user_id": user_id,
                "instance_id": instance_id,
                "mode": instance.mode,
                "warnings": instance.warnings
            }],
            "failed": []
        }

    except Exception as e:
        logging.error(f"API: Failed to create instance for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chatbot/{user_id}/status")
async def get_chatbot_status(user_id: str):
    """
    Polls for the status of a specific chatbot instance using its user_id.
    This can return the QR code for linking, success status, or other states.
    """
    if user_id not in active_users:
        raise HTTPException(status_code=404, detail=f"No active session found for user_id '{user_id}'.")

    instance_id = active_users[user_id]
    instance = chatbot_instances.get(instance_id)

    if not instance:
        # This case should ideally not happen if active_users is consistent with chatbot_instances
        logging.error(f"API: Inconsistency detected. user_id '{user_id}' is in active_users but instance '{instance_id}' not found.")
        raise HTTPException(status_code=500, detail="Internal server error: instance not found for active user.")

    try:
        # This endpoint is polled by the modal, so we treat it as a heartbeat.
        status = await instance.get_status(heartbeat=True)
        return status
    except Exception as e:
        logging.error(f"API: Failed to get status for instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


@app.get("/api/queue/{user_id}")
async def get_user_queue(user_id: str):
    """
    Returns a dictionary of all correspondent queues for a user, with the
    correspondent ID as the key and a list of messages as the value.
    """
    if queues_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    try:
        messages_cursor = queues_collection.find(
            {"user_id": user_id},
            {"_id": 0, "user_id": 0, "provider_name": 0}
        ).sort("id", 1)

        # Group messages by correspondent_id
        grouped_messages = {}
        for message in messages_cursor:
            correspondent_id = message.pop("correspondent_id", "__missing_correspondent_id__")
            if correspondent_id not in grouped_messages:
                grouped_messages[correspondent_id] = []
            grouped_messages[correspondent_id].append(message)

        return JSONResponse(content=grouped_messages)
    except Exception as e:
        logging.error(f"API: Failed to get queue for user '{user_id}' from DB: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get queue from database: {e}")


@app.get("/api/context/{user_id}")
async def get_user_context(user_id: str):
    """
    Returns a dictionary of all correspondent contexts for a user.
    """
    if user_id not in active_users:
        raise HTTPException(status_code=404, detail=f"No active session found for user_id '{user_id}'.")

    instance_id = active_users[user_id]
    instance = chatbot_instances.get(instance_id)
    if not instance or not instance.chatbot_model:
        raise HTTPException(status_code=404, detail="Chatbot model not found for this user.")

    try:
        histories = instance.chatbot_model.get_all_histories()
        # Format the histories for JSON response
        formatted_histories = {
            correspondent: [msg.content for msg in history.messages]
            for correspondent, history in histories.items()
        }
        return JSONResponse(content=formatted_histories)
    except Exception as e:
        logging.error(f"API: Failed to get context for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get context: {e}")


@app.delete("/api/queue/{user_id}/{correspondent_id}", status_code=204)
async def clear_correspondent_queue(user_id: str, correspondent_id: str):
    """
    Clears a specific correspondent's queue for a user, both in the database
    and in the active in-memory queue if a session is running.
    """
    if queues_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    try:
        # Handle the special case for messages without a correspondent_id
        if correspondent_id == "__missing_correspondent_id__":
            query = {"user_id": user_id, "correspondent_id": {"$exists": False}}
        else:
            query = {"user_id": user_id, "correspondent_id": correspondent_id}

        # First, verify that the queue exists in the database
        if queues_collection.count_documents(query, limit=1) == 0:
            error_msg = f"queue {user_id}/{correspondent_id} does not exist"
            return JSONResponse(status_code=410, content={"ERROR": True, "ERROR_MSG": error_msg})

        # Delete messages from MongoDB
        result = queues_collection.delete_many(query)
        logging.info(f"API: Deleted {result.deleted_count} messages from DB for user '{user_id}', correspondent '{correspondent_id}'.")

        # If there's an active session, clear the in-memory queue as well
        if user_id in active_users:
            instance_id = active_users[user_id]
            instance = chatbot_instances.get(instance_id)
            if instance and instance.user_queues_manager:
                queue = instance.user_queues_manager.get_queue(correspondent_id)
                if queue:
                    queue.clear()
                    logging.info(f"API: Cleared in-memory queue for user '{user_id}', correspondent '{correspondent_id}'.")

        return Response(status_code=204)

    except Exception as e:
        logging.error(f"API: Failed to clear queue for user '{user_id}', correspondent '{correspondent_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to clear queue.")


@app.delete("/api/queue/{user_id}", status_code=204)
async def clear_all_user_queues(user_id: str):
    """
    Clears all of a user's queues, both in the database and in the active
    in-memory queues if a session is running.
    """
    if queues_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    try:
        # First, verify that the user has any queues in the database
        query = {"user_id": user_id}
        if queues_collection.count_documents(query, limit=1) == 0:
            error_msg = f"no queues exist for user {user_id}"
            return JSONResponse(status_code=410, content={"ERROR": True, "ERROR_MSG": error_msg})

        # Delete all user's messages from MongoDB
        result = queues_collection.delete_many(query)
        logging.info(f"API: Deleted {result.deleted_count} total messages from DB for user '{user_id}'.")

        # If there's an active session, clear all in-memory queues for the user
        if user_id in active_users:
            instance_id = active_users[user_id]
            instance = chatbot_instances.get(instance_id)
            if instance and instance.user_queues_manager:
                all_queues = instance.user_queues_manager.get_all_queues()
                for queue in all_queues:
                    queue.clear()
                logging.info(f"API: Cleared all {len(all_queues)} in-memory queues for user '{user_id}'.")

        return Response(status_code=204)

    except Exception as e:
        logging.error(f"API: Failed to clear queues for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to clear queues.")


@app.delete("/chatbot/{user_id}")
async def unlink_chatbot(user_id: str):
    """
    Stops and unlinks a specific chatbot instance using its user_id.
    This involves cleaning up the session data.
    """
    if user_id not in active_users:
        raise HTTPException(status_code=404, detail=f"No active session found for user_id '{user_id}' to unlink.")

    instance_id = active_users[user_id]
    instance = chatbot_instances.get(instance_id)

    if not instance:
        # This case should ideally not happen.
        logging.error(f"API: Inconsistency detected. user_id '{user_id}' is in active_users but instance '{instance_id}' not found during unlink.")
        # Still, we should clean up the active_users entry
        del active_users[user_id]
        # Invalidate queue even if instance missing
        if actionable_queue_manager:
             actionable_queue_manager.move_user_to_holding(user_id)
        raise HTTPException(status_code=500, detail="Internal server error: instance not found for active user.")

    try:
        # Stop the instance and clean up the session data on the provider.
        await instance.stop(cleanup_session=True)
        
        # Lifecycle: User Unlinked -> Move items to Holding Queue
        if actionable_queue_manager:
             actionable_queue_manager.move_user_to_holding(user_id)
             
        return {"status": "success", "message": f"Session for user '{user_id}' is being terminated and cleaned up."}
    except Exception as e:
        logging.error(f"API: Failed to stop instance for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop instance: {e}")


@app.post("/chatbot/{user_id}/reload")
async def reload_chatbot(user_id: str):
    """
    Gracefully stops and restarts a chatbot instance to apply new configuration.
    The session data is preserved to avoid having to re-link the provider.
    """
    if user_id not in active_users:
        raise HTTPException(status_code=404, detail=f"No active session found for user_id '{user_id}' to reload.")

    logging.info(f"API: Received request to reload instance for user '{user_id}'.")

    try:
        # Step 1: Gracefully stop the current instance, preserving the session
        instance_id = active_users[user_id]
        instance = chatbot_instances.get(instance_id)
        if instance:
            await instance.stop(cleanup_session=False)
            logging.info(f"API: Gracefully stopped instance {instance_id} for user '{user_id}' for reload.")
            
            # Lifecycle: User stopping (Reload) -> Move to Holding
            if actionable_queue_manager:
                actionable_queue_manager.move_user_to_holding(user_id)
        else:
            # Clean up the active_users entry if the instance is missing for some reason
            remove_active_user(user_id)
            raise HTTPException(status_code=500, detail="Internal server error: instance not found for active user.")


        # Step 2: Fetch the latest configuration from the database
        if configurations_collection is None:
            raise HTTPException(status_code=503, detail="Database connection not available.")

        db_config = await run_in_threadpool(configurations_collection.find_one, {"config_data.user_id": user_id})
        if not db_config:
            db_config = await run_in_threadpool(configurations_collection.find_one, {"config_data.0.user_id": user_id})

        if not db_config:
            raise HTTPException(status_code=404, detail="Configuration not found in database for reload.")

        config_data = db_config.get("config_data")
        if isinstance(config_data, list):
            config_data = config_data[0] # Handle legacy array format

        config = UserConfiguration.model_validate(config_data)


        # Step 3: Create and start a new instance with the latest configuration
        new_instance_id = str(uuid.uuid4())
        logging.info(f"API: Restarting instance for user {user_id} as {new_instance_id}")

        # Listener to handle queue movement on connection (reload scenario)
        async def status_change_listener_reload(uid: str, status: str):
            if status == 'connected':
                 if actionable_queue_manager:
                     actionable_queue_manager.move_user_to_active(uid)
                     logging.info(f"EVENT: User {uid} connected (Reload). Moved items to ACTIVE queue.")

        loop = asyncio.get_running_loop()
        new_instance = ChatbotInstance(config=config, on_session_end=remove_active_user, queues_collection=queues_collection, main_loop=loop, on_status_change=status_change_listener_reload)
        chatbot_instances[new_instance_id] = new_instance
        await new_instance.start()

        # Update the active user tracking
        active_users[user_id] = new_instance_id

        # Update group tracker with new config (only if enabled)
        if group_tracker:
            if config.features.periodic_group_tracking.enabled:
                group_tracker.update_jobs(user_id, config.features.periodic_group_tracking.tracked_groups, config.configurations.user_details.timezone)
            else:
                group_tracker.update_jobs(user_id, [])  # Clear jobs when disabled

        logging.info(f"API: Instance {new_instance_id} for user '{user_id}' has been successfully reloaded.")

        return {"status": "success", "message": f"Chatbot for user '{user_id}' is being reloaded."}

    except Exception as e:
        logging.error(f"API: Failed to reload instance for user '{user_id}': {e}")
        # Attempt to clean up if the reload failed midway
        if user_id in active_users:
            del active_users[user_id]
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("shutdown")
def shutdown_event():
    """
    Gracefully shut down all running chatbot instances when the server is stopped.
    This should NOT delete the session data, so it can be resumed on next startup.
    """
    logging.info("API: Server is shutting down. Stopping all chatbot instances...")
    # Create a copy of the dictionary to avoid issues with modifying it while iterating
    for instance_id, instance in list(chatbot_instances.items()):
        logging.info(f"API: Stopping instance {instance_id} for user '{instance.user_id}' (no cleanup)...")
        # We call stop() without cleanup to ensure sessions are persisted.
        asyncio.run(instance.stop(cleanup_session=False))
        # Clean up the dictionaries
        if instance.user_id in active_users:
            del active_users[instance.user_id]

    # It's good practice to clear the main dict as well
    chatbot_instances.clear()
    logging.info("API: All instances stopped and cleaned up.")

    # Shutdown GroupTracker
    if group_tracker:
        group_tracker.shutdown()

    # Shutdown ActionableQueueManager
    global actionable_queue_manager
    if actionable_queue_manager:
        asyncio.run(actionable_queue_manager.stop_consumer())

    # Close MongoDB connection
    if mongo_client:
        mongo_client.close()
        logging.info("API: MongoDB connection closed.")

@app.get("/chatbot/{user_id}/groups")
async def get_active_groups(user_id: str):
    """
    Proxy endpoint to fetch active groups from the chat provider.
    """
    if user_id not in active_users:
        raise HTTPException(status_code=404, detail=f"No active session found for user_id '{user_id}'.")

    instance_id = active_users[user_id]
    instance = chatbot_instances.get(instance_id)

    if not instance or not hasattr(instance.provider_instance, 'get_active_groups'):
        raise HTTPException(status_code=400, detail="Provider does not support fetching groups.")

    try:
        groups = await instance.provider_instance.get_active_groups()
        return {"groups": groups}
    except Exception as e:
        logging.error(f"API: Failed to get active groups for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active groups: {e}")

@app.get("/api/trackedGroupMessages/{user_id}/{group_id}")
async def get_tracked_group_messages(user_id: str, group_id: str, lastPeriods: int = 0, from_time: int = Query(None, alias="from"), until_time: int = Query(None, alias="until")):
    """
    Returns all tracked message periods for a specific group.
    """
    if not group_tracker:
         raise HTTPException(status_code=503, detail="Group Tracker not initialized.")

    try:
        data = group_tracker.get_group_messages(user_id, group_id, last_periods=lastPeriods, time_from=from_time, time_until=until_time)
        if data is None:
             raise HTTPException(status_code=404, detail="Tracked group not found.")
        return JSONResponse(content=data)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"API: Failed to get tracked group messages for user '{user_id}' group '{group_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tracked group messages: {e}")

@app.get("/api/trackedGroupMessages/{user_id}")
async def get_all_tracked_group_messages(user_id: str, lastPeriods: int = 0, from_time: int = Query(None, alias="from"), until_time: int = Query(None, alias="until")):
    """
    Returns tracked message periods for all groups of a user.
    """
    if not group_tracker:
         raise HTTPException(status_code=503, detail="Group Tracker not initialized.")

    try:
        data = group_tracker.get_all_user_messages(user_id, last_periods=lastPeriods, time_from=from_time, time_until=until_time)
        return JSONResponse(content=data)
    except Exception as e:
        logging.error(f"API: Failed to get all tracked group messages for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get all tracked group messages: {e}")

@app.delete("/api/trackedGroupMessages/{user_id}/{group_id}")
async def delete_tracked_group_messages(user_id: str, group_id: str, lastPeriods: int = 0, from_time: int = Query(None, alias="from"), until_time: int = Query(None, alias="until")):
    """
    Deletes tracked message periods for a specific group.
    """
    if not group_tracker:
         raise HTTPException(status_code=503, detail="Group Tracker not initialized.")

    try:
        count = group_tracker.delete_group_messages(user_id, group_id, last_periods=lastPeriods, time_from=from_time, time_until=until_time)
        return {"status": "success", "deleted_count": count}
    except Exception as e:
        logging.error(f"API: Failed to delete tracked group messages for user '{user_id}' group '{group_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete tracked group messages: {e}")

@app.delete("/api/trackedGroupMessages/{user_id}")
async def delete_all_tracked_group_messages(user_id: str, lastPeriods: int = 0, from_time: int = Query(None, alias="from"), until_time: int = Query(None, alias="until")):
    """
    Deletes tracked message periods for all groups of a user.
    """
    if not group_tracker:
         raise HTTPException(status_code=503, detail="Group Tracker not initialized.")

    try:
        count = group_tracker.delete_all_user_messages(user_id, last_periods=lastPeriods, time_from=from_time, time_until=until_time)
        return {"status": "success", "deleted_count": count}
    except Exception as e:
        logging.error(f"API: Failed to delete all tracked group messages for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete all tracked group messages: {e}")







# --- Queue Management Endpoints ---

@app.get("/queues/{queue_type}")
async def get_queue_items(queue_type: str, user_id: Union[str, None] = None):
    """
    Get items from a specific queue (active, failed, unconnected).
    Optional user_id filter.
    """
    if not actionable_queue_manager:
        raise HTTPException(status_code=503, detail="Queue Manager not initialized")
    
    try:
        items = actionable_queue_manager.get_queue_items(queue_type, user_id)
        return {"items": items}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"API: Failed to get queue items: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/queues/{queue_type}/{message_id}")
async def delete_queue_item(queue_type: str, message_id: str):
    """
    Delete a specific item by message_id from the specified queue.
    """
    if not actionable_queue_manager:
        raise HTTPException(status_code=503, detail="Queue Manager not initialized")
    
    try:
        success = actionable_queue_manager.delete_queue_item(queue_type, message_id)
        if success:
            return {"status": "success", "message": f"Item {message_id} deleted from {queue_type}"}
        else:
            raise HTTPException(status_code=404, detail=f"Item {message_id} not found in {queue_type}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"API: Failed to delete queue item: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    # The log_config is modified at the module level to suppress the access logger.
    # We don't need to pass it here again, but we do for clarity.
    uvicorn.run(app, host="0.0.0.0", port=8000)
