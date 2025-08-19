import unittest
import time
from queue_manager import UserQueue, Sender

class TestUserQueue(unittest.TestCase):

    def test_message_truncation_and_queue_clearing(self):
        """
        Test that a message exceeding max_characters is truncated
        and that the queue is cleared before adding it.
        """
        # 1. Setup the queue with specific limits
        user_queue = UserQueue(
            user_id='test_user',
            vendor_name='test_vendor',
            max_messages=5,
            max_characters=100,
            max_days=1
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        # 2. Add some initial messages
        for i in range(3):
            user_queue.add_message(f"Initial message {i}", sender, 'user')

        self.assertEqual(len(user_queue.get_messages()), 3)

        # 3. Add a message that is too long
        long_message_content = "a" * 150
        user_queue.add_message(long_message_content, sender, 'user')

        # 4. Assertions
        messages = user_queue.get_messages()
        self.assertEqual(len(messages), 1, "Queue should only have one message")

        # Check that the message was truncated
        self.assertEqual(len(messages[0].content), 100, "Message content should be truncated to 100 characters")
        self.assertEqual(messages[0].content, "a" * 100, "Message content is not the truncated content")

    def test_fifo_eviction(self):
        """
        Test that the queue correctly evicts the oldest messages (FIFO)
        when the max_messages limit is reached.
        """
        # 1. Setup the queue
        user_queue = UserQueue(
            user_id='test_user_fifo',
            vendor_name='test_vendor',
            max_messages=3,
            max_characters=1000,
            max_days=1
        )
        sender = Sender(identifier='test_sender', display_name='Test Sender')

        # 2. Add messages to fill the queue
        for i in range(3):
            user_queue.add_message(f"Message {i}", sender, 'user')

        self.assertEqual(len(user_queue.get_messages()), 3)
        self.assertEqual(user_queue.get_messages()[0].content, "Message 0")

        # 3. Add one more message to trigger eviction
        user_queue.add_message("Message 3", sender, 'user')

        # 4. Assertions
        messages = user_queue.get_messages()
        self.assertEqual(len(messages), 3, "Queue should have 3 messages")
        self.assertEqual(messages[0].content, "Message 1", "Oldest message should have been evicted")
        self.assertEqual(messages[2].content, "Message 3", "Newest message should be at the end")

if __name__ == '__main__':
    unittest.main()
