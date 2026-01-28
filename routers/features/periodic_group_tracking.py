
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from dependencies import GlobalStateManager

router = APIRouter(
    prefix="/api/features/periodic_group_tracking",
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
        # Custom Logic: Enrich with Display Name
        # 1. Fetch Group Metadata
        groups_cursor = global_state.group_tracker.tracked_groups_collection.find({"user_id": user_id})
        group_map = {g['group_id']: g.get('display_name', 'Unknown') for g in groups_cursor}

        # 2. Fetch Periods
        cursor = global_state.group_tracker.tracked_group_periods_collection.find({"user_id": user_id}).sort("periodEnd", -1)
        
        results = []
        for doc in cursor:
            s_doc = _serialize_doc(doc)
            # Match identifier
            gid = s_doc.get('tracked_group_unique_identifier')
            if gid:
                s_doc['display_name'] = group_map.get(gid, 'Unknown Group')
            results.append(s_doc)
            
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
        cursor = global_state.group_tracker.tracked_group_periods_collection.find(
            {"user_id": user_id, "group_id": group_id}
        ).sort("periodEnd", -1)
        
        # Fetch display name once
        group_meta = global_state.group_tracker.tracked_groups_collection.find_one({"user_id": user_id, "group_id": group_id})
        display_name = group_meta.get('display_name', 'Unknown') if group_meta else 'Unknown'

        results = []
        for doc in cursor:
             s_doc = _serialize_doc(doc)
             s_doc['display_name'] = display_name
             results.append(s_doc)

        return JSONResponse(content=results)
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
