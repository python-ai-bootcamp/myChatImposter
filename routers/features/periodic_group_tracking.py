
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Response, Depends
from fastapi.responses import JSONResponse
from dependencies import GlobalStateManager, get_global_state

router = APIRouter(
    prefix="/api/internal/features/periodic_group_tracking",
    tags=["periodic_group_tracking"]
)

def ensure_tracker_initialized(state: GlobalStateManager = Depends(get_global_state)) -> GlobalStateManager:
    if not state.group_tracker:
        raise HTTPException(status_code=503, detail="Group Tracking not initialized.")
    return state

@router.get("/trackedGroupMessages/{bot_id}")
async def get_all_tracked_messages(bot_id: str, state: GlobalStateManager = Depends(ensure_tracker_initialized)):
    """
    Get all tracked messages for a user.
    """
    try:
        # Use History Service
        results = await state.group_tracker.history.get_tracked_periods(bot_id=bot_id)
        return JSONResponse(content=results)
    except Exception as e:
        logging.error(f"API: Error getting tracked messages for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tracked messages.")

@router.get("/trackedGroupMessages/{bot_id}/{group_id}")
async def get_group_tracked_messages(bot_id: str, group_id: str, state: GlobalStateManager = Depends(ensure_tracker_initialized)):
    """
    Get tracked messages for a specific group.
    """
    try:
        # Use History Service
        results = await state.group_tracker.history.get_tracked_periods(bot_id=bot_id, group_id=group_id)
        return JSONResponse(content=results)
    except Exception as e:
        logging.error(f"API: Error getting tracked messages for {bot_id}/{group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tracked messages.")

@router.delete("/trackedGroupMessages/{bot_id}")
async def delete_all_tracked_messages(bot_id: str, state: GlobalStateManager = Depends(ensure_tracker_initialized)):
    """
    Delete all tracked messages for a user.
    """
    try:
        # Use service layer (Item #020) which also fixes optimization (Item #007)
        deleted_count = await state.group_tracker.history.delete_all_user_messages(bot_id)
        logging.info(f"API: Deleted {deleted_count} tracked periods for {bot_id}.")
        return Response(status_code=204)
    except Exception as e:
        logging.error(f"API: Error deleting tracked messages for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete tracked messages.")

@router.delete("/trackedGroupMessages/{bot_id}/{group_id}")
async def delete_group_tracked_messages(bot_id: str, group_id: str, state: GlobalStateManager = Depends(ensure_tracker_initialized)):
    """
    Delete tracked messages for a specific group.
    """
    try:
        # Use service layer (Item #020) - Direct DB access was using wrong field name 'group_id' -> 'tracked_group_unique_identifier'
        await state.group_tracker.history.delete_group_messages(bot_id, group_id)
        return Response(status_code=204)
    except Exception as e:
        logging.error(f"API: Error deleting tracked messages for {bot_id}/{group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete tracked messages.")
