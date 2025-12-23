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
        llm_params.pop("system", None)
        api_key_source = llm_params.pop("api_key_source", "environment")
        api_key = llm_params.get("api_key")

        if api_key_source == "environment":
            llm_params.pop("api_key", None)
        elif api_key_source == "explicit":
            if not api_key:
                raise ValueError("api_key_source is 'explicit' but no api_key was provided.")
        else:
            raise ValueError(f"Unknown api_key_source value: {api_key_source}")

        return llm_params

    def get_llm(self):
        llm_params = self._build_llm_params()
        if "OPENAI_API_KEY" not in os.environ and "api_key" not in llm_params:
            raise ValueError("OPENAI_API_KEY environment variable is not set and no explicit api_key provided.")
        return ChatOpenAI(**llm_params)

    def get_system_prompt(self):
        return self.config.provider_config.system.format(user_id=self.user_id)
