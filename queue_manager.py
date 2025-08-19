import time
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Callable, List

@dataclass
class Message:
    id: int
    content: str
    sendingUser: str
    acceptedTime: int = field(default_factory=lambda: int(time.time() * 1000))
    messageSize: int = 0
    originatingTime: Optional[int] = None

    def __post_init__(self):
        self.messageSize = len(self.content)

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
        self._callbacks: List[Callable[[Message], None]] = []

    def register_callback(self, callback: Callable[[Message], None]):
        """Register a callback function to be triggered on new messages."""
        self._callbacks.append(callback)

    def _trigger_callbacks(self, message: Message):
        """Trigger all registered callbacks with the new message."""
        for callback in self._callbacks:
            try:
                callback(message)
            except Exception as e:
                print(f"Error in callback for user {self.user_id}: {e}")

    def _enforce_limits(self, new_message_size: int):
        """Evict old messages until the new message can be added."""
        now = time.time()

        # Evict by age first
        while self._messages and (now - self._messages[0].acceptedTime / 1000) > self.max_age_seconds:
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.messageSize
            print(f"QUEUE EVICT ({self.user_id}): Message {evicted_msg.id} evicted due to age.")

        # Evict by total characters
        while self._messages and (self._total_chars + new_message_size) > self.max_characters:
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.messageSize
            print(f"QUEUE EVICT ({self.user_id}): Message {evicted_msg.id} evicted due to total characters limit.")

        # Evict by total message count
        while len(self._messages) >= self.max_messages:
            evicted_msg = self._messages.popleft()
            self._total_chars -= evicted_msg.messageSize
            print(f"QUEUE EVICT ({self.user_id}): Message {evicted_msg.id} evicted due to message count limit.")

    def add_message(self, content: str, sending_user: str, originating_time: Optional[int] = None):
        """Create, add, and process a new message for the queue."""
        new_message_size = len(content)
        if new_message_size > self.max_characters:
            print(f"QUEUE REJECT ({self.user_id}): Message from {sending_user} is larger than the max character limit.")
            return

        self._enforce_limits(new_message_size)

        message = Message(
            id=self._next_message_id,
            content=content,
            sendingUser=sending_user,
            originatingTime=originating_time
        )

        self._messages.append(message)
        self._total_chars += message.messageSize
        self._next_message_id += 1

        # Log the message
        self._log_message(message)

        print(f"QUEUE ADD ({self.user_id}): Added message {message.id} from {message.sendingUser}. "
              f"Queue stats: {len(self._messages)} msgs, {self._total_chars} chars.")

        self._trigger_callbacks(message)

    def _log_message(self, message: Message):
        """Logs a message to the appropriate files."""
        os.makedirs('log', exist_ok=True)

        originating_time_str = str(message.originatingTime) if message.originatingTime is not None else 'None'

        # User-specific log
        user_log_path = os.path.join('log', f"{self.vendor_name}_{self.user_id}.log")
        user_log_line = (
            f"[{originating_time_str}]::[{message.acceptedTime}]::"
            f"[message_id={message.id}]::[sending_user={message.sendingUser}]:: {message.content}\n"
        )
        with open(user_log_path, 'a') as f:
            f.write(user_log_line)

        # Global log
        global_log_path = os.path.join('log', "all_vendors.log")
        global_log_line = (
            f"[{originating_time_str}]::[{message.acceptedTime}]::"
            f"[vendor_name={self.vendor_name}]::[user_id={self.user_id}]::"
            f"[message_id={message.id}]::[sending_user={message.sendingUser}]:: {message.content}\n"
        )
        with open(global_log_path, 'a') as f:
            f.write(global_log_line)

    def get_messages(self) -> List[Message]:
        return list(self._messages)
