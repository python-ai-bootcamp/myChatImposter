import time
import threading
import json
import os
import urllib.request
import urllib.error
import asyncio
import websockets
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
        self.loop = None
        self.base_url = os.environ.get("WHATSAPP_SERVER_URL", "http://localhost:9000")
        self.ws_url = self.base_url.replace("http", "ws")

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
            if self.logger: self.logger.log("Already listening.")
            return

        self.is_listening = True
        self.thread = threading.Thread(target=self._run_listen_loop, daemon=True)
        self.thread.start()
        if self.logger: self.logger.log("Started WebSocket listener for messages.")

    def _run_listen_loop(self):
        """Runs the asyncio event loop for the WebSocket listener."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._listen())
        self.loop.close()

    async def _listen(self):
        """The actual WebSocket listening loop."""
        uri = f"{self.ws_url}/{self.user_id}"
        while self.is_listening:
            try:
                async with websockets.connect(uri) as websocket:
                    if self.logger: self.logger.log(f"WebSocket connection established to {uri}")
                    async for message in websocket:
                        try:
                            messages = json.loads(message)
                            if self.logger: self.logger.log(f"Fetched {len(messages)} new message(s) via WebSocket.")
                            self._process_messages(messages)
                        except json.JSONDecodeError:
                            if self.logger: self.logger.log(f"ERROR: Could not decode JSON from WebSocket: {message}")
            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
                if self.is_listening:
                    if self.logger: self.logger.log(f"WARN: WebSocket connection closed: {e}. Reconnecting in 5s...")
                    await asyncio.sleep(5)
            except Exception as e:
                if self.is_listening:
                    if self.logger: self.logger.log(f"ERROR: Unhandled exception in WebSocket listener: {e}. Retrying in 10s...")
                    await asyncio.sleep(10)

    def _process_messages(self, messages):
        """Processes a list of incoming messages."""
        queue = self.user_queues.get(self.user_id)
        if not queue:
            if self.logger: self.logger.log("ERROR: Could not find a queue for myself.")
            return
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

    def stop_listening(self, cleanup_session: bool = False):
        """Stops the message listening loop."""
        if self.logger: self.logger.log(f"Stopping... (cleanup={cleanup_session})")
        self.is_listening = False

        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

        if self.thread:
            self.thread.join(timeout=5)
            if self.logger: self.logger.log("WebSocket listener thread stopped.")

        if cleanup_session:
            self._cleanup_server_session()

        if self.on_session_end and not self.session_ended:
            self.session_ended = True
            self.on_session_end(self.user_id)

    def _cleanup_server_session(self):
        """Requests session cleanup on the Node.js server."""
        if self.logger: self.logger.log("Requesting session cleanup on Node.js server.")
        try:
            req = urllib.request.Request(f"{self.base_url}/sessions/{self.user_id}", method='DELETE')
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    if self.logger: self.logger.log("Successfully requested session cleanup.")
        except Exception as e:
            if self.logger: self.logger.log(f"ERROR: Failed to request session cleanup: {e}")

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
                return {"status": "error", "message": f"Unexpected status code {response.status}"}
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"status": "disconnected", "message": "Session not found on Node.js server."}
            return {"status": "error", "message": f"HTTP Error {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"status": "initializing", "message": f"Node.js server is not reachable: {e.reason}"}
        except Exception as e:
            return {"status": "error", "message": f"Exception while getting status: {e}"}
