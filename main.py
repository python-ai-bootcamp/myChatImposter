import uuid
import threading
import sys
from fastapi import FastAPI, HTTPException, Body
from fastapi.concurrency import run_in_threadpool
from typing import Dict, Any, List

from chatbot_manager import ChatbotInstance
from logging_lock import lock

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

        with lock:
            sys.stdout.buffer.write(f"API: Received request to create instance {instance_id} for user {user_id}\n".encode('utf-8'))
            sys.stdout.flush()

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

            with lock:
                sys.stdout.buffer.write(f"API: Instance {instance_id} for user '{user_id}' is starting in the background.\n".encode('utf-8'))
                sys.stdout.flush()

            successful_creations.append({
                "user_id": user_id,
                "instance_id": instance_id,
                "mode": instance.mode
            })

        except Exception as e:
            with lock:
                # Using backslashreplace to handle potential encoding issues in the error message
                error_message = f"API_ERROR: Failed to create instance for user {user_id}: {e}\n"
                sys.stdout.buffer.write(error_message.encode('utf-8', 'backslashreplace'))
                sys.stdout.flush()
            failed_creations.append({"user_id": user_id, "error": str(e)})

    return {"successful": successful_creations, "failed": failed_creations}

@app.get("/chatbot/{instance_id}/status")
async def get_chatbot_status(instance_id: str):
    """
    Polls for the status of a specific chatbot instance.
    This can return the QR code for linking, success status, or other states.
    """
    with lock:
        sys.stdout.buffer.write(f"API: Received status request for instance {instance_id}\n".encode('utf-8'))
        sys.stdout.flush()
    instance = chatbot_instances.get(instance_id)

    if not instance:
        raise HTTPException(status_code=404, detail="Instance not found")

    try:
        status = instance.get_status()
        return status
    except Exception as e:
        with lock:
            sys.stdout.buffer.write(f"API_ERROR: Failed to get status for instance {instance_id}: {e}\n".encode('utf-8'))
            sys.stdout.flush()
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")

@app.on_event("shutdown")
def shutdown_event():
    """
    Gracefully shut down all running chatbot instances when the server is stopped.
    """
    with lock:
        sys.stdout.buffer.write("API: Server is shutting down. Stopping all chatbot instances...\n".encode('utf-8'))
        sys.stdout.flush()
    for instance_id, instance in chatbot_instances.items():
        with lock:
            sys.stdout.buffer.write(f"API: Stopping instance {instance_id}...\n".encode('utf-8'))
            try:
                sys.stdout.flush()
            except OSError:
                pass
        instance.stop()
    with lock:
        sys.stdout.buffer.write("API: All instances stopped.\n".encode('utf-8'))
        try:
            sys.stdout.flush()
        except OSError:
            pass

if __name__ == "__main__":
    import uvicorn
    # To run this directly for testing: uvicorn main:app --reload
    # The user will likely run it as per their deployment preference.
    uvicorn.run(app, host="0.0.0.0", port=8000)
