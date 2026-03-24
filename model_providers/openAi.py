from typing import Any, Dict
from langchain_openai import ChatOpenAI
from .chat_completion import ChatCompletionProvider
from config_models import ChatCompletionProviderConfig
import os


class OpenAiMixin:
    """Shared mixin for OpenAI-based providers.
    
    Centralizes the model_dump() → pop custom fields → resolve API key → 
    filter None-valued optional fields flow.
    
    Designed strictly to be mixed into subclasses of BaseModelProvider, 
    relying on self.config and inherited methods like _resolve_api_key().
    """
    def _build_llm_params(self) -> Dict[str, Any]:
        llm_params = self.config.provider_config.model_dump()
        
        # Remove custom configuration fields not accepted by ChatOpenAI
        llm_params.pop("api_key_source", None)
        llm_params.pop("record_llm_interactions", None)
        
        # Resolve API key centrally
        api_key = self._resolve_api_key()
        if api_key:
            llm_params["api_key"] = api_key
        else:
            llm_params.pop("api_key", None)
            if "OPENAI_API_KEY" not in os.environ:
                raise ValueError("OPENAI_API_KEY environment variable is not set and no explicit api_key provided.")
            
        reasoning_effort = llm_params.get("reasoning_effort")
        if reasoning_effort is None:
            llm_params.pop("reasoning_effort", None)
        
        seed = llm_params.get("seed")
        if seed is None:
            llm_params.pop("seed", None)

        return llm_params


class OpenAiChatProvider(ChatCompletionProvider, OpenAiMixin):
    def __init__(self, config: ChatCompletionProviderConfig):
        super().__init__(config)
        params = self._build_llm_params()
        self._llm = ChatOpenAI(**params)

    def get_llm(self):
        return self._llm

