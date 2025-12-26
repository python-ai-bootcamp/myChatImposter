import unittest
import os
import re
from unittest.mock import MagicMock, patch
from queue_manager import UserQueue, Sender
from config_models import QueueConfig

class TestUserQueueUpdated(unittest.TestCase):
    def setUp(self):
        # Create a mock for the MongoDB collection
        self.mock_queues_collection = MagicMock()

    def tearDown(self):
        # Clean up any log files created during tests
        log_dir = 'log'
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                if filename.startswith('test_vendor_'):
                    os.remove(os.path.join(log_dir, filename))

    def test_message_id_initialization(self):
        """
        Test that the UserQueue correctly initializes its message ID from the DB.
        """
        # 1. Test initialization with an existing message in the DB
        self.mock_queues_collection.find_one.return_value = {'id': 100}

        queue_config = QueueConfig(max_messages=5, max_characters=200, max_days=1, max_characters_single_message=50)
        user_queue = UserQueue(
            user_id='test_user_db',
            provider_name='test_vendor',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )

        # Verify it queried the database to initialize the next message ID
        self.mock_queues_collection.find_one.assert_called_once()
        self.assertEqual(user_queue._next_message_id, 101, "Next message ID should be initialized to 101")

        # 2. Test initialization with an empty DB
        self.mock_queues_collection.reset_mock()
        self.mock_queues_collection.find_one.return_value = None

        user_queue_empty = UserQueue(
            user_id='test_user_db_empty',
            provider_name='test_vendor',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        self.assertEqual(user_queue_empty._next_message_id, 1, "Next message ID should default to 1 for an empty DB")

    def test_single_message_truncation(self):
        """
        Test that a message exceeding max_characters_single_message is truncated.
        """
        queue_config = QueueConfig(
            max_messages=5,
            max_characters=200,
            max_days=1,
            max_characters_single_message=50
        )
        user_queue = UserQueue(
            user_id='test_user_truncate',
            provider_name='test_vendor',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        long_message_content = "a" * 100
        user_queue.add_message(long_message_content, sender, 'user')

        messages = user_queue.get_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(len(messages[0].content), 50, "Message should be truncated to 50 chars")
        self.assertEqual(messages[0].content, "a" * 50)

    def test_total_character_limit_eviction(self):
        """
        Test that old messages are evicted (FIFO) when the total max_characters limit is breached.
        """
        queue_config = QueueConfig(
            max_messages=10,
            max_characters=100,
            max_days=1,
            max_characters_single_message=100
        )
        user_queue = UserQueue(
            user_id='test_user_char_limit',
            provider_name='test_vendor',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        # Add messages that fill up 90% of the queue capacity
        user_queue.add_message("1" * 45, sender, 'user')  # Message 1, total chars = 45
        user_queue.add_message("2" * 45, sender, 'user')  # Message 2, total chars = 90

        self.assertEqual(len(user_queue.get_messages()), 2)
        self.assertEqual(user_queue._total_chars, 90)

        # Add a new message of 20 chars. This should exceed the 100 char limit.
        # To fit this message, the first message (45 chars) should be evicted.
        user_queue.add_message("3" * 20, sender, 'user')  # Message 3

        messages = user_queue.get_messages()
        self.assertEqual(len(messages), 2, "Queue should have 2 messages after eviction")
        self.assertEqual(user_queue._total_chars, 65, "Total chars should be 45 + 20 = 65")
        self.assertEqual(messages[0].content, "2" * 45, "The first message should have been evicted")
        self.assertEqual(messages[1].content, "3" * 20, "The new message should be at the end")

    def test_max_messages_limit_eviction(self):
        """
        Test that the queue correctly evicts the oldest messages (FIFO)
        when the max_messages limit is reached.
        """
        queue_config = QueueConfig(
            max_messages=3,
            max_characters=1000,
            max_days=1,
            max_characters_single_message=1000
        )
        user_queue = UserQueue(
            user_id='test_user_msg_limit',
            provider_name='test_vendor',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        for i in range(3):
            user_queue.add_message(f"Message {i}", sender, 'user')

        self.assertEqual(len(user_queue.get_messages()), 3)
        self.assertEqual(user_queue.get_messages()[0].content, "Message 0")

        # This message should trigger the eviction of "Message 0"
        user_queue.add_message("Message 3", sender, 'user')

        messages = user_queue.get_messages()
        self.assertEqual(len(messages), 3, "Queue should still have 3 messages")
        self.assertEqual(messages[0].content, "Message 1", "Oldest message should have been evicted")
        self.assertEqual(messages[2].content, "Message 3", "Newest message should be at the end")

    def test_retention_event_logging(self):
        """
        Test that retention events (evictions) are logged correctly.
        """
        user_id = 'test_user_log'
        provider_name = 'test_vendor'
        log_path = os.path.join('log', f"{provider_name}_{user_id}.log")

        # Ensure log file does not exist before test
        if os.path.exists(log_path):
            os.remove(log_path)

        queue_config = QueueConfig(
            max_messages=2,
            max_characters=100,
            max_days=1,
            max_characters_single_message=100
        )
        user_queue = UserQueue(
            user_id=user_id,
            provider_name=provider_name,
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        # Add messages to fill the queue
        user_queue.add_message("Message 1", sender, 'user')
        user_queue.add_message("Message 2", sender, 'user')

        # This message should trigger an eviction
        user_queue.add_message("Message 3", sender, 'user')

        # Verify the log file was created and contains the eviction event
        self.assertTrue(os.path.exists(log_path))

        with open(log_path, 'r') as f:
            log_content = f.read()

        # Check for the retention event log entry
        self.assertIn("[event_type=EVICT]", log_content)
        self.assertIn("[reason=message_count]", log_content)
        self.assertIn("[evicted_message_id=1]", log_content)

if __name__ == '__main__':
    unittest.main()
