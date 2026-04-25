from typing import Literal, overload
from dependencies import get_global_state
from config_models import ConfigTier, ChatCompletionProviderConfig, BaseModelProviderConfig, ImageTranscriptionProviderConfig, AudioTranscriptionProviderConfig

async def resolve_user(bot_id: str) -> str:
    """Returns the user_id of the owner of the given bot."""
    state = get_global_state()
    owner_doc = await state.credentials_collection.find_one(
        {"owned_bots": bot_id},
        {"user_id": 1}
    )
    if not owner_doc:
        raise ValueError(f"No owner found for bot_id: {bot_id}")
    return owner_doc["user_id"]

@overload
async def resolve_model_config(bot_id: str, config_tier: Literal["high", "low"]) -> ChatCompletionProviderConfig: ...
@overload
async def resolve_model_config(bot_id: str, config_tier: Literal["image_moderation"]) -> BaseModelProviderConfig: ...
@overload
async def resolve_model_config(bot_id: str, config_tier: Literal["image_transcription"]) -> ImageTranscriptionProviderConfig: ...
@overload
async def resolve_model_config(bot_id: str, config_tier: Literal["audio_transcription"]) -> AudioTranscriptionProviderConfig: ...
async def resolve_model_config(
    bot_id: str,
    config_tier: ConfigTier
) -> BaseModelProviderConfig:
    """Returns the specific model provider config for the given bot and tier.
    Uses a dictionary-based registry to map tiers to their Pydantic config models.
    """
    # Dictionary-based registry: maps ConfigTier values to their Pydantic config model classes
    _TIER_REGISTRY = {
        "high": ChatCompletionProviderConfig,
        "low": ChatCompletionProviderConfig,
        "image_moderation": BaseModelProviderConfig,
        "image_transcription": ImageTranscriptionProviderConfig,
        "audio_transcription": AudioTranscriptionProviderConfig,
    }

    state = get_global_state()
    db_config = await state.configurations_collection.find_one(
        {"config_data.bot_id": bot_id},
        {f"config_data.configurations.llm_configs.{config_tier}": 1}
    )
    if not db_config:
        raise ValueError(f"No configuration found for bot_id: {bot_id}")
    tier_data = (
        db_config.get("config_data", {})
        .get("configurations", {})
        .get("llm_configs", {})
        .get(config_tier)
    )
    if not tier_data:
        raise ValueError(f"Tier '{config_tier}' not found in configuration for bot_id: {bot_id}")
    
    # Resolve config class from registry with explicit failure
    config_class = _TIER_REGISTRY.get(config_tier)
    if config_class is None:
        raise ValueError(f"Unknown config tier: {config_tier}")
    return config_class.model_validate(tier_data)

async def resolve_bot_language(bot_id: str) -> str:
    """Returns the language_code for the given bot from its UserDetails configuration.
    
    This function must NEVER raise an exception under any circumstances.
    It always falls back to 'en' on any missing document, missing field, or unexpected error.
    Do NOT mirror resolve_model_config's error-raising pattern.
    """
    try:
        state = get_global_state()
        doc = await state.configurations_collection.find_one(
            {"config_data.bot_id": bot_id},
            {"config_data.configurations.user_details.language_code": 1}
        )
        language_code = (
            doc.get("config_data", {})
            .get("configurations", {})
            .get("user_details", {})
            .get("language_code")
        )
        if language_code:
            return language_code
        return "en"
    except Exception:
        return "en"
