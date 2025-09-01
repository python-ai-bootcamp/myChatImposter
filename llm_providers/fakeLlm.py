from langchain_community.llms.fake import FakeListLLM
from .base import BaseLlmProvider
from config_models import LLMProviderConfig

class FakeLlmProvider(BaseLlmProvider):
    def __init__(self, config: LLMProviderConfig, user_id: str):
        super().__init__(config, user_id)

    def get_llm(self):
        # The response array can be customized via the 'provider_config'
        provider_config_dict = self.config.provider_config.model_dump()
        response_array = provider_config_dict.get("response_array", [
            "This is a default response."
        ])
        # Format any placeholders in the response array
        formatted_responses = [resp.format(user_id=self.user_id) for resp in response_array]

        return FakeListLLM(responses=formatted_responses)

    def get_system_prompt(self):
        # The system prompt can also be customized
        return self.config.provider_config.system.format(user_id=self.user_id)
