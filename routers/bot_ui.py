
import logging
import re
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Body, Depends, Request
from fastapi.responses import JSONResponse
from dependencies import GlobalStateManager, get_global_state
from config_models import (
    RegularBotConfiguration, 
    BotConfiguration, 
    BotGeneralSettings, 
    ChatProviderConfig, 
    ChatProviderSettings, 
    LLMProviderConfig, 
    LLMProviderSettings,
    LLMConfigurations,
    QueueConfig,
    ContextConfig,
    DefaultConfigurations
)

BOT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,30}$')

router = APIRouter(
    prefix="/api/internal/ui/bots",
    tags=["bot_ui"]
)

def ensure_db_connected(state: GlobalStateManager = Depends(get_global_state)) -> GlobalStateManager:
    if state.configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")
    return state

@router.get("/validate/{bot_id}")
async def validate_bot_id(
    bot_id: str, 
    request: Request,
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Validate a bot_id for creation.
    Checks: format, uniqueness, and owner's limit.
    Returns { valid: bool, error_code: str|null, error_message: str|null }
    """
    # 1. Format Check
    if not BOT_ID_PATTERN.match(bot_id):
        return {
            "valid": False,
            "error_code": "invalid_format",
            "error_message": "Bot ID must be 1-30 characters, alphanumeric with _ or - only."
        }
    
    # 2. Uniqueness Check
    existing = await state.configurations_collection.find_one({"config_data.bot_id": bot_id})
    if existing:
        return {
            "valid": False,
            "error_code": "already_exists",
            "error_message": f"Bot ID '{bot_id}' already exists."
        }
    
    # 3. Ownership Limit Check (non-admins only)
    requester_id = request.headers.get("X-User-Id") # The human user ID
    if requester_id and state.credentials_collection is not None:
        cred = await state.credentials_collection.find_one({"user_id": requester_id})
        if cred:
            role = cred.get("role", "user")
            if role != "admin":
                owned = cred.get("owned_bots", [])
                limit = cred.get("max_user_configuration_limit", 5) # Keeping legacy name or update? sticking to what works for now
                if len(owned) >= limit:
                    return {
                        "valid": False,
                        "error_code": "limit_exceeded",
                        "error_message": f"You have reached your limit of {limit} bots."
                    }
    
    return {"valid": True, "error_code": None, "error_message": None}

@router.post("/{bot_id}/validate-config")
async def validate_config(
    bot_id: str, 
    request: Request,
    payload: Dict[str, Any] = Body(...),
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Validate a configuration before saving.
    Checks feature limit for user role only.
    Returns { valid: bool, error_code: str|null, error_message: str|null }
    """
    requester_id = request.headers.get("X-User-Id")
    if not requester_id:
        return {"valid": True, "error_code": None, "error_message": None}
    
    # Check requester role
    is_admin = False
    if state.credentials_collection is not None:
        cred = await state.credentials_collection.find_one({"user_id": requester_id})
        if cred and cred.get("role") == "admin":
            is_admin = True
    
    # Admins always pass
    if is_admin:
        return {"valid": True, "error_code": None, "error_message": None}
    
    # User role: Check feature limit
    features = payload.get("features", {})
    new_count = count_enabled_features(features)
    
    limit = await get_user_feature_limit(requester_id, state)
    current_global_usage_others = await calculate_global_feature_usage(requester_id, state, exclude_bot_id=bot_id)
    
    # Check if we are reducing or keeping same count (allow even if over limit)
    current_config = await state.configurations_collection.find_one({"config_data.bot_id": bot_id})
    old_count = 0
    if current_config:
        current_data = current_config.get("config_data", {})
        current_features = current_data.get("features", {})
        old_count = count_enabled_features(current_features)
    
    proposed_total = current_global_usage_others + new_count
    
    # Validation Rule:
    # 1. If we are under the limit, we are good.
    # 2. If we are over the limit, we are ONLY good if we are reducing/same usage.
    
    if proposed_total > limit:
        if new_count > old_count:
             return {
                "valid": False,
                "error_code": "feature_limit_exceeded",
                "error_message": f"Global feature limit exceeded. You are trying to use {proposed_total} features (New: {new_count}, Others: {current_global_usage_others}), but your limit is {limit}. (Previous Total: {current_global_usage_others + old_count})"
            }
    
    return {"valid": True, "error_code": None, "error_message": None}

@router.get("/schema", response_model=Dict[str, Any])
async def get_bot_ui_schema():
    """
    Get JSON Schema for RegularBotConfiguration.
    Frontend uses this to render the restricted form.
    """
    return RegularBotConfiguration.model_json_schema()

@router.get("/{bot_id}", response_model=RegularBotConfiguration)
async def get_bot_ui_configuration(bot_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Get restricted configuration for UI.
    Automatically filters out sensitive fields via response_model.
    """
    try:
        # We fetch the FULL config, but Pydantic filters it on return
        db_config = await state.configurations_collection.find_one({"config_data.bot_id": bot_id})
        
        if not db_config:
             raise HTTPException(status_code=404, detail="Configuration not found.")
        
        config_data = db_config.get("config_data", {})
        
        # Pydantic validation guarantees strictly typed response
        return config_data
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"UI API: Error getting config for {bot_id}: {e}")
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
        
    owned_bots = cred.get("owned_bots", []) # Changed from owned_user_configurations

    if not owned_bots:
         return 0
    
    # Filter exclusion
    if exclude_bot_id:
         owned_bots = [b for b in owned_bots if b != exclude_bot_id]
         
    if not owned_bots:
         return 0

    # 2. Fetch Configs & Sum
    cursor = state.configurations_collection.find(
        {"config_data.bot_id": {"$in": owned_bots}}
    )
    
    async for doc in cursor:
        config_data = doc.get("config_data", {})
        features = config_data.get("features", {})
        total += count_enabled_features(features)
        
    return total


@router.delete("/{bot_id}")
async def delete_bot_ui(
    bot_id: str, 
    request: Request,
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Delete a bot configuration (Restricted).
    Requires the requester to be the owner of the configuration.
    """
    requester_id = request.headers.get("X-User-Id")
    if not requester_id:
         raise HTTPException(status_code=400, detail="Missing X-User-Id header.")

    # 1. Verify Ownership
    is_owner = (requester_id == bot_id) # Self-deletion? Unlikely for bots, but maybe legacy?
    
    if not is_owner and state.credentials_collection is not None:
        cred = await state.credentials_collection.find_one(
            {"user_id": requester_id, "owned_bots": bot_id}
        )
        if cred:
            is_owner = True
    
    if not is_owner:
        raise HTTPException(status_code=403, detail="Permission Denied: You do not own this configuration.")

    # 2. Perform Deletion
    try:
        if state.group_tracker:
             state.group_tracker.update_jobs(bot_id, [])

        if bot_id in state.active_bots:
            instance_id = state.active_bots[bot_id]
            instance = state.chatbot_instances.get(instance_id)
            if instance:
                await instance.stop(cleanup_session=True)
                state.remove_active_bot(bot_id)
        
        if state.async_message_delivery_queue_manager:
             await state.async_message_delivery_queue_manager.move_user_to_holding(bot_id)

        query = {"config_data.bot_id": bot_id}
        
        result = await state.configurations_collection.delete_one(query)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Configuration not found.")
        
        # 3. Remove from owner's owned_bots list
        if state.credentials_collection is not None:
            await state.credentials_collection.update_one(
                {"owned_bots": bot_id},
                {"$pull": {"owned_bots": bot_id}}
            )
        
        logging.info(f"UI API: Deleted configuration for {bot_id} by {requester_id}.")
        return {"status": "success", "bot_id": bot_id}
    except Exception as e:
        logging.error(f"UI API: Error deleting bot {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not delete bot: {e}")

@router.patch("/{bot_id}")
async def update_bot_ui_configuration(
    bot_id: str, 
    request: Request,
    patch_data: RegularBotConfiguration = Body(...), 
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Create or update bot configuration (UI).
    - If config doesn't exist: creates a new one (used by regular users for creation).
    - If config exists: partially updates it.
    Enforces max_feature_limit in both cases.
    """
    try:
        # 1. Validation
        if patch_data.bot_id != bot_id:
            raise HTTPException(status_code=400, detail="Bot ID mismatch.")

        # Check if config exists
        current_config = await state.configurations_collection.find_one({"config_data.bot_id": bot_id})

        owner_id = request.headers.get("X-User-Id")

        # Check for Admin Override
        is_admin = False
        if owner_id and state.credentials_collection is not None:
            cred = await state.credentials_collection.find_one({"user_id": owner_id})
            if cred and cred.get("role") == "admin":
                is_admin = True

        if not current_config:
            # === CREATION PATH ===
            # Check Feature Limit
            if not is_admin and owner_id:
                limit = await get_user_feature_limit(owner_id, state)
                current_global_usage = await calculate_global_feature_usage(owner_id, state, exclude_bot_id=None)
                new_count = count_enabled_features(patch_data.features)
                total_usage = current_global_usage + new_count

                if total_usage > limit:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Global feature limit exceeded. You are trying to use {total_usage} features (New: {new_count}, Others: {current_global_usage}), but your limit is {limit}."
                    )

            # Construct Default Full Configuration (matching bot_management.py defaults)
            full_settings = BotGeneralSettings(
                user_details=patch_data.configurations.user_details,
                chat_provider_config=ChatProviderConfig(
                    provider_name=DefaultConfigurations.chat_provider_name,
                    provider_config=ChatProviderSettings()
                ),
                llm_configs=LLMConfigurations(
                    high=LLMProviderConfig(
                        provider_name=DefaultConfigurations.llm_provider_name,
                        provider_config=LLMProviderSettings(
                            model=DefaultConfigurations.llm_model_high,
                            api_key_source=DefaultConfigurations.llm_api_key_source,
                            temperature=DefaultConfigurations.llm_temperature,
                            reasoning_effort=DefaultConfigurations.llm_reasoning_effort
                        )
                    ),
                    low=LLMProviderConfig(
                        provider_name=DefaultConfigurations.llm_provider_name,
                        provider_config=LLMProviderSettings(
                            model=DefaultConfigurations.llm_model_low,
                            api_key_source=DefaultConfigurations.llm_api_key_source,
                            temperature=DefaultConfigurations.llm_temperature,
                            reasoning_effort=DefaultConfigurations.llm_reasoning_effort
                        )
                    )
                ),
                queue_config=QueueConfig(),
                context_config=ContextConfig()
            )

            full_config = BotConfiguration(
                bot_id=bot_id,
                configurations=full_settings,
                features=patch_data.features
            )

            # Save to DB
            await state.configurations_collection.insert_one({"config_data": full_config.model_dump()})

            # Add to Owner's List
            if owner_id and state.credentials_collection is not None:
                await state.credentials_collection.update_one(
                    {"user_id": owner_id},
                    {"$addToSet": {"owned_bots": bot_id}}
                )

            logging.info(f"UI API: Created new configuration for {bot_id} via PATCH (Owner: {owner_id})")

            return RegularBotConfiguration(
                bot_id=bot_id,
                configurations=patch_data.configurations,
                features=patch_data.features
            )

        else:
            # === UPDATE PATH ===
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
                current_data = current_config.get("config_data", {})
                current_features = current_data.get("features", {})
                old_count = count_enabled_features(current_features)

                new_features = update_payload["features"]
                new_count = count_enabled_features(new_features)

                if is_admin:
                    pass
                elif not owner_id:
                    limit = 5
                    new_global_total = new_count
                    if new_global_total > limit:
                        raise HTTPException(status_code=400, detail="Feature limit exceeded.")
                else:
                    limit = await get_user_feature_limit(owner_id, state)
                    current_global_usage_others = await calculate_global_feature_usage(owner_id, state, exclude_bot_id=bot_id)

                    old_global_total = current_global_usage_others + old_count
                    new_global_total = current_global_usage_others + new_count

                    if new_global_total > old_global_total and new_global_total > limit:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Global feature limit exceeded. You are trying to use {new_global_total} features (New: {new_count}, Others: {current_global_usage_others}), but your limit is {limit}. (Previous Total: {old_global_total})"
                        )

            # 4. Perform Update
            result = await state.configurations_collection.update_one(
                {"config_data.bot_id": bot_id},
                {"$set": mongo_update}
            )

            if result.matched_count == 0:
                raise HTTPException(status_code=404, detail="Configuration not found.")

            logging.info(f"UI API: Updated configuration for {bot_id}. Fields: {list(mongo_update.keys())}")
            return {"status": "success", "bot_id": bot_id}

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"UI API: Error in PATCH for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not process configuration: {e}")
