import importlib
import logging
from typing import Literal, Optional, Type
from motor.motor_asyncio import AsyncIOMotorCollection
from langchain_core.language_models import BaseChatModel

from config_models import LLMProviderConfig
from llm_providers.base import BaseLlmProvider
from services.token_consumption_service import TokenConsumptionService
from services.tracked_llm import TokenTrackingCallback

logger = logging.getLogger(__name__)

def find_provider_class(module, base_class: Type) -> Optional[Type]:
    """Helper to find the provider class in a module."""
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, base_class) and obj is not base_class:
            return obj
    return None

def create_tracked_llm(
    llm_config: LLMProviderConfig,
    user_id: str,
    bot_id: str,
    feature_name: str,
    config_tier: Literal["high", "low"],
    token_consumption_collection: AsyncIOMotorCollection
) -> BaseChatModel:
    """
    Central factory for obtaining LLM instances with automatic token tracking.
    
    The returned LLM has a TokenTrackingCallback pre-attached.
    Features use it as a normal LangChain LLM — tracking is invisible.
    
    Args:
        llm_config: Configuration for the LLM provider.
        user_id: The ID of the user (context).
        bot_id: The ID of the bot (context).
        feature_name: The name of the feature requesting the LLM.
        config_tier: "high" or "low" tier.
        token_consumption_collection: MongoDB collection for events.
        
    Returns:
        A LangChain BaseChatModel instance with tracking enabled.
    """
    try:
        # 1. Dynamically load provider
        llm_provider_module = importlib.import_module(f"llm_providers.{llm_config.provider_name}")
        LlmProviderClass = find_provider_class(llm_provider_module, BaseLlmProvider)
        
        if not LlmProviderClass:
            raise ImportError(f"Could not find a subclass of BaseLlmProvider in llm_providers.{llm_config.provider_name}")

        # 2. Create Provider instance & get LLM
        # Note: Some legacy providers might expect user_id in init
        provider = LlmProviderClass(config=llm_config, user_id=user_id)
        llm = provider.get_llm()
        
        # 3. Attach token tracking callback
        if token_consumption_collection is not None:
            token_service = TokenConsumptionService(token_consumption_collection)
            callback = TokenTrackingCallback(
                token_service=token_service,
                user_id=user_id,
                bot_id=bot_id,
                feature_name=feature_name,
                config_tier=config_tier,
                provider_name=llm_config.provider_name
            )
            
            # LangChain models have a 'callbacks' attribute (list of handlers)
            # We append to it (or create it if None/empty)
            # Note: We use callbacks=[callback] in invoke(), but attaching it to the 
            # model instance ensures it runs for all calls made with this instance.
            if hasattr(llm, "callbacks"):
                if llm.callbacks is None:
                    llm.callbacks = [callback]
                else:
                    llm.callbacks.append(callback)
            else:
                 # Fallback for models that might not have callbacks property initialized
                 llm.callbacks = [callback]
                 
        else:
            logger.warning("create_tracked_llm: token_consumption_collection is None! Token tracking DISABLED.")

        return llm

    except Exception as e:
        logger.error(f"Failed to create tracked LLM: {e}")
        raise
