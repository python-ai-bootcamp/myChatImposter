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


@app.get("/api/configurations/status")
async def get_all_configurations_status():
    """
    Returns a list of all config files along with their current session status.
    """
    statuses = []
    try:
        files = [f for f in os.listdir(CONFIGURATIONS_DIR) if f.endswith('.json') and os.path.isfile(CONFIGURATIONS_DIR / f)]
        for filename in files:
            user_id = None
            try:
                with open(CONFIGURATIONS_DIR / filename, 'r') as f:
                    # Assuming the config is a list with one object, or a single object
                    config_data = json.load(f)
                    if isinstance(config_data, list) and config_data:
                        user_id = config_data[0].get('user_id')
                    elif isinstance(config_data, dict):
                         user_id = config_data.get('user_id')
            except (json.JSONDecodeError, IndexError):
                # If file is not valid JSON or is empty, we can't get a user_id
                statuses.append({"filename": filename, "user_id": None, "status": "invalid_config"})
                continue

            if not user_id:
                statuses.append({"filename": filename, "user_id": None, "status": "invalid_config"})
                continue

            # Now check the status for this user_id
            if user_id in active_users:
                instance_id = active_users[user_id]
                instance = chatbot_instances.get(instance_id)
                if instance:
                    # Use a thread pool to avoid blocking on network calls
                    status_info = await run_in_threadpool(instance.get_status)
                    # The status from the provider can be 'open', which we map to 'connected' for the UI
                    status = status_info.get('status', 'unknown')
                    if status == 'open':
                        status = 'connected'
                    statuses.append({"filename": filename, "user_id": user_id, "status": status})
                else:
                    # Data inconsistency, should not happen
                    statuses.append({"filename": filename, "user_id": user_id, "status": "error"})
            else:
                statuses.append({"filename": filename, "user_id": user_id, "status": "disconnected"})

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
async def save_configuration_file(filename: str, content: Union[Dict, List] = Body(...)):
    """
    Saves content to a specific .json configuration file.
    """
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .json files are supported.")

    file_path = CONFIGURATIONS_DIR / filename
    try:
        with open(file_path, 'w') as f:
            json.dump(content, f, indent=4)
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
async def create_chatbots(configs: List[Dict[str, Any]] = Body(...)):
    """
    Creates and starts one or more new chatbot instances based on the provided list of configurations.
    Returns a JSON object with lists of successful and failed creations.
    """
    successful_creations = []
    failed_creations = []

    for config in configs:
        instance_id = str(uuid.uuid4())
        # Pre-validate that user_id exists to ensure it's available for error reporting
        user_id = config.get('user_id')
        if not user_id:
            failed_creations.append({
                "user_id": "unknown",
                "error": "Configuration must contain a 'user_id'"
            })
            continue

        # Check if a session for this user_id already exists
        if user_id in active_users:
            error_message = f"Conflict: An active session for user_id '{user_id}' already exists."
            console_log(f"API_WARN: {error_message}")

            # If this is a single-item request, raise 409. Otherwise, add to failed list.
            if len(configs) == 1:
                raise HTTPException(status_code=409, detail=error_message)

            failed_creations.append({ "user_id": user_id, "error": error_message })
            continue

        console_log(f"API: Received request to create instance {instance_id} for user {user_id}")

        try:
            # The 'user_id' check is now done before this block.

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

            successful_creations.append({
                "user_id": user_id,
                "instance_id": instance_id,
                "mode": instance.mode,
                "warnings": instance.warnings
            })

        except Exception as e:
            console_log(f"API_ERROR: Failed to create instance for user {user_id}: {e}")
            failed_creations.append({"user_id": user_id, "error": str(e)})

    return {"successful": successful_creations, "failed": failed_creations}

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
