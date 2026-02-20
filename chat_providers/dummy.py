import time
import threading
import asyncio
from typing import Dict, Optional, Any, Callable

from .base import BaseChatProvider
from queue_manager import BotQueuesManager, Sender, Group
from config_models import ChatProviderConfig
import logging


class DummyProvider(BaseChatProvider):
    """
    A template and simulation provider. It demonstrates the required interface
    and simulates receiving messages for a user in a background thread.
    """
    def __init__(self, bot_id: str, config: ChatProviderConfig, bot_queues: Dict[str, BotQueuesManager], on_session_end: Optional[Callable[[str], None]] = None, **kwargs):
        """
        Initializes the provider.
        - bot_id: The specific user this provider instance is for.
        - config: The 'provider_config' block from the JSON configuration.
        - bot_queues: A dictionary of all bot queues, passed by the Orchestrator.
        - on_session_end: A callback function to notify when a session ends.
        """
        super().__init__(bot_id, config, bot_queues, on_session_end, **kwargs)
        self.is_listening = False
        self.thread = None
        logging.info("Initialized DummyProvider")

    async def start_listening(self):
        """
        Starts the message listening loop in a background thread.
        A real provider would establish a connection to a service here.
        This MUST be non-blocking.
        """
        if self.is_listening:
            logging.warning("Already listening.")
            return

        self.is_listening = True
        # Running the listener in a daemon thread allows the main app to exit.
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        logging.info("Started listening for messages.")

    async def stop_listening(self, cleanup_session: bool = False):
        """Stops the message listening loop."""
        self.is_listening = False
        if self.thread:
            # The thread will exit on its own since it's a daemon and checks `is_listening`
            logging.info("Stopped listening.")

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
                "originating_time": now - 20000,
                "correspondent_id": "user1@c.us"
            },
            {
                "message": "I have a question about my account.", "sleep_time": 2500,
                "sender": Sender(identifier="user2@c.us", display_name="User Two"),
                "group": Group(identifier="group1@g.us", display_name="Test Group"),
                "originating_time": now - 15000,
                "correspondent_id": "group1@g.us"
            },
            {
                "message": "Can you tell me a joke?", "sleep_time": 500,
                "sender": Sender(identifier="user1@c.us", display_name="User One"),
                "group": None,
                "originating_time": now - 10000,
                "correspondent_id": "user1@c.us"
            },
            {
                "message": "This is a very long message to test the character limits of the queue and see if it triggers an eviction policy if the limits are set low enough for this user.", "sleep_time": 4000,
                "sender": Sender(identifier="user3@c.us", display_name="User Three"),
                "group": None,
                "originating_time": now - 5000,
                "correspondent_id": "user3@c.us"
            },
            {
                "message": "another message", "sleep_time": 1000,
                "sender": Sender(identifier="user3@c.us", display_name="User Three"),
                "group": None,
                "originating_time": now - 1000,
                "correspondent_id": "user3@c.us"
            },
            {
                "message": "yet another message", "sleep_time": 1000,
                "sender": Sender(identifier="user3@c.us", display_name="User Three"),
                "group": None,
                "originating_time": now - 1000,
                "correspondent_id": "user3@c.us"
            },
            {
                "message": "yet yet another message", "sleep_time": 1000,
                "sender": Sender(identifier="user3@c.us", display_name="User Three"),
                "group": None,
                "originating_time": now - 1000,
                "correspondent_id": "user3@c.us"
            },
        ]
        for item in simulated_messages:
            if not self.is_listening:
                break

            # Simulate a network delay.
            sleep_duration_ms = item["sleep_time"]
            if self.is_listening:
                logging.info(f"Waiting for {sleep_duration_ms}ms...")
            time.sleep(sleep_duration_ms / 1000.0)

            # CRITICAL: When a message is received, it's added to the bot's
            # queue. This is how the provider communicates with the main application.
            queues_manager = self.bot_queues.get(self.bot_id)
            if queues_manager:
                logging.info(f"Received a new message: '{item['message'][:30]}...' for correspondent {item['correspondent_id']}")
                if self.main_loop:
                    future = asyncio.run_coroutine_threadsafe(
                        queues_manager.add_message(
                            correspondent_id=item["correspondent_id"],
                            content=item["message"],
                            sender=item["sender"],
                            source='user',
                            originating_time=item["originating_time"],
                            group=item["group"]
                        ),
                        self.main_loop
                    )
                    try:
                        future.result(timeout=5)
                    except Exception as e:
                        logging.error(f"DummyProvider: Error adding message to queue: {e}")
                else:
                    logging.error("DummyProvider: No main_loop available to schedule async message addition.")
            else:
                logging.error(f"ERROR: Could not find a queues manager for myself.")

        logging.info("Finished simulating messages.")
        self.is_listening = False

    def sendMessage(self, recipient: str, message: str):
        """
        Sends a message back to the user.
        A real provider would use a client/API call to send the message here.
        """
        # For the simulation, we just print to the console.
        logging.info(f"Sending reply to {recipient} ---> {message}")

    async def send_file(self, recipient: str, file_data: bytes, filename: str, mime_type: str, caption: Optional[str] = None):
        """
        Sends a file attachment to the specified recipient.
        """
        logging.info(f"Sending file {filename} ({mime_type}) to {recipient} with caption: {caption}")

    def get_status(self, heartbeat: bool = False) -> Dict[str, Any]:
        """
        Returns the current status of the provider.
        """
        return {"status": "connected", "message": "Dummy provider is running."}

    @property
    def is_connected(self) -> bool:
        return True
