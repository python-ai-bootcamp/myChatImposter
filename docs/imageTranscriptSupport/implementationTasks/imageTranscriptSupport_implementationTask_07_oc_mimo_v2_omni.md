# Implementation Task: Image Transcription Support
## Implementation Task ID: 07_oc_mimo_v2_omni
## Feature: imageTranscriptSupport
## Status: PENDING

### Summary Table
| Task ID | Description | Spec Section | Status |
|---------|-------------|--------------|--------|
| 1.1 | Add `image_transcription` to `ConfigTier` in `config_models.py` | Configuration (lines 11-20) | PENDING |
| 1.2 | Create `ImageTranscriptionProviderSettings` class with `detail` field | Configuration (lines 11-20) | PENDING |
| 1.3 | Create `ImageTranscriptionProviderConfig` extending `ChatCompletionProviderConfig` | Configuration (lines 11-20) | PENDING |
| 1.4 | Update `LLMConfigurations` with required `image_transcription` field | Configuration (lines 11-20) | PENDING |
| 1.5 | Update `DefaultConfigurations` with image transcription defaults | Configuration (lines 11-20) | PENDING |
| 1.6 | Update `resolve_model_config` with `image_transcription` tier | Configuration (lines 11-20) | PENDING |
| 1.7 | Create `resolve_bot_language` function in `services/resolver.py` | Configuration (lines 11-20) | PENDING |
| 1.8 | Update `global_configurations.token_menu` with `image_transcription` pricing | Configuration (lines 11-20) | PENDING |
| 1.9 | Update `get_configuration_schema` in `routers/bot_management.py` | Configuration (lines 11-20) | PENDING |
| 2.1 | Add `unprocessable_media: bool = False` to `ProcessingResult` in `infrastructure/models.py` | Processing Flow (lines 22-40) | PENDING |
| 2.2 | Update `ImageVisionProcessor` to add GIF support in `DEFAULT_POOL_DEFINITIONS` | Processing Flow (lines 22-40) | PENDING |
| 2.3 | Create migration script `migrate_pool_definitions_gif.py` | Processing Flow (lines 22-40) | PENDING |
| 2.4 | Implement moderation and transcription flow in `ImageVisionProcessor` | Processing Flow (lines 22-40) | PENDING |
| 2.5 | Handle flagged images in `ImageVisionProcessor` | Processing Flow (lines 22-40) | PENDING |
| 3.1 | Create `ImageTranscriptionProvider` abstract class in `model_providers/image_transcription.py` | Provider Architecture (lines 179-317) | PENDING |
| 3.2 | Create `OpenAiImageTranscriptionProvider` in `model_providers/openAiImageTranscription.py` | Provider Architecture (lines 179-317) | PENDING |
| 3.3 | Refactor `model_providers/base.py` to add `LLMProvider` abstract class | Provider Architecture (lines 179-317) | PENDING |
| 3.4 | Refactor `model_providers/chat_completion.py` to become empty type marker | Provider Architecture (lines 179-317) | PENDING |
| 3.5 | Create `OpenAiMixin` in `model_providers/openAi.py` | Provider Architecture (lines 179-317) | PENDING |
| 3.6 | Refactor `OpenAiChatProvider` to use `OpenAiMixin` and constructor-time initialization | Provider Architecture (lines 179-317) | PENDING |
| 3.7 | Update `create_model_provider` return type and logic | Provider Architecture (lines 179-317) | PENDING |
| 3.8 | Update `find_provider_class` in `utils/provider_utils.py` | Provider Architecture (lines 179-317) | PENDING |
| 4.1 | Remove `caption` parameter from `BaseMediaProcessor.process_media` and all subclasses | Output Format (lines 42-140) | PENDING |
| 4.2 | Implement `format_processing_result` function in `media_processors/base.py` | Output Format (lines 42-140) | PENDING |
| 4.3 | Refactor `BaseMediaProcessor.process_job` with new logic | Output Format (lines 42-140) | PENDING |
| 4.4 | Update `BaseMediaProcessor._handle_unhandled_exception` | Output Format (lines 42-140) | PENDING |
| 4.5 | Update processor content definitions (CorruptMediaProcessor, UnsupportedMediaProcessor, StubSleepProcessor) | Output Format (lines 42-140) | PENDING |
| 5.1 | Create migration script `migrate_image_transcription.py` | Deployment Checklist (lines 348-363) | PENDING |
| 5.2 | Create migration script `migrate_token_menu_image_transcription.py` | Deployment Checklist (lines 348-363) | PENDING |
| 5.3 | Update `initialize_quota_and_bots.py` | Deployment Checklist (lines 348-363) | PENDING |
| 5.4 | Delete dead code `LLMProviderSettings` and `LLMProviderConfig` | Deployment Checklist (lines 348-363) | PENDING |
| 6.1 | Add new API endpoint `GET /api/internal/bots/tiers` | New Configuration Tier Checklist (lines 364-378) | PENDING |
| 6.2 | Update `EditPage.js` to fetch dynamic tiers and add `image_transcription` UI | New Configuration Tier Checklist (lines 364-378) | PENDING |
| 7.1 | Add tests for `detail` parameter filtering | Test Expectations (lines 380-393) | PENDING |
| 7.2 | Add tests for callback continuity | Test Expectations (lines 380-393) | PENDING |
| 7.3 | Add tests for transcription normalization | Test Expectations (lines 380-393) | PENDING |
| 7.4 | Add tests for flagged images handling | Test Expectations (lines 380-393) | PENDING |
| 7.5 | Add tests for `format_processing_result` | Test Expectations (lines 380-393) | PENDING |
| 7.6 | Add tests for timeout handling | Test Expectations (lines 380-393) | PENDING |
| 7.7 | Update existing tests for new content strings and signatures | Test Expectations (lines 380-393) | PENDING |

---

## Detailed Tasks

### Phase 1: Configuration and Models
#### Task 1.1: Add `image_transcription` to `ConfigTier` in `config_models.py`
- **Description**: Update `ConfigTier` Literal type to include `"image_transcription"`.
- **Spec Reference**: Configuration (lines 11-20), New Configuration Tier Checklist (lines 364-378).
- **Status**: PENDING

#### Task 1.2: Create `ImageTranscriptionProviderSettings` class
- **Description**: Create a new class inheriting from `ChatCompletionProviderSettings` with `detail: Literal["low", "high", "original", "auto"] = "auto"` field.
- **Spec Reference**: Configuration (lines 11-20).
- **Status**: PENDING

#### Task 1.3: Create `ImageTranscriptionProviderConfig`
- **Description**: Create a new config class extending `ChatCompletionProviderConfig` and redefine `provider_config: ImageTranscriptionProviderSettings`.
- **Spec Reference**: Configuration (lines 11-20).
- **Status**: PENDING

#### Task 1.4: Update `LLMConfigurations` with required `image_transcription` field
- **Description**: Add `image_transcription: ImageTranscriptionProviderConfig = Field(..., title="Image Transcription Model")` to `LLMConfigurations`. Make it required field.
- **Spec Reference**: Configuration (lines 11-20), New Configuration Tier Checklist (lines 364-378).
- **Status**: PENDING

#### Task 1.5: Update `DefaultConfigurations` with image transcription defaults
- **Description**: Add `model_provider_name_image_transcription = "openAiImageTranscription"` and default model/temperature/reasoning_effort using environment variables with fallbacks.
- **Spec Reference**: Configuration (lines 11-20), Deployment Checklist (lines 348-363).
- **Status**: PENDING

#### Task 1.6: Update `resolve_model_config` with `image_transcription` tier
- **Description**: Add overload and implementation branch for `image_transcription` tier returning `ImageTranscriptionProviderConfig`.
- **Spec Reference**: Configuration (lines 11-20), New Configuration Tier Checklist (lines 364-378).
- **Status**: PENDING

#### Task 1.7: Create `resolve_bot_language` function
- **Description**: Create a function in `services/resolver.py` that fetches `language_code` from bot configuration, falling back to `"en"` on any error.
- **Spec Reference**: Configuration (lines 11-20), Transcription (lines 31-41).
- **Status**: PENDING

#### Task 1.8: Update `global_configurations.token_menu`
- **Description**: Add `image_transcription` tier with pricing: `input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`.
- **Spec Reference**: Configuration (lines 11-20), Deployment Checklist (lines 348-363).
- **Status**: PENDING

#### Task 1.9: Update `get_configuration_schema` in `routers/bot_management.py`
- **Description**: Update schema surgery loop to iterate dynamically over `llm_configs_defs['properties'].keys()` and apply `reasoning_effort` title patches to both `ChatCompletionProviderSettings` and `ImageTranscriptionProviderSettings`.
- **Spec Reference**: Configuration (lines 11-20), New Configuration Tier Checklist (lines 364-378).
- **Status**: PENDING

### Phase 2: Processing Flow Updates
#### Task 2.1: Add `unprocessable_media` field to `ProcessingResult`
- **Description**: Add `unprocessable_media: bool = False` with docstring to `ProcessingResult` dataclass in `infrastructure/models.py`.
- **Spec Reference**: Processing Flow (lines 22-40).
- **Status**: PENDING

#### Task 2.2: Update `ImageVisionProcessor` to add GIF support
- **Description**: Update `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` to include `"image/gif"` in `ImageVisionProcessor` mime types list.
- **Spec Reference**: Processing Flow (lines 22-40).
- **Status**: PENDING

#### Task 2.3: Create migration script `migrate_pool_definitions_gif.py`
- **Description**: Create script that deletes `_mediaProcessorDefinitions` document from MongoDB `configurations` collection to force recreation from updated defaults.
- **Spec Reference**: Processing Flow (lines 22-40), Deployment Checklist (lines 348-363).
- **Status**: PENDING

#### Task 2.4: Implement moderation and transcription flow
- **Description**: Update `ImageVisionProcessor.process_media` to call `resolve_bot_language`, then use `image_transcription` tier to get provider, call `transcribe_image`. Also need to update method signature to remove `caption` parameter (see Task 4.1).
- **Spec Reference**: Processing Flow (lines 22-40), Transcription (lines 31-41).
- **Status**: PENDING

#### Task 2.5: Handle flagged images
- **Description**: In `ImageVisionProcessor`, if `moderation_result.flagged == True`, return `ProcessingResult` with `unprocessable_media=True` and content `"cannot process image as it violates safety guidelines"`, `failed_reason=None`.
- **Spec Reference**: Processing Flow (lines 22-40).
- **Status**: PENDING

### Phase 3: Provider Architecture
#### Task 3.1: Create `ImageTranscriptionProvider` abstract class
- **Description**: Create new file `model_providers/image_transcription.py` with abstract class extending `LLMProvider` and declaring `async def transcribe_image(base64_image: str, mime_type: str, language_code: str) -> str`.
- **Spec Reference**: Provider Architecture (lines 179-317).
- **Status**: PENDING

#### Task 3.2: Create `OpenAiImageTranscriptionProvider`
- **Description**: Create new file `model_providers/openAiImageTranscription.py` with concrete implementation extending `ImageTranscriptionProvider` and `OpenAiMixin`. Implement `transcribe_image` method with multimodal `HumanMessage`, prompt injection, and response normalization.
- **Spec Reference**: Provider Architecture (lines 179-317).
- **Status**: PENDING

#### Task 3.3: Refactor `model_providers/base.py` to add `LLMProvider`
- **Description**: Define abstract `LLMProvider` class inheriting from `BaseModelProvider` with abstract `get_llm() -> BaseChatModel` method.
- **Spec Reference**: Provider Architecture (lines 179-317).
- **Status**: PENDING

#### Task 3.4: Refactor `model_providers/chat_completion.py` to empty type marker
- **Description**: Remove `get_llm` abstract method and `abc` imports, make `ChatCompletionProvider` inherit from `LLMProvider` with `pass` body.
- **Spec Reference**: Provider Architecture (lines 179-317).
- **Status**: PENDING

#### Task 3.5: Create `OpenAiMixin`
- **Description**: Create mixin in `model_providers/openAi.py` with `_build_llm_params()` method containing shared OpenAI kwargs building logic.
- **Spec Reference**: Provider Architecture (lines 179-317).
- **Status**: PENDING

#### Task 3.6: Refactor `OpenAiChatProvider` to use `OpenAiMixin`
- **Description**: Update `OpenAiChatProvider` to inherit from `OpenAiMixin`, use constructor-time initialization, remove duplicate logic and print statements. Move httpx logger configuration to application startup.
- **Spec Reference**: Provider Architecture (lines 179-317).
- **Status**: PENDING

#### Task 3.7: Update `create_model_provider`
- **Description**: Update return type annotation to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider]`. Refactor to use unified `isinstance(provider, LLMProvider)` branch for token tracking.
- **Spec Reference**: Provider Architecture (lines 179-317).
- **Status**: PENDING

#### Task 3.8: Update `find_provider_class`
- **Description**: Add `obj.__module__ == module.__name__` filter in `inspect.getmembers` loop.
- **Spec Reference**: Provider Architecture (lines 179-317).
- **Status**: PENDING

### Phase 4: Output Format Refactoring
#### Task 4.1: Remove `caption` parameter from `process_media`
- **Description**: Update `BaseMediaProcessor.process_media` and all 7 subclasses (`ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`) to remove `caption` parameter. Update abstract method signature.
- **Spec Reference**: Output Format (lines 42-140).
- **Status**: PENDING

#### Task 4.2: Implement `format_processing_result` function
- **Description**: Create module-level function in `media_processors/base.py` that wraps content in brackets and appends caption if non-empty.
- **Spec Reference**: Output Format (lines 42-140).
- **Status**: PENDING

#### Task 4.3: Refactor `BaseMediaProcessor.process_job`
- **Description**: Replace existing implementation with new logic including prefix injection, format processing, and updated error handling.
- **Spec Reference**: Output Format (lines 42-140).
- **Status**: PENDING

#### Task 4.4: Update `BaseMediaProcessor._handle_unhandled_exception`
- **Description**: Update to set `unprocessable_media=True`, change content from `"[Media processing failed]"` to `"Media processing failed"`, and call `format_processing_result` before persistence.
- **Spec Reference**: Output Format (lines 42-140).
- **Status**: PENDING

#### Task 4.5: Update processor content definitions
- **Description**: Update `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, and `StubSleepProcessor` to return content without brackets and with correct `unprocessable_media` flag.
- **Spec Reference**: Output Format (lines 42-140).
- **Status**: PENDING

### Phase 5: Deployment and Migration
#### Task 5.1: Create migration script `migrate_image_transcription.py`
- **Description**: Iterate existing bot configs in MongoDB and add `config_data.configurations.llm_configs.image_transcription` where missing.
- **Spec Reference**: Deployment Checklist (lines 348-363).
- **Status**: PENDING

#### Task 5.2: Create migration script `migrate_token_menu_image_transcription.py`
- **Description**: Delete existing `token_menu` document and re-insert full correct menu from scratch (hard reset).
- **Spec Reference**: Deployment Checklist (lines 348-363).
- **Status**: PENDING

#### Task 5.3: Update `initialize_quota_and_bots.py`
- **Description**: Include `image_transcription` tier in the `token_menu` dictionary.
- **Spec Reference**: Deployment Checklist (lines 348-363).
- **Status**: PENDING

#### Task 5.4: Delete dead code
- **Description**: Remove `LLMProviderSettings` and `LLMProviderConfig` from `config_models.py`.
- **Spec Reference**: Deployment Checklist (lines 348-363).
- **Status**: PENDING

### Phase 6: Frontend Updates
#### Task 6.1: Add new API endpoint `GET /api/internal/bots/tiers`
- **Description**: Create endpoint that returns available tiers by reading `LLMConfigurations.model_fields.keys()`.
- **Spec Reference**: New Configuration Tier Checklist (lines 364-378).
- **Status**: PENDING

#### Task 6.2: Update `EditPage.js`
- **Description**: Fetch dynamic tiers from new endpoint, replace hardcoded tier arrays, add `image_transcription` UI schema entry.
- **Spec Reference**: New Configuration Tier Checklist (lines 364-378).
- **Status**: PENDING

### Phase 7: Testing
#### Task 7.1: Add tests for `detail` parameter filtering
- **Description**: Verify `detail` is filtered from `ChatOpenAI(...)` constructor kwargs and only used in transcription payload.
- **Spec Reference**: Test Expectations (lines 380-393).
- **Status**: PENDING

#### Task 7.2: Add tests for callback continuity
- **Description**: Verify callback attachment in `create_model_provider` and transcription invocation use same LLM object reference.
- **Spec Reference**: Test Expectations (lines 380-393).
- **Status**: PENDING

#### Task 7.3: Add tests for transcription normalization
- **Description**: Test all branches: string content, content blocks, unsupported content type.
- **Spec Reference**: Test Expectations (lines 380-393).
- **Status**: PENDING

#### Task 7.4: Add tests for flagged images handling
- **Description**: Test that `moderation_result.flagged == True` returns correct `ProcessingResult`.
- **Spec Reference**: Test Expectations (lines 380-393).
- **Status**: PENDING

#### Task 7.5: Add tests for `format_processing_result`
- **Description**: Test bracket wrapping and caption appending logic.
- **Spec Reference**: Test Expectations (lines 380-393).
- **Status**: PENDING

#### Task 7.6: Add tests for timeout handling
- **Description**: Test that `asyncio.TimeoutError` returns `ProcessingResult` with `unprocessable_media=True`.
- **Spec Reference**: Test Expectations (lines 380-393).
- **Status**: PENDING

#### Task 7.7: Update existing tests
- **Description**: Update tests for new content strings and method signatures (e.g., `test_process_media_bot_id_signature`).
- **Spec Reference**: Test Expectations (lines 380-393).
- **Status**: PENDING