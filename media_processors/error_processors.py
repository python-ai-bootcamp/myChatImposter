from infrastructure.models import ProcessingResult
from media_processors.base import BaseMediaProcessor


class CorruptMediaProcessor(BaseMediaProcessor):
    async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:
        media_type = mime_type.replace("media_corrupt_", "")
        return ProcessingResult(
            content=f"Corrupted {media_type} media could not be downloaded",
            failed_reason=f"download failed - {media_type} corrupted",
            unprocessable_media=True
        )


class UnsupportedMediaProcessor(BaseMediaProcessor):
    async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:
        return ProcessingResult(
            content=f"Unsupported {mime_type} media",
            failed_reason=f"unsupported mime type: {mime_type}",
            unprocessable_media=True
        )

