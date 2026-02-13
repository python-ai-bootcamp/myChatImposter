from langchain_community.llms.fake import FakeListLLM
from .base import BaseLlmProvider
from config_models import LLMProviderConfig


# Enhanced Fake LLM for Token Usage Testing
class MockTokenLLM(FakeListLLM):
    """
    A subclass of FakeListLLM that injects token usage metadata into the response.
    Used for testing the TokenTrackingCallback.
    """
    def _call(self, prompt: str, stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> str:
        response = super()._call(prompt, stop, run_manager, **kwargs)
        # We need to ensure the run_manager context has the usage info, 
        # OR we just rely on the LLMResult having it. 
        # FakeListLLM returns a string, processed by LangChain into an LLMResult.
        # But BaseChatModel wrappers usually handle the LLMResult construction.
        # Wait, usually ChatModels use `_generate`. `FakeListLLM` is an LLM, not a ChatModel.
        # But our provider returns `FakeListLLM` which is then used as a ChatModel adapter?
        # Actually OpenAiLlmProvider returns `ChatOpenAI`. 
        # We should use `FakeListChatModel` if available, or just patch the result.
        
        # Simpler approach: The provider returns this object. 
        # Whatever consumes it gets the response.
        return response

    @property
    def _llm_type(self) -> str:
        return "mock_token_llm"

# We need a FakeChatModel to properly support message inputs and usage metadata
from langchain_community.chat_models.fake import FakeListChatModel
from langchain_core.messages import AIMessage

class MockTokenChatModel(FakeListChatModel):
    def _generate(self, messages: List[Any], stop: Optional[List[str]] = None, run_manager: Optional[Any] = None, **kwargs: Any) -> Any:
        # Generate the result using the parent class
        result = super()._generate(messages, stop, run_manager, **kwargs)
        
        # Inject usage metadata into the first generation's message
        if result.generations:
            # Debug what we got
            # print(f"DEBUG: generations type: {type(result.generations)}")
            # print(f"DEBUG: generations[0] type: {type(result.generations[0])}")
            
            # Access the first generation. 
            # Standard: List[List[Generation]]
            # If standard, gen_list = result.generations[0]
            # Ensure it is a list
            first_completion = result.generations[0]
            if isinstance(first_completion, list):
                gen = first_completion[0]
            else:
                # Fallback if somehow it is not nested list (should not happen in standard LangChain)
                gen = first_completion

            if hasattr(gen, 'message'):
                message: AIMessage = gen.message
                # Standard LangChain usage metadata
                message.usage_metadata = {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15
                }
            # Also populate llm_output for our secondary strategy
            if result.llm_output is None:
                result.llm_output = {}
            result.llm_output["token_usage"] = {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
            
        return result

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

        # Use our enhanced mock if requested (or default to it for safety?)
        # For simplicity, let's switch to MockTokenChatModel entirely as it is backward compatible
        # with standard fake list usage but adds token metadata.
        return MockTokenChatModel(responses=formatted_responses)

