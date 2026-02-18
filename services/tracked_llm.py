from typing import Any, Dict, List, Literal, Optional
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult
from services.token_consumption_service import TokenConsumptionService
import logging

logger = logging.getLogger(__name__)

class TokenTrackingCallback(AsyncCallbackHandler):
    """
    A LangChain callback handler that automatically tracks token consumption
    and records it to the TokenConsumptionService.
    """

    def __init__(self, 
                 token_service: TokenConsumptionService,
                 user_id: str,
                 bot_id: str,
                 feature_name: str,
                 config_tier: Literal["high", "low"],
                 provider_name: str):
        self.token_service = token_service
        self.user_id = user_id
        self.bot_id = bot_id
        self.feature_name = feature_name
        self.config_tier = config_tier
        self.provider_name = provider_name

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM ends running."""
        try:
            input_tokens = 0
            output_tokens = 0
            cached_input_tokens = 0
            
            # --- Strategy 1: LangChain Standard 'usage_metadata' ---
            # Newer LangChain versions standardize usage on the AIMessage in generations.
            if response.generations and response.generations[0]:
                first_gen = response.generations[0][0]
                if hasattr(first_gen, 'message') and hasattr(first_gen.message, 'usage_metadata'):
                    usage = first_gen.message.usage_metadata
                    if usage:
                        input_tokens = usage.get('input_tokens', 0)
                        output_tokens = usage.get('output_tokens', 0)
                        # Try to extract cached tokens if available in standard metadata (e.g. Anthropic)
                        # Langchain might put it in input_token_details
                        if 'input_token_details' in usage:
                            cached_input_tokens = usage['input_token_details'].get('cache_read', 0)
            
            # --- Strategy 2: Provider-Specific Normalizer (Fallback or Enrichment) ---
            # Even if we got basic tokens, we might need provider specific extraction for cached tokens
            # if LangChain didn't normalize them yet.
            provider_input, provider_output, provider_cached = self._extract_provider_specific_usage(response.llm_output)
            
            if input_tokens == 0 and output_tokens == 0:
                input_tokens = provider_input
                output_tokens = provider_output
            
            if cached_input_tokens == 0 and provider_cached > 0:
                 cached_input_tokens = provider_cached

            # --- Record Event ---
            if input_tokens > 0 or output_tokens > 0:
                await self.token_service.record_event(
                    user_id=self.user_id,
                    bot_id=self.bot_id,
                    feature_name=self.feature_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input_tokens,
                    config_tier=self.config_tier
                )
            elif response.llm_output:
                 logger.warning(
                     f"TokenTrackingCallback: Could not extract usage from {self.provider_name}. "
                     f"LLM Output keys: {response.llm_output.keys()}"
                 )

        except Exception as e:
            logger.error(f"TokenTrackingCallback error: {e}")

    def _extract_provider_specific_usage(self, llm_output: Optional[Dict]) -> tuple[int, int, int]:
        """
        Normalizer for different provider formats in llm_output.
        Returns (input_tokens, output_tokens, cached_input_tokens).
        """
        if not llm_output:
            return 0, 0, 0
            
        input_t = 0
        output_t = 0
        cached_t = 0

        # OpenAI style: 'token_usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'prompt_tokens_details': {'cached_tokens': 0}}
        if 'token_usage' in llm_output:
            usage = llm_output['token_usage']
            input_t = usage.get('prompt_tokens', 0)
            output_t = usage.get('completion_tokens', 0)
            
            details = usage.get('prompt_tokens_details', {})
            if details:
                cached_t = details.get('cached_tokens', 0)
            
        # Add other providers here as needed
        
        return input_t, output_t, cached_t
