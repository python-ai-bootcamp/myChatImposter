import time
import threading
from typing import Dict, Optional

# Assuming queue_manager.py is in the parent directory or accessible
from queue_manager import UserQueue, Sender, Group

class DummyVendor:
    """
    A template and simulation vendor. It demonstrates the required interface
    and simulates receiving messages for a user in a background thread.
    """
    def __init__(self, user_id: str, config: Dict, user_queues: Dict[str, UserQueue]):
        """
        Initializes the vendor.
        - user_id: The specific user this vendor instance is for.
        - config: The 'vendor_config' block from the JSON configuration.
        - user_queues: A dictionary of all user queues, passed by the Orchestrator.
        """
        self.user_id = user_id
        self.config = config  # e.g., {'api_key': '...'}
        self.user_queues = user_queues
        self.is_listening = False
        self.thread = None
        print(f"VENDOR ({self.user_id}): Initialized DummyVendor with key '{self.config.get('api_key')}'")

    def start_listening(self):
        """
        Starts the message listening loop in a background thread.
        A real vendor would establish a connection to a service here.
        This MUST be non-blocking.
        """
        if self.is_listening:
            print(f"VENDOR ({self.user_id}): Already listening.")
            return

        self.is_listening = True
        # Running the listener in a daemon thread allows the main app to exit.
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        print(f"VENDOR ({self.user_id}): Started listening for messages.")

    def stop_listening(self):
        """Stops the message listening loop."""
        self.is_listening = False
        if self.thread:
            # The thread will exit on its own since it's a daemon and checks `is_listening`
            print(f"VENDOR ({self.user_id}): Stopped listening.")

    def _listen(self):
        """
        The actual listening loop. In a real vendor, this would be a loop
        polling an API, a WebSocket 'on_message' handler, or a web server
        endpoint for a webhook.
        """
        # This simulation just iterates through a list of predefined messages.
        now = int(time.time() * 1000)
        simulated_messages = [
            {
                "message": "Hello there!", "sleep_time": 1000,
                "sender": Sender(identifier="user1@c.us", display_name="User One"),
                "group": None,
                "originating_time": now - 20000
            },
            {
                "message": "I have a question about my account.", "sleep_time": 2500,
                "sender": Sender(identifier="user2@c.us", display_name="User Two"),
                "group": Group(identifier="group1@g.us", display_name="Test Group"),
                "originating_time": now - 15000
            },
            {
                "message": "Can you tell me a joke?", "sleep_time": 500,
                "sender": Sender(identifier="user1@c.us", display_name="User One"),
                "group": None,
                "originating_time": now - 10000
            },
            {
                "message": "This is a very long message to test the character limits of the queue and see if it triggers an eviction policy if the limits are set low enough for this user.", "sleep_time": 4000,
                "sender": Sender(identifier="user3@c.us", display_name="User Three"),
                "group": None,
                "originating_time": now - 5000
            },
            {
                "message": "another message", "sleep_time": 1000,
                "sender": Sender(identifier="user3@c.us", display_name="User Three"),
                "group": None,
                "originating_time": now - 1000
            },
            {
                "message": "yet another message", "sleep_time": 1000,
                "sender": Sender(identifier="user3@c.us", display_name="User Three"),
                "group": None,
                "originating_time": now - 1000
            },
            {
                "message": "yet yet another message", "sleep_time": 1000,
                "sender": Sender(identifier="user3@c.us", display_name="User Three"),
                "group": None,
                "originating_time": now - 1000
            },
        ]
        for item in simulated_messages:
            if not self.is_listening:
                break

            # Simulate a network delay.
            sleep_duration_ms = item["sleep_time"]
            print(f"VENDOR ({self.user_id}): Waiting for {sleep_duration_ms}ms...")
            time.sleep(sleep_duration_ms / 1000.0)

            # CRITICAL: When a message is received, it's added to the user's
            # queue. This is how the vendor communicates with the orchestrator.
            queue = self.user_queues.get(self.user_id)
            if queue:
                print(f"VENDOR ({self.user_id}): Received a new message: '{item['message'][:30]}...'")
                queue.add_message(
                    content=item["message"],
                    sender=item["sender"],
                    source='user',
                    originating_time=item["originating_time"],
                    group=item["group"]
                )
            else:
                print(f"VENDOR ERROR ({self.user_id}): Could not find a queue for myself.")

        print(f"VENDOR ({self.user_id}): Finished simulating messages.")
        self.is_listening = False

    def sendMessage(self, message: str):
        """
        Sends a message back to the user.
        A real vendor would use a client/API call to send the message here.
        """
        # For the simulation, we just print to the console.
        print(f"VENDOR ({self.user_id}): Sending reply ---> {message}")
