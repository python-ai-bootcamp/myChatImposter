# Feature Specification: Image Transcription Support

## Overview
- This feature adds automatic image transcription to `ImageVisionProcessor`.
Every image processed by the media processing pipeline which arrives to the `ImageVisionProcessor` will be processed in order to produce a textual representation describing the image content
- this will be achieved by using a model provider external api


## Requirements

### Configuration
- `image_transcription` is added as a new per-bot tier in `LLMConfigurations` (alongside `high`, `low`, `image_moderation`), with defaults matching the `low` tier (`OpenAiChatProvider` with `gpt-5-mini`). Individual bots may override to any compatible chat model (e.g. `gpt-5`) through their config.
- A new `ImageTranscriptionProviderConfig` extends `ChatCompletionProviderConfig` with an additional `detail: Literal["low", "high", "auto"] = "auto"` field. The `LLMConfigurations.image_transcription` field type is `ImageTranscriptionProviderConfig`.
- `ConfigTier` is updated to include `"image_transcription"`.
- `resolve_model_config` in `services/resolver.py` returns `ImageTranscriptionProviderConfig` for the `"image_transcription"` tier.

### Processing Flow
- `ImageVisionProcessor` will first moderate the image (as it currently does)
- After `moderation_result` is obtained:
  - If `moderation_result.flagged == false`: proceed to transcribe the image (see below)
  - If `moderation_result.flagged == true`: return a clean placeholder (no `failed_reason`, no failure archival) with content: `"[Transcribed image multimedia message was flagged with following problematic tags: ('tag1', 'tag2', ...)]"` where the tags are the keys from `moderation_result.categories` whose value is `true`. Moderation flagging is treated as a normal processing outcome, not an error.

### Transcription
- `ImageVisionProcessor` will use the bot's `image_transcription` tier to resolve an `ImageTranscriptionProvider` and call `provider.transcribe_image(base64_image, mime_type)` to transcribe the actual image bytes (base64-encoded) into a message describing the image.
- The transcription prompt is hardcoded in the provider (no system message): *"Describe the contents of this image concisely in 1-3 sentences, if there is text in the image add the text inside image to description as well"*

### Output Format
- The produced image transcript will be formatted and passed to the caller, arriving at the bot message queue as if it was a text message (using base media processor existing mechanism).
- Caption handling — if the original WhatsApp message included a caption, it is appended:

  With caption:
  ```
  [Attached image description: <transcription>]
  [Image caption: <caption>]
  ```

  Without caption:
  ```
  [Attached image description: <transcription>]
  ```

## Relevant Background Information
### Project Files
- `media_processors/base.py`
- `media_processors/stub_processors.py`
- `media_processors/media_file_utils.py`
- `media_processors/factory.py`
- `media_processors/error_processors.py`
- `media_processors/image_vision_processor.py`
- `media_processors/__init__.py`
- `model_providers/base.py`
- `model_providers/openAi.py`
- `model_providers/openAiModeration.py`
- `model_providers/image_moderation.py`
- `model_providers/chat_completion.py`
- `model_providers/image_transcription.py` *(new — abstract `ImageTranscriptionProvider`)*
- `model_providers/openAiImageTranscription.py` *(new — concrete `OpenAiImageTranscriptionProvider`)*
- `services/media_processing_service.py`
- `services/model_factory.py`
- `services/resolver.py`
- `utils/provider_utils.py`
- `config_models.py`
- `queue_manager.py`
- `infrastructure/models.py`


### External Resource
- https://developers.openai.com/api/docs/guides/images-vision?format=base64-encoded

## Technical Details

### 1) Provider Architecture
A dedicated `ImageTranscriptionProvider` abstract class (in `model_providers/image_transcription.py`) exposes a `transcribe_image(base64_image, mime_type) -> str` method, mirroring the `ImageModerationProvider` pattern. A concrete `OpenAiImageTranscriptionProvider` (in `model_providers/openAiImageTranscription.py`) internally builds a `ChatOpenAI` LLM, constructs a multimodal `HumanMessage` with content blocks (text prompt + `image_url` with `detail="auto"`), invokes it, and returns `response.content`. `create_model_provider` in `services/model_factory.py` is extended to handle `ImageTranscriptionProvider` as a third branch.

### 2) OpenAI Vision Parameter
The provider reads the `detail` parameter from its `ImageTranscriptionProviderConfig` (default `"auto"`, see OpenAI docs on [Images and vision](https://developers.openai.com/api/docs/guides/images-vision?format=base64-encoded)). The `detail` parameter controls image tokenization fidelity (how many patches/tiles the image is broken into). Valid values: `"low"`, `"high"`, `"auto"`. It defaults to `"auto"` but is overridable per-bot through config.
