
import asyncio
import uuid
import logging
from typing import Dict, Any, List, Union
from fastapi import APIRouter, HTTPException, Body, Response, Request
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from pymongo.errors import DuplicateKeyError

from config_models import (
    UserConfiguration, ConfigurationsSettings, FeaturesConfiguration,
    ChatProviderConfig, LLMProviderConfig, ChatProviderSettings, LLMProviderSettings,
    UserDetails, QueueConfig, ContextConfig
)
from services.session_manager import SessionManager
from services.ingestion_service import IngestionService
from features.automatic_bot_reply.service import AutomaticBotReplyService
from features.kid_phone_safety_tracking.service import KidPhoneSafetyService
from features.kid_phone_safety_tracking.service import KidPhoneSafetyService
from dependencies import GlobalStateManager, get_global_state
from fastapi import Depends

router = APIRouter(
    prefix="/api/internal/users",
    tags=["users"]
)

# Access global state
# Access global state (Removed global var)

# --- Helper Functions ---

# Note: _status_change_listener has been moved to UserLifecycleService
# Use global_state.user_lifecycle_service.create_status_change_callback() instead

async def _get_user_config(user_id: str, configurations_collection) -> Union[dict, None]:
    """
    Helper to retrieve user configuration from DB.
    Expects config_data to be a dict (legacy list format has been migrated).
    """
    try:
        db_config = await configurations_collection.find_one({"config_data.user_id": user_id})
        
        if not db_config:
            return None

        config_data = db_config.get("config_data")
        if isinstance(config_data, dict):
            return config_data
        return None
    except Exception as e:
        logging.error(f"HELPER: Error retrieving config for {user_id}: {e}")
        return None

def ensure_db_connected(state: GlobalStateManager = Depends(get_global_state)) -> GlobalStateManager:
    if state.configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")
    return state


async def _setup_session(config: UserConfiguration, state: GlobalStateManager) -> SessionManager:
    """
    Create and configure a SessionManager with all services and features.
    Used by both link_user and reload_user to avoid duplication.
    
    Returns a fully configured SessionManager (not yet started).
    """
    loop = asyncio.get_running_loop()
    
    instance = SessionManager(
        config=config,
        on_session_end=state.remove_active_user,
        queues_collection=state.queues_collection,
        main_loop=loop,
        on_status_change=state.user_lifecycle_service.create_status_change_callback()
    )
    
    # 1. Ingestion Service
    if state.queues_collection is not None:
        ingester = IngestionService(instance, state.queues_collection)
        ingester.start()
        instance.register_service(ingester)

    # 2. Features Subscription
    if config.features.automatic_bot_reply.enabled:
        bot_service = AutomaticBotReplyService(instance)
        instance.register_message_handler(bot_service.handle_message)
        instance.register_feature("automatic_bot_reply", bot_service)
    
    if config.features.kid_phone_safety_tracking.enabled:
        kid_service = KidPhoneSafetyService(instance)
        instance.register_message_handler(kid_service.handle_message)
        instance.register_feature("kid_phone_safety_tracking", kid_service)
    
    return instance

# --- Routes ---

@router.get("", response_model=Dict[str, List[str]])
async def list_users(state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Returns a list of all user_ids that have a configuration.
    (Formerly /api/configurations)
    """
    try:
        user_ids = []
        cursor = state.configurations_collection.find({}, {"config_data.user_id": 1, "_id": 0})
        async for doc in cursor:
            config_data = doc.get("config_data", {})
            if isinstance(config_data, dict):
                uid = config_data.get("user_id")
                if uid: user_ids.append(uid)
        return {"user_ids": user_ids}
    except Exception as e:
        logging.error(f"API: Could not list user_ids: {e}")
        raise HTTPException(status_code=500, detail="Could not list user_ids.")

@router.get("/{user_id}/info")
async def get_user_info(user_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Get listing-format status for a single user.
    Returns same format as /status but for one user only.
    Used by frontend for regular users via /me/info endpoint.
    """
    try:
        # Check if config exists
        config_data = await _get_user_config(user_id, state.configurations_collection)
        if not config_data:
            raise HTTPException(status_code=404, detail="Configuration not found")

        # Check Auth
        is_authenticated = False
        if state.baileys_sessions_collection is not None:
            auth_doc = await state.baileys_sessions_collection.find_one({"_id": f"{user_id}-creds"})
            if auth_doc:
                is_authenticated = True

        # Check Active Session
        instance = state.get_chatbot_instance_by_user(user_id)
        status_info = {"status": "disconnected"}
        if instance:
            status_info = await instance.get_status()

        # Return in same format as /status endpoint (array with one item)
        return {
            "configurations": [{
                "user_id": user_id,
                "status": status_info.get('status', 'unknown'),
                "authenticated": is_authenticated
            }]
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"API: Error getting info for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not get user info.")

@router.get("/status")
async def list_users_status(state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Returns status for all configurations (admin-only).
    (Formerly /api/configurations/status)
    """
    statuses = []
    try:
        cursor = state.configurations_collection.find({})
        db_configs = await cursor.to_list(length=None)
        for db_config in db_configs:
            config_data = db_config.get("config_data")
            user_id = None
            try:
                # Basic validation/extraction
                if isinstance(config_data, dict):
                    config_val = config_data
                else:
                    continue # Skip invalid

                # We do minimal validation to extract ID, not full model validation to avoid crashes on bad data
                user_id = config_val.get("user_id")
                if not user_id: continue

                # Check Auth
                is_authenticated = False
                if state.baileys_sessions_collection is not None:
                     auth_doc = await state.baileys_sessions_collection.find_one({"_id": f"{user_id}-creds"})
                     if auth_doc: is_authenticated = True

                # Check Active Session
                instance = state.get_chatbot_instance_by_user(user_id)
                status_info = {"status": "disconnected"}
                if instance:
                     status_info = await instance.get_status()

                statuses.append({
                    "user_id": user_id,
                    "status": status_info.get('status', 'unknown'),
                    "authenticated": is_authenticated
                })

            except Exception as e:
                logging.warning(f"API: Error processing status for config: {e}")
                if user_id:
                     statuses.append({"user_id": user_id, "status": "error", "authenticated": False})

        return {"configurations": statuses}
    except Exception as e:
         logging.error(f"API: Error listing statuses: {e}")
         raise HTTPException(status_code=500, detail="Could not get statuses.")

@router.get("/schema", response_model=Dict[str, Any])
async def get_configuration_schema():
    """
    Returns the JSON Schema for UserConfiguration.
    (Formerly /api/configurations/schema)
    """
    schema = UserConfiguration.model_json_schema()
    defs_key = '$defs' if '$defs' in schema else 'definitions'

    # Schema Patching Logic (Preserved from main.py)
    if defs_key in schema and 'LLMProviderSettings' in schema[defs_key]:
        llm_settings_schema = schema[defs_key]['LLMProviderSettings']
        original_props = llm_settings_schema.get('properties', {}).copy()
        original_props.pop('api_key_source', None)
        original_props.pop('api_key', None)

        schema_from_env = {
            "title": "API Key From Environment",
            "properties": {
                "api_key_source": {"const": "environment"},
                **original_props
            }
        }
        schema_explicit = {
            "title": "API Key From User Input",
            "properties": {
                "api_key_source": {"const": "explicit"},
                "api_key": {"type": "string", "title": "API Key", "minLength": 1},
                **original_props
            },
            "required": ["api_key"]
        }
        
        schema[defs_key]['LLMProviderSettings'] = {
            "oneOf": [schema_from_env, schema_explicit]
        }

    # Patch reasoning_effort titles
    if defs_key in schema and 'LLMProviderSettings' in schema[defs_key]:
         llm_settings = schema[defs_key]['LLMProviderSettings']
         if 'oneOf' in llm_settings:
             for branch in llm_settings['oneOf']:
                 if 'properties' in branch and 'reasoning_effort' in branch['properties']:
                     re = branch['properties']['reasoning_effort']
                     if 'anyOf' in re:
                         for option in re['anyOf']:
                             if option.get('type') == 'string' or 'enum' in option:
                                 option['title'] = 'Defined'
                                 option['default'] = 'minimal'
                             elif option.get('type') == 'null':
                                 option['title'] = 'Undefined'

    return schema

@router.get("/defaults", response_model=UserConfiguration)
async def get_user_defaults():
    """
    Get default user configuration template.
    """
    return UserConfiguration(
        user_id="default_template",
        configurations=ConfigurationsSettings(
            user_details=UserDetails(),
            chat_provider_config=ChatProviderConfig(
                provider_name="whatsapp_baileys",
                provider_config=ChatProviderSettings()
            ),
            # Explicitly include LLM config which was missing in frontend defaults
            llm_provider_config=LLMProviderConfig(
                provider_name="openai",
                provider_config=LLMProviderSettings(
                    model="gpt-4",
                    api_key_source="environment"
                )
            ),
            queue_config=QueueConfig(),
            context_config=ContextConfig()
        ),
        features=FeaturesConfiguration()
    )

@router.get("/{user_id}")
async def get_user_configuration(user_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Get user configuration.
    """
    try:
        config_data = await _get_user_config(user_id, state.configurations_collection)
        
        if not config_data:
             raise HTTPException(status_code=404, detail="Configuration not found.")
        
        return JSONResponse(content=config_data)
    except Exception as e:
        logging.error(f"API: Error getting config for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve configuration.")

@router.put("/{user_id}")
async def save_user_configuration(user_id: str, config: UserConfiguration = Body(...), state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Create or update user configuration.
    Only accepts a single UserConfiguration dict (list format is no longer supported).
    """
    try:
        json_data = config.model_dump(exclude_unset=True)
        check_uid = json_data.get("user_id")
        
        if check_uid != user_id:
            raise HTTPException(status_code=400, detail="User ID mismatch.")

        db_document = {"config_data": json_data}
        query = {
            "$or": [
                {"config_data.user_id": user_id},
                {"config_data.0.user_id": user_id}  # Still query both for migration support
            ]
        }
        
        await state.configurations_collection.update_one(query, {"$set": db_document}, upsert=True)
        logging.info(f"API: Saved configuration for {user_id}.")
        return {"status": "success", "user_id": user_id}
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Configuration already exists.")
    except Exception as e:
        logging.error(f"API: Error saving config for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save configuration: {e}")

@router.delete("/{user_id}")
async def delete_user(user_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Delete user configuration and stop/unlink session.
    """
    try:
        # Stop tracking jobs
        if state.group_tracker:
             logging.info(f"API: Stopping tracking jobs for {user_id}")
             state.group_tracker.update_jobs(user_id, [])

        # Stop instance if active
        if user_id in state.active_users:
            instance_id = state.active_users[user_id]
            instance = state.chatbot_instances.get(instance_id)
            if instance:
                logging.info(f"API: Stopping instance for {user_id} before delete.")
                # We call stop(cleanup_session=True) to fully unlink
                await instance.stop(cleanup_session=True)
                state.remove_active_user(user_id)
        
        # Cleanup Lifecycle: Move items to Holding Queue
        if state.async_message_delivery_queue_manager:
             state.async_message_delivery_queue_manager.move_user_to_holding(user_id)

        query = {
            "$or": [
                {"config_data.user_id": user_id},
                {"config_data.0.user_id": user_id}
            ]
        }
        result = await state.configurations_collection.delete_one(query)
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Configuration not found.")
        
        logging.info(f"API: Deleted configuration for {user_id}.")
        return {"status": "success", "user_id": user_id}
    except Exception as e:
        logging.error(f"API: Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not delete user: {e}")

@router.get("/{user_id}/status")
async def get_user_status(user_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Get user status (Polling with Heartbeat).
    (Formerly /chatbot/{user_id}/status)
    """
    if user_id not in state.active_users:
         raise HTTPException(status_code=404, detail="No active session found.")
    
    instance_id = state.active_users[user_id]
    instance = state.chatbot_instances.get(instance_id)
    
    if not instance:
        # Inconsistency check
        state.remove_active_user(user_id)
        raise HTTPException(status_code=500, detail="Instance not found.")
    
    try:
        # HEARTBEAT=TRUE IS CRITICAL FOR PREVENTING ZOMBIE SESSIONS
        status = await instance.get_status(heartbeat=True)
        return status
    except Exception as e:
        logging.error(f"API: Error getting status for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")

@router.post("/{user_id}/actions/link")
async def link_user(user_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Start user session (Link).
    Loads config from DB and starts ChatbotInstance.
    """
    
    # Check for existing session
    if user_id in state.active_users:
        existing_id = state.active_users[user_id]
        existing_inst = state.chatbot_instances.get(existing_id)
        if existing_inst:
            status = await existing_inst.get_status()
            if status.get("status") in ["disconnected", "error"]:
                 logging.info(f"API: Cleaning up dead session for {user_id} before linking.")
                 await existing_inst.stop(cleanup_session=False)
                 state.remove_active_user(user_id)
            else:
                 raise HTTPException(status_code=409, detail=f"Active session exists (Status: {status.get('status')})")

    # Load Config
    try:
        config_data = await _get_user_config(user_id, state.configurations_collection)
        
        if not config_data:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        config = UserConfiguration.model_validate(config_data)

        # Start Instance
        instance_id = str(uuid.uuid4())
        logging.info(f"API: Starting new instance {instance_id} for {user_id}")
        
        instance = await _setup_session(config, state)

        state.chatbot_instances[instance_id] = instance
        await instance.start()
        state.active_users[user_id] = instance_id

        if state.group_tracker:
                 state.group_tracker.update_jobs(user_id, [])

        return {
            "status": "success",
            "message": "Session started",
            "instance_id": instance_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"API: Link failed for {user_id}: {e}")
        # Cleanup if partial failure
        if user_id in state.active_users:
             state.remove_active_user(user_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/actions/unlink")
async def unlink_user(user_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Stop user session (Unlink).
    """
    if user_id not in state.active_users:
         # If not in active_users, we might still want to ensure cleanup of trackers
         if state.group_tracker:
             state.group_tracker.update_jobs(user_id, [])
         raise HTTPException(status_code=404, detail="No active session found.")

    instance_id = state.active_users[user_id]
    instance = state.chatbot_instances.get(instance_id)

    if not instance:
        state.remove_active_user(user_id)
        if state.async_message_delivery_queue_manager:
             state.async_message_delivery_queue_manager.move_user_to_holding(user_id)
        # Ensure trackers stopped
        if state.group_tracker:
             state.group_tracker.update_jobs(user_id, [])
        raise HTTPException(status_code=500, detail="Instance not found.")

    try:
        # Stop tracking jobs
        # Stop tracking jobs (Safe Stop)
        if state.group_tracker:
             logging.info(f"API: Stopping tracking jobs for {user_id}")
             state.group_tracker.stop_tracking_jobs(user_id)

        await instance.stop(cleanup_session=True)
         # Lifecycle: User Unlinked -> Move items to Holding Queue
        if state.async_message_delivery_queue_manager:
             state.async_message_delivery_queue_manager.move_user_to_holding(user_id)
             
        # remove_active_user is called by callback in instance.stop usually, but calling explicit cleanup doesn't hurt if we want to be sure
        # instance.stop calls on_session_end if it finishes gracefully.
        
        return {"status": "success", "message": "Session unlinked"}
    except Exception as e:
        logging.error(f"API: Unlink failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/actions/reload")
async def reload_user(user_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Reload user session.
    Stops current instance (preserves session) and restarts with fresh config.
    """
    if user_id not in state.active_users:
         raise HTTPException(status_code=404, detail="No active session found.")
    
    logging.info(f"API: Reloading user {user_id}")
    
    # 1. Stop Current
    instance_id = state.active_users[user_id]
    instance = state.chatbot_instances.get(instance_id)
    
    try:
        if instance:
            await instance.stop(cleanup_session=False)
            if state.async_message_delivery_queue_manager:
                await state.async_message_delivery_queue_manager.move_user_to_holding(user_id)
        else:
             state.remove_active_user(user_id)
             raise HTTPException(status_code=500, detail="Instance missing.")
        
        # 2. Fetch Config
        config_data = await _get_user_config(user_id, state.configurations_collection)
        
        if not config_data:
             raise HTTPException(status_code=404, detail="Config not found for reload.")
             
        config = UserConfiguration.model_validate(config_data)
        
        # 3. Start New
        new_id = str(uuid.uuid4())
        
        new_instance = await _setup_session(config, state)
        
        state.chatbot_instances[new_id] = new_instance
        await new_instance.start()
        state.active_users[user_id] = new_id
        
        if state.group_tracker:
                  state.group_tracker.stop_tracking_jobs(user_id)
        
        return {"status": "success", "message": "Reloaded"}

    except Exception as e:
        logging.error(f"API: Reload failed for {user_id}: {e}")
        if user_id in state.active_users:
             state.remove_active_user(user_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/groups")
async def get_user_groups(user_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    List user groups.
    """
    if user_id not in state.active_users:
         raise HTTPException(status_code=404, detail="No active session found.")
    
    instance = state.chatbot_instances.get(state.active_users[user_id])
    if not instance or not instance.provider_instance:
         raise HTTPException(status_code=500, detail="Instance not ready.")
    
    try:
        groups = await instance.provider_instance.get_groups()
        return {"user_id": user_id, "groups": groups}
    except Exception as e:
        logging.error(f"API: Error getting groups for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
