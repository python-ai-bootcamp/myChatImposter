
import logging
import re
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


USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,30}$')

router = APIRouter(
    prefix="/api/internal/ui/users",
    tags=["user_ui"]
)

def ensure_db_connected(state: GlobalStateManager = Depends(get_global_state)) -> GlobalStateManager:
    if state.configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")
    return state

@router.get("/validate/{user_id}")
async def validate_user_id(
    user_id: str, 
    request: Request,
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Validate a user_id for creation.
    Checks: format, uniqueness, and owner's limit.
    Returns { valid: bool, error_code: str|null, error_message: str|null }
    """
    # 1. Format Check
    if not USER_ID_PATTERN.match(user_id):
        return {
            "valid": False,
            "error_code": "invalid_format",
            "error_message": "User ID must be 1-30 characters, alphanumeric with _ or - only."
        }
    
    # 2. Uniqueness Check
    existing = await state.configurations_collection.find_one({"config_data.user_id": user_id})
    if existing:
        return {
            "valid": False,
            "error_code": "already_exists",
            "error_message": f"User ID '{user_id}' already exists."
        }
    
    # 3. Ownership Limit Check (non-admins only)
    requester_id = request.headers.get("X-User-Id")
    if requester_id and state.credentials_collection is not None:
        cred = await state.credentials_collection.find_one({"user_id": requester_id})
        if cred:
            role = cred.get("role", "user")
            if role != "admin":
                owned = cred.get("owned_user_configurations", [])
                limit = cred.get("max_user_configuration_limit", 5)
                if len(owned) >= limit:
                    return {
                        "valid": False,
                        "error_code": "limit_exceeded",
                        "error_message": f"You have reached your limit of {limit} configurations."
                    }
    
    return {"valid": True, "error_code": None, "error_message": None}

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

async def calculate_global_feature_usage(
    owner_id: str, 
    state: GlobalStateManager, 
    exclude_bot_id: str = None
) -> int:
    """
    Sum of enabled features across ALL bots owned by owner_id.
    Optionally exclude a specific bot_id (useful for updates where we add the new count manually).
    """
    total = 0
    if state.credentials_collection is None:
         return 0
         
    # 1. Get List of Owned Bots
    cred = await state.credentials_collection.find_one({"user_id": owner_id})
    if not cred:
        return 0
        
    owned_bots = cred.get("owned_user_configurations", [])

    if not owned_bots:
         return 0
    
    # Filter exclusion
    if exclude_bot_id:
         owned_bots = [b for b in owned_bots if b != exclude_bot_id]
         
    if not owned_bots:
         return 0

    # 2. Fetch Configs & Sum
    cursor = state.configurations_collection.find(
        {"config_data.user_id": {"$in": owned_bots}}
    )
    
    async for doc in cursor:
        config_data = doc.get("config_data", {})
        features = config_data.get("features", {})
        total += count_enabled_features(features)
        
    return total

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
            current_global_usage = 0
            # For creation without owner_id, we can't check global usage effectively
        else:
            # Check for Admin Override
            is_admin = False
            if state.credentials_collection is not None:
                cred = await state.credentials_collection.find_one({"user_id": owner_id})
                if cred and cred.get("role") == "admin":
                    is_admin = True

            if is_admin:
                 pass
            else:
                limit = await get_user_feature_limit(owner_id, state)
                current_global_usage = await calculate_global_feature_usage(owner_id, state, exclude_bot_id=None)
                
                new_count = count_enabled_features(payload.features)
                total_usage = current_global_usage + new_count
                
                if total_usage > limit:
                     raise HTTPException(
                         status_code=400, 
                         detail=f"Global feature limit exceeded. You have used {total_usage} features (New: {new_count}, Others: {current_global_usage}), but your limit is {limit}."
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
        
        # 3. Remove from owner's owned_user_configurations list
        if state.credentials_collection is not None:
            await state.credentials_collection.update_one(
                {"owned_user_configurations": user_id},
                {"$pull": {"owned_user_configurations": user_id}}
            )
        
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
            
            # Check for Admin Override
            is_admin = False
            if owner_id and state.credentials_collection is not None:
                cred = await state.credentials_collection.find_one({"user_id": owner_id})
                if cred and cred.get("role") == "admin":
                    is_admin = True
            
            if is_admin:
                # Admins bypass feature limits
                pass
            elif not owner_id:
                limit = 5
                current_global_usage_others = 0
                old_global_total = 0 # Cannot verify delta without owner context
                
                # Check Limit for anonymous/system? Default block if over 5
                new_global_total = new_count
                if new_global_total > limit:
                     raise HTTPException(status_code=400, detail="Feature limit exceeded.")
            else:
                limit = await get_user_feature_limit(owner_id, state)
                # Exclude THIS bot from the sum, because we are replacing its features
                current_global_usage_others = await calculate_global_feature_usage(owner_id, state, exclude_bot_id=user_id)
                
                # Calculate OLD global total
                # We need the old count of THIS bot. 
                # current_config is fetched at step 3.
                old_config_data = current_config.get("config_data", {})
                old_features = old_config_data.get("features", {})
                old_count = count_enabled_features(old_features)
                
                old_global_total = current_global_usage_others + old_count
            
                new_global_total = current_global_usage_others + new_count

                # Logic: If count INCREASES (new > old) AND exceeds limit -> Block
                # If count stays same or decreases, allow even if > limit (maintenance mode)
                if new_global_total > old_global_total and new_global_total > limit:
                     raise HTTPException(
                         status_code=400, 
                         detail=f"Global feature limit exceeded. You are trying to use {new_global_total} features (New: {new_count}, Others: {current_global_usage_others}), but your limit is {limit}. (Previous Total: {old_global_total})"
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
