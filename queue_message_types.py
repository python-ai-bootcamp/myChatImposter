from enum import Enum

class QueueMessageType(str, Enum):
    TEXT = "text"
    ICS_ACTIONABLE_ITEM = "ics_actionable_item"
