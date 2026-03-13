# Feature Specification: Media Processor Image Moderation

## Overview
This feature adds automatic image moderation to `ImageVisionProcessor`.
Every image processed by the media processing pipeline must be sent to the OpenAI Moderation API.

This is a preparation phase:
- Actual moderation policy enforcement is out of scope for this phase.
- Actual image understanding/generation is out of scope for this phase.
- Current behavior is moderation + logging + existing stub-style `ProcessingResult`.

## Requirements
- Use the bot-specific `image_moderation` configuration from bot settings (no global hardcoded fallback path).
- Use OpenAI moderation model `omni-moderation-latest` through `openAiModeration` provider configuration.
- Moderate actual image bytes (base64-encoded), not only metadata.
- Log moderation outputs for auditing/debugging using Python `logging`.

## Relevant Background Information
### Project Files
- `media_processors\base.py`
- `media_processors\stub_processors.py`
- `media_processors\media_file_utils.py`
- `media_processors\factory.py`
- `media_processors/error_processors.py`
- `media_processors/__init__.py`
- `model_providers\base.py`
- `model_providers\openAi.py`
- `model_providers\openAiModeration.py`
- `model_providers\image_moderation.py`
- `model_providers/chat_completion.py`
- `services\media_processing_service.py`
- `services\model_factory.py`
- `services\resolver.py`
- `utils/provider_utils.py`
- `config_models.py`
- `queue_manager.py`
- `infrastructure/models.py`


### External Resource
- https://developers.openai.com/api/docs/guides/moderation/

## Technical Details

### 1) `ImageVisionProcessor` Extraction and Strict Module Hygiene
`ImageVisionProcessor` must be extracted from `media_processors\stub_processors.py` into `media_processors\image_vision_processor.py`.
The extracted `ImageVisionProcessor` inherits directly from `BaseMediaProcessor` (not `StubSleepProcessor`).

Mandatory strict hygiene rules:
1. `media_processors\image_vision_processor.py` is the only canonical source for `ImageVisionProcessor`.
2. Remove `ImageVisionProcessor` from `media_processors\stub_processors.py` completely.
3. Do not keep alias/re-export bridge imports in `stub_processors.py`.
4. Update `media_processors\factory.py` import and `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` to the new module.
5. Add/adjust a verification test or assertion proving factory resolution points to the new module.

### 2) `process_media()` Contract Update
Update media processing contract from:
- `process_media(file_path, mime_type, caption, quota_exceeded)`

To:
- `process_media(file_path, mime_type, caption, bot_id)`

Rules:
- Keep `caption` support for existing error processors.
- Remove `quota_exceeded` from the `process_media()` contract.
- Update base processor and all concrete processors to the new signature.

**Base class call site (`media_processors/base.py`):** In `BaseMediaProcessor.process_job`, pass `job.bot_id` instead of `job.quota_exceeded` as the fourth argument.

Current:
```python
result = await asyncio.wait_for(
    self.process_media(file_path, job.mime_type, job.placeholder_message.content, job.quota_exceeded),
    timeout=self.processing_timeout,
)
```

Should be:
```python
result = await asyncio.wait_for(
    self.process_media(file_path, job.mime_type, job.placeholder_message.content, job.bot_id),
    timeout=self.processing_timeout,
)
```

**Abstract method and subclasses:** Update the abstract method in `BaseMediaProcessor` and all concrete implementations.

Current:
```python
@abstractmethod
async def process_media(self, file_path: str, mime_type: str, caption: str, quota_exceeded: Optional[bool]) -> ProcessingResult:
    """Subclass implements ONLY this: actual AI/conversion logic."""
    ...
```

Should be:
```python
@abstractmethod
async def process_media(self, file_path: str, mime_type: str, caption: str, bot_id: str) -> ProcessingResult:
    """Subclass implements ONLY this: actual AI/conversion logic."""
    ...
```

Affected subclasses (update signature; processors other than `ImageVisionProcessor` can ignore `bot_id`):
- `StubSleepProcessor` (and its subclasses: `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`)
- `CorruptMediaProcessor`, `UnsupportedMediaProcessor`
- `ImageVisionProcessor` (in new `image_vision_processor.py`)

### 3) Image Data Loading (Event-Loop Safe)
Inside `ImageVisionProcessor.process_media()`:
1. Read image bytes from `file_path`.
2. Base64-encode those bytes into a raw base64 string.

Event-loop safety requirement:
- Offload file read and base64 encoding from the event loop using `asyncio.to_thread(...)`.

### 4) Provider Resolution and Moderation Call
`ImageVisionProcessor` must resolve moderation provider from bot configuration using factory-based resolution:
- `await create_model_provider(bot_id, "media_processing", "image_moderation")`

Rules:
- Validate that resolved provider implements `ImageModerationProvider`.
- Do not hardcode provider/model/API key path in processor.
- Provider uses `openai` SDK directly (no LangChain wrapper).
- SDK call must stay async.

Provider contract update:
- `ImageModerationProvider.moderate_image(base64_image: str, mime_type: str) -> ModerationResult`
- `OpenAiModerationProvider.moderate_image(base64_image: str, mime_type: str) -> ModerationResult`

Input payload shape:
- Construct data URI internally in provider:
  - `data_uri = f"data:{mime_type};base64,{base64_image}"`
- Send exact moderation input structure:
  - `[{"type": "image_url", "image_url": {"url": data_uri}}]`

Return handling:
- `OpenAiModerationProvider` returns normalized `ModerationResult`.
- `ImageVisionProcessor` logs `moderation_result.model_dump()`.

### 5) Error Handling Strategy
If moderation/provider/config resolution throws:
- Do not catch inside `ImageVisionProcessor.process_media()` for manual fallback content.
- Let exception bubble to `BaseMediaProcessor.process_job`.
- Rely on existing centralized `_handle_unhandled_exception` fallback behavior.

### 6) Logging Requirements
- In `OpenAiModerationProvider.moderate_image()`: log raw SDK response (debug visibility).
- In `ImageVisionProcessor.process_media()`: on success, log normalized moderation dictionary via `logger.info(moderation_result.model_dump())`.

### 7) Processing Result for This Phase
Return a stub-style `ProcessingResult` without embedding moderation payload in message content:
- `ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")`
