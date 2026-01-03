from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal

class ChatProviderSettings(BaseModel):
    allow_group_messages: bool = False
    process_offline_messages: bool = False

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
    system: str = ""

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

class UserConfiguration(BaseModel):
    user_id: str
    respond_to_whitelist: List[str] = Field(default_factory=list, title="Respond To Direct Contact Whitelist")
    respond_to_whitelist_group: List[str] = Field(default_factory=list, title="Respond To Group Whitelist")
    periodic_group_tracking: List[PeriodicGroupTrackingConfig] = Field(default_factory=list, title="Periodic Group Tracking")
    chat_provider_config: ChatProviderConfig
    queue_config: QueueConfig
    context_config: ContextConfig = Field(default_factory=ContextConfig)
    llm_provider_config: Optional[LLMProviderConfig] = None
