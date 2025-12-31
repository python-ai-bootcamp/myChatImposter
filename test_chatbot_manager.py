import unittest
from unittest.mock import MagicMock, patch
import time
import asyncio
from chatbot_manager import CorrespondenceIngester, Message, Sender, ChatbotModel
from queue_manager import UserQueuesManager
from config_models import QueueConfig
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import Runnable

# A fake LLM class to have more control over the mock's behavior
class FakeLlm(Runnable):
    def invoke(self, *args, **kwargs):
        # The LLM's output is an AIMessage, which the StrOutputParser then handles.
        return AIMessage(content="This is a mock response.")

class TestChatbotModel(unittest.TestCase):
    def setUp(self):
        # Instantiate the ChatbotModel with the fake LLM
        self.chatbot_model = ChatbotModel(
            user_id='test_user',
            llm=FakeLlm(),
            system_prompt='You are a helpful assistant.'
        )

    def test_message_history_prefixing(self):
        """
        Tests that the user's message and the bot's response are correctly
        prefixed before being added to the message history.
        """
        # 1. Simulate a user sending a message
        user_message_content = "Hello, bot!"
        sender_display_name = "Test User"
        prefixed_user_message = f"{sender_display_name}: {user_message_content}"

        # This call will trigger the conversation chain
        response = self.chatbot_model.get_response_sync(prefixed_user_message)

        # 2. Verify the response from the mock LLM
        self.assertEqual(response, "This is a mock response.")

        # 3. Verify the message history
        history = self.chatbot_model.message_history.messages

        # Expected history:
        # - A HumanMessage with the user's prefixed message
        # - An AIMessage with the bot's prefixed response
        self.assertEqual(len(history), 2)

        # Check the user's message in the history
        self.assertIsInstance(history[0], HumanMessage)
        self.assertEqual(history[0].content, prefixed_user_message)

        # Check the bot's message in the history
        self.assertIsInstance(history[1], AIMessage)
        self.assertEqual(history[1].content, "Bot: This is a mock response.")

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
