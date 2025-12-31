import asyncio
import json
import os
import threading
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Dict, Optional, Callable
from collections import deque

import httpx
import websockets

from queue_manager import UserQueuesManager, Sender, Group, Message
from logging_lock import FileLogger
from .base import BaseChatProvider
from config_models import ChatProviderConfig


class WhatsAppBaileysProvider(BaseChatProvider):
    def __init__(self, user_id: str, config: ChatProviderConfig, user_queues: Dict[str, UserQueuesManager], on_session_end: Optional[Callable[[str], None]] = None, logger: Optional[FileLogger] = None, main_loop=None):
        super().__init__(user_id, config, user_queues, on_session_end, logger)
        self.is_listening = False
        self.session_ended = False
        self.main_loop = main_loop
        self.cleanup_on_stop = False
        self.listen_task = None
        self.base_url = os.environ.get("WHATSAPP_SERVER_URL", "http://localhost:9000")
        self.ws_url = self.base_url.replace("http", "ws")
        self.sent_message_ids = deque(maxlen=100)

    async def _send_config_to_server(self):
        if self.logger: self.logger.log(f"Connecting to Node.js server at {self.base_url}")
        try:
            config_data = {"userId": self.user_id, "config": self.config.provider_config.model_dump()}
            url = f"{self.base_url}/initialize"
            if self.logger: self.logger.log(f"DEBUG: Sending POST to {url} with data: {config_data}")
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=config_data, headers={'Content-Type': 'application/json'})
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
        self.listen_task = self.main_loop.create_task(self._listen())
        if self.logger: self.logger.log("Started WebSocket listener for messages.")

    async def _listen(self):
        uri = f"{self.ws_url}/{self.user_id}"
        while self.is_listening:
            try:
                async with websockets.connect(uri, open_timeout=10) as websocket:
                    if self.logger: self.logger.log(f"WebSocket connection established to {uri}")
                    while self.is_listening:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            self._process_ws_message(message)
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            if self.logger: self.logger.log("WARN: WebSocket connection closed unexpectedly.")
                            break
            except asyncio.CancelledError:
                if self.logger: self.logger.log("Listen task cancelled.")
                break
            except Exception as e:
                if self.is_listening:
                    if isinstance(e, (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, asyncio.TimeoutError)):
                        if self.logger: self.logger.log(f"WARN: WebSocket connection issue: {e}. Reconnecting in 5s...")
                    else:
                        if self.logger: self.logger.log(f"ERROR: Unhandled exception in WebSocket listener: {e}. Retrying in 10s...")
                    await asyncio.sleep(5)

        if self.logger: self.logger.log("Listen loop is stopping. Performing cleanup...")
        try:
            async with websockets.connect(uri, open_timeout=5) as ws:
                if self.logger: self.logger.log(f"Temporary WebSocket connection established for cleanup.")
                payload = json.dumps({"action": "disconnect", "cleanup_session": self.cleanup_on_stop})
                await ws.send(payload)
                await asyncio.sleep(0.5)
                if self.logger: self.logger.log(f"Sent final disconnect message (cleanup={self.cleanup_on_stop}).")
        except Exception as e:
            if self.logger: self.logger.log(f"WARN: Could not send final disconnect message via WebSocket: {e}")
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
            if group_info and not self.config.provider_config.allow_group_messages:
                continue
            group = Group(
                identifier=group_info['id'],
                display_name=group_info.get('name') or group_info['id'],
                alternate_identifiers=group_info.get('alternate_identifiers', [])
            ) if group_info else None

            direction = msg.get('direction', 'incoming')
            provider_message_id = msg.get('provider_message_id')
            source = 'user'  # Default source

            if direction == 'outgoing':
                correspondent_id = msg.get('recipient_id')
                # For outgoing messages, the 'sender' is the bot/user itself.
                sender = Sender(identifier=f"bot_{self.user_id}", display_name=f"Bot ({self.user_id})")

                if provider_message_id and provider_message_id in self.sent_message_ids:
                    source = 'bot'  # This is an echo of a message the bot sent
                    self.sent_message_ids.remove(provider_message_id)
                else:
                    source = 'user_outgoing'  # This is a message the user sent from their device
            else:  # incoming
                correspondent_id = group.identifier if group else msg['sender']
                primary_identifier = msg['sender']
                all_alternates = msg.get('alternate_identifiers') or []
                if not isinstance(all_alternates, list): all_alternates = []

                permanent_jid = next((alt_id for alt_id in all_alternates if alt_id.endswith('@s.whatsapp.net')), None)
                if permanent_jid:
                    if not group: correspondent_id = permanent_jid
                    primary_identifier = permanent_jid
                    if msg['sender'] not in all_alternates: all_alternates.append(msg['sender'])

                sender = Sender(
                    identifier=primary_identifier,
                    display_name=msg.get('display_name', msg['sender']),
                    alternate_identifiers=all_alternates
                )
                source = 'user'

            if not correspondent_id:
                if self.logger: self.logger.log(f"ERROR: Could not determine correspondent_id for message. Skipping. Data: {msg}")
                continue

            queues_manager.add_message(
                correspondent_id=correspondent_id,
                content=msg['message'],
                sender=sender,
                source=source,
                group=group,
                provider_message_id=provider_message_id
            )

    async def stop_listening(self, cleanup_session: bool = False):
        if self.logger: self.logger.log(f"Stopping... (cleanup={cleanup_session})")
        self.is_listening = False
        self.cleanup_on_stop = cleanup_session

        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                if self.logger: self.logger.log("Listen task successfully cancelled.")

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
                response = await client.post(
                    f"{self.base_url}/sessions/{self.user_id}/send",
                    json={"recipient": recipient, "message": message},
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                if response.status_code == 200:
                    response_data = response.json()
                    provider_message_id = response_data.get('provider_message_id')
                    if provider_message_id:
                        self.sent_message_ids.append(provider_message_id)
                        if self.logger: self.logger.log(f"Successfully sent message. Tracking provider_message_id: {provider_message_id}")
                else:
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
