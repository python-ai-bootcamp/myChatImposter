
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

@router.get("/trackedGroupMessages/{user_id}")
async def get_all_tracked_messages(user_id: str, state: GlobalStateManager = Depends(ensure_tracker_initialized)):
    """
    Get all tracked messages for a user.
    """
    try:
        # Use History Service
        results = await state.group_tracker.history.get_tracked_periods(user_id=user_id)
        return JSONResponse(content=results)
    except Exception as e:
        logging.error(f"API: Error getting tracked messages for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tracked messages.")

@router.get("/trackedGroupMessages/{user_id}/{group_id}")
async def get_group_tracked_messages(user_id: str, group_id: str, state: GlobalStateManager = Depends(ensure_tracker_initialized)):
    """
    Get tracked messages for a specific group.
    """
    try:
        # Use History Service
        results = await state.group_tracker.history.get_tracked_periods(user_id=user_id, group_id=group_id)
        return JSONResponse(content=results)
    except Exception as e:
        logging.error(f"API: Error getting tracked messages for {user_id}/{group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tracked messages.")

@router.delete("/trackedGroupMessages/{user_id}")
async def delete_all_tracked_messages(user_id: str, state: GlobalStateManager = Depends(ensure_tracker_initialized)):
    """
    Delete all tracked messages for a user.
    """
    try:
        result = await state.group_tracker.history.delete_all_user_messages(user_id)
        logging.info(f"API: Deleted tracked periods for {user_id}.")
        return Response(status_code=204)
    except Exception as e:
        logging.error(f"API: Error deleting tracked messages for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete tracked messages.")

@router.delete("/trackedGroupMessages/{user_id}/{group_id}")
async def delete_group_tracked_messages(user_id: str, group_id: str, state: GlobalStateManager = Depends(ensure_tracker_initialized)):
    """
    Delete tracked messages for a specific group.
    """
    try:
        result = await state.group_tracker.history.delete_group_messages(user_id, group_id)
        return Response(status_code=204)
    except Exception as e:
        logging.error(f"API: Error deleting tracked messages for {user_id}/{group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete tracked messages.")
