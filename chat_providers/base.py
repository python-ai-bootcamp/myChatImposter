from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List

from queue_manager import UserQueuesManager
from config_models import ChatProviderConfig

class BaseChatProvider(ABC):
    """
    Abstract base class for all chat providers.
    It defines the interface that all chat providers must implement.
    """
    def __init__(self, bot_id: str, config: ChatProviderConfig, user_queues: Dict[str, UserQueuesManager], on_session_end: Optional[Callable[[str], None]] = None, on_status_change: Optional[Callable[[str, str], None]] = None, main_loop=None, **kwargs):
        self.bot_id = bot_id
        self.config = config
        self.user_queues = user_queues
        self.on_session_end = on_session_end
        # self.logger = logger # DEPRECATED
        self.on_status_change = on_status_change
        self.main_loop = main_loop
        super().__init__()

    @abstractmethod
    async def start_listening(self):
        """
        Starts the provider's message listening process.
        This should be a non-blocking method (e.g., run in a separate thread).
        """
        pass

    @abstractmethod
    async def stop_listening(self, cleanup_session: bool = False):
        """
        Stops the provider's message listening process gracefully.
        """
        pass

    @abstractmethod
    def sendMessage(self, recipient: str, message: str):
        """
        Sends a message to the specified recipient.
        """
        pass

    @abstractmethod
    async def send_file(self, recipient: str, file_data: bytes, filename: str, mime_type: str, caption: Optional[str] = None):
        """
        Sends a file attachment to the specified recipient.
        """
        pass

    @abstractmethod
    def get_status(self, heartbeat: bool = False) -> Dict[str, Any]:
        """
        Returns the current status of the provider.
        This is used for polling the connection status (e.g., QR code for WhatsApp).
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Returns True if the provider is currently connected and ready to send messages.
        """
        pass

    def update_cache_policy(self, max_interval: int):
        """
        Updates the internal cache policy (if applicable) based on tracking intervals.
        Default implementation does nothing.
        """
        pass

    async def fetch_historic_messages(self, identifier: str, limit: int = 500) -> List[Dict]:
        """
        Fetches historic messages for a given identifier (group or user).
        Default implementation returns empty list.
        """
        return []

    def is_bot_message(self, message_id: str) -> bool:
        """
        Checks if a message with the given ID was sent by the bot itself.
        Default implementation returns False.
        """
        return False
