from typing import Any, Dict
from langchain_openai import ChatOpenAI
from .base import BaseLlmProvider
from config_models import LLMProviderConfig
import os

class OpenAiLlmProvider(BaseLlmProvider):
    def __init__(self, config: LLMProviderConfig, user_id: str):
        super().__init__(config, user_id)

    def _build_llm_params(self) -> Dict[str, Any]:
        llm_params = self.config.provider_config.model_dump()
        api_key_source = llm_params.pop("api_key_source", "environment")
        api_key = llm_params.get("api_key")

        if api_key_source == "environment":
            llm_params.pop("api_key", None)
        elif api_key_source == "explicit":
            if not api_key:
                raise ValueError("api_key_source is 'explicit' but no api_key was provided.")
        else:
            raise ValueError(f"Unknown api_key_source value: {api_key_source}")

        # "reasoning_effort" might not be a direct init arg in older LangChain versions,
        # so we move it to model_kwargs to be safe, or leave it if ChatOpenAI handles it.
        # Safest approach for new O1-like params is often model_kwargs.
        reasoning_effort = llm_params.pop("reasoning_effort", None)
        
        print(f"DEBUG: Configured reasoning_effort: {reasoning_effort}")

        if reasoning_effort:
            if "model_kwargs" not in llm_params:
                llm_params["model_kwargs"] = {}
            llm_params["model_kwargs"]["reasoning_effort"] = reasoning_effort

        print(f"DEBUG: Final llm_params keys: {list(llm_params.keys())}")
        if "model_kwargs" in llm_params:
             print(f"DEBUG: Final model_kwargs: {llm_params['model_kwargs']}")

        return llm_params

    def get_llm(self):
        llm_params = self._build_llm_params()

        # Log the parameters being used (carefully masking sensitive info)
        safe_params = {k: v for k, v in llm_params.items() if k != 'api_key'}
        # Check if 'api_key' exists in the original params or env, just for logging presence
        has_api_key = 'api_key' in llm_params or 'OPENAI_API_KEY' in os.environ
        print(f"DEBUG: Initializing ChatOpenAI with params: {safe_params}, Has API Key: {has_api_key}")

        # Enable httpx logging to see network requests/retries
        import logging
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.INFO)
        # Ensure it prints to console if not already configured
        if not httpx_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('DEBUG:httpx: %(message)s'))
            httpx_logger.addHandler(handler)

        if "OPENAI_API_KEY" not in os.environ and "api_key" not in llm_params:
            raise ValueError("OPENAI_API_KEY environment variable is not set and no explicit api_key provided.")
        
        llm = ChatOpenAI(**llm_params)
        
        # Enable httpx logging to see network requests/retries (useful for debugging latency)
        # To disable, set level to logging.WARNING
        import logging
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.INFO)
        if not httpx_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('DEBUG:httpx: %(message)s'))
            httpx_logger.addHandler(handler)
        
        return llm
