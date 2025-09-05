import time
import threading
import json
import os
import requests  # Using requests library for easier HTTP communication
from typing import Dict

from queue_manager import UserQueue, Sender, Group
from logging_lock import console_log
from .base import BaseChatProvider
from config_models import ChatProviderConfig

# The base URL of the Node.js Baileys server.
# It's recommended to use an environment variable for this in a containerized setup.
NODE_SERVER_URL = os.environ.get("BAILEYS_SERVER_URL", "http://localhost:3000")

class WhatsAppBaileysProvider(BaseChatProvider):
    """
    A provider that connects to a centralized, multi-session Node.js Baileys server
    to send and receive WhatsApp messages.
    """
    def __init__(self, user_id: str, config: ChatProviderConfig, user_queues: Dict[str, UserQueue], on_session_end=None):
        super().__init__(user_id, config, user_queues, on_session_end)
        self.is_listening = False
        self.session_ended = False
        self.thread = None
        self.base_url = f"{NODE_SERVER_URL}/sessions/{self.user_id}"

        console_log(f"PROVIDER ({self.user_id}): Initialized. Will connect to Node.js server at {NODE_SERVER_URL}")

    def start_listening(self):
        """
        Ensures a session is created on the Node.js server and starts polling for messages.
        """
        if self.is_listening:
            console_log(f"PROVIDER ({self.user_id}): Already listening.")
            return

        # --- Create session on the Node.js server ---
        try:
            console_log(f"PROVIDER ({self.user_id}): Creating session on Node.js server...")
            payload = {
                "userId": self.user_id,
                "config": self.config.provider_config.model_dump()
            }
            response = requests.post(f"{NODE_SERVER_URL}/sessions", json=payload, timeout=20)

            if response.status_code == 409: # Conflict, session exists
                 console_log(f"PROVIDER ({self.user_id}): Session already exists on Node.js server. Proceeding.")
            elif response.status_code != 201: # Created
                console_log(f"PROVIDER_ERROR ({self.user_id}): Failed to create session. Status: {response.status_code}, Body: {response.text}")
                raise Exception(f"Failed to create session on Node.js server: {response.text}")

            console_log(f"PROVIDER ({self.user_id}): Session created or confirmed on Node.js server.")

        except requests.exceptions.RequestException as e:
            console_log(f"PROVIDER_ERROR ({self.user_id}): Could not connect to Node.js server to create session: {e}")
            # We can't proceed without the node server, so we'll stop here.
            # The main application logic can decide whether to retry.
            if self.on_session_end and not self.session_ended:
                 self.session_ended = True
                 self.on_session_end(self.user_id)
            return

        self.is_listening = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        console_log(f"PROVIDER ({self.user_id}): Started polling for messages from Node.js server.")

    def stop_listening(self):
        """
        Stops the message listening loop and deletes the session from the Node.js server.
        """
        console_log(f"PROVIDER ({self.user_id}): Stopping...")
        self.is_listening = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
            console_log(f"PROVIDER ({self.user_id}): Polling thread stopped.")

        # --- Delete session on the Node.js server ---
        try:
            console_log(f"PROVIDER ({self.user_id}): Deleting session from Node.js server...")
            response = requests.delete(self.base_url, timeout=20)
            if response.status_code not in [200, 404]: # OK or Not Found
                console_log(f"PROVIDER_WARN ({self.user_id}): Failed to cleanly delete session. Status: {response.status_code}, Body: {response.text}")
            else:
                 console_log(f"PROVIDER ({self.user_id}): Session deleted from Node.js server.")
        except requests.exceptions.RequestException as e:
            console_log(f"PROVIDER_WARN ({self.user_id}): Could not connect to Node.js server to delete session: {e}")

        # Call the session end callback to clean up the main application's state
        if self.on_session_end and not self.session_ended:
            self.session_ended = True
            self.on_session_end(self.user_id)

    def _listen(self):
        """
        The actual listening loop. It polls the Node.js server's /messages endpoint
        for this specific user's session.
        """
        while self.is_listening:
            try:
                response = requests.get(f"{self.base_url}/messages", timeout=15)
                if response.status_code == 200:
                    messages = response.json()
                    if messages:
                        console_log(f"PROVIDER ({self.user_id}): Fetched {len(messages)} new message(s).")
                        queue = self.user_queues.get(self.user_id)
                        if queue:
                            for msg in messages:
                                group_info = msg.get('group')
                                if group_info and not self.config.provider_config.allow_group_messages:
                                    continue

                                sender = Sender(identifier=msg['sender'], display_name=msg.get('display_name', msg['sender']))
                                group = Group(identifier=group_info['id'], display_name=group_info.get('name') or group_info['id']) if group_info else None

                                queue.add_message(content=msg['message'], sender=sender, source='user', group=group)
                        else:
                            console_log(f"PROVIDER_ERROR ({self.user_id}): Could not find a queue for myself.")
                elif response.status_code == 404:
                    console_log(f"PROVIDER_ERROR ({self.user_id}): Session not found on Node server. Ending listener.")
                    self.is_listening = False # Stop the loop
                else:
                    console_log(f"PROVIDER_ERROR ({self.user_id}): Error polling for messages. Status: {response.status_code}, Body: {response.text}")

            except requests.exceptions.RequestException as e:
                console_log(f"PROVIDER_ERROR ({self.user_id}): Exception while polling for messages: {e}")
                # If we can't reach the server, wait a bit before retrying.
                time.sleep(5)

            time.sleep(5) # Poll every 5 seconds

    def sendMessage(self, recipient: str, message: str):
        """
        Sends a message back to the user via the Node.js server.
        """
        console_log(f"PROVIDER ({self.user_id}): Sending reply to {recipient} ---> {message[:50]}...")
        try:
            payload = {"recipient": recipient, "message": message}
            response = requests.post(f"{self.base_url}/send", json=payload, timeout=20)
            if response.status_code != 200:
                console_log(f"PROVIDER_ERROR ({self.user_id}): Failed to send message. Status: {response.status_code}, Body: {response.text}")
        except requests.exceptions.RequestException as e:
            console_log(f"PROVIDER_ERROR ({self.user_id}): Exception while sending message: {e}")

    def get_status(self) -> Dict:
        """
        Gets the connection status from the Node.js server for this session.
        """
        try:
            response = requests.get(f"{self.base_url}/status", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                # If a session is not found (404), it's equivalent to it being disconnected.
                if response.status_code == 404:
                    return {"status": "disconnected", "message": "Session not found on the server."}
                return {"status": "error", "message": f"Failed to get status, HTTP {response.status_code}"}
        except requests.exceptions.RequestException as e:
            # This can happen if the node server itself is down.
            return {"status": "error", "message": f"Could not connect to the Baileys server: {e}"}
