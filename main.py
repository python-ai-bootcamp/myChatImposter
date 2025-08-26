import uuid
import threading
import sys
from fastapi import FastAPI, HTTPException, Body
from typing import Dict, Any

from chatbot_manager import ChatbotInstance
from logging_lock import lock

app = FastAPI()

# In-memory storage for chatbot instances
chatbot_instances: Dict[str, ChatbotInstance] = {}

@app.put("/chatbot")
async def create_chatbot(config: Dict[str, Any] = Body(...)):
    """
    Creates and starts a new chatbot instance based on the provided configuration.
    The configuration should be for a single user.
    """
    instance_id = str(uuid.uuid4())
    with lock:
        sys.stdout.buffer.write(f"API: Received request to create instance {instance_id}\n".encode('utf-8'))
        sys.stdout.flush()

    try:
        # The config must have a user_id
        if 'user_id' not in config:
            raise HTTPException(status_code=400, detail="Configuration must contain a 'user_id'")

        instance = ChatbotInstance(config=config)
        chatbot_instances[instance_id] = instance

        # Start the instance in a background thread so we can return the ID immediately
        thread = threading.Thread(target=instance.start)
        thread.daemon = True
        thread.start()

        with lock:
            sys.stdout.buffer.write(f"API: Instance {instance_id} for user '{config['user_id']}' is starting in the background.\n".encode('utf-8'))
            sys.stdout.flush()
        return {"instance_id": instance_id}

    except Exception as e:
        with lock:
            sys.stdout.buffer.write(f"API_ERROR: Failed to create instance {instance_id}: {e}\n".encode('utf-8'))
            sys.stdout.flush()
        # Clean up if instance was partially created
        if instance_id in chatbot_instances:
            del chatbot_instances[instance_id]
        raise HTTPException(status_code=500, detail=f"Failed to create chatbot instance: {e}")

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
            sys.stdout.flush()
        instance.stop()
    with lock:
        sys.stdout.buffer.write("API: All instances stopped.\n".encode('utf-8'))
        sys.stdout.flush()

if __name__ == "__main__":
    import uvicorn
    # To run this directly for testing: uvicorn main:app --reload
    # The user will likely run it as per their deployment preference.
    uvicorn.run(app, host="0.0.0.0", port=8000)
