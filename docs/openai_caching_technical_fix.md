# OpenAI Prompt Caching Technical Documentation

This document describes the technical implementation and findings for correctly tracking OpenAI prompt caching tokens.

## The Core Issue

The original `TokenTrackingCallback` was attempting to extract cached tokens using a generic LangChain standardization that works for Anthropic (`cache_read` inside `input_token_details`) but fails for OpenAI. 

OpenAI reports cached tokens inside a provider-specific dictionary structure that LangChain's standard `usage_metadata` (at least in the current version) does not always flatten into the primary usage object.

## Technical Fix: Provider-Specific Extraction

The fix involved modifying `services/tracked_llm.py` to explicitly look for the OpenAI-specific nested structure.

### 1. OpenAI Response Structure
When a cache hit occurs, OpenAI returns a response containing:
```json
{
  "token_usage": {
    "prompt_tokens": 1270,
    "completion_tokens": 155,
    "total_tokens": 1425,
    "prompt_tokens_details": {
      "cached_tokens": 1152
    }
  }
}
```

### 2. Implementation in `tracked_llm.py`

I updated the `TokenTrackingCallback` to navigate this specific hierarchy. 

#### [MODIFY] `_extract_provider_specific_usage`
This method was updated to safely navigate the `prompt_tokens_details` map:

```python
def _extract_provider_specific_usage(self, llm_output: Optional[Dict]) -> tuple[int, int, int]:
    if not llm_output:
        return 0, 0, 0
        
    input_t = 0
    output_t = 0
    cached_t = 0

    # OpenAI-specific structure: 'token_usage' -> 'prompt_tokens_details' -> 'cached_tokens'
    if 'token_usage' in llm_output:
        usage = llm_output['token_usage']
        input_t = usage.get('prompt_tokens', 0)
        output_t = usage.get('completion_tokens', 0)
        
        details = usage.get('prompt_tokens_details', {})
        if details:
            cached_t = details.get('cached_tokens', 0)
    
    return input_t, output_t, cached_t
```

#### [MODIFY] `on_llm_end`
I added an extra safety check directly in the callback handler to ensure that if `cached_input_tokens` is still 0 after initial extraction, we double-check the `llm_output` manually:

```python
# --- Extra Check for OpenAI 'cached_tokens' in llm_output ---
if cached_input_tokens == 0 and response.llm_output and 'token_usage' in response.llm_output:
    token_usage = response.llm_output['token_usage']
    if 'prompt_tokens_details' in token_usage:
        cached_tokens = token_usage['prompt_tokens_details'].get('cached_tokens', 0)
        if cached_tokens > 0:
            cached_input_tokens = cached_tokens
```
