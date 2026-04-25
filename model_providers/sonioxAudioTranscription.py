import asyncio
import logging

from soniox import AsyncSonioxClient
from soniox.types import CreateTranscriptionConfig

from model_providers.audio_transcription import AudioTranscriptionProvider

logger = logging.getLogger(__name__)

# GC-safe background task retention: prevents Python from garbage-collecting
# fire-and-forget cleanup tasks before they complete.
_background_tasks = set()


class SonioxAudioTranscriptionProvider(AudioTranscriptionProvider):
    """Concrete Soniox audio transcription provider.
    
    Uses the AsyncSonioxClient with the explicit 4-step async pattern:
    1. Upload file
    2. Create transcription job
    3. Wait for completion
    4. Get transcript
    
    The convenience transcribe() wrapper is intentionally NOT used.
    """

    async def initialize(self):
        """Create the async Soniox client with the resolved API key."""
        self.client = AsyncSonioxClient(api_key=self._resolve_api_key())

    async def transcribe_audio(self, audio_path: str, mime_type: str) -> str:
        """Orchestrate the full Soniox async transcription lifecycle.
        
        Cleanup of remote resources (uploaded file + transcription job) is guaranteed
        via a fire-and-forget asyncio task in the finally block, which safely bypasses
        CancelledError from the parent task's timeout wrapper.
        """
        transcription = None
        file = None
        try:
            # Step 1: Upload
            file = await self.client.files.upload(audio_path)

            # Step 2: Create transcription job
            config = CreateTranscriptionConfig(model=self.config.provider_config.model)
            transcription = await self.client.stt.create(config=config, file_id=file.id)

            # Step 3: Wait for completion
            await self.client.stt.wait(transcription.id)

            # Step 4: Get transcript
            transcript = await self.client.stt.get_transcript(transcription.id)

            # Token tracking (estimated — Soniox does not provide native token usage)
            if self._token_tracker:
                job_info = await self.client.stt.get(transcription.id)
                if job_info:
                    await self._token_tracker(
                        # Note: Soniox does not provide token usage natively.
                        # We use an arithmetic estimation based on audio duration and output text length.
                        input_tokens=int((job_info.audio_duration_ms or 0) / 120),
                        output_tokens=int(len(transcript.text) * 0.3),
                        cached_input_tokens=0
                    )

            return transcript.text

        finally:
            async def _cleanup():
                if transcription:
                    try:
                        await self.client.stt.delete_if_exists(transcription.id)
                    except Exception as e:
                        logger.error(f"Failed to cleanup Soniox transcription resource: {e}")
                if file:
                    try:
                        await self.client.files.delete_if_exists(file.id)
                    except Exception as e:
                        logger.error(f"Failed to cleanup Soniox file resource: {e}")

            task = asyncio.create_task(_cleanup())
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
