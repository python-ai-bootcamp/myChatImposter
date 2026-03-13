import inspect
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from media_processors.factory import PROCESSOR_CLASS_MAP
from media_processors.base import BaseMediaProcessor
from media_processors.stub_processors import StubSleepProcessor, AudioTranscriptionProcessor, VideoDescriptionProcessor, DocumentProcessor
from media_processors.error_processors import CorruptMediaProcessor, UnsupportedMediaProcessor
from media_processors.image_vision_processor import ImageVisionProcessor
from model_providers.image_moderation import ImageModerationProvider
from model_providers.openAiModeration import OpenAiModerationProvider

# Task 17 - Factory resolution points to media_processors.image_vision_processor
def test_image_vision_processor_factory_resolution():
    cls = PROCESSOR_CLASS_MAP["ImageVisionProcessor"]
    assert cls.__module__ == "media_processors.image_vision_processor"

# Task 18 - process_media(..., bot_id: str) signature on all processors
def test_process_media_bot_id_signature():
    for cls in [BaseMediaProcessor, StubSleepProcessor, CorruptMediaProcessor,
                UnsupportedMediaProcessor, ImageVisionProcessor]:
        params = list(inspect.signature(cls.process_media).parameters.values())
        fourth = params[4]  # self=0, file_path=1, mime_type=2, caption=3, bot_id=4
        assert fourth.name == "bot_id"
        assert fourth.annotation is str

# Task 19 - moderate_image(base64_image, mime_type) signatures on both provider classes
def test_moderate_image_signature():
    for cls in [ImageModerationProvider, OpenAiModerationProvider]:
        params = list(inspect.signature(cls.moderate_image).parameters.values())
        assert params[1].name == "base64_image" and params[1].annotation is str
        assert params[2].name == "mime_type" and params[2].annotation is str

# Task 20 - Event-loop safety — image loading via asyncio.to_thread
@pytest.mark.asyncio
@patch("media_processors.image_vision_processor.asyncio.to_thread", new_callable=AsyncMock)
@patch("media_processors.image_vision_processor.create_model_provider", new_callable=AsyncMock)
async def test_image_process_loop_safety(mock_create_provider, mock_to_thread):
    processor = ImageVisionProcessor([], 60.0)
    mock_to_thread.return_value = "base64_encoded_dummy"
    
    mock_provider = AsyncMock(spec=ImageModerationProvider)
    from model_providers.image_moderation import ModerationResult
    mock_provider.moderate_image.return_value = ModerationResult(flagged=False, categories={}, category_scores={})
    
    mock_create_provider.return_value = mock_provider
    
    await processor.process_media("dummy_path", "image/jpeg", "caption", "bot_123")
    
    mock_to_thread.assert_called_once()
    args = mock_to_thread.call_args[0]
    assert callable(args[0])
    assert args[1] == "dummy_path"

# Task 21 - Moderation SDK payload shape
@pytest.mark.asyncio
@patch("model_providers.openAiModeration.OpenAiModerationProvider._resolve_api_key", return_value="fake_key")
@patch("model_providers.openAiModeration.AsyncOpenAI")
async def test_moderation_sdk_payload(mock_openai_cls, mock_resolve_api_key):
    mock_client = AsyncMock()
    mock_openai_cls.return_value = mock_client
    
    config = MagicMock()
    config.provider_config.model = "omni-moderation-latest"
    
    # Needs a dummy patch context if OpenAiModerationProvider does anything weird on init, but we mocked _resolve_api_key
    provider = OpenAiModerationProvider(config)
    
    mock_response = AsyncMock()
    mock_result = AsyncMock()
    mock_result.flagged = False
    
    class MockDumpable:
        def model_dump(self): return {}
        
    mock_result.categories = MockDumpable()
    mock_result.category_scores = MockDumpable()
    
    mock_response.results = [mock_result]
    mock_client.moderations.create.return_value = mock_response
    
    await provider.moderate_image("raw_base64_data", "image/png")
    
    mock_client.moderations.create.assert_called_once_with(
        model="omni-moderation-latest",
        input=[{"type": "image_url", "image_url": {"url": "data:image/png;base64,raw_base64_data"}}]
    )
