import unittest
from unittest.mock import MagicMock, patch
import time
import asyncio
from chatbot_manager import CorrespondenceIngester, Message, Sender, ChatbotModel
from queue_manager import UserQueuesManager
from config_models import QueueConfig, ContextConfig
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import Runnable

# A fake LLM class to have more control over the mock's behavior
class FakeLlm(Runnable):
    async def ainvoke(self, *args, **kwargs):
        # The LLM's output is an AIMessage, which the StrOutputParser then handles.
        return AIMessage(content="This is a mock response.")

    def invoke(self, *args, **kwargs):
        # The LLM's output is an AIMessage, which the StrOutputParser then handles.
        return AIMessage(content="This is a mock response.")

class TestChatbotModelWithContext(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.llm = FakeLlm()

    async def test_shared_context(self):
        """Test that context is shared between correspondents when shared_context is True."""
        context_config = ContextConfig(shared_context=True)
        model = ChatbotModel('user1', self.llm, 'system', context_config)

        await model.get_response_async(content="My name is Bob", sender_name="Test", correspondent_id='c1')
        self.assertEqual(len(model.shared_history.messages), 2)

        # c2 should know Bob's name
        await model.get_response_async(content="What is my name?", sender_name="Test", correspondent_id='c2')
        self.assertEqual(len(model.shared_history.messages), 4)
        self.assertIn("Test: My name is Bob", model.shared_history.messages[0].content)

    async def test_isolated_context(self):
        """Test that context is isolated between correspondents when shared_context is False."""
        context_config = ContextConfig(shared_context=False)
        model = ChatbotModel('user1', self.llm, 'system', context_config)

        await model.get_response_async(content="My name is Bob", sender_name="Test", correspondent_id='c1')
        self.assertIn('c1', model.histories)
        self.assertEqual(len(model.histories['c1'].messages), 2)
        self.assertEqual(len(model.shared_history.messages), 0) # Shared history should be unused

        await model.get_response_async(content="My name is Alice", sender_name="Test", correspondent_id='c2')
        self.assertIn('c2', model.histories)
        self.assertEqual(len(model.histories['c2'].messages), 2)

        # History of c1 should be separate from c2
        self.assertIn("Test: My name is Bob", model.histories['c1'].messages[0].content)
        self.assertIn("Test: My name is Alice", model.histories['c2'].messages[0].content)

    async def test_trimming_by_max_messages(self):
        """Test that history is trimmed to max_messages."""
        context_config = ContextConfig(max_messages=2, shared_context=True)
        model = ChatbotModel('user1', self.llm, 'system', context_config)

        await model.get_response_async(content="Message 1", sender_name="Test", correspondent_id='c1')
        await model.get_response_async(content="Message 2", sender_name="Test", correspondent_id='c1')

        # This call should trigger trimming.
        await model.get_response_async(content="Message 3", sender_name="Test", correspondent_id='c1')

        history = model.shared_history.messages
        # After trimming, history should contain (human: msg2), (ai_response), (human: msg3), (ai_response)
        # But the model trims *before* invoking, so the history checked has (human: msg2), (ai_response)
        # Then the new message is added. So it becomes (human: msg2), (ai_response), (human: msg3)
        # And after the response, it's 4 messages long.
        self.assertEqual(len(history), 4)
        self.assertEqual(history[0].content, "Test: Message 2")
        self.assertEqual(history[1].content, "Bot: This is a mock response.")
        self.assertEqual(history[2].content, "Test: Message 3")

    async def test_trimming_by_max_characters(self):
        """Test that history is trimmed by total characters."""
        # Total chars for "Test: 123456789" (15) + "Bot: This is a mock response." (26) is 41
        context_config = ContextConfig(max_characters=40, shared_context=True)
        model = ChatbotModel('user1', self.llm, 'system', context_config)

        await model.get_response_async(content="123456789", sender_name="Test", correspondent_id='c1')
        await model.get_response_async(content="short", sender_name="Test", correspondent_id='c1')

        history = model.shared_history.messages
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].content, "Bot: This is a mock response.")
        self.assertEqual(history[1].content, "Test: short")

    @patch('time.time')
    async def test_trimming_by_age(self, mock_time):
        """Test that history is trimmed by message age."""
        start_time = 1700000000.0
        mock_time.return_value = start_time

        context_config = ContextConfig(max_days=1, shared_context=True)
        model = ChatbotModel('user1', self.llm, 'system', context_config)

        # Add the first message
        await model.get_response_async(content="Old message", sender_name="Test", correspondent_id='c1')
        self.assertEqual(len(model.shared_history.messages), 2)

        # Simulate time passing (2 days)
        mock_time.return_value = start_time + (2 * 24 * 60 * 60)

        # Add a new message, which should trigger eviction of the old one
        await model.get_response_async(content="New message", sender_name="Test", correspondent_id='c1')

        history = model.shared_history.messages
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].content, "Test: New message")

    async def test_single_message_truncation(self):
        """Test that individual messages (both user and bot) are truncated."""
        context_config = ContextConfig(max_characters_single_message=10, shared_context=True)
        # The fake LLM returns a 26-char response, so it should be truncated
        model = ChatbotModel('user1', self.llm, 'system', context_config)

        # User message is also longer than 10 chars
        response = await model.get_response_async(
            content="This is a long user message",
            sender_name="TestSender",
            correspondent_id='c1'
        )

        # The response from the model should be complete
        self.assertEqual(response, "This is a mock response.")

        history = model.shared_history.messages
        self.assertEqual(len(history), 2)
        # Check that the messages in the history are truncated
        self.assertEqual(history[0].content, "TestSender: This is a ")
        self.assertEqual(history[1].content, "Bot: This is a ")

class TestCorrespondenceIngester(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_queues_collection = MagicMock()
        self.mock_queues_collection.insert_one = MagicMock()

        self.queue_config = QueueConfig(max_messages=10, max_characters=1000, max_days=1)
        self.user_queues_manager = UserQueuesManager(
            user_id='test_ingester_user',
            provider_name='test_vendor',
            queue_config=self.queue_config,
            queues_collection=self.mock_queues_collection
        )
        self.ingester = CorrespondenceIngester(
            user_id='test_ingester_user',
            provider_name='test_vendor',
            user_queues_manager=self.user_queues_manager,
            queues_collection=self.mock_queues_collection,
            main_loop=asyncio.get_running_loop()
        )

    async def test_ingester_processes_message(self):
        """
        Test that the ingester pulls a message from the queue and persists it to the database.
        """
        # Add a message to a correspondent's queue
        correspondent_id = 'cor1'
        sender = Sender(identifier='test_sender', display_name='Test Sender')
        self.user_queues_manager.add_message(correspondent_id, "Test message", sender, 'user')

        # Start the ingester
        self.ingester.start()

        # Give the ingester a moment to process the message
        await asyncio.sleep(1.5)

        # Stop the ingester
        await self.ingester.stop()

        # Verify that insert_one was called on the mock collection
        self.mock_queues_collection.insert_one.assert_called_once()

        # Check the content of the inserted document
        inserted_doc = self.mock_queues_collection.insert_one.call_args[0][0]
        self.assertEqual(inserted_doc['content'], "Test message")
        self.assertEqual(inserted_doc['user_id'], 'test_ingester_user')
        self.assertEqual(inserted_doc['provider_name'], 'test_vendor')
        self.assertEqual(inserted_doc['correspondent_id'], correspondent_id)

        # Verify that the message was removed from the in-memory queue
        cor_queue = self.user_queues_manager.get_queue(correspondent_id)
        self.assertEqual(len(cor_queue.get_messages()), 0)

if __name__ == '__main__':
    unittest.main()
