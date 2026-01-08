import asyncio
import json
import os
import threading
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Dict, Optional, Callable, List
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
        self.sent_message_ids = deque()
        self.max_cache_interval = 0
        self.max_cache_size = 100

    def update_cache_policy(self, max_interval: int):
        self.max_cache_interval = max_interval
        if self.logger: self.logger.log(f"Updated cache policy: max_interval={max_interval}s, max_size={self.max_cache_size}")

    def _cleanup_cache(self):
        cutoff = time.time() - self.max_cache_interval
        # We need to remove items that are BOTH (older than max_cache_interval) AND (outside the recent max_cache_size items)
        # So we keep items that are EITHER (newer than max_cache_interval) OR (within the last max_cache_size items)

        # sent_message_ids is a deque of (id, timestamp). Oldest items are at the left (index 0).
        # We iterate from the left and remove items until we hit one that should be kept.

        while len(self.sent_message_ids) > self.max_cache_size:
            # Check the oldest item
            item_id, timestamp = self.sent_message_ids[0]

            # If it's also too old, remove it.
            # If it's within the time window, we stop removing because all subsequent items are newer.
            if timestamp < cutoff:
                self.sent_message_ids.popleft()
            else:
                break

    def is_bot_message(self, provider_message_id: str) -> bool:
        if not provider_message_id:
            return False
        if self.logger: self.logger.log(f"Checking is_bot_message for ID: {provider_message_id}. Cache size: {len(self.sent_message_ids)}")
        for msg_id, _ in self.sent_message_ids:
            if msg_id == provider_message_id:
                if self.logger: self.logger.log(f"MATCH FOUND in cache for ID: {provider_message_id}")
                return True
        if self.logger: self.logger.log(f"No match found in cache for ID: {provider_message_id}")
        return False

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
        self.listen_task = self.main_loop.create_task(self._listen())
        if self.logger: self.logger.log("Started WebSocket listener for messages.")

    async def _listen(self):
        uri = f"{self.ws_url}/{self.user_id}"
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            if not self.is_listening:
                break
            try:
                async with websockets.connect(uri, open_timeout=10) as websocket:
                    if self.logger: self.logger.log(f"WebSocket connection established to {uri}")
                    # Connection successful, now enter the main listening loop
                    while self.is_listening:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            self._process_ws_message(message)
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            if self.logger: self.logger.log("WARN: WebSocket connection closed unexpectedly.")
                            break # Break inner loop to reconnect

                    if self.is_listening: # If we broke due to connection closed, retry
                        if self.logger: self.logger.log("Attempting to re-establish WebSocket connection...")
                        continue # Go to the next attempt in the outer loop
                    else: # If we broke because listening stopped, exit
                        break

            except websockets.exceptions.InvalidStatusCode as e:
                # This is the key change: catch specific connection rejection errors
                if e.status_code == 404 and attempt < max_retries - 1:
                     if self.logger: self.logger.log(f"WARN: WebSocket connection rejected (404), likely a race condition. Retrying in {retry_delay}s... ({attempt + 1}/{max_retries})")
                     await asyncio.sleep(retry_delay)
                     continue # Go to the next attempt
                else:
                    if self.logger: self.logger.log(f"ERROR: WebSocket connection failed with status {e.status_code}. Giving up after {attempt + 1} attempts.")
                    break # Give up

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
                recipient_id = msg.get('recipient_id')
                if group:
                    correspondent_id = group.identifier
                else:
                    permanent_jid = next((alt_id for alt_id in (msg.get('alternate_identifiers') or []) if alt_id.endswith('@s.whatsapp.net')), None)
                    correspondent_id = permanent_jid or recipient_id

                if provider_message_id and self.is_bot_message(provider_message_id):
                    source = 'bot'
                    actual_sender_data = msg.get('actual_sender')
                    alternate_identifiers = []
                    if actual_sender_data:
                        alternate_identifiers = actual_sender_data.get('alternate_identifiers', [])

                    sender = Sender(
                        identifier=f"bot_{self.user_id}",
                        display_name=f"Bot ({self.user_id})",
                        alternate_identifiers=alternate_identifiers
                    )
                    # Do not remove from cache here
                else:
                    source = 'user_outgoing'
                    actual_sender_data = msg.get('actual_sender')
                    if actual_sender_data:
                        sender = Sender(
                            identifier=actual_sender_data.get('identifier'),
                            display_name=actual_sender_data.get('display_name'),
                            alternate_identifiers=actual_sender_data.get('alternate_identifiers', [])
                        )
                    else:
                        # Fallback for safety, though actual_sender should always be present for outgoing
                        sender = Sender(identifier=f"user_{self.user_id}", display_name=f"User ({self.user_id})")
            else:  # incoming
                correspondent_id = group.identifier if group else msg['sender']
                primary_identifier = msg['sender']
                all_alternates = msg.get('alternate_identifiers') or []
                if not isinstance(all_alternates, list): all_alternates = []

                permanent_jid = next((alt_id for alt_id in all_alternates if alt_id.endswith('@s.whatsapp.net')), None)
                if permanent_jid:
                    if not group: correspondent_id = permanent_jid
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

            originating_time = msg.get('originating_time')

            queues_manager.add_message(
                correspondent_id=correspondent_id,
                content=msg['message'],
                sender=sender,
                source=source,
                group=group,
                provider_message_id=provider_message_id,
                originating_time=originating_time
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
                        self.sent_message_ids.append((provider_message_id, time.time()))
                        self._cleanup_cache()
                        if self.logger: self.logger.log(f"Successfully sent message. Tracking provider_message_id: {provider_message_id}")
                    else:
                        if self.logger: self.logger.log("WARN: Sent message but got no provider_message_id in response.")
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

    async def get_active_groups(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/sessions/{self.user_id}/groups", timeout=10)
                if response.status_code == 200:
                    return response.json().get('groups', [])
                if self.logger: self.logger.log(f"ERROR: Failed to fetch active groups: {response.text}")
                return []
        except Exception as e:
            if self.logger: self.logger.log(f"ERROR: Exception while fetching active groups: {e}")
            return []

    async def fetch_historic_messages(self, group_id: str, limit: int = 500) -> Optional[List]:
        try:
            payload = {"groupId": group_id, "limit": limit}
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/sessions/{self.user_id}/fetch-messages",
                    json=payload,
                    timeout=60
                )
                if response.status_code == 200:
                    return response.json().get('messages', [])
                if self.logger: self.logger.log(f"ERROR: Failed to fetch historic messages: {response.text}")
                return None # Return None to indicate failure
        except Exception as e:
            if self.logger: self.logger.log(f"ERROR: Exception while fetching historic messages: {e}")
            return None # Return None to indicate failure
