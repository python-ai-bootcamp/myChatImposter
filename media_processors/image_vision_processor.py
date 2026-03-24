import asyncio
import base64
import logging
import os
from typing import Optional

from infrastructure.models import ProcessingResult
from media_processors.base import BaseMediaProcessor
from services.model_factory import create_model_provider
from services.resolver import resolve_bot_language
from model_providers.image_moderation import ImageModerationProvider
from model_providers.image_transcription import ImageTranscriptionProvider

logger = logging.getLogger(__name__)


def _load_image_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class ImageVisionProcessor(BaseMediaProcessor):
    async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:
        """Image processing pipeline:
        1. Load image as base64 (off main thread)
        2. Run moderation check
        3. If flagged → return unprocessable result
        4. If clean → run transcription
        5. Return transcription result as raw content
        """
        # Step 1: Load image (event-loop safe via asyncio.to_thread)
        base64_image = await asyncio.to_thread(_load_image_base64, file_path)

        # Step 2: Moderation check
        try:
            moderation_provider = await create_model_provider(bot_id, "media_processing", "image_moderation")
            if not isinstance(moderation_provider, ImageModerationProvider):
                raise TypeError(f"Expected ImageModerationProvider, got {type(moderation_provider)}")

            moderation_result = await moderation_provider.moderate_image(base64_image, mime_type)
            logger.info(f"IMAGE MODERATION ({bot_id}): {moderation_result.model_dump()}")

            # Step 3: If flagged → unprocessable
            if moderation_result.flagged:
                logger.warning(f"IMAGE MODERATION ({bot_id}): Image flagged by moderation.")
                return ProcessingResult(
                    content="Image flagged by content moderation",
                    unprocessable_media=True,
                )
        except Exception as e:
            logger.error(f"IMAGE MODERATION ({bot_id}): Moderation failed: {e}")
            return ProcessingResult(
                content="Image could not be moderated",
                failed_reason=f"Moderation error: {e}",
            )

        # Step 4: Transcription (only if moderation passed)
        try:
            transcription_provider = await create_model_provider(bot_id, "media_processing", "image_transcription")
            if not isinstance(transcription_provider, ImageTranscriptionProvider):
                raise TypeError(f"Expected ImageTranscriptionProvider, got {type(transcription_provider)}")

            language_code = await resolve_bot_language(bot_id)
            transcription = await transcription_provider.transcribe_image(base64_image, mime_type, language_code)

            # Step 5: Return transcription as raw content
            return ProcessingResult(content=transcription)

        except Exception as e:
            logger.error(f"IMAGE TRANSCRIPTION ({bot_id}): Transcription failed: {e}")
            return ProcessingResult(
                content="Image could not be transcribed",
                failed_reason=f"Transcription error: {e}",
            )
