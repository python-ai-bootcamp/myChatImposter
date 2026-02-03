
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Body, Depends
from fastapi.responses import JSONResponse
from dependencies import GlobalStateManager, get_global_state
from config_models import (
    RegularUserConfiguration, 
    UserConfiguration, 
    ConfigurationsSettings, 
    ChatProviderConfig, 
    ChatProviderSettings, 
    LLMProviderConfig, 
    LLMProviderSettings
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


@router.put("/{user_id}", response_model=RegularUserConfiguration)
async def create_user_ui_configuration(
    user_id: str,
    payload: RegularUserConfiguration = Body(...),
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Create a new configuration with default values, overridden by the provided restricted configuration.
    This allows regular users to create new 'bots' (configurations) without access to admin settings.
    """
    try:
        # 1. Validation
        if payload.user_id != user_id:
             raise HTTPException(status_code=400, detail="User ID mismatch.")

        # 2. Check existence
        existing = await state.configurations_collection.find_one({"config_data.user_id": user_id})
        if existing:
             # If it exists, we could reject or upsert. 
             # For safety/clarity, creating a NEW restricted user should probably fail if it already exists?
             # Or we treat it as an overwrite of the restricted fields?
             # Let's reject to prevent accidental overwrite of ADMIN configs by a regular user.
             # Use PATCH to update existing.
             raise HTTPException(status_code=409, detail="Configuration already exists. Use PATCH to update.")

        # 3. Construct Default Full Configuration
        # We need to construct the full UserConfiguration object.
        # We'll use defaults for sensitive fields (Queue, etc.)
        
        default_chat_config = ChatProviderConfig(
            provider_name="whatsapp_baileys",
            provider_config=ChatProviderSettings()
        )
        
        default_llm_config = LLMProviderConfig(
            provider_name="openai",
            provider_config=LLMProviderSettings(
                model="gpt-4o",
                api_key_source="environment" 
            )
        )
        
        # Merge incoming restricted payload
        full_settings = ConfigurationsSettings(
            user_details=payload.configurations.user_details,
            chat_provider_config=default_chat_config,
            llm_provider_config=default_llm_config
            # queue_config and context_config use defaults from model
        )
        
        full_config = UserConfiguration(
            user_id=user_id,
            configurations=full_settings,
            features=payload.features
        )
        
        # 4. Save to DB
        await state.configurations_collection.insert_one({"config_data": full_config.model_dump()})
        
        logging.info(f"UI API: Created new configuration for {user_id}")
        
        # Return the restricted view
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

@router.patch("/{user_id}")
async def update_user_ui_configuration(
    user_id: str, 
    patch_data: RegularUserConfiguration = Body(...), 
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Partially update user configuration (UI).
    Only updates fields present in RegularUserConfiguration.
    """
    try:
        # 1. Validation
        if patch_data.user_id != user_id:
            raise HTTPException(status_code=400, detail="User ID mismatch.")

        # 2. Extract ALLOWED fields only
        # We explicitly dump 'configurations.user_details' and 'features'
        # Any other field is ignored by definition of the model
        update_payload = patch_data.model_dump(exclude_unset=True)
        
        # 3. Build MongoDB $set query
        # We must be careful not to overwrite the entire 'configurations' object 
        # because it contains 'queue_config' which is missing here!
        # We map explicitly to dot-notation for safety.
        
        mongo_update = {}
        
        # Features (Safe to replace entire object usually, but let's be granular)
        if "features" in update_payload:
            mongo_update["config_data.features"] = update_payload["features"]
            
        # User Details (Nested inside configurations)
        if "configurations" in update_payload and "user_details" in update_payload["configurations"]:
             mongo_update["config_data.configurations.user_details"] = update_payload["configurations"]["user_details"]
             
        if not mongo_update:
             return {"status": "ignored", "message": "No valid fields to update"}

        result = await state.configurations_collection.update_one(
            {"config_data.user_id": user_id},
            {"$set": mongo_update}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Configuration not found.")
            
        logging.info(f"UI API: Updated configuration for {user_id}. Fields: {list(mongo_update.keys())}")
        return {"status": "success", "user_id": user_id}

    except Exception as e:
        logging.error(f"UI API: Error updating config for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not update configuration: {e}")
