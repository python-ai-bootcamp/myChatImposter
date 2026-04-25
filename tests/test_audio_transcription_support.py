"""Tests for the Audio Transcription Support feature.

Covers:
- ConfigTier includes 'audio_transcription'
- LLMConfigurations requires audio_transcription field
- AudioTranscriptionProviderSettings defaults
- AudioTranscriptionProcessor signature verification
- AudioTranscriptionProcessor successful transcription flow
- AudioTranscriptionProcessor empty transcript failure
- AudioTranscriptionProcessor exception handling
- format_processing_result prefix injection for audio
- format_processing_result prefix suppression for unprocessable
- BaseMediaProcessor.process_job timeout sets unprocessable_media=True
- BaseMediaProcessor._handle_unhandled_exception sets unprocessable_media=True
- Factory maps AudioTranscriptionProcessor correctly
"""
import inspect
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import get_args
from dataclasses import asdict

from config_models import (
    ConfigTier,
    LLMConfigurations,
    ChatCompletionProviderConfig,
    ChatCompletionProviderSettings,
    BaseModelProviderConfig,
    BaseModelProviderSettings,
    ImageTranscriptionProviderConfig,
    ImageTranscriptionProviderSettings,
    AudioTranscriptionProviderConfig,
    AudioTranscriptionProviderSettings,
)
from infrastructure.models import ProcessingResult, MediaProcessingJob
from media_processors.base import format_processing_result, BaseMediaProcessor
from media_processors.audio_transcription_processor import AudioTranscriptionProcessor
from media_processors.factory import PROCESSOR_CLASS_MAP
from model_providers.audio_transcription import AudioTranscriptionProvider
from queue_manager import Message, Sender


# =============================================================================
# ConfigTier includes 'audio_transcription'
# =============================================================================

def test_config_tier_includes_audio_transcription():
    valid_tiers = get_args(ConfigTier)
    assert "audio_transcription" in valid_tiers


# =============================================================================
# LLMConfigurations requires audio_transcription
# =============================================================================

def test_llm_configurations_requires_audio_transcription():
    """LLMConfigurations must fail validation without audio_transcription."""
    with pytest.raises(Exception):
        LLMConfigurations(
            high=ChatCompletionProviderConfig(
                provider_name="openAi",
                provider_config=ChatCompletionProviderSettings(model="test")
            ),
            low=ChatCompletionProviderConfig(
                provider_name="openAi",
                provider_config=ChatCompletionProviderSettings(model="test")
            ),
            image_moderation=BaseModelProviderConfig(
                provider_name="openAiModeration",
                provider_config=BaseModelProviderSettings(model="test")
            ),
            image_transcription=ImageTranscriptionProviderConfig(
                provider_name="openAiImageTranscription",
                provider_config=ImageTranscriptionProviderSettings(model="test")
            ),
            # Missing audio_transcription → should fail
        )


def test_llm_configurations_valid_with_audio_transcription():
    """LLMConfigurations should validate with all five tiers."""
    config = LLMConfigurations(
        high=ChatCompletionProviderConfig(
            provider_name="openAi",
            provider_config=ChatCompletionProviderSettings(model="test")
        ),
        low=ChatCompletionProviderConfig(
            provider_name="openAi",
            provider_config=ChatCompletionProviderSettings(model="test")
        ),
        image_moderation=BaseModelProviderConfig(
            provider_name="openAiModeration",
            provider_config=BaseModelProviderSettings(model="test")
        ),
        image_transcription=ImageTranscriptionProviderConfig(
            provider_name="openAiImageTranscription",
            provider_config=ImageTranscriptionProviderSettings(model="test")
        ),
        audio_transcription=AudioTranscriptionProviderConfig(
            provider_name="sonioxAudioTranscription",
            provider_config=AudioTranscriptionProviderSettings(model="stt-async-v4")
        ),
    )
    assert config.audio_transcription is not None


# =============================================================================
# AudioTranscriptionProviderSettings defaults
# =============================================================================

def test_audio_transcription_settings_temperature_default():
    settings = AudioTranscriptionProviderSettings(model="stt-async-v4")
    assert settings.temperature == 0.0


# =============================================================================
# AudioTranscriptionProcessor signature verification
# =============================================================================

def test_audio_transcription_processor_signature():
    """AudioTranscriptionProcessor.process_media should have: (self, file_path, mime_type, bot_id)"""
    params = list(inspect.signature(AudioTranscriptionProcessor.process_media).parameters.values())
    param_names = [p.name for p in params]
    assert "caption" not in param_names, "AudioTranscriptionProcessor still has caption parameter"
    assert params[1].name == "file_path"
    assert params[2].name == "mime_type"
    assert params[3].name == "bot_id"
    assert params[3].annotation is str


# =============================================================================
# AudioTranscriptionProcessor successful transcription flow
# =============================================================================

@pytest.mark.asyncio
@patch("media_processors.audio_transcription_processor.create_model_provider", new_callable=AsyncMock)
async def test_audio_transcription_success(mock_create_provider):
    """Successful transcription returns ProcessingResult with transcript text."""
    processor = AudioTranscriptionProcessor([], 60.0)
    
    mock_provider = AsyncMock(spec=AudioTranscriptionProvider)
    mock_provider.transcribe_audio.return_value = "Hello, this is a test audio."
    mock_create_provider.return_value = mock_provider
    
    result = await processor.process_media("dummy_file.ogg", "audio/ogg", "bot_123")
    
    assert result.content == "Hello, this is a test audio."
    assert result.unprocessable_media is False
    assert result.failed_reason is None
    mock_provider.transcribe_audio.assert_called_once_with("dummy_file.ogg", "audio/ogg")


# =============================================================================
# AudioTranscriptionProcessor empty transcript failure
# =============================================================================

@pytest.mark.asyncio
@patch("media_processors.audio_transcription_processor.create_model_provider", new_callable=AsyncMock)
async def test_audio_transcription_empty_transcript(mock_create_provider):
    """Empty transcript should return unprocessable result."""
    processor = AudioTranscriptionProcessor([], 60.0)
    
    mock_provider = AsyncMock(spec=AudioTranscriptionProvider)
    mock_provider.transcribe_audio.return_value = ""
    mock_create_provider.return_value = mock_provider
    
    result = await processor.process_media("dummy_file.ogg", "audio/ogg", "bot_123")
    
    assert result.unprocessable_media is True
    assert "Unexpected format" in result.failed_reason
    assert result.content == "Unable to transcribe audio content"


# =============================================================================
# AudioTranscriptionProcessor exception handling
# =============================================================================

@pytest.mark.asyncio
@patch("media_processors.audio_transcription_processor.create_model_provider", new_callable=AsyncMock)
async def test_audio_transcription_exception(mock_create_provider):
    """Exception during transcription should return unprocessable result."""
    processor = AudioTranscriptionProcessor([], 60.0)
    
    mock_provider = AsyncMock(spec=AudioTranscriptionProvider)
    mock_provider.transcribe_audio.side_effect = Exception("API down")
    mock_create_provider.return_value = mock_provider
    
    result = await processor.process_media("dummy_file.ogg", "audio/ogg", "bot_123")
    
    assert result.unprocessable_media is True
    assert "Transcription error" in result.failed_reason
    assert result.content == "Unable to transcribe audio content"


# =============================================================================
# format_processing_result prefix injection (success)
# =============================================================================

def test_format_audio_prefix_injection():
    """Successful audio result should get 'Audio Transcription: ' prefix."""
    result = format_processing_result(
        content="hello world",
        caption="cap",
        mime_type="audio/ogg"
    )
    assert result.content.startswith("[Audio Transcription: hello world]")


# =============================================================================
# format_processing_result prefix suppressed for unprocessable
# =============================================================================

def test_format_audio_prefix_suppressed_unprocessable():
    """Unprocessable media should NOT get the prefix."""
    result = format_processing_result(
        content="Unable to transcribe",
        caption="cap",
        mime_type="audio/ogg",
        unprocessable_media=True
    )
    assert "Audio Transcription:" not in result.content
    assert "[Unable to transcribe]" in result.content


# =============================================================================
# BaseMediaProcessor.process_job timeout sets unprocessable_media=True
# =============================================================================

def _make_dummy_job(mime_type="audio/ogg"):
    """Helper to create a minimal MediaProcessingJob for testing."""
    sender = Sender(identifier="user1", display_name="User 1")
    msg = Message(
        id=1, content="", sender=sender, source="user",
        accepted_time=1000, message_size=0
    )
    return MediaProcessingJob(
        job_id="test_job_id",
        bot_id="bot_123",
        correspondent_id="user1",
        placeholder_message=msg,
        guid="test_guid",
        mime_type=mime_type,
        status="processing"
    )


@pytest.mark.asyncio
async def test_process_job_timeout_sets_unprocessable():
    """process_job timeout should produce unprocessable_media=True, suppressing prefix."""

    class SlowProcessor(BaseMediaProcessor):
        async def process_media(self, file_path, mime_type, bot_id):
            await asyncio.sleep(999)  # will be interrupted by timeout
            return ProcessingResult(content="should not reach")

    processor = SlowProcessor([], 0.01)  # 10ms timeout
    job = _make_dummy_job()

    # Mock db and get_bot_queues
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock_collection.insert_one = AsyncMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    captured_result = {}

    async def capture_persist(job_arg, result, db):
        captured_result["result"] = result
        return True

    # Patch resolve_media_path and delete_media_file
    with patch("media_processors.base.resolve_media_path", return_value="fake_path"), \
         patch("media_processors.base.delete_media_file"):
        
        # Override _persist_result_first to capture the formatted result
        processor._persist_result_first = capture_persist
        processor._archive_to_failed = AsyncMock()

        await processor.process_job(job, lambda x: None, mock_db)

    assert "result" in captured_result
    result = captured_result["result"]
    # Timeout should produce unprocessable_media=True, which suppresses prefix
    assert result.unprocessable_media is True
    assert "Audio Transcription:" not in result.content


# =============================================================================
# BaseMediaProcessor._handle_unhandled_exception sets unprocessable_media=True
# =============================================================================

@pytest.mark.asyncio
async def test_handle_unhandled_exception_sets_unprocessable():
    """_handle_unhandled_exception should set unprocessable_media=True."""

    class DummyProcessor(BaseMediaProcessor):
        async def process_media(self, file_path, mime_type, bot_id):
            return ProcessingResult(content="unused")

    processor = DummyProcessor([], 60.0)
    job = _make_dummy_job()

    # Mock db
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock_collection.insert_one = AsyncMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)

    captured_result = {}

    async def capture_persist(job_arg, result, db):
        captured_result["result"] = result
        return True

    processor._persist_result_first = capture_persist
    processor._archive_to_failed = AsyncMock()

    await processor._handle_unhandled_exception(job, mock_db, "test error")

    assert "result" in captured_result
    result = captured_result["result"]
    assert result.unprocessable_media is True
    # No prefix should be injected
    assert "Audio Transcription:" not in result.content
    assert "Media processing failed" in result.content


# =============================================================================
# Factory maps AudioTranscriptionProcessor correctly
# =============================================================================

def test_factory_maps_audio_transcription_processor():
    """PROCESSOR_CLASS_MAP should map AudioTranscriptionProcessor from the new module."""
    assert "AudioTranscriptionProcessor" in PROCESSOR_CLASS_MAP
    assert PROCESSOR_CLASS_MAP["AudioTranscriptionProcessor"] is AudioTranscriptionProcessor
