from langchain_community.llms.fake import FakeListLLM
from .base import BaseLlmProvider

class FakeLlmProvider(BaseLlmProvider):
    def __init__(self, config: dict, user_id: str):
        super().__init__(config, user_id)

    def get_llm(self):
        # The response array can be customized via the 'vendor_config'
        response_array = self.config.get("response_array", [
            "This is a default response."
        ])

        # Format any placeholders in the response array
        formatted_responses = [resp.format(user_id=self.user_id) for resp in response_array]

        return FakeListLLM(responses=formatted_responses)

    def get_system_prompt(self):
        # The system prompt can also be customized
        system_prompt = self.config.get("system", "You are a helpful assistant.")
        return system_prompt.format(user_id=self.user_id)
