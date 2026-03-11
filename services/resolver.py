from typing import Literal, overload
from dependencies import get_global_state
from config_models import ConfigTier, ChatCompletionProviderConfig, BaseModelProviderConfig

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
async def resolve_model_config(
    bot_id: str,
    config_tier: ConfigTier
) -> BaseModelProviderConfig:
    """Returns the specific model provider config for the given bot and tier.
    Returns ChatCompletionProviderConfig for high/low tiers; BaseModelProviderConfig for image_moderation.
    """
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
    
    # Parse with the appropriate config model based on tier
    if config_tier == "image_moderation":
        return BaseModelProviderConfig.model_validate(tier_data)
    else:
        return ChatCompletionProviderConfig.model_validate(tier_data)
