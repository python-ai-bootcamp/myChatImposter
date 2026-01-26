import asyncio
import json
import os
import threading
import base64
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Dict, Optional, Callable, List, Any
from collections import deque
import time

import httpx
import websockets

from queue_manager import UserQueuesManager, Sender, Group, Message
import logging

from .base import BaseChatProvider
from config_models import ChatProviderConfig


class WhatsAppBaileysProvider(BaseChatProvider):
    def __init__(self, user_id: str, config: ChatProviderConfig, user_queues: Dict[str, UserQueuesManager], on_session_end: Optional[Callable[[str], None]] = None, on_status_change: Optional[Callable[[str, str], None]] = None, main_loop=None, **kwargs):
        # Pass unknown kwargs up to ensure compatibility
        super().__init__(user_id, config, user_queues, on_session_end, on_status_change, main_loop=main_loop, **kwargs)

        self.user_jid = None
        self.sock = None
        self._connected = False
        self._listener_task = None
        self._stop_event = asyncio.Event()

        # Restoring attributes required for logic
        self.is_listening = False
        self.session_ended = False
        self.cleanup_on_stop = False
        self.listen_task = None

        self.base_url = os.environ.get("WHATSAPP_SERVER_URL", "http://localhost:9000")
        self.ws_url = self.base_url.replace("http", "ws")
        self.sent_message_ids = deque()
        self.pending_bot_messages = deque()
        self.max_cache_interval = 0
        self.max_cache_size = 100
        # Status cache for push-based updates
        self._cached_status = {"status": "initializing", "qr": None}
        self._ws_connection = None  # Reference to active WebSocket for sending messages
        self.user_jid = None  # User's own WhatsApp JID for sending messages to self

    def update_cache_policy(self, max_interval: int):
        self.max_cache_interval = max_interval
        logging.info(f"Updated cache policy: max_interval={max_interval}s, max_size={self.max_cache_size}")

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
        # Use console_log for visibility
        # console_log(f"DEBUG_BOT: Checking ID {provider_message_id}. Cache size: {len(self.sent_message_ids)}")
        for msg_id, _ in self.sent_message_ids:
            if msg_id == provider_message_id:
                logging.info(f"BOT: MATCH FOUND in cache for ID: {provider_message_id}")
                return True
        # console_log(f"DEBUG_BOT: No match found in cache for ID: {provider_message_id}")
        return False

    def _check_and_consume_pending(self, recipient_id: str, content: str) -> bool:
        """
        Checks if a message matches a pending bot message by content and recipient.
        This handles race conditions where the WebSocket event arrives before the HTTP response returns the ID.
        Also cleans up stale pending messages (TTL 30s).
        """
        now = time.time()
        # Clean up stale pending messages
        while self.pending_bot_messages and now - self.pending_bot_messages[0][2] > 30:
            self.pending_bot_messages.popleft()

        logging.info(f"BOT: Checking pending. Recipient: '{recipient_id}', Content: '{content[:30]}...'")
        logging.info(f"BOT: Pending buffer: {[(r, c[:10], t) for r, c, t in self.pending_bot_messages]}")

        for i, (p_recipient, p_content, p_time) in enumerate(self.pending_bot_messages):
            # We assume strict matching for now. Recipient formatting might vary slightly,
            # but usually it's consistent if we use what we sent.
            # p_recipient is what we passed to sendMessage. recipient_id is from the incoming message.
            # If recipient_id is None, skip check.
            if recipient_id and recipient_id != p_recipient:
                logging.info(f"BOT: Recipient mismatch: '{recipient_id}' != '{p_recipient}'")
                continue

            if content == p_content:
                logging.info(f"BOT: MATCH FOUND in pending buffer for content: {content[:20]}...")
                # Remove from deque
                del self.pending_bot_messages[i]
                return True
            else:
                logging.info(f"BOT: Content mismatch. \nReceived: '{content}'\nPending:  '{p_content}'")
                pass

        logging.info(f"BOT: No pending match found.")
        return False

    async def _send_config_to_server(self):
        logging.info(f"Connecting to Node.js server at {self.base_url}")
        try:
            config_data = {"userId": self.user_id, "config": self.config.provider_config.model_dump()}
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/initialize", json=config_data, headers={'Content-Type': 'application/json'})
                if response.status_code == 200:
                    logging.info("Successfully sent configuration to Node.js server.")
                else:
                    logging.warning(f"Failed to send config. Status: {response.status_code}, Body: {response.text}")
        except Exception as e:
            logging.error(f"Exception while sending configuration: {e}")

    async def start_listening(self):
        if self.is_listening:
            logging.warning("Already listening.")
            return
        await self._send_config_to_server()
        self.is_listening = True
        self.listen_task = self.main_loop.create_task(self._listen())
        logging.info("Started WebSocket listener for messages.")

    async def _listen(self):
        uri = f"{self.ws_url}/{self.user_id}"
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            if not self.is_listening:
                break
            try:
                async with websockets.connect(uri, open_timeout=10) as websocket:
                    logging.info(f"WebSocket connection established to {uri}")
                    self._ws_connection = websocket
                    # Request initial status sync from Baileys
                    try:
                        await websocket.send(json.dumps({"action": "request_status"}))
                    except Exception as e:
                        logging.warning(f"Could not send request_status: {e}")
                    # Connection successful, now enter the main listening loop
                    while self.is_listening:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                            await self._process_ws_message(message)
                        except asyncio.TimeoutError:
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logging.info("WebSocket connection closed unexpectedly.")
                            break # Break inner loop to reconnect

                    if self.is_listening: # If we broke due to connection closed, retry
                        logging.info("Attempting to re-establish WebSocket connection...")
                        continue # Go to the next attempt in the outer loop
                    else: # If we broke because listening stopped, exit
                        break

            except websockets.exceptions.InvalidStatusCode as e:
                # This is the key change: catch specific connection rejection errors
                if e.status_code == 404 and attempt < max_retries - 1:
                     logging.warning(f"WebSocket connection rejected (404), likely a race condition. Retrying in {retry_delay}s... ({attempt + 1}/{max_retries})")
                     await asyncio.sleep(retry_delay)
                     continue # Go to the next attempt
                else:
                    logging.error(f"WebSocket connection failed with status {e.status_code}. Giving up after {attempt + 1} attempts.")
                    break # Give up

            except asyncio.CancelledError:
                logging.info("Listen task cancelled.")
                break
            except Exception as e:
                if self.is_listening:
                    if isinstance(e, (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, asyncio.TimeoutError)):
                        logging.warning(f"WebSocket connection issue: {e}. Reconnecting in 5s...")
                    else:
                        logging.error(f"Unhandled exception in WebSocket listener: {e}. Retrying in 10s...")
                    await asyncio.sleep(5)

        logging.info("Listen loop is stopping. Performing cleanup...")
        try:
            async with websockets.connect(uri, open_timeout=5) as ws:
                logging.info(f"Temporary WebSocket connection established for cleanup.")
                payload = json.dumps({"action": "disconnect", "cleanup_session": self.cleanup_on_stop})
                await ws.send(payload)
                await asyncio.sleep(0.5)
                logging.info(f"Sent final disconnect message (cleanup={self.cleanup_on_stop}).")
        except Exception as e:
            logging.error(f"Could not send final disconnect message via WebSocket: {e}")
            if self.cleanup_on_stop:
                await self._cleanup_server_session()

        logging.info("Listen loop has gracefully exited.")

    async def _process_ws_message(self, message: str):
        try:
            data = json.loads(message)
            # Handle status_update messages from Baileys
            if isinstance(data, dict) and data.get('type') == 'status_update':
                self._cached_status = {
                    "status": data.get('status', 'unknown'),
                    "qr": data.get('qr')
                }
                logging.info(f"Status update received: {self._cached_status['status']}")
                
                # Notify listener of status change (e.g., to trigger queue movements)
                if self.on_status_change:
                     try:
                         # We invoke it synchronously as it should be lightweight/async-safe or fire-and-forget
                         # But since it might do DB ops, better to ensure we don't block heavily.
                         # Assuming the listener handles its own concurrency or is fast.
                         if asyncio.iscoroutinefunction(self.on_status_change):
                            asyncio.create_task(self.on_status_change(self.user_id, self._cached_status['status']))
                         else:
                            self.on_status_change(self.user_id, self._cached_status['status'])
                     except Exception as e:
                         logging.error(f"ERROR: Failed to invoke on_status_change callback: {e}")

                # Store user JID for sending messages to self
                if data.get('user_jid'):
                    self.user_jid = data.get('user_jid')
                    logging.info(f"User JID received: {self.user_jid}")
                return
            # Handle message arrays (existing behavior)
            if isinstance(data, list):
                logging.info(f"Fetched {len(data)} new message(s) via WebSocket.")
                self._process_messages(data)
        except json.JSONDecodeError:
            logging.error(f"ERROR: Could not decode JSON from WebSocket: {message}")

    def _process_messages(self, messages):
        queues_manager = self.user_queues.get(self.user_id)
        if not queues_manager:
            logging.error("ERROR: Could not find a queues manager for myself.")
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

                is_bot = False
                if provider_message_id and self.is_bot_message(provider_message_id):
                    is_bot = True
                elif self._check_and_consume_pending(recipient_id, msg.get('message')):
                    is_bot = True
                    # CRITICAL: Add to cache immediately so history/future checks work
                    if provider_message_id:
                        # Check if already present to avoid duplicates (though deque allows it, cleaner not to)
                        if not any(x[0] == provider_message_id for x in self.sent_message_ids):
                            self.sent_message_ids.append((provider_message_id, time.time()))
                            self._cleanup_cache()
                            logging.info(f"Race condition resolved: Added ID {provider_message_id} to cache from pending match.")

                if is_bot:
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
                logging.error(f"ERROR: Could not determine correspondent_id for message. Skipping. Data: {msg}")
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
        logging.info(f"Stopping... (cleanup={cleanup_session})")
        self.is_listening = False
        self.cleanup_on_stop = cleanup_session

        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                logging.info("Listen task successfully cancelled.")

        if self.on_session_end and not self.session_ended:
            self.session_ended = True
            self.on_session_end(self.user_id)

    async def _cleanup_server_session(self):
        logging.info("Requesting session cleanup on Node.js server via HTTP DELETE.")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(f"{self.base_url}/sessions/{self.user_id}")
                if response.status_code == 200:
                    logging.info("Successfully requested session cleanup via HTTP.")
        except Exception as e:
            logging.error(f"Failed to request session cleanup via HTTP: {e}")

    async def sendMessage(self, recipient: str, message: str):
        logging.info(f"Sending reply to {recipient} ---> {message[:50]}...")
        logging.info(f"BOT: Adding to pending: Recipient: '{recipient}', Content: '{message[:30]}...'")

        # Add to pending buffer immediately to handle race conditions
        self.pending_bot_messages.append((recipient, message, time.time()))

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
                        # Only add if not already added by race condition handler
                        if not any(x[0] == provider_message_id for x in self.sent_message_ids):
                            self.sent_message_ids.append((provider_message_id, time.time()))
                            self._cleanup_cache()
                            logging.info(f"Successfully sent message. Tracking provider_message_id: {provider_message_id}")
                    else:
                        logging.warning("WARN: Sent message but got no provider_message_id in response.")
                else:
                    error_msg = f"Failed to send message. Status: {response.status_code}, Body: {response.text}"
                    logging.error(f"{error_msg}")
                    raise Exception(error_msg)
        except Exception as e:
            logging.error(f"Exception while sending message: {e}")
            raise e

    async def send_file(self, recipient: str, file_data: bytes, filename: str, mime_type: str, caption: Optional[str] = None):
        """
        Sends a file to the specified recipient using the Baileys HTTP API.
        """
        if not recipient:
            logging.error("send_file called with empty recipient.")
            return

        url = f"{self.base_url}/sessions/{self.user_id}/send"
        
        # Convert bytes to base64 string
        content_b64 = base64.b64encode(file_data).decode('utf-8')

        payload = {
            "recipient": recipient,
            "type": "document",
            "content": content_b64,
            "fileName": filename,
            "mimetype": mime_type,
            "caption": caption
        }

        try:
            logging.info(f"DEBUG: sending file {filename} to {recipient}...")
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)
                if response.status_code != 200:
                        error_msg = f"Failed to send file. Status: {response.status_code}, Body: {response.text}"
                        logging.error(f"{error_msg}")
                        raise Exception(error_msg)
                
                result = response.json()
                logging.info(f"File sent to {recipient}. ID: {result.get('provider_message_id')}")
                return result

        except Exception as e:
            logging.error(f"send_file failed: {e}")
            raise e

    async def get_status(self, heartbeat: bool = False) -> Dict:
        """Returns cached status. If heartbeat=True, sends heartbeat ping over WebSocket."""
        if heartbeat:
            # Send heartbeat over WebSocket instead of HTTP
            if self._ws_connection:
                try:
                    await self._ws_connection.send(json.dumps({"action": "heartbeat"}))
                except Exception as e:
                    logging.warning(f"Could not send heartbeat: {e}")
        
        # Return cached status (no HTTP call needed)
        return self._cached_status.copy()



    async def get_groups(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{self.base_url}/sessions/{self.user_id}/groups", timeout=10)
                if response.status_code == 200:
                    return response.json().get('groups', [])
                logging.warning(f"Failed to fetch active groups: {response.text}")
                return []
        except Exception as e:
            logging.error(f"Exception while fetching active groups: {e}")
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
                logging.warning(f"Failed to fetch historic messages: {response.text}")
                return None # Return None to indicate failure
                return None # Return None to indicate failure
        except Exception as e:
            logging.error(f"Exception while fetching historic messages: {e}")
            return None # Return None to indicate failure

    @property
    def is_connected(self) -> bool:
        """
        Returns True if the provider is currently connected and authenticated.
        For Baileys, we assume connection if user_jid is set and listening is active.
        """
        return bool(self.is_listening and self.user_jid)
