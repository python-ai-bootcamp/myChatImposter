from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from config_models import BaseModelProviderConfig

class BaseModelProvider(ABC):
    def __init__(self, config: BaseModelProviderConfig):
        self.config = config

    async def initialize(self):
        """No-op initialization hook. Concrete providers may override to set up
        external HTTP clients or other async resources. Intentionally NOT
        @abstractmethod so existing providers inherit safely."""
        pass

    def _resolve_api_key(self) -> Optional[str]:
        """Shared utility: resolves the API key based on api_key_source.
        
        CONSTRAINT: This method must remain strictly synchronous and perform no 
        external I/O or background async polling, relying strictly on the pre-resolved
        synchronous self.config properties. This is required because ChatOpenAI 
        instantiation happens inside synchronous __init__ constructors.
        """
        settings = self.config.provider_config
        if settings.api_key_source == "explicit":
            if not settings.api_key:
                raise ValueError("api_key_source is 'explicit' but no api_key provided.")
            return settings.api_key
        return None


class LLMProvider(BaseModelProvider, ABC):
    """Abstract base class for providers that expose a LangChain BaseChatModel.
    Both ChatCompletionProvider and ImageTranscriptionProvider inherit from this.
    """
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        ...

