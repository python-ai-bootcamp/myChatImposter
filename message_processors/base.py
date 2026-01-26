from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseMessageProcessor(ABC):
    """
    Abstract base class for processing different types of queued messages.
    """
    
    @abstractmethod
    async def process(self, message_doc: dict, target_instance) -> None:
        """
        Process the message document and deliver it via the target chatbot instance.
        
        Args:
            message_doc: The message document from the queue (dict).
            target_instance: The ChatbotInstance object (containing provider, config, etc.).
            
        Raises:
            Exception: If processing or sending fails.
        """
        pass
