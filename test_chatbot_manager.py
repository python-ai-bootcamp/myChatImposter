import unittest
from unittest.mock import MagicMock, patch
import time
from chatbot_manager import CorrespondenceIngester, Message, Sender
from queue_manager import UserQueue
from config_models import QueueConfig

class TestCorrespondenceIngester(unittest.TestCase):
    def setUp(self):
        self.mock_queues_collection = MagicMock()
        self.queue_config = QueueConfig(max_messages=10, max_characters=1000, max_days=1)
        self.user_queue = UserQueue(
            user_id='test_ingester_user',
            provider_name='test_vendor',
            queue_config=self.queue_config,
            queues_collection=None  # Ingester handles the collection
        )
        self.ingester = CorrespondenceIngester(
            user_id='test_ingester_user',
            provider_name='test_vendor',
            user_queue=self.user_queue,
            queues_collection=self.mock_queues_collection
        )

    def test_ingester_processes_message(self):
        """
        Test that the ingester pulls a message from the queue and persists it to the database.
        """
        # Add a message to the queue
        sender = Sender(identifier='test_sender', display_name='Test Sender')
        self.user_queue.add_message("Test message", sender, 'user')

        # Start the ingester
        self.ingester.start()

        # Give the ingester a moment to process the message
        time.sleep(1.5)

        # Stop the ingester
        self.ingester.stop()

        # Verify that insert_one was called on the mock collection
        self.mock_queues_collection.insert_one.assert_called_once()

        # Check the content of the inserted document
        inserted_doc = self.mock_queues_collection.insert_one.call_args[0][0]
        self.assertEqual(inserted_doc['content'], "Test message")
        self.assertEqual(inserted_doc['user_id'], 'test_ingester_user')
        self.assertEqual(inserted_doc['provider_name'], 'test_vendor')

        # Verify that the message was removed from the in-memory queue
        self.assertEqual(len(self.user_queue.get_messages()), 0)

if __name__ == '__main__':
    unittest.main()
