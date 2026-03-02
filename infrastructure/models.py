from dataclasses import dataclass, field
from typing import Any, Optional

from queue_manager import Message


@dataclass
class MediaProcessingJob:
    job_id: Any
    bot_id: str
    correspondent_id: str
    placeholder_message: Message
    guid: str
    mime_type: str
    status: str
    original_filename: Optional[str] = None
    quota_exceeded: Optional[bool] = None
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ProcessingResult:
    content: str
    failed_reason: Optional[str] = None
