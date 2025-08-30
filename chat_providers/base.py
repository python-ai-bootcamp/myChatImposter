from abc import ABC, abstractmethod
from typing import Dict, Any

from queue_manager import UserQueue

class BaseChatProvider(ABC):
    """
    Abstract base class for all chat providers.
    It defines the interface that all chat providers must implement.
    """
    def __init__(self, user_id: str, config: Dict, user_queues: Dict[str, UserQueue]):
        self.user_id = user_id
        self.config = config
        self.user_queues = user_queues
        super().__init__()

    @abstractmethod
    def start_listening(self):
        """
        Starts the provider's message listening process.
        This should be a non-blocking method (e.g., run in a separate thread).
        """
        pass

    @abstractmethod
    def stop_listening(self):
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
    def get_status(self) -> Dict[str, Any]:
        """
        Returns the current status of the provider.
        This is used for polling the connection status (e.g., QR code for WhatsApp).
        """
        pass
