
import asyncio
import uuid
import logging
from typing import Dict, Any, List, Union
from fastapi import APIRouter, HTTPException, Body, Response, Request, Query, Header
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from pymongo.errors import DuplicateKeyError

from config_models import (
    BotConfiguration, BotGeneralSettings, FeaturesConfiguration,
    ChatProviderConfig, LLMProviderConfig, ChatProviderSettings, LLMProviderSettings,
    UserDetails, QueueConfig, ContextConfig, DefaultConfigurations,
    RegularBotConfiguration, RegularBotGeneralSettings
)

from infrastructure.exceptions import (
    ProviderConnectionError, 
    ProviderAuthenticationError, 
    ProviderError
)
from services.session_manager import SessionManager
from services.ingestion_service import IngestionService
from features.automatic_bot_reply.service import AutomaticBotReplyService
from features.kid_phone_safety_tracking.service import KidPhoneSafetyService
from dependencies import GlobalStateManager, get_global_state
from fastapi import Depends

router = APIRouter(
    prefix="/api/internal/bots",
    tags=["bots"]
)

# --- Helper Functions ---

async def _get_bot_config(bot_id: str, configurations_collection) -> Union[dict, None]:
    """
    Helper to retrieve bot configuration from DB.
    Expects config_data to be a dict.
    """
    try:
        db_config = await configurations_collection.find_one({"config_data.bot_id": bot_id})
        
        if not db_config:
            return None

        config_data = db_config.get("config_data")
        if isinstance(config_data, dict):
            return config_data
        return None
    except Exception as e:
        logging.error(f"HELPER: Error retrieving config for {bot_id}: {e}")
        return None

def ensure_db_connected(state: GlobalStateManager = Depends(get_global_state)) -> GlobalStateManager:
    if state.configurations_collection is None:
        raise HTTPException(status_code=503, detail="Database connection not available.")
    return state


async def _setup_session(config: BotConfiguration, state: GlobalStateManager) -> SessionManager:
    """
    Create and configure a SessionManager with all services and features.
    
    Returns a fully configured SessionManager (not yet started).
    """
    loop = asyncio.get_running_loop()
    
    instance = SessionManager(
        config=config,
        on_session_end=state.remove_active_bot,
        queues_collection=state.queues_collection,
        main_loop=loop,
        on_status_change=state.bot_lifecycle_service.create_status_change_callback()
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
async def list_bots(
    state: GlobalStateManager = Depends(ensure_db_connected),
    bot_ids: List[str] = Query(None)
):
    """
    Returns a list of all bot_ids that have a configuration.
    """
    try:
        bot_ids_list = []
        
        # Build query (filter by provided IDs if any)
        query = {}
        if bot_ids:
            query = {"config_data.bot_id": {"$in": bot_ids}}
            
        cursor = state.configurations_collection.find(query, {"config_data.bot_id": 1, "_id": 0})
        async for doc in cursor:
            config_data = doc.get("config_data", {})
            if isinstance(config_data, dict):
                bid = config_data.get("bot_id")
                if bid: bot_ids_list.append(bid)
        return {"bot_ids": bot_ids_list}
    except Exception as e:
        logging.error(f"API: Could not list bot_ids: {e}")
        raise HTTPException(status_code=500, detail="Could not list bot_ids.")

@router.get("/{bot_id}/info")
async def get_bot_info(bot_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Get listing-format status for a single bot.
    """
    try:
        # Check if config exists
        config_data = await _get_bot_config(bot_id, state.configurations_collection)
        if not config_data:
            raise HTTPException(status_code=404, detail="Configuration not found")

        # Check Auth (Baileys session)
        is_authenticated = False
        if state.baileys_sessions_collection is not None:
            auth_doc = await state.baileys_sessions_collection.find_one({"_id": f"{bot_id}-creds"})
            if auth_doc:
                is_authenticated = True

        # Check Active Session
        instance = state.get_chatbot_instance_by_bot(bot_id)
        status_info = {"status": "disconnected"}
        if instance:
            status_info = await instance.get_status()

        # Determine Owner
        owner = "unknown"
        if state.credentials_collection is not None:
            # Find credential that owns this configuration
            owner_doc = await state.credentials_collection.find_one(
                {"owned_bots": bot_id},
                {"user_id": 1}
            )
            if owner_doc:
                owner = owner_doc.get("user_id")
        
        return {
            "configurations": [{
                "bot_id": bot_id,
                "status": status_info.get('status', 'unknown'),
                "authenticated": is_authenticated,
                "owner": owner
            }]
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"API: Error getting info for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not get bot info.")

@router.get("/status")
async def list_bots_status(
    state: GlobalStateManager = Depends(ensure_db_connected),
    bot_ids: List[str] = Query(None)
):
    """
    Returns status for all bots (admin-only).
    """
    statuses = []
    try:
        # Pre-fetch ownership map for efficiency
        owner_map = {}
        if state.credentials_collection is not None:
             creds_cursor = state.credentials_collection.find({}, {"user_id": 1, "owned_bots": 1})
             async for cred in creds_cursor:
                 owner_id = cred.get("user_id")
                 owned_bots = cred.get("owned_bots", [])
                 for bid in owned_bots:
                     owner_map[bid] = owner_id
        
        # Build Query
        query = {}
        if bot_ids:
            query = {"config_data.bot_id": {"$in": bot_ids}}
            
        cursor = state.configurations_collection.find(query)
        db_configs = await cursor.to_list(length=None)
        for db_config in db_configs:
            config_data = db_config.get("config_data")
            bot_id = None
            try:
                if isinstance(config_data, dict):
                    config_val = config_data
                else:
                    continue
                
                bot_id = config_val.get("bot_id")
                if not bot_id: continue

                # Check Auth
                is_authenticated = False
                if state.baileys_sessions_collection is not None:
                     auth_doc = await state.baileys_sessions_collection.find_one({"_id": f"{bot_id}-creds"})
                     if auth_doc: is_authenticated = True

                # Check Active Session
                instance = state.get_chatbot_instance_by_bot(bot_id)
                status_info = {"status": "disconnected"}
                if instance:
                     status_info = await instance.get_status()

                statuses.append({
                    "bot_id": bot_id,
                    "status": status_info.get('status', 'unknown'),
                    "authenticated": is_authenticated,
                    "owner": owner_map.get(bot_id, "unknown")
                })

            except Exception as e:
                logging.warning(f"API: Error processing status for bot config: {e}")
                if bot_id:
                     statuses.append({"bot_id": bot_id, "status": "error", "authenticated": False})

        return {"configurations": statuses}
    except Exception as e:
         logging.error(f"API: Error listing statuses: {e}")
         raise HTTPException(status_code=500, detail="Could not get statuses.")

@router.get("/schema", response_model=Dict[str, Any])
async def get_configuration_schema(
    x_user_role: str = Header(default="user", alias="X-User-Role")
):
    """
    Returns the JSON Schema for BotConfiguration.
    Filtered by role: Users get RegularBotConfiguration schema.
    """
    if x_user_role == "user":
        return RegularBotConfiguration.model_json_schema()

    schema = BotConfiguration.model_json_schema()
    defs_key = '$defs' if '$defs' in schema else 'definitions'

    # Schema Patching Logic
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

@router.get("/defaults", response_model=Union[BotConfiguration, RegularBotConfiguration])
async def get_bot_defaults(
    x_user_role: str = Header(default="user", alias="X-User-Role")
):
    """
    Get default bot configuration template.
    Filtered based on user role using 'RegularBotConfiguration'.
    """
    full_defaults = BotConfiguration(
        bot_id="default_template",
        configurations=BotGeneralSettings(
            user_details=UserDetails(),
            chat_provider_config=ChatProviderConfig(
                provider_name=DefaultConfigurations.chat_provider_name,
                provider_config=ChatProviderSettings()
            ),
            llm_provider_config=LLMProviderConfig(
                provider_name=DefaultConfigurations.llm_provider_name,
                provider_config=LLMProviderSettings(
                    model=DefaultConfigurations.llm_model,
                    api_key_source=DefaultConfigurations.llm_api_key_source,
                    temperature=DefaultConfigurations.llm_temperature,
                    reasoning_effort=DefaultConfigurations.llm_reasoning_effort
                )
            ),
            queue_config=QueueConfig(),
            context_config=ContextConfig()
        ),
        features=FeaturesConfiguration()
    )

    if x_user_role == "user":
        # Use the restricted model
        user_defaults = RegularBotConfiguration(
            bot_id=full_defaults.bot_id,
            configurations=RegularBotGeneralSettings(
                user_details=full_defaults.configurations.user_details
            ),
            features=full_defaults.features
        )
        return user_defaults

    return full_defaults

@router.get("/{bot_id}")
async def get_bot_configuration(
    bot_id: str, 
    state: GlobalStateManager = Depends(ensure_db_connected),
    x_user_role: str = Header(default="user", alias="X-User-Role")
):
    """
    Get bot configuration.
    Filtered based on user role.
    """
    try:
        config_data = await _get_bot_config(bot_id, state.configurations_collection)
        
        if not config_data:
             raise HTTPException(status_code=404, detail="Configuration not found.")
        
        # Role-based filtering
        if x_user_role == "user":
            try:
                # Validate into full model first to ensure structure
                full_config = BotConfiguration.model_validate(config_data)
                
                # Downcast to RegularBotConfiguration
                user_config = RegularBotConfiguration(
                    bot_id=full_config.bot_id,
                    configurations=RegularBotGeneralSettings(
                        user_details=full_config.configurations.user_details
                    ),
                    features=full_config.features
                )
                
                return JSONResponse(content=user_config.model_dump())
            except Exception as e:
                 logging.error(f"API: Error transforming config for user view: {e}")
                 raise HTTPException(status_code=500, detail="Error preparing user configuration.")
        
        return JSONResponse(content=config_data)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"API: Error getting config for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve configuration.")

@router.put("/{bot_id}")
async def save_bot_configuration(bot_id: str, config: BotConfiguration = Body(...), state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Create or update bot configuration.
    """
    try:
        json_data = config.model_dump(exclude_unset=True)
        check_id = json_data.get("bot_id")
        
        if check_id != bot_id:
            raise HTTPException(status_code=400, detail="Bot ID mismatch.")

        db_document = {"config_data": json_data}
        query = {"config_data.bot_id": bot_id}
        
        await state.configurations_collection.update_one(query, {"$set": db_document}, upsert=True)
        logging.info(f"API: Saved configuration for {bot_id}.")
        return {"status": "success", "bot_id": bot_id}
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Configuration already exists.")
    except Exception as e:
        logging.error(f"API: Error saving config for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save configuration: {e}")

@router.delete("/{bot_id}")
async def delete_bot(bot_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Delete bot configuration and stop/unlink session.
    """
    try:
        if not state.bot_lifecycle_service:
            raise HTTPException(status_code=500, detail="Bot Lifecycle Service not initialized.")

        # 1. Clean up bot data (Instance, Queues, Config, Tracking)
        success = await state.bot_lifecycle_service.delete_bot_data(bot_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Configuration not found.")
        
        # 2. Remove from owner's owned_bots list (Credentials)
        if state.credentials_collection is not None:
            await state.credentials_collection.update_one(
                {"owned_bots": bot_id},
                {"$pull": {"owned_bots": bot_id}}
            )
        
        logging.info(f"API: Deleted configuration for {bot_id}.")
        return {"status": "success", "bot_id": bot_id}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"API: Error deleting bot {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not delete bot: {e}")

@router.get("/{bot_id}/status")
async def get_bot_status(bot_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Get bot status (Polling with Heartbeat).
    """
    if bot_id not in state.active_bots:
         raise HTTPException(status_code=404, detail="No active session found.")
    
    instance_id = state.active_bots[bot_id]
    instance = state.chatbot_instances.get(instance_id)
    
    if not instance:
        state.remove_active_bot(bot_id)
        raise HTTPException(status_code=500, detail="Instance not found.")
    
    try:
        status = await instance.get_status(heartbeat=True)
        return status
    except Exception as e:
        logging.error(f"API: Error getting status for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {e}")

@router.post("/{bot_id}/actions/link")
async def link_bot(bot_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Start bot session (Link).
    """
    
    # Check for existing session
    if bot_id in state.active_bots:
        existing_id = state.active_bots[bot_id]
        existing_inst = state.chatbot_instances.get(existing_id)
        if existing_inst:
            status = await existing_inst.get_status()
            if status.get("status") in ["disconnected", "error"]:
                 logging.info(f"API: Cleaning up dead session for {bot_id} before linking.")
                 await existing_inst.stop(cleanup_session=False)
                 state.remove_active_bot(bot_id)
            else:
                 raise HTTPException(status_code=409, detail=f"Active session exists (Status: {status.get('status')})")

    # Load Config
    try:
        config_data = await _get_bot_config(bot_id, state.configurations_collection)
        
        if not config_data:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        config = BotConfiguration.model_validate(config_data)

        # Start Instance
        instance_id = str(uuid.uuid4())
        logging.info(f"API: Starting new instance {instance_id} for {bot_id}")
        
        instance = await _setup_session(config, state)

        state.chatbot_instances[instance_id] = instance
        await instance.start()
        state.active_bots[bot_id] = instance_id

        if state.group_tracker:
                 state.group_tracker.update_jobs(bot_id, [])

        return {
            "status": "success",
            "message": "Session started",
            "instance_id": instance_id
        }

    except HTTPException:
        raise
    except ProviderAuthenticationError as e:
        logging.error(f"API: Auth failed for {bot_id}: {e}")
        if bot_id in state.active_bots: state.remove_active_bot(bot_id)
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    except ProviderConnectionError as e:
        logging.error(f"API: Connection failed for {bot_id}: {e}")
        if bot_id in state.active_bots: state.remove_active_bot(bot_id)
        raise HTTPException(status_code=503, detail=f"Provider unavailable: {e}")
    except Exception as e:
        logging.error(f"API: Link failed for {bot_id}: {e}")
        if bot_id in state.active_bots:
             state.remove_active_bot(bot_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{bot_id}/actions/unlink")
async def unlink_bot(bot_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Stop bot session (Unlink).
    """
    if bot_id not in state.active_bots:
         if state.group_tracker:
             state.group_tracker.update_jobs(bot_id, [])
         raise HTTPException(status_code=404, detail="No active session found.")

    instance_id = state.active_bots[bot_id]
    instance = state.chatbot_instances.get(instance_id)

    if not instance:
        state.remove_active_bot(bot_id)
        if state.async_message_delivery_queue_manager:
             await state.async_message_delivery_queue_manager.move_user_to_holding(bot_id)
        if state.group_tracker:
             state.group_tracker.update_jobs(bot_id, [])
        raise HTTPException(status_code=500, detail="Instance not found.")

    try:
        if state.group_tracker:
             logging.info(f"API: Stopping tracking jobs for {bot_id}")
             state.group_tracker.stop_tracking_jobs(bot_id)

        await instance.stop(cleanup_session=True)
        if state.async_message_delivery_queue_manager:
             await state.async_message_delivery_queue_manager.move_user_to_holding(bot_id)
             
        return {"status": "success", "message": "Session unlinked"}
    except Exception as e:
        logging.error(f"API: Unlink failed for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{bot_id}/actions/reload")
async def reload_bot(bot_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    Reload bot session.
    """
    if bot_id not in state.active_bots:
         raise HTTPException(status_code=404, detail="No active session found.")
    
    logging.info(f"API: Reloading bot {bot_id}")
    
    # 1. Stop Current
    instance_id = state.active_bots[bot_id]
    instance = state.chatbot_instances.get(instance_id)
    
    try:
        if instance:
            await instance.stop(cleanup_session=False)
            if state.async_message_delivery_queue_manager:
                await state.async_message_delivery_queue_manager.move_user_to_holding(bot_id)
        else:
             state.remove_active_bot(bot_id)
             raise HTTPException(status_code=500, detail="Instance missing.")
        
        # 2. Fetch Config
        config_data = await _get_bot_config(bot_id, state.configurations_collection)
        
        if not config_data:
             raise HTTPException(status_code=404, detail="Config not found for reload.")
             
        config = BotConfiguration.model_validate(config_data)
        
        # 3. Start New
        new_id = str(uuid.uuid4())
        
        new_instance = await _setup_session(config, state)
        
        state.chatbot_instances[new_id] = new_instance
        await new_instance.start()
        state.active_bots[bot_id] = new_id
        
        if state.group_tracker:
                  state.group_tracker.stop_tracking_jobs(bot_id)
        
        return {"status": "success", "message": "Reloaded"}

    except ProviderAuthenticationError as e:
        logging.error(f"API: Reload auth failed for {bot_id}: {e}")
        if bot_id in state.active_bots: state.remove_active_bot(bot_id)
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")
    except ProviderConnectionError as e:
        logging.error(f"API: Reload connection failed for {bot_id}: {e}")
        if bot_id in state.active_bots: state.remove_active_bot(bot_id)
        raise HTTPException(status_code=503, detail=f"Provider unavailable: {e}")
    except Exception as e:
        logging.error(f"API: Reload failed for {bot_id}: {e}")
        if bot_id in state.active_bots:
             state.remove_active_bot(bot_id)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{bot_id}/groups")
async def get_bot_groups(bot_id: str, state: GlobalStateManager = Depends(ensure_db_connected)):
    """
    List bot groups.
    """
    if bot_id not in state.active_bots:
         raise HTTPException(status_code=404, detail="No active session found.")
    
    instance = state.chatbot_instances.get(state.active_bots[bot_id])
    if not instance or not instance.provider_instance:
         raise HTTPException(status_code=500, detail="Instance not ready.")
    
    try:
        groups = await instance.provider_instance.get_groups()
        return {"bot_id": bot_id, "groups": groups}
    except Exception as e:
        logging.error(f"API: Error getting groups for {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{bot_id}/validate-config")
async def validate_bot_config(
    bot_id: str,
    body: Dict[str, Any] = Body(...),
    state: GlobalStateManager = Depends(ensure_db_connected)
):
    """
    Validate bot configuration features against user limits.
    Intended for UI pre-save validation.
    """
    # Note: In a real implementation, this would check against the user's
    # actual limits from their subscription/account.
    # For now, it's a stub that returns valid=True to prevent 404s.
    return {"valid": True, "error_message": None}
