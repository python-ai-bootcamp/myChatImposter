import logging

from infrastructure.models import ProcessingResult
from media_processors.base import BaseMediaProcessor
from services.model_factory import create_model_provider
from model_providers.audio_transcription import AudioTranscriptionProvider

logger = logging.getLogger(__name__)


class AudioTranscriptionProcessor(BaseMediaProcessor):
    """Processor for audio transcription using the bot's audio_transcription tier.
    
    Processes audio files natively and directly (no moderation step).
    Follows the same error handling pattern as ImageVisionProcessor.
    """

    async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:
        """Transcribe audio using the bot's configured audio transcription provider.
        
        Error handling uses `except Exception as e:` (NOT BaseException) because
        asyncio.CancelledError inherits from BaseException in Python 3.9+,
        and catching it would break the worker's graceful shutdown flow.
        """
        try:
            provider = await create_model_provider(bot_id, "audio_transcription", "audio_transcription")
            if not isinstance(provider, AudioTranscriptionProvider):
                raise TypeError(f"Expected AudioTranscriptionProvider, got {type(provider)}")

            transcript_text = await provider.transcribe_audio(file_path, mime_type)

            # Check for empty/unexpected result
            if not transcript_text.strip():
                return ProcessingResult(
                    content="Unable to transcribe audio content",
                    failed_reason="Unexpected format from Soniox API",
                    unprocessable_media=True
                )

            # Success: return raw text (formatting delegated to format_processing_result)
            return ProcessingResult(content=transcript_text)

        except Exception as e:
            logger.error(f"AUDIO TRANSCRIPTION ({bot_id}): Transcription failed: {e}")
            return ProcessingResult(
                content="Unable to transcribe audio content",
                failed_reason=f"Transcription error: {e}",
                unprocessable_media=True
            )
