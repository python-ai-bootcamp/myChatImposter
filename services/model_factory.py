import importlib
import logging
from typing import Literal, Optional, Type, Union
from langchain_core.language_models import BaseChatModel

from config_models import ConfigTier
from model_providers.base import BaseModelProvider
from model_providers.chat_completion import ChatCompletionProvider
from model_providers.image_moderation import ImageModerationProvider
from services.token_consumption_service import TokenConsumptionService
from services.tracked_llm import TokenTrackingCallback
from services.resolver import resolve_user, resolve_model_config
from dependencies import get_global_state

logger = logging.getLogger(__name__)

from utils.provider_utils import find_provider_class

async def create_model_provider(
    bot_id: str,
    feature_name: str,
    config_tier: ConfigTier
) -> Union[BaseChatModel, ImageModerationProvider]:
    """
    Central factory for instantiating model providers based on the database configuration.
    
    If the resolved tier is ChatCompletion, it returns a LangChain BaseChatModel 
    with a TokenTrackingCallback pre-attached. 
    If the resolved tier is ImageModeration, it returns the native ImageModerationProvider.
    """
    try:
        # 1. Resolve configuration and user
        config = await resolve_model_config(bot_id, config_tier)
        user_id = await resolve_user(bot_id)
        
        # 2. Dynamically load provider
        provider_module = importlib.import_module(f"model_providers.{config.provider_name}")
        ProviderClass = find_provider_class(provider_module, BaseModelProvider)
        
        if not ProviderClass:
            raise ImportError(f"Could not find a subclass of BaseModelProvider in model_providers.{config.provider_name}")

        # 3. Create Provider instance (dropping user_id from constructor)
        provider = ProviderClass(config=config)
        
        # 4. Polymorphic tracking attachment
        if isinstance(provider, ChatCompletionProvider):
            llm = provider.get_llm()
            
            state = get_global_state()
            token_consumption_collection = state.token_consumption_collection
            
            if token_consumption_collection is not None:
                token_service = TokenConsumptionService(token_consumption_collection)
                callback = TokenTrackingCallback(
                    token_service=token_service,
                    user_id=user_id,
                    bot_id=bot_id,
                    feature_name=feature_name,
                    config_tier=config_tier,
                    provider_name=config.provider_name
                )
                
                if hasattr(llm, "callbacks"):
                    if llm.callbacks is None:
                        llm.callbacks = [callback]
                    else:
                        llm.callbacks.append(callback)
                else:
                     llm.callbacks = [callback]
            else:
                logger.warning("create_model_provider: token_consumption_collection is None! Token tracking DISABLED.")

            return llm
            
        elif isinstance(provider, ImageModerationProvider):
            return provider
            
        else:
            raise TypeError(f"Unknown provider type: {type(provider)}")

    except Exception as e:
        logger.error(f"Failed to create model provider: {e}")
        raise
