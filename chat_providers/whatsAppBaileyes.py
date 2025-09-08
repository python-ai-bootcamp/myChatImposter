import time
import threading
import json
import os
import urllib.request
import urllib.error
from typing import Dict, Optional, Callable

from queue_manager import UserQueue, Sender, Group, Message
from logging_lock import FileLogger
from .base import BaseChatProvider
from config_models import ChatProviderConfig

class WhatsAppBaileysProvider(BaseChatProvider):
    """
    A provider that connects to a Node.js Baileys server to send and receive WhatsApp messages.
    """
    def __init__(self, user_id: str, config: ChatProviderConfig, user_queues: Dict[str, UserQueue], on_session_end: Optional[Callable[[str], None]] = None, logger: Optional[FileLogger] = None):
        """
        Initializes the provider.
        - user_id: The specific user this provider instance is for.
        - config: The 'provider_config' block from the JSON configuration.
        - user_queues: A dictionary of all user queues, passed by the main application.
        - on_session_end: Callback to notify when a session ends.
        - logger: An instance of FileLogger for logging.
        """
        super().__init__(user_id, config, user_queues, on_session_end, logger)
        self.is_listening = False
        self.session_ended = False
        self.thread = None
        self.base_url = os.environ.get("WHATSAPP_SERVER_URL", "http://localhost:9000")

        # The Node.js server is now a separate container managed by docker-compose.
        # We just need to know its URL.
        if self.logger:
            self.logger.log(f"Connecting to Node.js server at {self.base_url}")
        self._send_config_to_server()

    def _send_config_to_server(self):
        """Sends the user-specific configuration to the Node.js server."""
        try:
            config_data = {
                "userId": self.user_id,
                "config": self.config.provider_config.model_dump()
            }
            data = json.dumps(config_data).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/initialize",
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    if self.logger:
                        self.logger.log("Successfully sent configuration to Node.js server.")
                else:
                    body = response.read().decode('utf-8', 'backslashreplace')
                    if self.logger:
                        self.logger.log(f"ERROR: Failed to send config. Status: {response.status}, Body: {body}")
        except Exception as e:
            if self.logger:
                self.logger.log(f"ERROR: Exception while sending configuration: {e}")


    def start_listening(self):
        """Starts the message listening loop in a background thread."""
        if self.is_listening:
            if self.logger:
                self.logger.log("Already listening.")
            return

        self.is_listening = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        if self.logger:
            self.logger.log("Started polling for messages from Node.js server.")

    def stop_listening(self, cleanup_session: bool = False):
        """
        Stops the message listening loop.

        Args:
            cleanup_session (bool): If True, deletes the session data from the Node.js server.
                                    This should be used for unlinking, not for shutdown.
        """
        if self.logger:
            self.logger.log(f"Stopping... (cleanup={cleanup_session})")
        self.is_listening = False
        if self.thread:
            # The thread will exit on its own since it checks `is_listening`
            self.thread.join()
            if self.logger:
                self.logger.log("Polling thread stopped.")

        # If requested, tell the Node.js server to clean up the session.
        if cleanup_session:
            if self.logger:
                self.logger.log("Requesting session cleanup on Node.js server.")
            try:
                req = urllib.request.Request(f"{self.base_url}/sessions/{self.user_id}", method='DELETE')
                with urllib.request.urlopen(req) as response:
                    if response.status == 200:
                        if self.logger:
                            self.logger.log("Successfully requested session cleanup.")
            except Exception as e:
                if self.logger:
                    self.logger.log(f"ERROR: Failed to request session cleanup: {e}")

        # Call the session end callback to clean up the main application's state
        if self.on_session_end and not self.session_ended:
            self.session_ended = True
            self.on_session_end(self.user_id)

    def _listen(self):
        """
        The actual listening loop. It polls the Node.js server's /messages
        endpoint to fetch incoming WhatsApp messages for a specific user.
        """
        messages_url = f"{self.base_url}/sessions/{self.user_id}/messages"
        while self.is_listening:
            try:
                with urllib.request.urlopen(messages_url, timeout=10) as response:
                    if response.status == 200:
                        messages = json.loads(response.read().decode('utf-8'))
                        if messages:
                            if self.logger:
                                self.logger.log(f"Fetched {len(messages)} new message(s).")
                            queue = self.user_queues.get(self.user_id)
                            if queue:
                                for msg in messages:
                                    group_info = msg.get('group')
                                    if group_info and not self.config.provider_config.allow_group_messages:
                                        continue

                                    sender = Sender(identifier=msg['sender'], display_name=msg.get('display_name', msg['sender']))
                                    group = Group(identifier=group_info['id'], display_name=group_info.get('name') or group_info['id']) if group_info else None
                                    queue.add_message(
                                        content=msg['message'],
                                        sender=sender,
                                        source='user',
                                        group=group
                                    )
                            elif self.logger:
                                self.logger.log("ERROR: Could not find a queue for myself.")
                    elif response.status == 404:
                         if self.logger:
                            self.logger.log("WARN: Session not found on Node.js server. It might be initializing.")
                         time.sleep(5) # Wait longer if session is not ready
                    elif self.logger:
                        self.logger.log(f"ERROR: Error polling for messages. Status: {response.status}")
            except urllib.error.URLError as e:
                time.sleep(2)
                continue
            except Exception as e:
                if self.logger:
                    self.logger.log(f"ERROR: Exception while polling for messages: {e}")

            time.sleep(5)

    def sendMessage(self, recipient: str, message: str):
        """
        Sends a message back to the user via the Node.js server for a specific session.
        """
        if self.logger:
            self.logger.log(f"Sending reply to {recipient} ---> {message[:50]}...")
        try:
            data = json.dumps({"recipient": recipient, "message": message}).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/sessions/{self.user_id}/send",
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    body = response.read().decode('utf-8', 'backslashreplace')
                    if self.logger:
                        self.logger.log(f"ERROR: Failed to send message. Status: {response.status}, Body: {body}")
        except Exception as e:
            if self.logger:
                self.logger.log(f"ERROR: Exception while sending message: {e}")

    def get_status(self) -> Dict:
        """
        Gets the connection status from the Node.js server for a specific session.
        """
        try:
            with urllib.request.urlopen(f"{self.base_url}/sessions/{self.user_id}/status", timeout=5) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
                else:
                    return {"status": "error", "message": f"Failed to get status, HTTP {response.status}"}
        except urllib.error.URLError as e:
            return {"status": "initializing", "message": "Node.js server is not reachable yet."}
        except Exception as e:
            return {"status": "error", "message": f"Exception while getting status: {e}"}
