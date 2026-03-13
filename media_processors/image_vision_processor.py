import asyncio
import base64
import logging
import os
from typing import Optional

from infrastructure.models import ProcessingResult
from media_processors.base import BaseMediaProcessor
from services.model_factory import create_model_provider
from model_providers.image_moderation import ImageModerationProvider

logger = logging.getLogger(__name__)

def _load_image_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

class ImageVisionProcessor(BaseMediaProcessor):
    async def process_media(self, file_path: str, mime_type: str, caption: str, bot_id: str) -> ProcessingResult:
        base64_image = await asyncio.to_thread(_load_image_base64, file_path)
        
        provider = await create_model_provider(bot_id, "media_processing", "image_moderation")
        if not isinstance(provider, ImageModerationProvider):
            raise TypeError(f"Expected ImageModerationProvider, got {type(provider)}")
            
        moderation_result = await provider.moderate_image(base64_image, mime_type)
        
        logger.info(moderation_result.model_dump())
        
        return ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")
