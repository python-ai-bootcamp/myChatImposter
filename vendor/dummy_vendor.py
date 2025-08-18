import time
import threading
from typing import Dict

# Assuming queue_manager.py is in the parent directory or accessible
from queue_manager import UserQueue

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
        simulated_messages = [
            {"message": "Hello there!", "sleep_time": 1000},
            {"message": "I have a question about my account.", "sleep_time": 2500},
            {"message": "Can you tell me a joke?", "sleep_time": 500},
            {"message": "This is a very long message to test the character limits of the queue and see if it triggers an eviction policy if the limits are set low enough for this user.", "sleep_time": 4000},
            {"message": "Another message.", "sleep_time": 1500},
            {"message": "Final message for now.", "sleep_time": 2000}
        ]
        for item in simulated_messages:
            if not self.is_listening:
                break

            msg_content = item["message"]
            sleep_duration_ms = item["sleep_time"]

            # Simulate a network delay.
            print(f"VENDOR ({self.user_id}): Waiting for {sleep_duration_ms}ms...")
            time.sleep(sleep_duration_ms / 1000.0)

            # CRITICAL: When a message is received, it's added to the user's
            # queue. This is how the vendor communicates with the orchestrator.
            queue = self.user_queues.get(self.user_id)
            if queue:
                print(f"VENDOR ({self.user_id}): Received a new message: '{msg_content[:30]}...'")
                queue.add_message(content=msg_content, sending_user=self.user_id)
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
