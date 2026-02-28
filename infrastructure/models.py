from dataclasses import dataclass, field
from typing import Any, Dict, Optional

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
    media_metadata: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ProcessingResult:
    content: str
    failed_reason: Optional[str] = None
