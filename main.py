import uuid
import threading
import sys
import logging
import time
import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from typing import Dict, Any, List, Union
from uvicorn.config import LOGGING_CONFIG

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

CONFIGURATIONS_DIR = Path("configurations")

@app.on_event("startup")
async def startup_event():
    """
    Ensure the configurations directory exists on startup.
    """
    if not CONFIGURATIONS_DIR.exists():
        console_log(f"API: Configurations directory not found at '{CONFIGURATIONS_DIR}'. Creating it.")
        CONFIGURATIONS_DIR.mkdir(parents=True, exist_ok=True)
    else:
        console_log(f"API: Found configurations directory at '{CONFIGURATIONS_DIR}'.")


@app.get("/api/configurations")
async def get_configuration_files():
    """
    Returns a list of all .json configuration files in the configurations directory.
    """
    try:
        files = [f for f in os.listdir(CONFIGURATIONS_DIR) if f.endswith('.json') and os.path.isfile(CONFIGURATIONS_DIR / f)]
        return {"files": files}
    except Exception as e:
        console_log(f"API_ERROR: Could not list configuration files: {e}")
        raise HTTPException(status_code=500, detail="Could not list configuration files.")


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
                    # This is the object choice
                    item['title'] = "Respond Using Llm"
                elif item.get('type') == 'null':
                    # This is the null choice
                    item['title'] = "Collection Only"

    # Explicitly set the api_key to be a string to avoid type ambiguity on the frontend
    if defs_key in schema and 'LLMProviderSettings' in schema[defs_key]:
        api_key_schema = schema[defs_key]['LLMProviderSettings']['properties']['api_key']
        # Pydantic's Optional[str] can become anyOf:[{type:'string'}, {type:'null'}]
        # We simplify this to just a string type for the password widget.
        if 'anyOf' in api_key_schema:
            api_key_schema['type'] = 'string'
            del api_key_schema['anyOf']

    return schema


@app.get("/api/configurations/status")
async def get_all_configurations_status():
    """
    Returns a list of all config files along with their current session status.
    Validates each config file against the UserConfiguration model.
    """
    statuses = []
    try:
        files = [f for f in os.listdir(CONFIGURATIONS_DIR) if f.endswith('.json') and os.path.isfile(CONFIGURATIONS_DIR / f)]
        for filename in files:
            file_path = CONFIGURATIONS_DIR / filename
            try:
                # Read and parse the JSON file first
                with open(file_path, 'r') as f:
                    config_data = json.load(f)

                # Handle both single object and list-of-one-object formats
                if isinstance(config_data, list) and config_data:
                    config_to_validate = config_data[0]
                elif isinstance(config_data, dict):
                    config_to_validate = config_data
                else:
                    # If the format is neither a list with content nor a dict, it's invalid
                    raise ValueError("Configuration file is empty or has an unsupported format.")

                # Validate the data using the Pydantic model
                config = UserConfiguration.model_validate(config_to_validate)
                user_id = config.user_id

                # Now check the status for this user_id
                if user_id in active_users:
                    instance_id = active_users[user_id]
                    instance = chatbot_instances.get(instance_id)
                    if instance:
                        status_info = await run_in_threadpool(instance.get_status)
                        status = status_info.get('status', 'unknown')
                        statuses.append({"filename": filename, "user_id": user_id, "status": status})
                    else:
                        statuses.append({"filename": filename, "user_id": user_id, "status": "error"})
                else:
                    statuses.append({"filename": filename, "user_id": user_id, "status": "disconnected"})

            except (json.JSONDecodeError, Exception) as e:
                # Catches JSON errors and Pydantic validation errors
                console_log(f"API_WARN: Could not process '{filename}': {e}")
                statuses.append({"filename": filename, "user_id": None, "status": "invalid_config"})
                continue

        return {"configurations": statuses}
    except Exception as e:
        console_log(f"API_ERROR: Could not get configuration statuses: {e}")
        raise HTTPException(status_code=500, detail="Could not get configuration statuses.")


@app.get("/api/configurations/{filename}")
async def get_configuration_file(filename: str):
    """
    Returns the content of a specific .json configuration file.
    """
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .json files are supported.")

    file_path = CONFIGURATIONS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Configuration file not found.")

    return FileResponse(path=file_path, media_type='application/json', filename=filename)


@app.put("/api/configurations/{filename}")
async def save_configuration_file(filename: str, config: Union[UserConfiguration, List[UserConfiguration]] = Body(...)):
    """
    Saves a UserConfiguration or a list of them to a specific .json file.
    """
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .json files are supported.")

    file_path = CONFIGURATIONS_DIR / filename
    try:
        with open(file_path, 'w') as f:
            if isinstance(config, list):
                # It's a list of Pydantic models, so we dump each one to a dict
                json_data = [item.model_dump() for item in config]
                # Then we dump the list of dicts to a JSON string
                f.write(json.dumps(json_data, indent=4))
            else:
                # It's a single Pydantic model, so we can use its method directly
                f.write(config.model_dump_json(indent=4))
        console_log(f"API: Successfully saved configuration file '{filename}'")
        return {"status": "success", "filename": filename}
    except Exception as e:
        console_log(f"API_ERROR: Could not save configuration file '{filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Could not save configuration file: {e}")


@app.delete("/api/configurations/{filename}")
async def delete_configuration_file(filename: str):
    """
    Deletes a specific .json configuration file.
    """
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .json files are supported.")

    file_path = CONFIGURATIONS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Configuration file not found.")

    try:
        os.remove(file_path)
        console_log(f"API: Successfully deleted configuration file '{filename}'")
        return {"status": "success", "filename": filename}
    except Exception as e:
        console_log(f"API_ERROR: Could not delete configuration file '{filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Could not delete configuration file: {e}")


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
        # The stop() method will trigger the on_session_end callback,
        # which in turn calls remove_active_user to clean up the state.
        instance.stop()
        return {"status": "success", "message": f"Session for user '{user_id}' is being terminated."}
    except Exception as e:
        console_log(f"API_ERROR: Failed to stop instance for user '{user_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop instance: {e}")


@app.on_event("shutdown")
def shutdown_event():
    """
    Gracefully shut down all running chatbot instances when the server is stopped.
    """
    console_log("API: Server is shutting down. Stopping all chatbot instances...")
    # Create a copy of the dictionary to avoid issues with modifying it while iterating
    for instance_id, instance in list(chatbot_instances.items()):
        console_log(f"API: Stopping instance {instance_id} for user '{instance.user_id}'...")
        instance.stop()
        # Clean up the dictionaries
        if instance.user_id in active_users:
            del active_users[instance.user_id]

    # It's good practice to clear the main dict as well
    chatbot_instances.clear()
    console_log("API: All instances stopped and cleaned up.")

if __name__ == "__main__":
    import uvicorn
    # The log_config is modified at the module level to suppress the access logger.
    # We don't need to pass it here again, but we do for clarity.
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=LOGGING_CONFIG)
