import asyncio
import json
import os
import threading
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Dict, Optional, Callable

import httpx
import websockets

from queue_manager import UserQueuesManager, Sender, Group, Message
from logging_lock import FileLogger
from .base import BaseChatProvider
from config_models import ChatProviderConfig


class WhatsAppBaileysProvider(BaseChatProvider):
    def __init__(self, user_id: str, config: ChatProviderConfig, user_queues: Dict[str, UserQueuesManager], on_session_end: Optional[Callable[[str], None]] = None, logger: Optional[FileLogger] = None):
        super().__init__(user_id, config, user_queues, on_session_end, logger)
        self.is_listening = False
        self.session_ended = False
        self.thread = None
        self.loop = None
        self.stop_event = None
        self.cleanup_on_stop = False  # New flag to signal cleanup action
        self.base_url = os.environ.get("WHATSAPP_SERVER_URL", "http://localhost:9000")
        self.ws_url = self.base_url.replace("http", "ws")

    async def _send_config_to_server(self):
        if self.logger: self.logger.log(f"Connecting to Node.js server at {self.base_url}")
        try:
            config_data = {"userId": self.user_id, "config": self.config.provider_config.model_dump()}
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/initialize", json=config_data, headers={'Content-Type': 'application/json'})
                if response.status_code == 200:
                    if self.logger: self.logger.log("Successfully sent configuration to Node.js server.")
                else:
                    if self.logger: self.logger.log(f"ERROR: Failed to send config. Status: {response.status_code}, Body: {response.text}")
        except Exception as e:
            if self.logger: self.logger.log(f"ERROR: Exception while sending configuration: {e}")

    async def start_listening(self):
        if self.is_listening:
            if self.logger: self.logger.log("Already listening.")
            return
        await self._send_config_to_server()
        self.is_listening = True
        self.thread = threading.Thread(target=self._run_listen_loop, daemon=True)
        self.thread.start()
        if self.logger: self.logger.log("Started WebSocket listener for messages.")

    def _run_listen_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.stop_event = asyncio.Event()
        try:
            self.loop.run_until_complete(self._listen(self.stop_event))
        finally:
            if self.logger: self.logger.log("Closing asyncio loop.")
            try:
                tasks = asyncio.all_tasks(loop=self.loop)
                for task in tasks: task.cancel()
                self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            except Exception as e:
                if self.logger: self.logger.log(f"Error during loop cleanup: {e}")
            finally:
                asyncio.set_event_loop(None)
                self.loop.close()
                if self.logger: self.logger.log("Listener thread event loop closed.")

    async def _listen(self, stop_event):
        uri = f"{self.ws_url}/{self.user_id}"
        websocket = None
        while not stop_event.is_set():
            try:
                async with websockets.connect(uri, open_timeout=10) as ws:
                    websocket = ws
                    if self.logger: self.logger.log(f"WebSocket connection established to {uri}")
                    while not stop_event.is_set():
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            self._process_ws_message(message)
                        except asyncio.TimeoutError:
                            continue
            except Exception as e:
                if not stop_event.is_set():
                    if isinstance(e, (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, asyncio.TimeoutError)):
                        if self.logger: self.logger.log(f"WARN: WebSocket connection issue: {e}. Reconnecting in 5s...")
                    else:
                        if self.logger: self.logger.log(f"ERROR: Unhandled exception in WebSocket listener: {e}. Retrying in 10s...")
                    await asyncio.sleep(5)
            finally:
                websocket = None

        # Loop has been stopped, now perform cleanup
        if self.logger: self.logger.log("Listen loop stop event received.")
        # Re-establish a temporary connection to send the final disconnect message
        try:
            async with websockets.connect(uri, open_timeout=5) as ws:
                if self.logger: self.logger.log(f"Temporary WebSocket connection established for cleanup.")
                payload = json.dumps({"action": "disconnect", "cleanup_session": self.cleanup_on_stop})
                await ws.send(payload)
                await asyncio.sleep(0.5) # Give it a moment
                if self.logger: self.logger.log(f"Sent final disconnect message (cleanup={self.cleanup_on_stop}).")
        except Exception as e:
            if self.logger: self.logger.log(f"WARN: Could not send final disconnect message: {e}")
            # Fallback to HTTP if websocket fails
            if self.cleanup_on_stop:
                await self._cleanup_server_session()

        if self.logger: self.logger.log("Listen loop has gracefully exited.")

    def _process_ws_message(self, message: str):
        try:
            data = json.loads(message)
            if isinstance(data, list):
                if self.logger: self.logger.log(f"Fetched {len(data)} new message(s) via WebSocket.")
                self._process_messages(data)
        except json.JSONDecodeError:
            if self.logger: self.logger.log(f"ERROR: Could not decode JSON from WebSocket: {message}")

    def _process_messages(self, messages):
        queues_manager = self.user_queues.get(self.user_id)
        if not queues_manager:
            if self.logger: self.logger.log("ERROR: Could not find a queues manager for myself.")
            return
        for msg in messages:
            group_info = msg.get('group')
            if group_info and not self.config.provider_config.allow_group_messages: continue
            group = Group(identifier=group_info['id'], display_name=group_info.get('name') or group_info['id'], alternate_identifiers=group_info.get('alternate_identifiers', [])) if group_info else None
            correspondent_id = group.identifier if group else msg['sender']
            primary_identifier = msg['sender']
            all_alternates = msg.get('alternate_identifiers') or []
            if not isinstance(all_alternates, list): all_alternates = []
            permanent_jid = next((alt_id for alt_id in all_alternates if alt_id.endswith('@s.whatsapp.net')), None)
            if permanent_jid:
                if not group: correspondent_id = permanent_jid
                primary_identifier = permanent_jid
                if msg['sender'] not in all_alternates: all_alternates.append(msg['sender'])
            sender = Sender(identifier=primary_identifier, display_name=msg.get('display_name', msg['sender']), alternate_identifiers=all_alternates)
            queues_manager.add_message(correspondent_id=correspondent_id, content=msg['message'], sender=sender, source='user', group=group, provider_message_id=msg.get('provider_message_id'))

    async def stop_listening(self, cleanup_session: bool = False):
        if self.logger: self.logger.log(f"Stopping... (cleanup={cleanup_session})")
        self.cleanup_on_stop = cleanup_session
        if self.stop_event and not self.stop_event.is_set():
            if self.logger: self.logger.log("Setting stop event for listener thread.")
            if self.loop and self.loop.is_running():
                 self.loop.call_soon_threadsafe(self.stop_event.set)

        if self.thread:
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                if self.logger: self.logger.log("WARN: Listener thread did not terminate in time.")
            else:
                if self.logger: self.logger.log("Listener thread terminated successfully.")

        if self.on_session_end and not self.session_ended:
            self.session_ended = True
            self.on_session_end(self.user_id)

    async def _cleanup_server_session(self):
        if self.logger: self.logger.log("Requesting session cleanup on Node.js server via HTTP DELETE.")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"{self.base_url}/sessions/{self.user_id}")
                if response.status_code == 200:
                    if self.logger: self.logger.log("Successfully requested session cleanup via HTTP.")
        except Exception as e:
            if self.logger: self.logger.log(f"ERROR: Failed to request session cleanup via HTTP: {e}")

    async def sendMessage(self, recipient: str, message: str):
        if self.logger: self.logger.log(f"Sending reply to {recipient} ---> {message[:50]}...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/sessions/{self.user_id}/send", json={"recipient": recipient, "message": message}, headers={'Content-Type': 'application/json'})
                if response.status_code != 200:
                    if self.logger: self.logger.log(f"ERROR: Failed to send message. Status: {response.status_code}, Body: {response.text}")
        except Exception as e:
            if self.logger: self.logger.log(f"ERROR: Exception while sending message: {e}")

    async def get_status(self) -> Dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/sessions/{self.user_id}/status", timeout=5)
                if response.status_code == 200:
                    return response.json()
                return {"status": "error", "message": f"Unexpected status code {response.status_code}"}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"status": "disconnected", "message": "Session not found on Node.js server."}
            return {"status": "error", "message": f"HTTP Error {e.response.status_code}: {e.response.text}"}
        except httpx.RequestError as e:
            return {"status": "initializing", "message": f"Node.js server is not reachable: {e}"}
        except Exception as e:
            return {"status": "error", "message": f"Exception while getting status: {e}"}
