
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from dependencies import GlobalStateManager

router = APIRouter(
    prefix="/api/internal/async-message-delivery-queue",
    tags=["async_message_delivery_queue"]
)

global_state = GlobalStateManager.get_instance()

def _get_collection(queue_type: str):
    manager = global_state.async_message_delivery_queue_manager
    if not manager:
        raise HTTPException(status_code=503, detail="Delivery Queue Manager not initialized.")
    
    if queue_type == "active":
        return manager.queue_collection
    elif queue_type == "failed":
        return manager.failed_collection
    elif queue_type == "unconnected":
        return manager.unconnected_collection
    else:
        raise HTTPException(status_code=400, detail="Invalid queue type. Must be 'active', 'failed', or 'unconnected'.")

@router.get("/{queue_type}/{user_id}")
async def get_delivery_queue(queue_type: str, user_id: str):
    """
    Get items from specific delivery queue for a user.
    """
    collection = _get_collection(queue_type)
    try:
        # Query based on nested message_metadata.message_destination.user_id
        query = {"message_metadata.message_destination.user_id": user_id}
        cursor = collection.find(query, {"_id": 0})
        results = await cursor.to_list(length=None)
        return JSONResponse(content=results)
    except Exception as e:
        logging.error(f"API: Error getting delivery queue {queue_type} for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue items.")

@router.delete("/{queue_type}/{message_id}")
async def delete_delivery_item(queue_type: str, message_id: str):
    """
    Delete a specific message from the queue.
    """
    collection = _get_collection(queue_type)
    try:
        query = {"message_metadata.message_id": message_id}
        result = await collection.delete_one(query)
        if result.deleted_count == 0:
             return JSONResponse(status_code=404, content={"detail": "Message not found."})
        return Response(status_code=204)
    except Exception as e:
        logging.error(f"API: Error deleting item {message_id} from {queue_type}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete item.")
