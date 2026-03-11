from typing import Any, Dict
from langchain_openai import ChatOpenAI
from .chat_completion import ChatCompletionProvider
from config_models import ChatCompletionProviderConfig
import os
import logging

class OpenAiChatProvider(ChatCompletionProvider):
    def __init__(self, config: ChatCompletionProviderConfig):
        super().__init__(config)

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
            
        print(f"DEBUG: Configured reasoning_effort: {reasoning_effort}, seed: {seed}")
        print(f"DEBUG: Final llm_params keys: {list(llm_params.keys())}")

        return llm_params

    def get_llm(self):
        llm_params = self._build_llm_params()

        safe_params = {k: v for k, v in llm_params.items() if k != 'api_key'}
        has_api_key = 'api_key' in llm_params or 'OPENAI_API_KEY' in os.environ
        print(f"DEBUG: Initializing ChatOpenAI with params: {safe_params}, Has API Key: {has_api_key}")

        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.INFO)
        if not httpx_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('DEBUG:httpx: %(message)s'))
            httpx_logger.addHandler(handler)

        llm = ChatOpenAI(**llm_params)
        return llm
