
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from dependencies import GlobalStateManager

router = APIRouter(
    prefix="/api/internal/features/periodic_group_tracking",
    tags=["periodic_group_tracking"]
)

global_state = GlobalStateManager.get_instance()

def _ensure_tracker_db():
    if not global_state.group_tracker:
        raise HTTPException(status_code=503, detail="Group Tracking not initialized.")

def _serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB types to JSON serializable."""
    if not doc:
        return doc
    new_doc = {}
    for k, v in doc.items():
        if k == '_id':
            new_doc[k] = str(v)
        elif hasattr(v, 'isoformat'):
             new_doc[k] = v.isoformat()
        elif isinstance(v, list):
             new_doc[k] = [_serialize_doc(i) if isinstance(i, dict) else i for i in v]
        elif isinstance(v, dict):
             new_doc[k] = _serialize_doc(v)
        else:
             new_doc[k] = v
    return new_doc

@router.get("/trackedGroupMessages/{user_id}")
async def get_all_tracked_messages(user_id: str):
    """
    Get all tracked messages for a user.
    """
    _ensure_tracker_db()
    try:
        # Use History Service
        results = global_state.group_tracker.history.get_tracked_periods(user_id=user_id)
        return JSONResponse(content=results)
    except Exception as e:
        logging.error(f"API: Error getting tracked messages for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tracked messages.")

@router.get("/trackedGroupMessages/{user_id}/{group_id}")
async def get_group_tracked_messages(user_id: str, group_id: str):
    """
    Get tracked messages for a specific group.
    """
    _ensure_tracker_db()
    try:
        # Use History Service
        results = global_state.group_tracker.history.get_tracked_periods(user_id=user_id, group_id=group_id)
        return JSONResponse(content=results)
    except Exception as e:
        logging.error(f"API: Error getting tracked messages for {user_id}/{group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tracked messages.")
    except Exception as e:
        logging.error(f"API: Error getting tracked messages for {user_id}/{group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tracked messages.")

@router.delete("/trackedGroupMessages/{user_id}")
async def delete_all_tracked_messages(user_id: str):
    """
    Delete all tracked messages for a user.
    """
    _ensure_tracker_db()
    try:
        result = global_state.group_tracker.tracked_group_periods_collection.delete_many({"user_id": user_id})
        logging.info(f"API: Deleted {result.deleted_count} tracked periods for {user_id}.")
        return Response(status_code=204)
    except Exception as e:
        logging.error(f"API: Error deleting tracked messages for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete tracked messages.")

@router.delete("/trackedGroupMessages/{user_id}/{group_id}")
async def delete_group_tracked_messages(user_id: str, group_id: str):
    """
    Delete tracked messages for a specific group.
    """
    _ensure_tracker_db()
    try:
        result = global_state.group_tracker.tracked_group_periods_collection.delete_many(
            {"user_id": user_id, "group_id": group_id}
        )
        return Response(status_code=204)
    except Exception as e:
        logging.error(f"API: Error deleting tracked messages for {user_id}/{group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete tracked messages.")
