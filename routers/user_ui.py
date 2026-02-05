
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Body, Depends, Request
from fastapi.responses import JSONResponse
from dependencies import GlobalStateManager, get_global_state
from config_models import (
    RegularUserConfiguration, 
    UserConfiguration, 
    ConfigurationsSettings, 
    ChatProviderConfig, 
    ChatProviderSettings, 
    LLMProviderConfig, 
    LLMProviderSettings,
    DefaultConfigurations
)



router = APIRouter(
    prefix="/api/internal/ui/users",
    tags=["user_ui"]
)

def ensure_db_connected(state: GlobalStateManager = Depends(get_global_state)) -> GlobalStateManager:
    if state.configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")
    return state

@router.get("/schema", response_model=Dict[str, Any])
async def get_user_ui_schema():
    """
    Get JSON Schema for RegularUserConfiguration.
    Frontend uses this to render the restricted form.
    """
    return RegularUserConfiguration.model_json_schema()

@router.get("/{user_id}", response_model=RegularUserConfiguration)
async def get_user_ui_configuration(user_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Get restricted configuration for UI.
    Automatically filters out sensitive fields via response_model.
    """
    try:
        # We fetch the FULL config, but Pydantic filters it on return
        db_config = await state.configurations_collection.find_one({"config_data.user_id": user_id})
        
        if not db_config:
             raise HTTPException(status_code=404, detail="Configuration not found.")
        
        config_data = db_config.get("config_data", {})
        
        # Pydantic validation guarantees strictly typed response
        return config_data
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"UI API: Error getting config for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve configuration.")



def count_enabled_features(features_data: Any) -> int:
    """Helper to count enabled features from Pydantic model or dict."""
    count = 0
    data = features_data
    if hasattr(features_data, "model_dump"):
        data = features_data.model_dump()
    
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict) and value.get("enabled") is True:
                count += 1
    return count

async def get_user_feature_limit(user_id: str, state: GlobalStateManager) -> int:
    """Fetch user's max_feature_limit from credentials."""
    if state.credentials_collection is not None:
        cred = await state.credentials_collection.find_one({"user_id": user_id})
        if cred:
            return cred.get("max_feature_limit", 5)
    return 5

@router.put("/{user_id}", response_model=RegularUserConfiguration)
async def create_user_ui_configuration(
    user_id: str,
    request: Request,
    payload: RegularUserConfiguration = Body(...),
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Create a new configuration with restricted view.
    Enforces max_feature_limit.
    """
    try:
        # 1. Validation
        if payload.user_id != user_id:
             raise HTTPException(status_code=400, detail="User ID mismatch.")

        # Check Existience
        existing = await state.configurations_collection.find_one({"config_data.user_id": user_id})
        if existing:
             raise HTTPException(status_code=409, detail="Configuration already exists. Use PATCH to update.")

        # 2. Check Feature Limit
        # Use Requester ID (Owner) for limit check
        owner_id = request.headers.get("X-User-Id")
        if not owner_id:
            # Fallback or strict? Strict is safer.
            # But during local dev without gateway it might fail. 
            # We default to 5 if missing, assuming admin or system.
            limit = 5
        else:
            limit = await get_user_feature_limit(owner_id, state)
            
        new_count = count_enabled_features(payload.features)
        
        if new_count > limit:
             raise HTTPException(
                 status_code=400, 
                 detail=f"Feature limit exceeded. You have enabled {new_count} features, but your limit is {limit}."
             )

        # 3. Construct Default Full Configuration
        default_chat_config = ChatProviderConfig(
            provider_name=DefaultConfigurations.chat_provider_name,
            provider_config=ChatProviderSettings()
        )
        
        default_llm_config = LLMProviderConfig(
            provider_name=DefaultConfigurations.llm_provider_name,
            provider_config=LLMProviderSettings(
                model=DefaultConfigurations.llm_model,
                api_key_source=DefaultConfigurations.llm_api_key_source,
                temperature=DefaultConfigurations.llm_temperature,
                reasoning_effort=DefaultConfigurations.llm_reasoning_effort
            )
        )
        
        full_settings = ConfigurationsSettings(
            user_details=payload.configurations.user_details,
            chat_provider_config=default_chat_config,
            llm_provider_config=default_llm_config
        )
        
        full_config = UserConfiguration(
            user_id=user_id,
            configurations=full_settings,
            features=payload.features
        )
        
        # 4. Save to DB
        await state.configurations_collection.insert_one({"config_data": full_config.model_dump()})
        
        logging.info(f"UI API: Created new configuration for {user_id}")
        
        return RegularUserConfiguration(
            user_id=user_id,
            configurations=payload.configurations,
            features=payload.features
        )

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"UI API: Error creating config for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not create configuration: {e}")

@router.delete("/{user_id}")
async def delete_user_ui(
    user_id: str, 
    request: Request,
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Delete a user configuration (Restricted).
    Requires the requester to be the owner of the configuration.
    """
    requester_id = request.headers.get("X-User-Id")
    if not requester_id:
         raise HTTPException(status_code=400, detail="Missing X-User-Id header.")

    # 1. Verify Ownership
    is_owner = (requester_id == user_id)
    
    if not is_owner and state.credentials_collection is not None:
        cred = await state.credentials_collection.find_one(
            {"user_id": requester_id, "owned_user_configurations": user_id}
        )
        if cred:
            is_owner = True
    
    if not is_owner:
        raise HTTPException(status_code=403, detail="Permission Denied: You do not own this configuration.")

    # 2. Perform Deletion
    try:
        if state.group_tracker:
             state.group_tracker.update_jobs(user_id, [])

        if user_id in state.active_users:
            instance_id = state.active_users[user_id]
            instance = state.chatbot_instances.get(instance_id)
            if instance:
                await instance.stop(cleanup_session=True)
                state.remove_active_user(user_id)
        
        if state.async_message_delivery_queue_manager:
             await state.async_message_delivery_queue_manager.move_user_to_holding(user_id)

        query = {
            "$or": [
                {"config_data.user_id": user_id},
                {"config_data.0.user_id": user_id}
            ]
        }
        result = await state.configurations_collection.delete_one(query)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Configuration not found.")
        
        logging.info(f"UI API: Deleted configuration for {user_id} by {requester_id}.")
        return {"status": "success", "user_id": user_id}
    except Exception as e:
        logging.error(f"UI API: Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not delete user: {e}")

@router.patch("/{user_id}")
async def update_user_ui_configuration(
    user_id: str, 
    request: Request,
    patch_data: RegularUserConfiguration = Body(...), 
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Partially update user configuration (UI).
    Enforces max_feature_limit (only if increasing count).
    """
    try:
        # 1. Validation
        if patch_data.user_id != user_id:
            raise HTTPException(status_code=400, detail="User ID mismatch.")

        # 2. Extract allowed fields
        update_payload = patch_data.model_dump(exclude_unset=True)
        mongo_update = {}
        
        if "features" in update_payload:
            mongo_update["config_data.features"] = update_payload["features"]
            
        if "configurations" in update_payload and "user_details" in update_payload["configurations"]:
             mongo_update["config_data.configurations.user_details"] = update_payload["configurations"]["user_details"]
             
        if not mongo_update:
             return {"status": "ignored", "message": "No valid fields to update"}

        # 3. Check Feature Limit (if features are being updated)
        if "features" in update_payload:
            # Fetch existing config
            current_config = await state.configurations_collection.find_one({"config_data.user_id": user_id})
            if not current_config:
                 raise HTTPException(status_code=404, detail="Configuration not found.")
            
            # Count Old
            current_data = current_config.get("config_data", {})
            current_features = current_data.get("features", {})
            old_count = count_enabled_features(current_features)
            
            # Count New (Merge logic)
            new_features = update_payload["features"]
            new_count = count_enabled_features(new_features)
            
            # Use Requester ID (Owner) for limit check
            owner_id = request.headers.get("X-User-Id")
            if not owner_id:
                limit = 5
            else:
                limit = await get_user_feature_limit(owner_id, state)
            
            # Logic: If count increases AND exceeds limit -> Block
            if new_count > old_count and new_count > limit:
                 raise HTTPException(
                     status_code=400, 
                     detail=f"Feature limit exceeded. You are trying to enable {new_count} features, but your limit is {limit}."
                 )

        # 4. Perform Update
        result = await state.configurations_collection.update_one(
            {"config_data.user_id": user_id},
            {"$set": mongo_update}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Configuration not found.")
            
        logging.info(f"UI API: Updated configuration for {user_id}. Fields: {list(mongo_update.keys())}")
        return {"status": "success", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"UI API: Error updating config for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not update configuration: {e}")
