import importlib
import logging
from typing import Literal, Optional, Type, Union
from langchain_core.language_models import BaseChatModel

from config_models import ConfigTier
from model_providers.base import BaseModelProvider, LLMProvider
from model_providers.chat_completion import ChatCompletionProvider
from model_providers.image_moderation import ImageModerationProvider
from model_providers.image_transcription import ImageTranscriptionProvider
from model_providers.audio_transcription import AudioTranscriptionProvider
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
) -> Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider, AudioTranscriptionProvider]:
    """
    Central factory for instantiating model providers based on the database configuration.
    
    Return contract:
    - ChatCompletionProvider: returns raw BaseChatModel with TokenTrackingCallback attached.
    - ImageModerationProvider: returns the provider wrapper directly (no LLM, no token tracking).
    - ImageTranscriptionProvider: returns the provider wrapper directly (with token tracking
      attached to its internal LLM via get_llm()).
    - AudioTranscriptionProvider: returns the provider wrapper directly with token tracking
      injected via set_token_tracker().
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

        # 3. Create Provider instance
        provider = ProviderClass(config=config)

        # 4. Initialize provider (sets up external HTTP clients etc.)
        await provider.initialize()

        # 5. Universal token infrastructure extraction (before type checks)
        state = get_global_state()
        token_consumption_collection = state.token_consumption_collection

        # 6. Polymorphic tracking attachment
        if isinstance(provider, LLMProvider):
            llm = provider.get_llm()
            
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

            # Subtype-specific return: ChatCompletionProvider returns raw LLM,
            # ImageTranscriptionProvider returns the wrapper
            if isinstance(provider, ChatCompletionProvider):
                return llm
            else:
                return provider
            
        elif isinstance(provider, ImageModerationProvider):
            return provider

        elif isinstance(provider, AudioTranscriptionProvider):
            if token_consumption_collection is not None:
                token_service = TokenConsumptionService(token_consumption_collection)

                async def token_tracker(input_tokens: int, output_tokens: int, cached_input_tokens: int = 0):
                    await token_service.record_event(
                        user_id=user_id,
                        bot_id=bot_id,
                        feature_name=feature_name,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cached_input_tokens=cached_input_tokens,
                        config_tier=config_tier
                    )

                provider.set_token_tracker(token_tracker)
            else:
                logger.warning("create_model_provider: token_consumption_collection is None! Token tracking DISABLED for AudioTranscriptionProvider.")
            return provider
            
        else:
            raise TypeError(f"Unknown provider type: {type(provider)}")

    except Exception as e:
        logger.error(f"Failed to create model provider: {e}")
        raise
