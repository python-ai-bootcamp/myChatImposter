import time
import os
import sys
import threading
import asyncio
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, List, Dict, Any
from pymongo.collection import Collection
from pymongo import DESCENDING

import logging
# from logging_lock import lock, get_timestamp
from config_models import QueueConfig

@dataclass
class Sender:
    identifier: str
    display_name: str
    alternate_identifiers: List[str] = field(default_factory=list)

@dataclass
class Group:
    identifier: str
    display_name: str
    alternate_identifiers: List[str] = field(default_factory=list)

@dataclass
class Message:
    id: int
    content: str
    sender: Sender
    source: str  # 'user' or 'bot'
    accepted_time: int = field(default_factory=lambda: int(time.time() * 1000))
    message_size: int = 0
    originating_time: Optional[int] = None
    group: Optional[Group] = None
    provider_message_id: Optional[str] = None
    media_processing_id: Optional[str] = None

    def __post_init__(self):
        self.message_size = len(self.content)

class CorrespondentQueue:
    def __init__(self, bot_id: str, provider_name: str, correspondent_id: str, queue_config: QueueConfig, queues_collection: Optional[Collection] = None, main_loop = None):
        self.bot_id = bot_id
        self.provider_name = provider_name
        self.correspondent_id = correspondent_id
        self.main_loop = main_loop
        self.max_messages = queue_config.max_messages
        self.max_characters = queue_config.max_characters
        self.max_characters_single_message = queue_config.max_characters_single_message
        self.max_age_seconds = queue_config.max_days * 24 * 60 * 60
        self._queues_collection = queues_collection

        self._messages: deque[Message] = deque()
        self._next_message_id = 1
        self._total_chars = 0
        self._callbacks: List[Callable[[str, Message], None]] = []
        self._recent_provider_message_ids: deque[str] = deque(maxlen=20)
        self._recent_provider_message_ids: deque[str] = deque(maxlen=20)
        self._new_message_event = asyncio.Event() # Changed to asyncio.Event for async wait

    async def initialize(self):
        """Async initialization to load state from DB."""
        if self._queues_collection is not None:
            await self._initialize_next_message_id()

    async def _initialize_next_message_id(self):
        """Sets the next message ID based on the last message in the database for this correspondent."""
        try:
            # Async Find One
            last_message = await self._queues_collection.find_one(
                {"bot_id": self.bot_id, "provider_name": self.provider_name, "correspondent_id": self.correspondent_id},
                sort=[("id", DESCENDING)]
            )
            if last_message and 'id' in last_message:
                self._next_message_id = last_message['id'] + 1
                logging.info(f"QUEUE INIT ({self.bot_id}/{self.correspondent_id}): Initialized next message ID to {self._next_message_id} from database.")
            else:
                logging.info(f"QUEUE INIT ({self.bot_id}/{self.correspondent_id}): No previous messages found in DB. Starting message ID at 1.")
        except Exception as e:
            logging.error(f"QUEUE: Could not initialize next message ID from DB: {e}")

    def register_callback(self, callback: Callable[[str, Message], None]):
        """Register a callback function to be triggered on new messages."""
        self._callbacks.append(callback)

    def _trigger_callbacks(self, message: Message):
        """Trigger all registered callbacks with the new message."""
        for callback in self._callbacks:
            if self.main_loop:
                asyncio.run_coroutine_threadsafe(callback(self.bot_id, self.correspondent_id, message), self.main_loop)
            else:
                logging.error(f"QUEUE: No main event loop provided to run async callback.")

    def _iter_unprotected_messages(self):
        for message in self._messages:
            if not message.media_processing_id:
                yield message

    def _evict_oldest_unprotected(self, reason: str, new_message_size: int) -> bool:
        for idx, message in enumerate(self._messages):
            if message.media_processing_id:
                continue
            del self._messages[idx]
            self._total_chars -= message.message_size
            self._log_retention_event(message, reason, new_message_size)
            logging.info(f"QUEUE EVICT ({self.bot_id}): Message {message.id} evicted due to {reason}.")
            return True
        return False

    def _enforce_limits(self, new_message_size: int):
        """Evict old unprotected messages until the new message can be added."""
        now = time.time()

        while True:
            stale_unprotected = next(
                (m for m in self._iter_unprotected_messages() if (now - m.accepted_time / 1000) > self.max_age_seconds),
                None
            )
            if not stale_unprotected:
                break
            if not self._evict_oldest_unprotected("age", new_message_size):
                break

        while True:
            unprotected_messages = list(self._iter_unprotected_messages())
            unprotected_total_chars = sum(m.message_size for m in unprotected_messages)
            if (unprotected_total_chars + new_message_size) <= self.max_characters:
                break
            if not self._evict_oldest_unprotected("total_characters", new_message_size):
                break

        while True:
            unprotected_count = sum(1 for _ in self._iter_unprotected_messages())
            if unprotected_count < self.max_messages:
                break
            if not self._evict_oldest_unprotected("message_count", new_message_size):
                break

    async def add_message(
        self,
        content: str,
        sender: Sender,
        source: str,
        originating_time: Optional[int] = None,
        group: Optional[Group] = None,
        provider_message_id: Optional[str] = None,
        media_processing_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        original_filename: Optional[str] = None,
        media_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Message]:
        """Create, add, and process a new message for the queue."""
        if provider_message_id:
            if provider_message_id in self._recent_provider_message_ids:
                logging.info(f"QUEUE DUPE ({self.bot_id}): Duplicate message ID {provider_message_id} received, ignoring.")
                return None
            self._recent_provider_message_ids.append(provider_message_id)

        # Truncate the message if it exceeds the single message character limit.
        if media_processing_id is None and len(content) > self.max_characters_single_message:
            logging.warning(f"QUEUE TRUNCATE ({self.bot_id}): Message from {sender.display_name} is larger than the single message character limit ({self.max_characters_single_message}), truncating.")
            content = content[:self.max_characters_single_message]

        new_message_size = len(content)

        if media_processing_id is None:
            self._enforce_limits(new_message_size)

        message = Message(
            id=self._next_message_id,
            content=content,
            sender=sender,
            source=source,
            originating_time=originating_time,
            group=group,
            provider_message_id=provider_message_id,
            media_processing_id=media_processing_id,
        )

        self._messages.append(message)
        self._total_chars += message.message_size
        self._next_message_id += 1

        # Log the message
        self._log_message(message)

        logging.info(f"QUEUE ADD ({self.bot_id}): Added message {message.id} from {message.sender.display_name}. Queue stats: {len(self._messages)} msgs, {self._total_chars} chars.")

        self._new_message_event.set()
        if not message.media_processing_id:
            self._trigger_callbacks(message)
        return message

    def inject_placeholder(self, message: Message):
        """Insert pre-constructed placeholder without callbacks or re-processing."""
        self._messages.append(message)
        self._total_chars += message.message_size
        self._next_message_id = max(self._next_message_id, message.id + 1)
        self._new_message_event.set()

    async def update_message_by_media_id(self, guid: str, content: str) -> bool:
        for message in self._messages:
            if message.media_processing_id == guid:
                self._total_chars -= message.message_size
                message.content = content
                message.media_processing_id = None
                message.message_size = len(content)
                self._total_chars += message.message_size
                self._trigger_callbacks(message)
                return True
        return False

    def has_media_processing_id(self, guid: str) -> bool:
        return any(message.media_processing_id == guid for message in self._messages)

    def pop_message(self) -> Optional[Message]:
        """Pops the oldest message from the queue in a thread-safe manner."""
        try:
            message = self._messages.popleft()
            self._total_chars -= message.message_size
            return message
        except IndexError:
            # The queue is empty, so we clear the event.
            self._new_message_event.clear()
            return None

    def pop_ready_message(self) -> Optional[Message]:
        for idx, message in enumerate(self._messages):
            if message.media_processing_id:
                continue
            del self._messages[idx]
            self._total_chars -= message.message_size
            if not self._messages:
                self._new_message_event.clear()
            return message
        if not self._messages:
            self._new_message_event.clear()
        return None

    async def wait_for_message(self, timeout: Optional[float] = None) -> bool:
        """
        Waits for a new message to be added to the queue. Returns True if an event was
        triggered, False if it timed out.
        """
        try:
            await asyncio.wait_for(self._new_message_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    def _log_message(self, message: Message):
        """
        Logs a message using standard logging. 
        Previously wrote to specific files manually. Now delegates to the logging framework.
        """
        originating_time_str = str(message.originating_time) if message.originating_time is not None else 'None'
        sender_str = f"{message.sender.display_name} ({message.sender.identifier})"
        group_str = f"[group={message.group.display_name} ({message.group.identifier})]" if message.group else ""

        log_msg = f"MESSAGE: [originating={originating_time_str}] [accepted={message.accepted_time}] [id={message.id}] [sender={sender_str}] {group_str} :: {message.content}"
        
        # Log to standard logger
        logging.info(f"({self.provider_name}/{self.bot_id}/{self.correspondent_id}) {log_msg}")

    def get_messages(self) -> List[Message]:
        return list(self._messages)

    def clear(self):
        """Clears all messages from the in-memory queue and resets the message ID."""
        self._messages.clear()
        self._total_chars = 0
        self._next_message_id = 1
        logging.info(f"QUEUE CLEAR ({self.bot_id}/{self.correspondent_id}): In-memory queue cleared and message ID reset.")

    def _log_retention_event(self, evicted_message: Message, reason: str, new_message_size: int = 0):
        """
        Logs a retention event using standard logging.
        """
        log_msg = f"RETENTION EVENT: [type=EVICT] [reason={reason}] [evicted_id={evicted_message.id}] [queue_size={len(self._messages)+1}]"
        logging.info(f"({self.bot_id}) {log_msg}")

class BotQueuesManager:
    def __init__(
        self,
        bot_id: str,
        provider_name: str,
        queue_config: QueueConfig,
        queues_collection: Optional[Collection] = None,
        main_loop = None,
        media_jobs_collection = None,
    ):
        self.bot_id = bot_id
        self.provider_name = provider_name
        self.queue_config = queue_config
        self.main_loop = main_loop
        self.queues_collection = queues_collection
        self._queues: dict[str, CorrespondentQueue] = {}
        self._callbacks: List[Callable[[str, str, Message], None]] = []
        self._lock = threading.Lock()
        self.media_jobs_collection = media_jobs_collection

    async def get_or_create_queue(self, correspondent_id: str) -> CorrespondentQueue:
        # Use asyncio Lock instead of threading Lock? 
        # Actually since we are in async, we assume single threaded event loop, 
        # but race conditions can happen during await.
        # However, checking dict membership is atomic in Python GIL, but let's be safe.
        # For strict async safety we would use asyncio.Lock() but we can't await in __init__.
        # We'll just rely on the fact that dict operations are atomic.
        
        if correspondent_id not in self._queues:
            # Double check pattern not easy without lock, but standard dict check is usually fine in single loop.
            logging.info(f"QUEUE_MANAGER ({self.bot_id}): Creating new queue for correspondent '{correspondent_id}'.")
            queue = CorrespondentQueue(
                bot_id=self.bot_id,
                provider_name=self.provider_name,
                correspondent_id=correspondent_id,
                queue_config=self.queue_config,
                queues_collection=self.queues_collection,
                main_loop=self.main_loop
            )
            # AWAIT initialization
            await queue.initialize()

            # Register all existing manager-level callbacks to the new queue
            for callback in self._callbacks:
                queue.register_callback(callback)
            self._queues[correspondent_id] = queue
            
        return self._queues[correspondent_id]

    async def add_message(
        self,
        correspondent_id: str,
        content: str,
        sender: Sender,
        source: str,
        originating_time: Optional[int] = None,
        group: Optional[Group] = None,
        provider_message_id: Optional[str] = None,
        media_processing_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        original_filename: Optional[str] = None,
        media_metadata: Optional[Dict[str, Any]] = None,
    ):
        queue = await self.get_or_create_queue(correspondent_id)
        message = await queue.add_message(
            content,
            sender,
            source,
            originating_time,
            group,
            provider_message_id,
            media_processing_id=media_processing_id,
            mime_type=mime_type,
            original_filename=original_filename,
            media_metadata=media_metadata,
        )
        if (
            message
            and media_processing_id
            and mime_type
            and self.media_jobs_collection is not None
        ):
            job_doc = {
                "bot_id": self.bot_id,
                "correspondent_id": correspondent_id,
                "placeholder_message": asdict(message),
                "guid": media_processing_id,
                "mime_type": mime_type,
                "original_filename": original_filename,
                "status": "pending",
                "media_metadata": media_metadata or {},
                "created_at": int(time.time() * 1000),
            }
            await self.media_jobs_collection.insert_one(job_doc)

    def register_callback(self, callback: Callable[[str, str, Message], None]):
        """Register a callback to be added to all queues."""
        with self._lock:
            self._callbacks.append(callback)
            # Add this new callback to all already-existing queues
            for queue in self._queues.values():
                queue.register_callback(callback)

    def get_all_queues(self) -> List[CorrespondentQueue]:
        with self._lock:
            return list(self._queues.values())

    def get_queue(self, correspondent_id: str) -> Optional[CorrespondentQueue]:
        return self._queues.get(correspondent_id)

    async def update_message_by_media_id(self, correspondent_id: str, guid: str, content: str) -> bool:
        queue = await self.get_or_create_queue(correspondent_id)
        return await queue.update_message_by_media_id(guid, content)

    async def inject_placeholder(self, correspondent_id: str, message: Message):
        queue = await self.get_or_create_queue(correspondent_id)
        queue.inject_placeholder(message)

    async def has_media_processing_id(self, correspondent_id: str, guid: str) -> bool:
        queue = await self.get_or_create_queue(correspondent_id)
        return queue.has_media_processing_id(guid)

    async def reap_and_promote_jobs(self, holding_collection, active_collection):
        while True:
            doc = await holding_collection.find_one_and_delete(
                {
                    "bot_id": self.bot_id,
                    "$or": [
                        {"status": "completed", "result": {"$exists": True}},
                        {"status": {"$in": ["pending", "processing"]}},
                        {"status": "completed", "result": {"$exists": False}},
                    ],
                },
                sort=[("created_at", 1)],
            )
            if not doc:
                break
            placeholder_doc = doc.get("placeholder_message", {})
            sender_doc = placeholder_doc.get("sender", {})
            sender = Sender(
                identifier=sender_doc.get("identifier", "unknown"),
                display_name=sender_doc.get("display_name", "unknown"),
                alternate_identifiers=sender_doc.get("alternate_identifiers", []),
            )
            group = None
            if placeholder_doc.get("group"):
                group_doc = placeholder_doc["group"]
                group = Group(
                    identifier=group_doc.get("identifier", ""),
                    display_name=group_doc.get("display_name", ""),
                    alternate_identifiers=group_doc.get("alternate_identifiers", []),
                )
            message = Message(
                id=placeholder_doc.get("id", 0),
                content=placeholder_doc.get("content", ""),
                sender=sender,
                source=placeholder_doc.get("source", "user"),
                accepted_time=placeholder_doc.get("accepted_time", int(time.time() * 1000)),
                message_size=placeholder_doc.get("message_size", 0),
                originating_time=placeholder_doc.get("originating_time"),
                group=group,
                provider_message_id=placeholder_doc.get("provider_message_id"),
                media_processing_id=placeholder_doc.get("media_processing_id"),
            )
            await self.inject_placeholder(doc["correspondent_id"], message)
            if doc.get("status") == "completed" and doc.get("result"):
                await self.update_message_by_media_id(doc["correspondent_id"], doc["guid"], doc["result"])
            else:
                promoted = dict(doc)
                promoted.pop("_id", None)
                promoted["status"] = "pending"
                await active_collection.insert_one(promoted)
