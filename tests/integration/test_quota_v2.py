
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from services.quota_service import QuotaService
from services.token_consumption_service import TokenConsumptionService
from services.tracked_llm import TokenTrackingCallback
from langchain_core.outputs import LLMResult, Generation, ChatGeneration
from langchain_core.messages import AIMessage

# Mock Data
MOCK_TOKEN_MENU = {
    "high": {
        "input_tokens": 10.0,   # $10 per 1M
        "output_tokens": 30.0,  # $30 per 1M
        "cached_input_tokens": 1.0 # $1 per 1M (cheap!)
    }
}

@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Mock collections
    db.__getitem__ = MagicMock()
    return db

@pytest_asyncio.fixture
async def quota_service(mock_db):
    service = QuotaService(mock_db)
    service._token_menu = MOCK_TOKEN_MENU
    return service

@pytest.mark.asyncio
async def test_calculate_cost_with_cache(quota_service):
    # Case 1: No cache
    # 1000 input * 10/1M = 0.01
    # 1000 output * 30/1M = 0.03
    # Total = 0.04
    cost = quota_service.calculate_cost(1000, 1000, "high", cached_input_tokens=0)
    assert abs(cost - 0.04) < 0.000001

    # Case 2: 50% cache
    # 500 input (uncached) * 10/1M = 0.005
    # 500 input (cached) * 1/1M = 0.0005
    # 1000 output * 30/1M = 0.03
    # Total = 0.0355
    cost = quota_service.calculate_cost(1000, 1000, "high", cached_input_tokens=500)
    assert abs(cost - 0.0355) < 0.000001
    
    # Case 3: 100% cache
    # 0 input (uncached)
    # 1000 input (cached) * 1/1M = 0.001
    # 1000 output * 30/1M = 0.03
    # Total = 0.031
    cost = quota_service.calculate_cost(1000, 1000, "high", cached_input_tokens=1000)
    assert abs(cost - 0.031) < 0.000001

@pytest.mark.asyncio
async def test_atomic_update_call(quota_service):
    # Identify that update_one is called with $inc
    quota_service.credentials_collection.update_one = AsyncMock()
    quota_service.credentials_collection.find_one = AsyncMock(return_value={
        "llm_quota": {"enabled": True, "dollars_used": 0.5, "dollars_per_period": 10.0}
    })
    
    await quota_service.update_user_usage("user123", 0.05)
    
    # Verify call arguments
    args = quota_service.credentials_collection.update_one.call_args_list[0]
    filter_arg = args[0][0]
    update_arg = args[0][1]
    
    assert filter_arg == {"user_id": "user123"}
    assert "$inc" in update_arg
    assert update_arg["$inc"]["llm_quota.dollars_used"] == 0.05

@pytest.mark.asyncio
async def test_token_tracking_extraction():
    token_service = AsyncMock()
    handler = TokenTrackingCallback(
        token_service=token_service,
        user_id="u1", bot_id="b1", feature_name="f", 
        config_tier="high", provider_name="openai"
    )
    
    # Simulate LLMResult with standard usage_metadata + cached tokens check
    # Note: We are simulating the logic we added to on_llm_end
    
    # Mock response with OpenAI-like output in llm_output (Strategy 2)
    llm_output = {
        'token_usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'prompt_tokens_details': {
                'cached_tokens': 25
            }
        }
    }
    result = LLMResult(generations=[], llm_output=llm_output)
    
    await handler.on_llm_end(result)
    
    # Verify record_event called with correct cached tokens
    token_service.record_event.assert_called_once()
    call_kwargs = token_service.record_event.call_args[1]
    
    assert call_kwargs['input_tokens'] == 100
    assert call_kwargs['output_tokens'] == 50
    assert call_kwargs['cached_input_tokens'] == 25
