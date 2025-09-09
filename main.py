import uuid
import threading
import sys
import logging
import time
import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from typing import Dict, Any, List, Union
from uvicorn.config import LOGGING_CONFIG
from pymongo import MongoClient

from chatbot_manager import ChatbotInstance
from logging_lock import console_log
from config_models import UserConfiguration

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

@app.on_event("startup")
async def startup_event():
    """
    Connect to MongoDB and create a unique index on startup.
    """
    global mongo_client, db, configurations_collection
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017/")
    console_log(f"API: Connecting to MongoDB at {mongodb_url}")
    try:
        mongo_client = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command('ismaster')
        db = mongo_client.get_database("chat_manager")
        configurations_collection = db.get_collection("configurations")

        # Create a unique index on the 'user_id' field of the 'config_data'
        # This is a bit more complex because user_id is inside an array of objects.
        # To handle both object and array-of-one-object, we need to be careful.
        # A simple index on "config_data.user_id" works for the object case.
        # MongoDB can index into arrays, so it should also work for the array case.
        try:
            # Check if the 'config_data' field is an array and handle accordingly
            # This is a simplified approach. A more robust solution might involve a schema migration.
            configurations_collection.create_index("config_data.user_id", unique=True)
            console_log("API: Ensured unique index exists for 'config_data.user_id'.")
        except Exception as index_e:
            console_log(f"API_WARN: Could not create unique index, it may already exist or there's a data issue: {index_e}")

        console_log("API: Successfully connected to MongoDB.")
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


# In-memory storage for chatbot instances
chatbot_instances: Dict[str, ChatbotInstance] = {}
active_users: Dict[str, str] = {} # Maps user_id to instance_id

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
        # Extract the user_id from the config_data field.
        # This assumes config_data is either a single object or an array with one object.
        # Using an aggregation pipeline is more robust for this.
        pipeline = [
            {"$unwind": "$config_data"}, # Deconstructs the array field
            {"$project": {"user_id": "$config_data.user_id", "_id": 0}}
        ]
        # A more direct approach if config_data is always an object or you need to handle both
        # For simplicity, we'll assume the structure is consistent and query directly.
        # Note: a simple find with projection is harder if the data can be an object OR an array.
        # The aggregation pipeline handles both cases gracefully after an initial check or assumption.

        # Let's try a simpler find and handle the two cases in python
        user_ids = []
        for doc in configurations_collection.find({}, {"config_data.user_id": 1, "_id": 0}):
            config_data = doc.get("config_data", {})
            if isinstance(config_data, list) and config_data:
                user_ids.append(config_data[0].get("user_id"))
            elif isinstance(config_data, dict):
                user_ids.append(config_data.get("user_id"))

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

    # Remove the old, problematic anyOf logic for api_key
    if defs_key in schema and 'LLMProviderSettings' in schema[defs_key]:
        llm_settings_schema = schema[defs_key]['LLMProviderSettings']
        if 'properties' in llm_settings_schema and 'api_key' in llm_settings_schema['properties']:
            # The model is Optional[str], so we make it a simple string field that is not required by default.
            # Its requirement will be handled by the dependency logic below.
            llm_settings_schema['properties']['api_key'] = {
                "title": "API Key",
                "type": "string"
            }

        # Add dependency logic: if api_key_source is 'explicit', then api_key is required.
        llm_settings_schema['dependencies'] = {
            "api_key_source": {
                "oneOf": [
                    {
                        "properties": {
                            "api_key_source": {"const": "environment"}
                        }
                    },
                    {
                        "properties": {
                            "api_key_source": {"const": "explicit"},
                        },
                        "required": ["api_key"]
                    }
                ]
            }
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

                if user_id_from_config in active_users:
                    instance_id = active_users[user_id_from_config]
                    instance = chatbot_instances.get(instance_id)
                    status = await run_in_threadpool(instance.get_status) if instance else {"status": "error"}
                    statuses.append({"user_id": user_id_from_config, "status": status.get('status', 'unknown')})
                else:
                    statuses.append({"user_id": user_id_from_config, "status": "disconnected"})

            except Exception as e:
                # Attempt to find a user_id even if validation fails, for better error reporting
                uid = "unknown"
                if isinstance(config_data, list) and config_data and isinstance(config_data[0], dict):
                    uid = config_data[0].get('user_id', 'unknown')
                elif isinstance(config_data, dict):
                    uid = config_data.get('user_id', 'unknown')

                console_log(f"API_WARN: Could not process config for user_id '{uid}': {e}")
                statuses.append({"user_id": uid, "status": "invalid_config"})
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
        # The query needs to look inside the config_data field.
        db_config = configurations_collection.find_one({"config_data.user_id": user_id})
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
            json_data = [item.model_dump() for item in config]
            # Ensure the user_id in the body matches the one in the URL
            if not json_data or json_data[0].get("user_id") != user_id:
                raise HTTPException(status_code=400, detail="User ID in URL and body do not match.")
        else:
            json_data = config.model_dump()
            if json_data.get("user_id") != user_id:
                raise HTTPException(status_code=400, detail="User ID in URL and body do not match.")

        db_document = {
            "config_data": json_data
        }

        # Use update_one with upsert=True based on the user_id within the config_data
        configurations_collection.update_one(
            {"config_data.user_id": user_id},
            {"$set": db_document},
            upsert=True
        )

        console_log(f"API: Successfully saved configuration for user_id '{user_id}' to DB.")
        return {"status": "success", "user_id": user_id}
    except Exception as e:
        console_log(f"API_ERROR: Could not save configuration for user_id '{user_id}' to DB: {e}")
        # Handle potential duplicate key error from the unique index
        if "E11000 duplicate key error" in str(e):
            raise HTTPException(status_code=409, detail=f"A configuration with this user_id already exists.")
        raise HTTPException(status_code=500, detail=f"Could not save configuration: {e}")


@app.delete("/api/configurations/{user_id}")
async def delete_configuration_by_user_id(user_id: str):
    """
    Deletes a specific configuration from the database by user_id.
    """
    if configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

    try:
        # The query needs to look inside the config_data field.
        result = configurations_collection.delete_one({"config_data.user_id": user_id})
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
        def blocking_init_and_start(current_config, current_instance_id) -> ChatbotInstance:
            """
            This function contains the synchronous, blocking code.
            It returns the created instance so its mode can be inspected.
            """
            instance = ChatbotInstance(config=current_config, on_session_end=remove_active_user)
            chatbot_instances[current_instance_id] = instance
            instance.start()
            return instance

        # Run the blocking code in a thread pool to avoid blocking the event loop
        instance = await run_in_threadpool(blocking_init_and_start, config, instance_id)

        # Add the new instance to our active user tracking
        active_users[user_id] = instance_id

        console_log(f"API: Instance {instance_id} for user '{user_id}' is starting in the background.")

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
        status = instance.get_status()
        return status
    except Exception as e:
        console_log(f"API_ERROR: Failed to get status for instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")


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
        instance.stop(cleanup_session=True)
        return {"status": "success", "message": f"Session for user '{user_id}' is being terminated and cleaned up."}
    except Exception as e:
        console_log(f"API_ERROR: Failed to stop instance for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop instance: {e}")


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
        instance.stop(cleanup_session=False)
        # Clean up the dictionaries
        if instance.user_id in active_users:
            del active_users[instance.user_id]

    # It's good practice to clear the main dict as well
    chatbot_instances.clear()
    console_log("API: All instances stopped and cleaned up.")

    # Close MongoDB connection
    if mongo_client:
        mongo_client.close()
        console_log("API: MongoDB connection closed.")


if __name__ == "__main__":
    import uvicorn
    # The log_config is modified at the module level to suppress the access logger.
    # We don't need to pass it here again, but we do for clarity.
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=LOGGING_CONFIG)
