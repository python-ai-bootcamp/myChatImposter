import asyncio
import os

from infrastructure.models import ProcessingResult
from media_processors.base import BaseMediaProcessor


class StubSleepProcessor(BaseMediaProcessor):
    sleep_seconds: int = 1
    media_label: str = "media"

    async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:
        if os.path.exists(file_path):
            with open(file_path, "rb"):
                pass
        await asyncio.sleep(self.sleep_seconds)
        return ProcessingResult(content=f"Transcripted {self.media_label} multimedia message with guid='{os.path.basename(file_path)}'")



class VideoDescriptionProcessor(StubSleepProcessor):
    sleep_seconds = 60
    media_label = "video"


class DocumentProcessor(StubSleepProcessor):
    sleep_seconds = 5
    media_label = "document"
