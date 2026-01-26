import logging
from queue_message_types import QueueMessageType
from message_processors.base import BaseMessageProcessor
from message_processors.text_processor import TextMessageProcessor
from message_processors.ics_processor import IcsActionableItemProcessor

logger = logging.getLogger(__name__)

class MessageProcessorFactory:
    _processors = {
        QueueMessageType.TEXT.value: TextMessageProcessor(),
        QueueMessageType.ICS_ACTIONABLE_ITEM.value: IcsActionableItemProcessor()
    }

    @classmethod
    def get_processor(cls, message_type: str) -> BaseMessageProcessor:
        """
        Returns the appropriate processor for the given message type.
        Raises ValueError if type is unknown.
        """
        processor = cls._processors.get(message_type)
        if not processor:
             raise ValueError(f"No processor found for message type: {message_type}")
        return processor
