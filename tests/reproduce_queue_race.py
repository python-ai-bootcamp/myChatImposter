import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from queue_manager import BotQueuesManager, CorrespondentQueue
from config_models import QueueConfig

class TestQueueRaceCondition(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_get_or_create_queue(self):
        """
        Verify that concurrent calls to get_or_create_queue do not cause multiple initializations.
        """
        bot_id = "test_bot"
        provider_name = "test_provider"
        correspondent_id = "test_cor"
        queue_config = QueueConfig(max_messages=10, max_characters=1000, max_days=1, max_characters_single_message=100)
        
        # Mock queues_collection
        mock_collection = MagicMock()
        # Mock find_one to return a dummy value
        mock_collection.find_one = AsyncMock(return_value={"id": 1})

        manager = BotQueuesManager(
            bot_id=bot_id,
            provider_name=provider_name,
            queue_config=queue_config,
            queues_collection=mock_collection,
            main_loop=asyncio.get_running_loop()
        )

        # Patch CorrespondentQueue.initialize to track calls and add a small delay
        # to increase the chance of a race condition if locking isn't working.
        original_init = CorrespondentQueue.initialize
        call_count = 0
        
        async def mock_initialize(self):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate some async work
            await original_init(self)

        with patch.object(CorrespondentQueue, 'initialize', mock_initialize):
            # Fire multiple concurrent requests for the same queue
            tasks = [manager.get_or_create_queue(correspondent_id) for _ in range(10)]
            queues = await asyncio.gather(*tasks)

            # All returned objects should be the same instance
            self.assertEqual(len(set(id(q) for q in queues)), 1)
            
            # Initialization should have only happened once
            self.assertEqual(call_count, 1, "CorrespondentQueue.initialize should only be called once")

if __name__ == "__main__":
    unittest.main()
