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
from logging_lock import console_log
from config_models import UserConfiguration, PeriodicGroupTrackingConfig


# Suppress the default uvicorn access logger
access_logger = logging.getLogger("uvicorn.access")
access_logger.disabled = True
# Keep the default uvicorn logger for startup/shutdown messages, but without timestamps for now
# as we can't reliably reformat them.
default_logger = logging.getLogger("uvicorn")
default_logger.propagate = False # Prevent logs from reaching root logger
# You might want to add a handler if you want to see uvicorn's default logs,
# but for now, we are suppressing them to avoid un-timestamped messages.
# For a production setup, a more sophisticated logging setup would be needed.


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

@app.on_event("startup")
async def startup_event():
    """
    Connect to MongoDB and create a unique index on startup.
    """
    global mongo_client, db, configurations_collection, queues_collection, baileys_sessions_collection, group_tracker
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017/")
    console_log(f"API: Connecting to MongoDB at {mongodb_url}")
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
            console_log("API: Ensured unique index exists for 'config_data.user_id'.")
        except Exception as index_e:
            console_log(f"API_WARN: Could not create unique index, it may already exist or there's a data issue: {index_e}")

        console_log("API: Successfully connected to MongoDB.")

        # Initialize GroupTracker
        group_tracker = GroupTracker(mongodb_url, chatbot_instances)
        group_tracker.start()

    except Exception as e:
        console_log(f"API_ERROR: Could not connect to MongoDB: {e}")
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
    console_log(f'INFO:     {request.client.host}:{request.client.port} - "{request.method} {request.url.path} HTTP/{request.scope["http_version"]}" {response.status_code} ({process_time:.2f}ms)')

    return response


def remove_active_user(user_id: str):
    """Callback function to remove a user from the active list."""
    if user_id in active_users:
        instance_id = active_users[user_id]
        console_log(f"API: Session ended for user '{user_id}'. Removing from active list.")
        del active_users[user_id]
        if instance_id in chatbot_instances:
            # Also remove the main instance object to free memory
            del chatbot_instances[instance_id]
    else:
        console_log(f"API_WARN: Tried to remove non-existent user '{user_id}' from active list.")

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
        console_log(f"API_ERROR: Could not list user_ids from DB: {e}")
        raise HTTPException(status_code=500, detail="Could not list user_ids.")


@app.get("/api/configurations/schema", response_model=Dict[str, Any])
async def get_configuration_schema():
    """
    Returns the JSON Schema for the UserConfiguration model, with modifications
    for better frontend rendering.
    """
    schema = UserConfiguration.model_json_schema()
    defs_key = '$defs' if '$defs' in schema else 'definitions'

    # Add descriptive titles to the oneOf choices for llm_provider_config for the dropdown
    if 'llm_provider_config' in schema['properties']:
        llm_config_schema = schema['properties']['llm_provider_config']
        if 'anyOf' in llm_config_schema:
            for item in llm_config_schema['anyOf']:
                if '$ref' in item:
                    item['title'] = "Respond Using Llm"
                elif item.get('type') == 'null':
                    item['title'] = "Collection Only"

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
                         # DEBUG: Log check details
                         console_log(f"API_DEBUG: Checking auth for user_id='{user_id_from_config}' in collection '{baileys_sessions_collection.name}'")
                         auth_doc = await run_in_threadpool(baileys_sessions_collection.find_one, {"_id": f"{user_id_from_config}-creds"})
                         
                         if auth_doc:
                             console_log(f"API_DEBUG: Found auth doc for '{user_id_from_config}'")
                             is_authenticated = True
                         else:
                             console_log(f"API_DEBUG: No auth doc found for '{user_id_from_config}-creds'")
                             pass
                    else:
                        console_log("API_WARN: baileys_sessions_collection is None during status check.")
                except Exception as auth_e:
                    console_log(f"API_WARN: Error checking auth status for {user_id_from_config}: {auth_e}")
                
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

                console_log(f"API_WARN: Could not process config for user_id '{uid}': {e}")
                statuses.append({"user_id": uid, "status": "invalid_config", "authenticated": False})
                continue

        return {"configurations": statuses}
    except Exception as e:
        console_log(f"API_ERROR: Could not get configuration statuses from DB: {e}")
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
        console_log(f"API_ERROR: Could not retrieve config for user_id '{user_id}' from DB: {e}")
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

        console_log(f"API: Successfully saved configuration for user_id '{user_id}' to DB.")
        return {"status": "success", "user_id": user_id}
    except DuplicateKeyError:
        console_log(f"API_ERROR: Duplicate key error for user_id '{user_id}'.")
        raise HTTPException(status_code=409, detail=f"A configuration with user_id '{user_id}' already exists.")
    except Exception as e:
        console_log(f"API_ERROR: Could not save configuration for user_id '{user_id}' to DB: {e}")
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
        result = configurations_collection.delete_one(query)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Configuration not found.")

        console_log(f"API: Successfully deleted configuration for user_id '{user_id}' from DB.")
        return {"status": "success", "user_id": user_id}
    except HTTPException:
        raise
    except Exception as e:
        console_log(f"API_ERROR: Could not delete configuration for user_id '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Could not delete configuration: {e}")


@app.put("/chatbot")
async def create_chatbot(config: UserConfiguration = Body(...)):
    """
    Creates and starts a new chatbot instance based on the provided configuration.
    Returns a JSON object with the result.
    """
    instance_id = str(uuid.uuid4())
    user_id = config.user_id

    if user_id in active_users:
        error_message = f"Conflict: An active session for user_id '{user_id}' already exists."
        console_log(f"API_WARN: {error_message}")
        raise HTTPException(status_code=409, detail=error_message)

    console_log(f"API: Received request to create instance {instance_id} for user {user_id}")

    try:
        loop = asyncio.get_running_loop()
        loop = asyncio.get_running_loop()
        instance = ChatbotInstance(config=config, on_session_end=remove_active_user, queues_collection=queues_collection, main_loop=loop)
        chatbot_instances[instance_id] = instance
        await instance.start()

        # Add the new instance to our active user tracking
        active_users[user_id] = instance_id

        console_log(f"API: Instance {instance_id} for user '{user_id}' is starting in the background.")

        # Update group tracker with new config
        if group_tracker:
            group_tracker.update_jobs(user_id, config.periodic_group_tracking)

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
        console_log(f"API_ERROR: Failed to create instance for user {user_id}: {e}")
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
        console_log(f"API_ERROR: Inconsistency detected. user_id '{user_id}' is in active_users but instance '{instance_id}' not found.")
        raise HTTPException(status_code=500, detail="Internal server error: instance not found for active user.")

    try:
        status = await instance.get_status()
        return status
    except Exception as e:
        console_log(f"API_ERROR: Failed to get status for instance {instance_id}: {e}")
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
        console_log(f"API_ERROR: Failed to get queue for user '{user_id}' from DB: {e}")
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
        console_log(f"API_ERROR: Failed to get context for user '{user_id}': {e}")
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
        console_log(f"API: Deleted {result.deleted_count} messages from DB for user '{user_id}', correspondent '{correspondent_id}'.")

        # If there's an active session, clear the in-memory queue as well
        if user_id in active_users:
            instance_id = active_users[user_id]
            instance = chatbot_instances.get(instance_id)
            if instance and instance.user_queues_manager:
                queue = instance.user_queues_manager.get_queue(correspondent_id)
                if queue:
                    queue.clear()
                    console_log(f"API: Cleared in-memory queue for user '{user_id}', correspondent '{correspondent_id}'.")

        return Response(status_code=204)

    except Exception as e:
        console_log(f"API_ERROR: Failed to clear queue for user '{user_id}', correspondent '{correspondent_id}': {e}")
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
        console_log(f"API: Deleted {result.deleted_count} total messages from DB for user '{user_id}'.")

        # If there's an active session, clear all in-memory queues for the user
        if user_id in active_users:
            instance_id = active_users[user_id]
            instance = chatbot_instances.get(instance_id)
            if instance and instance.user_queues_manager:
                all_queues = instance.user_queues_manager.get_all_queues()
                for queue in all_queues:
                    queue.clear()
                console_log(f"API: Cleared all {len(all_queues)} in-memory queues for user '{user_id}'.")

        return Response(status_code=204)

    except Exception as e:
        console_log(f"API_ERROR: Failed to clear queues for user '{user_id}': {e}")
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
        console_log(f"API_ERROR: Inconsistency detected. user_id '{user_id}' is in active_users but instance '{instance_id}' not found during unlink.")
        # Still, we should clean up the active_users entry
        del active_users[user_id]
        raise HTTPException(status_code=500, detail="Internal server error: instance not found for active user.")

    try:
        # Stop the instance and clean up the session data on the provider.
        await instance.stop(cleanup_session=True)
        return {"status": "success", "message": f"Session for user '{user_id}' is being terminated and cleaned up."}
    except Exception as e:
        console_log(f"API_ERROR: Failed to stop instance for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop instance: {e}")


@app.post("/chatbot/{user_id}/reload")
async def reload_chatbot(user_id: str):
    """
    Gracefully stops and restarts a chatbot instance to apply new configuration.
    The session data is preserved to avoid having to re-link the provider.
    """
    if user_id not in active_users:
        raise HTTPException(status_code=404, detail=f"No active session found for user_id '{user_id}' to reload.")

    console_log(f"API: Received request to reload instance for user '{user_id}'.")

    try:
        # Step 1: Gracefully stop the current instance, preserving the session
        instance_id = active_users[user_id]
        instance = chatbot_instances.get(instance_id)
        if instance:
            await instance.stop(cleanup_session=False)
            console_log(f"API: Gracefully stopped instance {instance_id} for user '{user_id}' for reload.")
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
        console_log(f"API: Restarting instance for user {user_id} as {new_instance_id}")

        loop = asyncio.get_running_loop()
        loop = asyncio.get_running_loop()
        loop = asyncio.get_running_loop()
        new_instance = ChatbotInstance(config=config, on_session_end=remove_active_user, queues_collection=queues_collection, main_loop=loop)
        chatbot_instances[new_instance_id] = new_instance
        await new_instance.start()

        # Update the active user tracking
        active_users[user_id] = new_instance_id

        # Update group tracker with new config
        if group_tracker:
            group_tracker.update_jobs(user_id, config.periodic_group_tracking)

        console_log(f"API: Instance {new_instance_id} for user '{user_id}' has been successfully reloaded.")

        return {"status": "success", "message": f"Chatbot for user '{user_id}' is being reloaded."}

    except Exception as e:
        console_log(f"API_ERROR: Failed to reload instance for user '{user_id}': {e}")
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
    console_log("API: Server is shutting down. Stopping all chatbot instances...")
    # Create a copy of the dictionary to avoid issues with modifying it while iterating
    for instance_id, instance in list(chatbot_instances.items()):
        console_log(f"API: Stopping instance {instance_id} for user '{instance.user_id}' (no cleanup)...")
        # We call stop() without cleanup to ensure sessions are persisted.
        asyncio.run(instance.stop(cleanup_session=False))
        # Clean up the dictionaries
        if instance.user_id in active_users:
            del active_users[instance.user_id]

    # It's good practice to clear the main dict as well
    chatbot_instances.clear()
    console_log("API: All instances stopped and cleaned up.")

    # Shutdown GroupTracker
    global group_tracker
    if group_tracker:
        group_tracker.shutdown()

    # Close MongoDB connection
    if mongo_client:
        mongo_client.close()
        console_log("API: MongoDB connection closed.")

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
        console_log(f"API_ERROR: Failed to get active groups for user '{user_id}': {e}")
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
        console_log(f"API_ERROR: Failed to get tracked group messages for user '{user_id}' group '{group_id}': {e}")
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
        console_log(f"API_ERROR: Failed to get all tracked group messages for user '{user_id}': {e}")
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
        console_log(f"API_ERROR: Failed to delete tracked group messages for user '{user_id}' group '{group_id}': {e}")
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
        console_log(f"API_ERROR: Failed to delete all tracked group messages for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete all tracked group messages: {e}")






if __name__ == "__main__":
    import uvicorn
    # The log_config is modified at the module level to suppress the access logger.
    # We don't need to pass it here again, but we do for clarity.
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=LOGGING_CONFIG)
