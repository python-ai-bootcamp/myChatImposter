import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from services.token_consumption_service import TokenConsumptionService
from services.tracked_llm import TokenTrackingCallback
from langchain_core.outputs import LLMResult, Generation, ChatGeneration
from langchain_core.messages import AIMessage

class TestTokenServices(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_collection = AsyncMock()
        self.service = TokenConsumptionService(self.mock_collection)
        self.user_id = "test_user"
        self.bot_id = "test_bot"
        self.feature = "test_feature"
        self.tier = "high"

    async def test_record_event(self):
        await self.service.record_event(
            self.user_id, self.bot_id, self.feature, 10, 20, self.tier
        )
        
        self.mock_collection.insert_one.assert_called_once()
        call_args = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(call_args["user_id"], self.user_id)
        self.assertEqual(call_args["input_tokens"], 10)
        self.assertEqual(call_args["output_tokens"], 20)
        self.assertTrue(isinstance(call_args["timestamp"], datetime))

    async def test_callback_strategy_1_standard_metadata(self):
        """Test extraction from message.usage_metadata"""
        callback = TokenTrackingCallback(self.service, self.user_id, self.bot_id, self.feature, self.tier, "openai")
        
        # Create a result with usage_metadata on the message
        msg = AIMessage(content="foo")
        msg.usage_metadata = {"input_tokens": 5, "output_tokens": 5}
        generation = ChatGeneration(message=msg)
        result = LLMResult(generations=[[generation]])
        
        await callback.on_llm_end(result)
        
        self.mock_collection.insert_one.assert_called_once()
        call_args = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(call_args["input_tokens"], 5)
        self.assertEqual(call_args["output_tokens"], 5)

    async def test_callback_strategy_2_provider_specific(self):
        """Test extraction from llm_output (OpenAI style fallback)"""
        callback = TokenTrackingCallback(self.service, self.user_id, self.bot_id, self.feature, self.tier, "openai")
        
        # Result without usage_metadata on message, but with llm_output
        msg = AIMessage(content="foo") 
        generation = ChatGeneration(message=msg)
        result = LLMResult(
            generations=[[generation]],
            llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 10}}
        )
        
        await callback.on_llm_end(result)
        
        self.mock_collection.insert_one.assert_called_once()
        call_args = self.mock_collection.insert_one.call_args[0][0]
        self.assertEqual(call_args["input_tokens"], 10)
        self.assertEqual(call_args["output_tokens"], 10)

    async def test_callback_strategy_3_fallback(self):
        """Test callback logging when no logic matches"""
        callback = TokenTrackingCallback(self.service, self.user_id, self.bot_id, self.feature, self.tier, "unknown_provider")
        
        msg = AIMessage(content="foo")
        generation = ChatGeneration(message=msg)
        # We need non-empty llm_output to trigger the warning logic
        result = LLMResult(generations=[[generation]], llm_output={"unknown_key": 123})
        
        with self.assertLogs('services.tracked_llm', level='WARNING') as cm:
            await callback.on_llm_end(result)
            self.assertTrue(any("Could not extract usage" in o for o in cm.output))
            
        self.mock_collection.insert_one.assert_not_called()

class TestLLMFactory(unittest.IsolatedAsyncioTestCase):
    @patch('importlib.import_module')
    @patch('services.llm_factory.find_provider_class')
    async def test_create_tracked_llm_attaches_callback(self, mock_find, mock_import):
        from services.llm_factory import create_tracked_llm
        from config_models import LLMProviderConfig, LLMProviderSettings
        
        # Mock Provider Class
        mock_provider_cls = MagicMock()
        mock_provider_instance = MagicMock()
        mock_llm = MagicMock()
        mock_llm.callbacks = None # Simulate no callbacks initially
        
        mock_provider_cls.return_value = mock_provider_instance
        mock_provider_instance.get_llm.return_value = mock_llm
        mock_find.return_value = mock_provider_cls
        
        # Config
        config = LLMProviderConfig(provider_name="test_provider", provider_config=LLMProviderSettings(model="test"))
        mock_collection = AsyncMock()
        
        # Call factory
        llm = create_tracked_llm(config, "user", "bot", "feature", "high", mock_collection)
        
        # Assertions
        self.assertIsNotNone(llm.callbacks)
        self.assertEqual(len(llm.callbacks), 1)
        self.assertTrue(isinstance(llm.callbacks[0], TokenTrackingCallback))
        self.assertEqual(llm.callbacks[0].feature_name, "feature")

if __name__ == '__main__':
    unittest.main()
