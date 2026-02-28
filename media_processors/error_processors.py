from typing import Any, Dict

from infrastructure.models import ProcessingResult
from media_processors.base import BaseMediaProcessor


class CorruptMediaProcessor(BaseMediaProcessor):
    async def process_media(self, file_path: str, mime_type: str, caption: str, media_metadata: Dict[str, Any]) -> ProcessingResult:
        media_type = mime_type.replace("media_corrupt_", "")
        prefix = f"[Corrupted {media_type} media could not be downloaded]"
        content = f"{prefix} {caption}".strip() if caption else prefix
        return ProcessingResult(content=content, failed_reason=f"download failed - {media_type} corrupted")


class UnsupportedMediaProcessor(BaseMediaProcessor):
    async def process_media(self, file_path: str, mime_type: str, caption: str, media_metadata: Dict[str, Any]) -> ProcessingResult:
        prefix = f"[Unsupported {mime_type} media]"
        content = f"{prefix} {caption}".strip() if caption else prefix
        return ProcessingResult(content=content, failed_reason=f"unsupported mime type: {mime_type}")
