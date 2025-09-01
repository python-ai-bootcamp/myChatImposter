from langchain_openai import ChatOpenAI
from .base import BaseLlmProvider
from config_models import LLMProviderConfig

class OpenAiLlmProvider(BaseLlmProvider):
    def __init__(self, config: LLMProviderConfig, user_id: str):
        super().__init__(config, user_id)

    def get_llm(self):
        # The ChatOpenAI client will automatically use the OPENAI_API_KEY environment variable
        # if the api_key argument is not provided. We will pass all config keys to the constructor
        # and let it pick the ones it needs. This makes the provider flexible.

        # We need to separate the system prompt from the LLM parameters.
        llm_params = self.config.provider_config.model_dump()
        llm_params.pop("system", None)

        return ChatOpenAI(**llm_params)

    def get_system_prompt(self):
        # The system prompt can also be customized
        return self.config.provider_config.system.format(user_id=self.user_id)
