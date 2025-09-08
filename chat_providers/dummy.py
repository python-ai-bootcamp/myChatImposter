import time
import threading
from typing import Dict, Optional, Any, Callable

from .base import BaseChatProvider
from queue_manager import UserQueue, Sender, Group
from config_models import ChatProviderConfig
from logging_lock import FileLogger

class DummyProvider(BaseChatProvider):
    """
    A template and simulation provider. It demonstrates the required interface
    and simulates receiving messages for a user in a background thread.
    """
    def __init__(self, user_id: str, config: ChatProviderConfig, user_queues: Dict[str, UserQueue], on_session_end: Optional[Callable[[str], None]] = None, logger: Optional[FileLogger] = None):
        """
        Initializes the provider.
        - user_id: The specific user this provider instance is for.
        - config: The 'provider_config' block from the JSON configuration.
        - user_queues: A dictionary of all user queues, passed by the Orchestrator.
        - on_session_end: A callback function to notify when a session ends.
        - logger: An instance of FileLogger for logging.
        """
        super().__init__(user_id, config, user_queues, on_session_end, logger)
        self.is_listening = False
        self.thread = None
        if self.logger:
            self.logger.log("Initialized DummyProvider")

    def start_listening(self):
        """
        Starts the message listening loop in a background thread.
        A real provider would establish a connection to a service here.
        This MUST be non-blocking.
        """
        if self.is_listening:
            if self.logger:
                self.logger.log("Already listening.")
            return

        self.is_listening = True
        # Running the listener in a daemon thread allows the main app to exit.
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        if self.logger:
            self.logger.log("Started listening for messages.")

    def stop_listening(self, cleanup_session: bool = False):
        """Stops the message listening loop."""
        self.is_listening = False
        if self.thread and self.logger:
            # The thread will exit on its own since it's a daemon and checks `is_listening`
            self.logger.log("Stopped listening.")

    def _listen(self):
        """
        The actual listening loop. In a real provider, this would be a loop
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
            if self.logger:
                self.logger.log(f"Waiting for {sleep_duration_ms}ms...")
            time.sleep(sleep_duration_ms / 1000.0)

            # CRITICAL: When a message is received, it's added to the user's
            # queue. This is how the provider communicates with the main application.
            queue = self.user_queues.get(self.user_id)
            if queue:
                if self.logger:
                    self.logger.log(f"Received a new message: '{item['message'][:30]}...'")
                queue.add_message(
                    content=item["message"],
                    sender=item["sender"],
                    source='user',
                    originating_time=item["originating_time"],
                    group=item["group"]
                )
            elif self.logger:
                self.logger.log(f"ERROR: Could not find a queue for myself.")

        if self.logger:
            self.logger.log("Finished simulating messages.")
        self.is_listening = False

    def sendMessage(self, recipient: str, message: str):
        """
        Sends a message back to the user.
        A real provider would use a client/API call to send the message here.
        """
        # For the simulation, we just print to the console.
        if self.logger:
            self.logger.log(f"Sending reply to {recipient} ---> {message}")

    def get_status(self) -> Dict[str, Any]:
        """
        Returns the current status of the provider.
        For the dummy provider, it always returns a 'connected' status.
        """
        return {"status": "connected", "message": "Dummy provider is running."}
