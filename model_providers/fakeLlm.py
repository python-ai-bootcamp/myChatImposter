from typing import Optional, List, Any
from langchain_community.llms.fake import FakeListLLM
from .chat_completion import ChatCompletionProvider
from config_models import ChatCompletionProviderConfig

# Enhanced Fake LLM for Token Usage Testing
class MockTokenLLM(FakeListLLM):
    """
    A subclass of FakeListLLM that injects token usage metadata into the response.
    Used for testing the TokenTrackingCallback.
    """
    def _call(self, prompt: str, stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> str:
        response = super()._call(prompt, stop, run_manager, **kwargs)
        return response

    @property
    def _llm_type(self) -> str:
        return "mock_token_llm"

from langchain_community.chat_models.fake import FakeListChatModel
from langchain_core.messages import AIMessage

class MockTokenChatModel(FakeListChatModel):
    def _generate(self, messages: List[Any], stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> Any:
        result = super()._generate(messages, stop, run_manager, **kwargs)
        
        if result.generations:
            first_completion = result.generations[0]
            if isinstance(first_completion, list):
                gen = first_completion[0]
            else:
                gen = first_completion

            if hasattr(gen, 'message'):
                message: AIMessage = gen.message
                message.usage_metadata = {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15
                }
            if result.llm_output is None:
                result.llm_output = {}
            result.llm_output["token_usage"] = {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
            
        return result

class FakeLlmProvider(ChatCompletionProvider):
    def __init__(self, config: ChatCompletionProviderConfig):
        super().__init__(config)

    def get_llm(self):
        provider_config_dict = self.config.provider_config.model_dump()
        response_array = provider_config_dict.get("response_array", [
            "This is a default response."
        ])
        
        # Test frameworks parsing this expectation must update to expect a parameterless string 
        # instead of {user_id}.
        formatted_responses = [resp.format() for resp in response_array]

        return MockTokenChatModel(responses=formatted_responses)

