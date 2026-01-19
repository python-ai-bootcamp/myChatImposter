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
        # Remove our recording flag - it's not an LLM parameter
        llm_params.pop("record_llm_interactions", None)

        if api_key_source == "environment":
            llm_params.pop("api_key", None)
        elif api_key_source == "explicit":
            if not api_key:
                raise ValueError("api_key_source is 'explicit' but no api_key was provided.")
        else:
            raise ValueError(f"Unknown api_key_source value: {api_key_source}")

        # reasoning_effort is now a direct ChatOpenAI parameter
        # Just pop it if None so we don't pass null to the constructor
        reasoning_effort = llm_params.get("reasoning_effort")
        if reasoning_effort is None:
            llm_params.pop("reasoning_effort", None)
        
        # seed for reproducibility - pop if None
        seed = llm_params.get("seed")
        if seed is None:
            llm_params.pop("seed", None)
        
        print(f"DEBUG: Configured reasoning_effort: {reasoning_effort}, seed: {seed}")
        print(f"DEBUG: Final llm_params keys: {list(llm_params.keys())}")

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
