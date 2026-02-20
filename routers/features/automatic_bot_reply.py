
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from dependencies import GlobalStateManager

router = APIRouter(
    prefix="/api/internal/features/automatic_bot_reply",
    tags=["automatic_bot_reply"]
)

global_state = GlobalStateManager.get_instance()

def _ensure_db_connected():
    if global_state.queues_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")

# --- Queue Endpoints ---

@router.get("/queue/{bot_id}")
async def get_bot_queue(bot_id: str):
    """
    Returns a dictionary of all correspondent queues for a bot.
    """
    _ensure_db_connected()
    try:
        messages_cursor = global_state.queues_collection.find(
            {"bot_id": bot_id},
            {"_id": 0, "bot_id": 0, "provider_name": 0}
        ).sort("id", 1)

        grouped_messages = {}
        async for message in messages_cursor:
            correspondent_id = message.pop("correspondent_id", "__missing_correspondent_id__")
            if correspondent_id not in grouped_messages:
                grouped_messages[correspondent_id] = []
            grouped_messages[correspondent_id].append(message)

        return JSONResponse(content=grouped_messages)
    except Exception as e:
        logging.error(f"API: Failed to get queue for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue.")

@router.delete("/queue/{bot_id}")
async def clear_all_bot_queues(bot_id: str):
    """
    Clears all of a bot's queues (DB + In-Memory).
    """
    _ensure_db_connected()
    try:
        query = {"bot_id": bot_id}
        doc_count = await global_state.queues_collection.count_documents(query, limit=1)
        if doc_count == 0:
             return JSONResponse(status_code=410, content={"ERROR": True, "ERROR_MSG": f"no queues exist for bot {bot_id}"})
        
        result = await global_state.queues_collection.delete_many(query)
        logging.info(f"API: Deleted {result.deleted_count} messages for {bot_id}.")

        # Clear In-Memory
        instance = global_state.get_chatbot_instance_by_bot(bot_id)
        if instance and instance.bot_queues_manager:
            all_queues = instance.bot_queues_manager.get_all_queues()
            for queue in all_queues:
                queue.clear()
            logging.info(f"API: Cleared in-memory queues for {bot_id}.")
            
        return Response(status_code=204)
    except Exception as e:
         logging.error(f"API: Failed to clear queues for {bot_id}: {e}")
         raise HTTPException(status_code=500, detail="Failed to clear queues.")

@router.delete("/queue/{bot_id}/{correspondent_id}")
async def clear_correspondent_queue(bot_id: str, correspondent_id: str):
    """
    Clear specific correspondent queue.
    """
    _ensure_db_connected()
    try:
        if correspondent_id == "__missing_correspondent_id__":
            query = {"bot_id": bot_id, "correspondent_id": {"$exists": False}}
        else:
            query = {"bot_id": bot_id, "correspondent_id": correspondent_id}
        
        doc_count = await global_state.queues_collection.count_documents(query, limit=1)
        if doc_count == 0:
             return JSONResponse(status_code=410, content={"ERROR": True, "ERROR_MSG": f"queue {bot_id}/{correspondent_id} does not exist"})

        await global_state.queues_collection.delete_many(query)
        
        # In-Memory
        instance = global_state.get_chatbot_instance_by_bot(bot_id)
        if instance and instance.bot_queues_manager:
            queue = instance.bot_queues_manager.get_queue(correspondent_id)
            if queue: queue.clear()
            
        return Response(status_code=204)
    except Exception as e:
        logging.error(f"API: Failed to clear queue {bot_id}/{correspondent_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear queue.")

# --- Context Endpoints ---

@router.get("/context/{bot_id}")
async def get_bot_context(bot_id: str):
    """
    Get LLM-ready context.
    """
    if bot_id not in global_state.active_bots:
         raise HTTPException(status_code=404, detail="No active session found.")
    
    instance = global_state.get_chatbot_instance_by_bot(bot_id)
    if not instance:
         raise HTTPException(status_code=404, detail="Instance not found.")
    
    bot_service = instance.features.get("automatic_bot_reply")
    if not bot_service or not bot_service.chatbot_model:
         raise HTTPException(status_code=404, detail="Chatbot model not available (feature disabled?).")
    
    try:
        histories = bot_service.chatbot_model.get_all_histories()
        formatted_histories = {
            correspondent: [msg.content for msg in history.messages]
            for correspondent, history in histories.items()
        }
        return JSONResponse(content=formatted_histories)
    except Exception as e:
        logging.error(f"API: Failed to get context for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get context: {e}")

@router.delete("/context/{bot_id}")
async def clear_bot_context(bot_id: str):
    """
    Clear context (Not implemented in main.py, implementing stub or logic if possible).
    Usually context is derived from queue. If we clear queue, context clears. 
    But if 'Context' implies separate state in ChatbotModel, we should clear it there.
    ChatbotModel.get_all_histories() is read-only usually, derived from queue?
    If so, this might be a no-op or alias to clear queue.
    For now, return 501 Not Implemented or just 204 if it's transient.
    """
    # Assuming context is transient or derived. 
    # If user wants to clear context, they probably mean clear the memory.
    # Currently we don't have a clear_context method in ChatbotModel exposed in main.py logic.
    return Response(status_code=501) 

# --- Incoming Buffer Endpoints ---
# Placeholder implementation as discussed

@router.get("/incoming-buffer/{bot_id}")
async def get_incoming_buffer(bot_id: str):
    return JSONResponse(content={"message": "Not implemented yet. Placeholder for incoming buffer."})

@router.delete("/incoming-buffer/{bot_id}")
async def clear_incoming_buffer(bot_id: str):
    return Response(status_code=501)

@router.delete("/incoming-buffer/{bot_id}/{correspondent_id}")
async def clear_incoming_buffer_correspondent(bot_id: str, correspondent_id: str):
    return Response(status_code=501)
