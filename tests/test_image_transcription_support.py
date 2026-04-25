"""Tests for the Image Transcription Support feature.

Covers:
- T44: ConfigTier includes 'image_transcription'
- T45: LLMConfigurations requires image_transcription field
- T46: ImageTranscriptionProviderSettings.detail defaults to 'auto'
- T47: format_processing_result bracket-wrapping, caption, filename
- T48: process_media signature updated (no caption parameter)
- T49: ImageVisionProcessor moderation → transcription flow
- T50: OpenAiImageTranscriptionProvider response normalization
- T51: OpenAiMixin._build_llm_params() correctness
"""
import inspect
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import get_args

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
    DefaultConfigurations,
)
from infrastructure.models import ProcessingResult
from media_processors.base import format_processing_result, BaseMediaProcessor
from media_processors.stub_processors import StubSleepProcessor, VideoDescriptionProcessor, DocumentProcessor
from media_processors.error_processors import CorruptMediaProcessor, UnsupportedMediaProcessor
from media_processors.image_vision_processor import ImageVisionProcessor
from media_processors.factory import PROCESSOR_CLASS_MAP
from model_providers.base import LLMProvider, BaseModelProvider
from model_providers.chat_completion import ChatCompletionProvider
from model_providers.image_transcription import ImageTranscriptionProvider
from model_providers.image_moderation import ImageModerationProvider, ModerationResult
from model_providers.openAiImageTranscription import OpenAiImageTranscriptionProvider


# =============================================================================
# T44: ConfigTier includes 'image_transcription'
# =============================================================================

def test_config_tier_includes_image_transcription():
    valid_tiers = get_args(ConfigTier)
    assert "image_transcription" in valid_tiers


# =============================================================================
# T45: LLMConfigurations requires image_transcription
# =============================================================================

def test_llm_configurations_requires_image_transcription():
    """LLMConfigurations must fail validation without image_transcription."""
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
            # Missing image_transcription → should fail
        )


def test_llm_configurations_valid_with_image_transcription():
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
    assert config.image_transcription is not None


# =============================================================================
# T46: ImageTranscriptionProviderSettings defaults
# =============================================================================

def test_image_transcription_settings_detail_default():
    settings = ImageTranscriptionProviderSettings(model="gpt-5-mini")
    assert settings.detail == "auto"


def test_image_transcription_settings_custom_detail():
    settings = ImageTranscriptionProviderSettings(model="gpt-5-mini", detail="low")
    assert settings.detail == "low"


# =============================================================================
# T47: format_processing_result
# =============================================================================

def test_format_processing_result_basic():
    result = format_processing_result(content="hello", caption="world", mime_type="image/jpeg")
    assert result.content == "[Image Transcription: hello]\nworld"
    assert result.unprocessable_media is False


def test_format_processing_result_with_filename():
    result = format_processing_result(
        content="transcribed text",
        caption="user caption",
        mime_type="image/jpeg",
        original_filename="photo.jpg",
    )
    assert result.content == "[file: photo.jpg\nImage Transcription: transcribed text]\nuser caption"


def test_format_processing_result_empty_caption():
    result = format_processing_result(content="content", caption="", mime_type="image/jpeg")
    assert result.content == "[Image Transcription: content]\n"


def test_format_processing_result_unprocessable():
    result = format_processing_result(
        content="flagged",
        caption="cap",
        mime_type="image/jpeg",
        unprocessable_media=True,
    )
    assert result.unprocessable_media is True
    assert "[flagged]" in result.content


# =============================================================================
# T48: process_media signature (no caption param)
# =============================================================================

def test_process_media_no_caption_parameter():
    """All processor subclasses should have signature: process_media(self, file_path, mime_type, bot_id)"""
    for cls in [BaseMediaProcessor, StubSleepProcessor, CorruptMediaProcessor,
                UnsupportedMediaProcessor, ImageVisionProcessor]:
        params = list(inspect.signature(cls.process_media).parameters.values())
        param_names = [p.name for p in params]
        assert "caption" not in param_names, f"{cls.__name__} still has caption parameter"
        # Expected: self, file_path, mime_type, bot_id
        assert params[1].name == "file_path"
        assert params[2].name == "mime_type"
        assert params[3].name == "bot_id"
        assert params[3].annotation is str


# =============================================================================
# T49: ImageVisionProcessor moderation → transcription flow
# =============================================================================

@pytest.mark.asyncio
@patch("media_processors.image_vision_processor.resolve_bot_language", new_callable=AsyncMock, return_value="en")
@patch("media_processors.image_vision_processor.create_model_provider", new_callable=AsyncMock)
@patch("media_processors.image_vision_processor.asyncio.to_thread", new_callable=AsyncMock)
async def test_image_vision_clean_image_flow(mock_to_thread, mock_create_provider, mock_resolve_lang):
    """When moderation passes, transcription should run and return content."""
    processor = ImageVisionProcessor([], 60.0)
    mock_to_thread.return_value = "base64_encoded_dummy"

    # Moderation provider (first call)
    mock_mod_provider = AsyncMock(spec=ImageModerationProvider)
    mock_mod_provider.moderate_image.return_value = ModerationResult(
        flagged=False, categories={}, category_scores={}
    )
    
    # Transcription provider (second call)
    mock_trans_provider = AsyncMock(spec=ImageTranscriptionProvider)
    mock_trans_provider.transcribe_image.return_value = "A cat sitting on a mat"
    
    mock_create_provider.side_effect = [mock_mod_provider, mock_trans_provider]
    
    result = await processor.process_media("dummy_path", "image/jpeg", "bot_123")
    
    assert result.content == "A cat sitting on a mat"
    assert result.unprocessable_media is False
    mock_trans_provider.transcribe_image.assert_called_once()


@pytest.mark.asyncio
@patch("media_processors.image_vision_processor.create_model_provider", new_callable=AsyncMock)
@patch("media_processors.image_vision_processor.asyncio.to_thread", new_callable=AsyncMock)
async def test_image_vision_flagged_image(mock_to_thread, mock_create_provider):
    """When moderation flags the image, transcription should NOT run."""
    processor = ImageVisionProcessor([], 60.0)
    mock_to_thread.return_value = "base64_encoded_dummy"
    
    mock_mod_provider = AsyncMock(spec=ImageModerationProvider)
    mock_mod_provider.moderate_image.return_value = ModerationResult(
        flagged=True, categories={}, category_scores={}
    )
    mock_create_provider.return_value = mock_mod_provider
    
    result = await processor.process_media("dummy_path", "image/jpeg", "bot_123")
    
    assert result.unprocessable_media is True
    assert "flagged" in result.content.lower()
    # create_model_provider should only be called once (moderation only)
    assert mock_create_provider.call_count == 1


# =============================================================================
# T50: OpenAiImageTranscriptionProvider._normalize_response
# =============================================================================

def test_normalize_response_string():
    result = OpenAiImageTranscriptionProvider._normalize_response("hello world")
    assert result == "hello world"


def test_normalize_response_content_blocks():
    blocks = [
        {"type": "text", "text": "Part 1"},
        {"type": "text", "text": "Part 2"},
    ]
    result = OpenAiImageTranscriptionProvider._normalize_response(blocks)
    assert result == "Part 1 Part 2"


def test_normalize_response_plain_string_list():
    result = OpenAiImageTranscriptionProvider._normalize_response(["hello", "world"])
    assert result == "hello world"


def test_normalize_response_fallback():
    result = OpenAiImageTranscriptionProvider._normalize_response(12345)
    assert result == "Unable to transcribe image content"


# =============================================================================
# T51: OpenAiMixin._build_llm_params()
# =============================================================================

def test_build_llm_params_pops_custom_fields():
    from model_providers.openAi import OpenAiMixin
    
    class TestProvider(OpenAiMixin):
        def __init__(self):
            self.config = MagicMock()
            self.config.provider_config.model_dump.return_value = {
                "model": "gpt-5-mini",
                "api_key_source": "environment",
                "api_key": None,
                "record_llm_interactions": False,
                "temperature": 0.05,
                "reasoning_effort": None,
                "seed": None,
            }
        def _resolve_api_key(self):
            return None
    
    import os
    os.environ["OPENAI_API_KEY"] = "test_key"
    try:
        provider = TestProvider()
        params = provider._build_llm_params()
        assert "api_key_source" not in params
        assert "record_llm_interactions" not in params
        assert "reasoning_effort" not in params  # Should be popped if None
        assert "seed" not in params  # Should be popped if None
        assert params["model"] == "gpt-5-mini"
    finally:
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]


# =============================================================================
# Factory resolution
# =============================================================================

def test_factory_still_contains_image_vision_processor():
    assert "ImageVisionProcessor" in PROCESSOR_CLASS_MAP
    assert PROCESSOR_CLASS_MAP["ImageVisionProcessor"] is ImageVisionProcessor


# =============================================================================
# Provider hierarchy
# =============================================================================

def test_chat_completion_provider_inherits_llm_provider():
    assert issubclass(ChatCompletionProvider, LLMProvider)


def test_image_transcription_provider_inherits_llm_provider():
    assert issubclass(ImageTranscriptionProvider, LLMProvider)


def test_processing_result_has_unprocessable_media():
    result = ProcessingResult(content="test")
    assert hasattr(result, "unprocessable_media")
    assert result.unprocessable_media is False
