import time
import os
import sys
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Callable, List
from pymongo.collection import Collection
from pymongo import DESCENDING

from logging_lock import lock, get_timestamp, console_log
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

    def __post_init__(self):
        self.message_size = len(self.content)

class CorrespondentQueue:
    def __init__(self, user_id: str, provider_name: str, correspondent_id: str, queue_config: QueueConfig, queues_collection: Optional[Collection] = None):
        self.user_id = user_id
        self.provider_name = provider_name
        self.correspondent_id = correspondent_id
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
        self._new_message_event = threading.Event()

        if self._queues_collection is not None:
            self._initialize_next_message_id()

    def _initialize_next_message_id(self):
        """Sets the next message ID based on the last message in the database for this correspondent."""
        try:
            last_message = self._queues_collection.find_one(
                {"user_id": self.user_id, "provider_name": self.provider_name, "correspondent_id": self.correspondent_id},
                sort=[("id", DESCENDING)]
            )
            if last_message and 'id' in last_message:
                self._next_message_id = last_message['id'] + 1
                console_log(f"QUEUE INIT ({self.user_id}/{self.correspondent_id}): Initialized next message ID to {self._next_message_id} from database.")
            else:
                console_log(f"QUEUE INIT ({self.user_id}/{self.correspondent_id}): No previous messages found in DB. Starting message ID at 1.")
        except Exception as e:
            console_log(f"QUEUE DB_ERROR ({self.user_id}/{self.correspondent_id}): Could not initialize next message ID from DB: {e}")

    def register_callback(self, callback: Callable[[str, Message], None]):
        """Register a callback function to be triggered on new messages."""
        self._callbacks.append(callback)

    def _trigger_callbacks(self, message: Message):
        """Trigger all registered callbacks with the new message."""
        for callback in self._callbacks:
            # The callback itself will handle its own exceptions and logging
            callback(self.user_id, self.correspondent_id, message)

    def _enforce_limits(self, new_message_size: int):
        """Evict old messages until the new message can be added."""
        now = time.time()

        # Evict by age first
        while self._messages and (now - self._messages[0].accepted_time / 1000) > self.max_age_seconds:
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.message_size
            self._log_retention_event(evicted_msg, "age", new_message_size)
            console_log(f"QUEUE EVICT ({self.user_id}): Message {evicted_msg.id} evicted due to age.")

        # Evict by total characters
        while self._messages and (self._total_chars + new_message_size) > self.max_characters:
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.message_size
            self._log_retention_event(evicted_msg, "total_characters", new_message_size)
            console_log(f"QUEUE EVICT ({self.user_id}): Message {evicted_msg.id} evicted due to total characters limit.")

        # Evict by total message count
        while len(self._messages) >= self.max_messages:
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.message_size
            self._log_retention_event(evicted_msg, "message_count", new_message_size)
            console_log(f"QUEUE EVICT ({self.user_id}): Message {evicted_msg.id} evicted due to message count limit.")

    def add_message(self, content: str, sender: Sender, source: str, originating_time: Optional[int] = None, group: Optional[Group] = None, provider_message_id: Optional[str] = None):
        """Create, add, and process a new message for the queue."""
        if provider_message_id:
            if provider_message_id in self._recent_provider_message_ids:
                console_log(f"QUEUE DUPE ({self.user_id}): Duplicate message ID {provider_message_id} received, ignoring.")
                return
            self._recent_provider_message_ids.append(provider_message_id)

        # Truncate the message if it exceeds the single message character limit.
        if len(content) > self.max_characters_single_message:
            console_log(f"QUEUE TRUNCATE ({self.user_id}): Message from {sender.display_name} is larger than the single message character limit ({self.max_characters_single_message}), truncating.")
            content = content[:self.max_characters_single_message]

        new_message_size = len(content)

        self._enforce_limits(new_message_size)

        message = Message(
            id=self._next_message_id,
            content=content,
            sender=sender,
            source=source,
            originating_time=originating_time,
            group=group,
            provider_message_id=provider_message_id
        )

        self._messages.append(message)
        self._total_chars += message.message_size
        self._next_message_id += 1

        # Log the message
        self._log_message(message)

        console_log(f"QUEUE ADD ({self.user_id}): Added message {message.id} from {message.sender.display_name}. Queue stats: {len(self._messages)} msgs, {self._total_chars} chars.")

        self._new_message_event.set()
        self._trigger_callbacks(message)

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

    def wait_for_message(self, timeout: Optional[float] = None) -> bool:
        """
        Waits for a new message to be added to the queue. Returns True if an event was
        triggered, False if it timed out.
        """
        return self._new_message_event.wait(timeout)

    def _log_message(self, message: Message):
        """
        Logs a message to the appropriate files. This method is thread-safe.
        """
        with lock:
            os.makedirs('log', exist_ok=True)

            originating_time_str = str(message.originating_time) if message.originating_time is not None else 'None'

            sender_str = f"{message.sender.display_name} ({message.sender.identifier})"
            group_str = f"[group={message.group.display_name} ({message.group.identifier})]" if message.group else ""

            log_line_parts = [
                f"[originating_time={originating_time_str}]",
                f"[accepted_time={message.accepted_time}]",
                f"[message_id={message.id}]",
                f"[sending_user={sender_str}]"
            ]
            if group_str:
                log_line_parts.append(group_str)
            log_line_parts.append(f":: {message.content}\n")

            user_log_line = get_timestamp() + "::".join(log_line_parts)

            # Correspondent-specific log
            correspondent_log_path = os.path.join('log', f"{self.provider_name}_{self.user_id}_{self.correspondent_id}.log")
            with open(correspondent_log_path, 'a', encoding='utf-8') as f:
                f.write(user_log_line)

            # Global log
            global_log_path = os.path.join('log', "all_providers.log")
            global_log_line_parts = [
                f"[originating_time={originating_time_str}]",
                f"[accepted_time={message.accepted_time}]",
                f"[provider_name={self.provider_name}]",
                f"[user_id={self.user_id}]",
                f"[correspondent_id={self.correspondent_id}]",
                f"[message_id={message.id}]",
                f"[sending_user={sender_str}]"
            ]
            if group_str:
                global_log_line_parts.append(group_str)
            global_log_line_parts.append(f":: {message.content}\n")

            global_log_line = get_timestamp() + "::".join(global_log_line_parts)

            with open(global_log_path, 'a', encoding='utf-8') as f:
                f.write(global_log_line)

    def get_messages(self) -> List[Message]:
        return list(self._messages)

    def _log_retention_event(self, evicted_message: Message, reason: str, new_message_size: int = 0):
        """
        Logs a retention event to the correspondent-specific log file. This method is thread-safe.
        """
        with lock:
            os.makedirs('log', exist_ok=True)
            correspondent_log_path = os.path.join('log', f"{self.provider_name}_{self.user_id}_{self.correspondent_id}.log")

            log_line = f"{get_timestamp()}[retention_event_time={int(time.time() * 1000)}]::" \
                       f"[event_type=EVICT]::" \
                       f"[reason={reason}]::" \
                       f"[evicted_message_id={evicted_message.id}]::" \
                       f"[evicted_message_accepted_time={evicted_message.accepted_time}]::" \
                       f"[evicted_message_size={evicted_message.message_size}]::" \
                       f"[queue_max_messages={self.max_messages}]::" \
                       f"[queue_max_chars={self.max_characters}]::" \
                       f"[queue_max_days={self.max_age_seconds / (24 * 60 * 60)}]::" \
                       f"[current_messages={len(self._messages) + 1}]::" \
                       f"[current_chars={self._total_chars + evicted_message.message_size}]::" \
                       f"[new_message_size={new_message_size}]\n"

            with open(correspondent_log_path, 'a', encoding='utf-8') as f:
                f.write(log_line)

class UserQueuesManager:
    def __init__(self, user_id: str, provider_name: str, queue_config: QueueConfig, queues_collection: Optional[Collection] = None):
        self.user_id = user_id
        self.provider_name = provider_name
        self.queue_config = queue_config
        self.queues_collection = queues_collection
        self._queues: dict[str, CorrespondentQueue] = {}
        self._callbacks: List[Callable[[str, str, Message], None]] = []
        self._lock = threading.Lock()

    def get_or_create_queue(self, correspondent_id: str) -> CorrespondentQueue:
        with self._lock:
            if correspondent_id not in self._queues:
                console_log(f"QUEUE_MANAGER ({self.user_id}): Creating new queue for correspondent '{correspondent_id}'.")
                queue = CorrespondentQueue(
                    user_id=self.user_id,
                    provider_name=self.provider_name,
                    correspondent_id=correspondent_id,
                    queue_config=self.queue_config,
                    queues_collection=self.queues_collection
                )
                # Register all existing manager-level callbacks to the new queue
                for callback in self._callbacks:
                    queue.register_callback(callback)
                self._queues[correspondent_id] = queue
            return self._queues[correspondent_id]

    def add_message(self, correspondent_id: str, content: str, sender: Sender, source: str, originating_time: Optional[int] = None, group: Optional[Group] = None, provider_message_id: Optional[str] = None):
        queue = self.get_or_create_queue(correspondent_id)
        queue.add_message(content, sender, source, originating_time, group, provider_message_id)

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
        with self._lock:
            return self._queues.get(correspondent_id)
