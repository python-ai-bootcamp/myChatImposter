from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChatProviderConfig(BaseModel):
    provider_name: str
    allow_group_messages: bool = False
    process_offline_messages: bool = False

class QueueConfig(BaseModel):
    max_messages: int = 10
    max_characters: int = 1000
    max_days: int = 1
    max_characters_single_message: int = 300

class LLMProviderConfig(BaseModel):
    provider_name: str
    api_key: Optional[str] = None
    model: str
    temperature: float = 0.7
    system: str = ""
    provider_config: Dict[str, Any] = Field(default_factory=dict)

class UserConfiguration(BaseModel):
    user_id: str
    respond_to_whitelist: List[str] = Field(default_factory=list)
    chat_provider_config: ChatProviderConfig
    queue_config: QueueConfig
    llm_provider_config: Optional[LLMProviderConfig] = None
