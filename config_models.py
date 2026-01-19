from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class ChatProviderSettings(BaseModel):
    allow_group_messages: bool = False
    process_offline_messages: bool = False
    sync_full_history: bool = Field(default=True, title="Sync Full History")

    class Config:
        extra = 'allow'

class ChatProviderConfig(BaseModel):
    provider_name: str
    provider_config: ChatProviderSettings

class QueueConfig(BaseModel):
    max_messages: int = 10
    max_characters: int = 1000
    max_days: int = 1
    max_characters_single_message: int = 300

class LLMProviderSettings(BaseModel):
    api_key_source: Literal["environment", "explicit"] = Field(
        default="environment",
        title="API Key Source",
        description="Choose how the API key is provided."
    )
    api_key: Optional[str] = Field(
        default=None,
        title="API Key"
    )
    model: str
    temperature: float = 0.7
    reasoning_effort: Optional[Literal["low", "medium", "high", "minimal"]] = None
    seed: Optional[int] = Field(
        default=None,
        title="Seed",
        json_schema_extra={
            "anyOf": [
                {"type": "integer", "title": "Defined"},
                {"type": "null", "title": "Undefined"}
            ]
        }
    )
    record_llm_interactions: bool = Field(
        default=False,
        title="Record Traffic"
    )

    class Config:
        extra = 'allow'

class LLMProviderConfig(BaseModel):
    provider_name: str
    provider_config: LLMProviderSettings

class ContextConfig(BaseModel):
    max_messages: int = 10
    max_characters: int = 1000
    max_days: int = 1
    max_characters_single_message: int = 300
    shared_context: bool = True

class PeriodicGroupTrackingConfig(BaseModel):
    groupIdentifier: str = Field(..., title="Group Identifier", description="The stable JID of the group to track.")
    cronTrackingSchedule: str = Field(..., title="Cron Schedule", description="Cron expression for tracking frequency.")
    displayName: str = Field(..., title="Display Name", description="User-friendly name of the group.")

class UserDetails(BaseModel):
    first_name: str = Field(default="", title="First Name")
    last_name: str = Field(default="", title="Last Name")
    timezone: str = Field(default="UTC", title="Timezone")
    language_code: str = Field(
        default="en",
        title="Language"
    )

# Feature Models
class AutomaticBotReplyFeature(BaseModel):
    enabled: bool = Field(default=False, title="Enable automatic bot replies")
    respond_to_whitelist: List[str] = Field(default_factory=list, title="Respond To Direct Contact Whitelist")
    respond_to_whitelist_group: List[str] = Field(default_factory=list, title="Respond To Group Whitelist")
    chat_system_prompt: str = Field(default="", title="Chat System Prompt")

class PeriodicGroupTrackingFeature(BaseModel):
    enabled: bool = Field(default=False, title="Enable periodic group tracking")
    tracked_groups: List[PeriodicGroupTrackingConfig] = Field(default_factory=list, title="Tracked Groups")

class KidPhoneSafetyTrackingFeature(BaseModel):
    enabled: bool = Field(default=False, title="Enable kid phone safety tracking")

class FeaturesConfiguration(BaseModel):
    automatic_bot_reply: AutomaticBotReplyFeature = Field(default_factory=AutomaticBotReplyFeature, title="Automatic Bot Reply")
    periodic_group_tracking: PeriodicGroupTrackingFeature = Field(default_factory=PeriodicGroupTrackingFeature, title="Periodic Group Tracking")
    kid_phone_safety_tracking: KidPhoneSafetyTrackingFeature = Field(default_factory=KidPhoneSafetyTrackingFeature, title="Kid Phone Safety Tracking")

class ConfigurationsSettings(BaseModel):
    user_details: UserDetails = Field(default_factory=UserDetails, title="User Details")
    chat_provider_config: ChatProviderConfig = Field(..., title="Chat Provider Config")
    queue_config: QueueConfig = Field(default_factory=QueueConfig, title="Queue Config")
    context_config: ContextConfig = Field(default_factory=ContextConfig, title="Context Config")
    llm_provider_config: LLMProviderConfig = Field(..., title="LLM Provider Config")

class UserConfiguration(BaseModel):
    user_id: str
    configurations: ConfigurationsSettings = Field(..., title="General Configurations")
    features: FeaturesConfiguration = Field(default_factory=FeaturesConfiguration, title="Feature Configurations")

