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
    unprocessable_media: bool = False
    display_media_type: Optional[str] = None
    """display_media_type is a transient, processing-time-only variable strictly intended
    for consumption by format_processing_result. It is intentionally NOT persisted to the database."""

