import uuid
import threading
import sys
import logging
from fastapi import FastAPI, HTTPException, Body
from fastapi.concurrency import run_in_threadpool
from typing import Dict, Any, List
from uvicorn.logging import DefaultFormatter, AccessFormatter
from uvicorn.config import LOGGING_CONFIG

from chatbot_manager import ChatbotInstance
from logging_lock import console_log, get_timestamp

class TimestampDefaultFormatter(DefaultFormatter):
    def format(self, record: logging.LogRecord) -> str:
        original_message = super().format(record)
        return f"{get_timestamp()}{original_message}"

class TimestampAccessFormatter(AccessFormatter):
    def format(self, record: logging.LogRecord) -> str:
        original_message = super().format(record)
        return f"{get_timestamp()}{original_message}"

app = FastAPI()

# In-memory storage for chatbot instances
chatbot_instances: Dict[str, ChatbotInstance] = {}

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

        console_log(f"API: Received request to create instance {instance_id} for user {user_id}")

        try:
            # The 'user_id' check is now done before this block.

            def blocking_init_and_start(current_config, current_instance_id) -> ChatbotInstance:
                """
                This function contains the synchronous, blocking code.
                It returns the created instance so its mode can be inspected.
                """
                instance = ChatbotInstance(config=current_config)
                chatbot_instances[current_instance_id] = instance
                instance.start()
                return instance

            # Run the blocking code in a thread pool to avoid blocking the event loop
            instance = await run_in_threadpool(blocking_init_and_start, config, instance_id)

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

@app.get("/chatbot/{instance_id}/status")
async def get_chatbot_status(instance_id: str):
    """
    Polls for the status of a specific chatbot instance.
    This can return the QR code for linking, success status, or other states.
    """
    console_log(f"API: Received status request for instance {instance_id}")
    instance = chatbot_instances.get(instance_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    try:
        status = instance.get_status()
        return status
    except Exception as e:
        console_log(f"API_ERROR: Failed to get status for instance {instance_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")

@app.on_event("shutdown")
def shutdown_event():
    """
    Gracefully shut down all running chatbot instances when the server is stopped.
    """
    console_log("API: Server is shutting down. Stopping all chatbot instances...")
    for instance_id, instance in chatbot_instances.items():
        console_log(f"API: Stopping instance {instance_id}...")
        instance.stop()
    console_log("API: All instances stopped.")

if __name__ == "__main__":
    import uvicorn

    log_config = LOGGING_CONFIG.copy()
    log_config["formatters"]["default"]["()"] = "main.TimestampDefaultFormatter"
    log_config["formatters"]["access"]["()"] = "main.TimestampAccessFormatter"

    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
