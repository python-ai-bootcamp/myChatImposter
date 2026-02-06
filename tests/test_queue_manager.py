import asyncio
import unittest
import os
from unittest.mock import MagicMock, patch, AsyncMock
from pymongo import DESCENDING
from queue_manager import CorrespondentQueue, UserQueuesManager, Sender
from config_models import QueueConfig

class TestCorrespondentQueue(unittest.TestCase):
    def setUp(self):
        # Create a mock for the MongoDB collection
        self.mock_queues_collection = MagicMock()

    def tearDown(self):
        # Clean up any log files created during tests
        log_dir = 'log'
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                if filename.startswith('test_vendor_test_user'): # Broad pattern to catch all test logs
                    os.remove(os.path.join(log_dir, filename))

    def test_message_id_initialization(self):
        """
        Test that the CorrespondentQueue correctly initializes its message ID from the DB.
        """
        # 1. Test initialization with an existing message in the DB
        self.mock_queues_collection.find_one = AsyncMock(return_value={'id': 100})
        queue_config = QueueConfig(max_messages=5, max_characters=200, max_days=1, max_characters_single_message=50)

        cor_queue = CorrespondentQueue(
            user_id='test_user_db',
            provider_name='test_vendor',
            correspondent_id='cor1',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        asyncio.run(cor_queue.initialize())

        # Verify it queried the database with the correct correspondent_id
        self.mock_queues_collection.find_one.assert_called_with(
            {"user_id": "test_user_db", "provider_name": "test_vendor", "correspondent_id": "cor1"},
            sort=[("id", DESCENDING)]
        )
        self.assertEqual(cor_queue._next_message_id, 101, "Next message ID should be initialized to 101")

        # 2. Test initialization with an empty DB
        self.mock_queues_collection.reset_mock()
        self.mock_queues_collection.find_one.return_value = None

        cor_queue_empty = CorrespondentQueue(
            user_id='test_user_db_empty',
            provider_name='test_vendor',
            correspondent_id='cor2',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        self.assertEqual(cor_queue_empty._next_message_id, 1, "Next message ID should default to 1 for an empty DB")

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
        user_queue = CorrespondentQueue(
            user_id='test_user_truncate',
            provider_name='test_vendor',
            correspondent_id='cor_truncate',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        long_message_content = "a" * 100
        asyncio.run(user_queue.add_message(long_message_content, sender, 'user'))

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
        user_queue = CorrespondentQueue(
            user_id='test_user_char_limit',
            provider_name='test_vendor',
            correspondent_id='cor_char_limit',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        # Add messages that fill up 90% of the queue capacity
        asyncio.run(user_queue.add_message("1" * 45, sender, 'user'))  # Message 1, total chars = 45
        asyncio.run(user_queue.add_message("2" * 45, sender, 'user'))  # Message 2, total chars = 90

        self.assertEqual(len(user_queue.get_messages()), 2)
        self.assertEqual(user_queue._total_chars, 90)

        # Add a new message of 20 chars. This should exceed the 100 char limit.
        # To fit this message, the first message (45 chars) should be evicted.
        asyncio.run(user_queue.add_message("3" * 20, sender, 'user'))  # Message 3

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
        user_queue = CorrespondentQueue(
            user_id='test_user_msg_limit',
            provider_name='test_vendor',
            correspondent_id='cor_msg_limit',
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        for i in range(3):
            asyncio.run(user_queue.add_message(f"Message {i}", sender, 'user'))

        self.assertEqual(len(user_queue.get_messages()), 3)
        self.assertEqual(user_queue.get_messages()[0].content, "Message 0")

        # This message should trigger the eviction of "Message 0"
        asyncio.run(user_queue.add_message("Message 3", sender, 'user'))

        messages = user_queue.get_messages()
        self.assertEqual(len(messages), 3, "Queue should still have 3 messages")
        self.assertEqual(messages[0].content, "Message 1", "Oldest message should have been evicted")
        self.assertEqual(messages[2].content, "Message 3", "Newest message should be at the end")

    def test_retention_event_logging(self):
        """
        Test that retention events (evictions) are logged correctly to a correspondent-specific file.
        """
        user_id = 'test_user_log'
        provider_name = 'test_vendor'
        correspondent_id = 'cor_log'
        log_path = os.path.join('log', f"{provider_name}_{user_id}_{correspondent_id}.log")

        # Ensure log file does not exist before test
        if os.path.exists(log_path):
            os.remove(log_path)

        queue_config = QueueConfig(
            max_messages=2,
            max_characters=100,
            max_days=1,
            max_characters_single_message=100
        )
        user_queue = CorrespondentQueue(
            user_id=user_id,
            provider_name=provider_name,
            correspondent_id=correspondent_id,
            queue_config=queue_config,
            queues_collection=self.mock_queues_collection
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        # Add messages to fill the queue
        asyncio.run(user_queue.add_message("Message 1", sender, 'user'))
        asyncio.run(user_queue.add_message("Message 2", sender, 'user'))

        # This message should trigger an eviction
        with self.assertLogs(level='INFO') as cm:
            asyncio.run(user_queue.add_message("Message 3", sender, 'user'))
        
        # Verify the log file was created and contains the eviction event
        # self.assertTrue(os.path.exists(log_path)) # Deprecated file logging
        
        # Verify logging
        self.assertTrue(any("RETENTION EVENT" in o for o in cm.output), "Retention event not logged")
        self.assertTrue(any("reason=message_count" in o for o in cm.output))

class TestUserQueuesManager(unittest.TestCase):
    def setUp(self):
        self.mock_queues_collection = MagicMock()
        self.queue_config = QueueConfig(max_messages=10, max_characters=1000, max_days=1, max_characters_single_message=100)
        self.mock_loop = MagicMock()
        self.manager = UserQueuesManager(
            user_id='manager_user',
            provider_name='manager_vendor',
            queue_config=self.queue_config,
            queues_collection=self.mock_queues_collection,
            main_loop=self.mock_loop
        )

    def test_get_or_create_queue(self):
        """Test that queues are created on demand and retrieved correctly."""
        # First request should create a queue
        queue1 = asyncio.run(self.manager.get_or_create_queue('cor1'))
        self.assertIsInstance(queue1, CorrespondentQueue)
        self.assertEqual(queue1.correspondent_id, 'cor1')
        self.assertEqual(queue1.user_id, 'manager_user')

        # Second request for the same ID should return the same instance
        queue2 = asyncio.run(self.manager.get_or_create_queue('cor1'))
        self.assertIs(queue1, queue2)

        # Request for a different ID should create a new queue
        queue3 = asyncio.run(self.manager.get_or_create_queue('cor2'))
        self.assertIsNot(queue1, queue3)
        self.assertEqual(queue3.correspondent_id, 'cor2')

    def test_add_message_routes_correctly(self):
        """Test that add_message adds a message to the correct correspondent's queue."""
        sender = Sender(identifier='test_sender', display_name='Test Sender')
        asyncio.run(self.manager.add_message('cor1', "Hello Cor1", sender, 'user'))
        asyncio.run(self.manager.add_message('cor2', "Hello Cor2", sender, 'user'))

        cor1_queue = self.manager.get_queue('cor1')
        cor2_queue = self.manager.get_queue('cor2')
        cor3_queue = self.manager.get_queue('cor3')

        self.assertEqual(len(cor1_queue.get_messages()), 1)
        self.assertEqual(cor1_queue.get_messages()[0].content, "Hello Cor1")
        self.assertEqual(len(cor2_queue.get_messages()), 1)
        self.assertEqual(cor2_queue.get_messages()[0].content, "Hello Cor2")
        self.assertIsNone(cor3_queue)

    def test_callback_registration(self):
        """Test that callbacks are registered with all queues, including future ones."""
        mock_callback = MagicMock()
        mock_coroutine = MagicMock()
        mock_callback.return_value = mock_coroutine

        # Register callback before any queues are created
        self.manager.register_callback(mock_callback)

        # Create a queue, it should have the callback
        queue1 = asyncio.run(self.manager.get_or_create_queue('cor1'))
        self.assertIn(mock_callback, queue1._callbacks)

        # Trigger a message
        sender = Sender(identifier='test_sender', display_name='Test Sender')
        with patch('asyncio.run_coroutine_threadsafe') as mock_run_coroutine:
            asyncio.run(self.manager.add_message('cor1', "Test message", sender, 'user'))

            # 1. Assert that our mock callback was called to create the coroutine
            mock_callback.assert_called_once()
            args, _ = mock_callback.call_args
            self.assertEqual(args[0], 'manager_user')
            self.assertEqual(args[1], 'cor1')
            self.assertEqual(args[2].content, "Test message")

            # 2. Assert that the created coroutine was passed to run_coroutine_threadsafe
            mock_run_coroutine.assert_called_once_with(mock_coroutine, self.mock_loop)

        # Create a second queue, it should also have the callback
        queue2 = asyncio.run(self.manager.get_or_create_queue('cor2'))
        self.assertIn(mock_callback, queue2._callbacks)

if __name__ == '__main__':
    unittest.main()
