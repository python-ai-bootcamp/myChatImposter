import time
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Callable, List

@dataclass
class Sender:
    identifier: str
    display_name: str

@dataclass
class Group:
    identifier: str
    display_name: str

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

    def __post_init__(self):
        self.message_size = len(self.content)

class UserQueue:
    def __init__(self, user_id: str, vendor_name: str, max_messages: int, max_characters: int, max_days: int):
        self.user_id = user_id
        self.vendor_name = vendor_name
        self.max_messages = max_messages
        self.max_characters = max_characters
        self.max_age_seconds = max_days * 24 * 60 * 60

        self._messages: deque[Message] = deque()
        self._next_message_id = 1
        self._total_chars = 0
        self._callbacks: List[Callable[[str, Message], None]] = []

    def register_callback(self, callback: Callable[[str, Message], None]):
        """Register a callback function to be triggered on new messages."""
        self._callbacks.append(callback)

    def _trigger_callbacks(self, message: Message):
        """Trigger all registered callbacks with the new message."""
        for callback in self._callbacks:
            try:
                callback(self.user_id, message)
            except Exception as e:
                print(f"Error in callback for user {self.user_id}: {e}")

    def _enforce_limits(self, new_message_size: int):
        """Evict old messages until the new message can be added."""
        now = time.time()

        # Evict by age first
        while self._messages and (now - self._messages[0].accepted_time / 1000) > self.max_age_seconds:
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.message_size
            print(f"QUEUE EVICT ({self.user_id}): Message {evicted_msg.id} evicted due to age.")

        # Evict by total characters
        while self._messages and (self._total_chars + new_message_size) > self.max_characters:
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.message_size
            print(f"QUEUE EVICT ({self.user_id}): Message {evicted_msg.id} evicted due to total characters limit.")

        # Evict by total message count
        while len(self._messages) >= self.max_messages:
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.message_size
            print(f"QUEUE EVICT ({self.user_id}): Message {evicted_msg.id} evicted due to message count limit.")

    def add_message(self, content: str, sender: Sender, source: str, originating_time: Optional[int] = None, group: Optional[Group] = None):
        """Create, add, and process a new message for the queue."""
        # If a message is larger than the total character limit for the queue,
        # it gets truncated and all previous messages are cleared.
        if len(content) > self.max_characters:
            print(f"QUEUE TRUNCATE ({self.user_id}): Message from {sender.display_name} is larger than the max character limit ({self.max_characters}), truncating.")
            content = content[:self.max_characters]

            if self._messages:
                print(f"QUEUE CLEAR ({self.user_id}): Clearing all {len(self._messages)} messages to make room for oversized message.")
                self._messages.clear()
                self._total_chars = 0

        new_message_size = len(content)

        self._enforce_limits(new_message_size)

        message = Message(
            id=self._next_message_id,
            content=content,
            sender=sender,
            source=source,
            originating_time=originating_time,
            group=group
        )

        self._messages.append(message)
        self._total_chars += message.message_size
        self._next_message_id += 1

        # Log the message
        self._log_message(message)

        print(f"QUEUE ADD ({self.user_id}): Added message {message.id} from {message.sender.display_name}. "
              f"Queue stats: {len(self._messages)} msgs, {self._total_chars} chars.")

        self._trigger_callbacks(message)

    def _log_message(self, message: Message):
        """Logs a message to the appropriate files."""
        os.makedirs('log', exist_ok=True)

        originating_time_str = str(message.originating_time) if message.originating_time is not None else 'None'

        sender_str = f"{message.sender.display_name} ({message.sender.identifier})"
        group_str = f"::[group={message.group.display_name} ({message.group.identifier})]" if message.group else ""

        log_line_parts = [
            f"[originating_time={originating_time_str}]",
            f"[accepted_time={message.accepted_time}]",
            f"[message_id={message.id}]",
            f"[sending_user={sender_str}]"
        ]
        if group_str:
            log_line_parts.append(group_str)
        log_line_parts.append(f":: {message.content}\n")

        user_log_line = "::".join(log_line_parts)

        # User-specific log
        user_log_path = os.path.join('log', f"{self.vendor_name}_{self.user_id}.log")
        with open(user_log_path, 'a') as f:
            f.write(user_log_line)

        # Global log
        global_log_path = os.path.join('log', "all_vendors.log")
        global_log_line_parts = [
            f"[originating_time={originating_time_str}]",
            f"[accepted_time={message.accepted_time}]",
            f"[vendor_name={self.vendor_name}]",
            f"[user_id={self.user_id}]",
            f"[message_id={message.id}]",
            f"[sending_user={sender_str}]"
        ]
        if group_str:
            global_log_line_parts.append(group_str)
        global_log_line_parts.append(f":: {message.content}\n")

        global_log_line = "::".join(global_log_line_parts)

        with open(global_log_path, 'a') as f:
            f.write(global_log_line)

    def get_messages(self) -> List[Message]:
        return list(self._messages)
