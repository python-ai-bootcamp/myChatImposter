# Implementation Tasks for Feature: imageTranscriptSupport

## Task Summary

| Task | Description | Status |
| --- | --- | --- |
| 1 | Refactor `LLMProvider` and `ChatCompletionProvider` | <PENDING> |
| 2 | Create `ImageTranscriptionProvider` ABC | <PENDING> |
| 3 | Create `OpenAiMixin` and update `OpenAiChatProvider` | <PENDING> |
| 4 | Implement `OpenAiImageTranscriptionProvider` | <PENDING> |
| 5 | Update `ConfigTier` and delete dead config code | <PENDING> |
| 6 | Create Settings and Config models for Image Transcription | <PENDING> |
| 7 | Update `DefaultConfigurations` and env vars | <PENDING> |
| 8 | Update `LLMConfigurations` model | <PENDING> |
| 9 | Update `get_bot_defaults` in `bot_management.py` | <PENDING> |
| 10 | Create `migrate_image_transcription.py` migration script | <PENDING> |
| 11 | Update `initialize_quota_and_bots.py` token menu | <PENDING> |
| 12 | Create `migrate_token_menu_image_transcription.py` hard reset | <PENDING> |
| 13 | Create `migrate_pool_definitions_gif.py` script | <PENDING> |
| 14 | Update `resolve_model_config` inside `resolver.py` | <PENDING> |
| 15 | Create `resolve_bot_language` inside `resolver.py` | <PENDING> |
| 16 | Refactor `create_model_provider` in `model_factory.py` | <PENDING> |
| 17 | Update `find_provider_class` in `provider_utils.py` | <PENDING> |
| 18 | Update `ProcessingResult` model in `infrastructure/models.py` | <PENDING> |
| 19 | Add `image/gif` to pool definitions | <PENDING> |
| 20 | Centralize caption formatting in `BaseMediaProcessor` | <PENDING> |
| 21 | Refactor `BaseMediaProcessor.process_job()` | <PENDING> |
| 22 | Update `_handle_unhandled_exception` in `BaseMediaProcessor` | <PENDING> |
| 23 | Update content definitions in error/stub processors | <PENDING> |
| 24 | Handle moderation flagged scenarios in `ImageVisionProcessor` | <PENDING> |
| 25 | Implement transcription invocation in `ImageVisionProcessor` | <PENDING> |
| 26 | Update `get_configuration_schema` in API router | <PENDING> |
| 27 | Create `GET /api/internal/bots/tiers` endpoint | <PENDING> |
| 28 | Update Frontend `EditPage.js` dynamic UI logic | <PENDING> |
| 29 | Implement provider architecture/callback tests | <PENDING> |
| 30 | Implement transcription normalization tests | <PENDING> |
| 31 | Implement processor format and timeout tests | <PENDING> |
| 32 | Update existing content strings and signature tests | <PENDING> |


## Implementation Checklist

### Phase 1: Provider Architecture Foundation

- [ ] **Task 1: Refactor `LLMProvider` and `ChatCompletionProvider`**
  - **Description**: Add abstract `LLMProvider` extending `BaseModelProvider`. Refactor `ChatCompletionProvider` to an empty type marker.
  - **Spec Sections**: Provider Architecture.
  - **Status**: <PENDING>

- [ ] **Task 2: Create `ImageTranscriptionProvider` ABC**
  - **Description**: Create `ImageTranscriptionProvider` in `model_providers/image_transcription.py` inheriting from `LLMProvider`. Define `transcribe_image` method.
  - **Spec Sections**: Provider Architecture.
  - **Status**: <PENDING>

- [ ] **Task 3: Create `OpenAiMixin` and update `OpenAiChatProvider`**
  - **Description**: Implement `OpenAiMixin` for `_build_llm_params()`. Refactor `OpenAiChatProvider` to use the mixin and migrate httpx logger to `main.py`.
  - **Spec Sections**: Provider Architecture.
  - **Status**: <PENDING>

- [ ] **Task 4: Implement `OpenAiImageTranscriptionProvider`**
  - **Description**: Target `model_providers/openAiImageTranscription.py` and implement `OpenAiImageTranscriptionProvider` with proper constructor-time init and multimodal `ainvoke`.
  - **Spec Sections**: Provider Architecture, OpenAI Vision Parameter.
  - **Status**: <PENDING>


### Phase 2: Configuration & Models

- [ ] **Task 5: Update `ConfigTier` and delete dead config code**
  - **Description**: Add `"image_transcription"` to `ConfigTier` literal in `config_models.py`. Delete `LLMProviderSettings`/`LLMProviderConfig`.
  - **Spec Sections**: Configuration, New Configuration Tier Checklist, Deployment Checklist.
  - **Status**: <PENDING>

- [ ] **Task 6: Create Settings and Config models for Image Transcription**
  - **Description**: Add `ImageTranscriptionProviderSettings` and `ImageTranscriptionProviderConfig` extending Chat classes in `config_models.py`.
  - **Spec Sections**: Configuration, Provider Architecture.
  - **Status**: <PENDING>

- [ ] **Task 7: Update `DefaultConfigurations` and env vars**
  - **Description**: Add default model configs and explicit fallback values for `DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE` etc.
  - **Spec Sections**: Deployment Checklist.
  - **Status**: <PENDING>

- [ ] **Task 8: Update `LLMConfigurations` model**
  - **Description**: Define `image_transcription` as a strictly required field using `Field(...)`.
  - **Spec Sections**: Deployment Checklist.
  - **Status**: <PENDING>

- [ ] **Task 9: Update `get_bot_defaults` in `bot_management.py`**
  - **Description**: Include `image_transcription` tier within the default instantiation.
  - **Spec Sections**: Deployment Checklist.
  - **Status**: <PENDING>


### Phase 3: Database & Migrations

- [ ] **Task 10: Create `migrate_image_transcription.py` migration script**
  - **Description**: Add new script targeting `COLLECTION_BOT_CONFIGURATIONS` to loop existing bot configs and append missing `image_transcription`.
  - **Spec Sections**: Deployment Checklist.
  - **Status**: <PENDING>

- [ ] **Task 11: Update `initialize_quota_and_bots.py` token menu**
  - **Description**: Extend default `token_menu` template for quota init with the pricing entry for the `image_transcription` tier.
  - **Spec Sections**: Configuration, Deployment Checklist.
  - **Status**: <PENDING>

- [ ] **Task 12: Create `migrate_token_menu_image_transcription.py` hard reset**
  - **Description**: Hard delete and recreate the `global_configurations` document with the updated `token_menu` 3-tier menu.
  - **Spec Sections**: Deployment Checklist.
  - **Status**: <PENDING>

- [ ] **Task 13: Create `migrate_pool_definitions_gif.py` script**
  - **Description**: Hard delete the `_mediaProcessorDefinitions` MongoDB doc to enforce GIF support pool recreation on next boot.
  - **Spec Sections**: Processing Flow.
  - **Status**: <PENDING>


### Phase 4: Flow Resolvers & Provider Factory

- [ ] **Task 14: Update `resolve_model_config` inside `resolver.py`**
  - **Description**: Add python typing `@overload` for `image_transcription` and mapping return.
  - **Spec Sections**: Configuration, New Configuration Tier Checklist.
  - **Status**: <PENDING>

- [ ] **Task 15: Create `resolve_bot_language` inside `resolver.py`**
  - **Description**: Create function wrapped fully in bare `try/except` avoiding any crashes and returning `"en"` on failures.
  - **Spec Sections**: Configuration, Transcription.
  - **Status**: <PENDING>

- [ ] **Task 16: Refactor `create_model_provider` in `model_factory.py`**
  - **Description**: Switch factory to a unified `isinstance(provider, LLMProvider)` token tracking approach.
  - **Spec Sections**: Provider Architecture.
  - **Status**: <PENDING>

- [ ] **Task 17: Update `find_provider_class` in `provider_utils.py`**
  - **Description**: Add `obj.__module__ == module.__name__` check logic. Add documented clarification comment.
  - **Spec Sections**: Provider Architecture.
  - **Status**: <PENDING>


### Phase 5: Media Processors Refactoring

- [ ] **Task 18: Update `ProcessingResult` model in `infrastructure/models.py`**
  - **Description**: Add `unprocessable_media: bool = False` indicating failure to transcribe meaning.
  - **Spec Sections**: Processing Flow.
  - **Status**: <PENDING>

- [ ] **Task 19: Add `image/gif` to pool definitions**
  - **Description**: Update `DEFAULT_POOL_DEFINITIONS` within `services/media_processing_service.py` extending the MIME pool list.
  - **Spec Sections**: Processing Flow.
  - **Status**: <PENDING>

- [ ] **Task 20: Centralize caption formatting in `BaseMediaProcessor`**
  - **Description**: Strip `caption` from all `process_media` signatures across classes and construct a pure standalone `format_processing_result` helper function inside `base.py`.
  - **Spec Sections**: Output Format.
  - **Status**: <PENDING>

- [ ] **Task 21: Refactor `BaseMediaProcessor.process_job()`**
  - **Description**: Drop-in the provided snippet with updated prefix injection execution and generic outcome unconditional formatting.
  - **Spec Sections**: Output Format.
  - **Status**: <PENDING>

- [ ] **Task 22: Update `_handle_unhandled_exception` in `BaseMediaProcessor`**
  - **Description**: Adjust default generic string formatting inside the global exception handler logic block.
  - **Spec Sections**: Output Format.
  - **Status**: <PENDING>

- [ ] **Task 23: Update content definitions in error/stub processors**
  - **Description**: Remove brackets and redundant prefix formatting from target processor returns (`CorruptMediaProcessor`, `UnsupportedMediaProcessor`, etc.).
  - **Spec Sections**: Output Format.
  - **Status**: <PENDING>


### Phase 6: Image Vision Processor Implementation

- [ ] **Task 24: Handle moderation flagged scenarios in `ImageVisionProcessor`**
  - **Description**: If `flagged == True`, trigger static short content reply and trigger `unprocessable_media`.
  - **Spec Sections**: Processing Flow.
  - **Status**: <PENDING>

- [ ] **Task 25: Implement transcription invocation in `ImageVisionProcessor`**
  - **Description**: When `flagged == False`, look up bot language, invoke `transcribe_image`, applying spec's string structural normalization rules safely.
  - **Spec Sections**: Transcription.
  - **Status**: <PENDING>


### Phase 7: Frontend & API Updates

- [ ] **Task 26: Update `get_configuration_schema` in API router**
  - **Description**: Update dynamic loop fetching properties directly plus modify schema titles appropriately.
  - **Spec Sections**: Configuration, New Configuration Tier Checklist.
  - **Status**: <PENDING>

- [ ] **Task 27: Create `GET /api/internal/bots/tiers` endpoint**
  - **Description**: Route returning list structure mapping derived from `LLMConfigurations.model_fields.keys()`.
  - **Spec Sections**: New Configuration Tier Checklist.
  - **Status**: <PENDING>

- [ ] **Task 28: Update Frontend `EditPage.js` dynamic UI logic**
  - **Description**: Fetch tier API instead of hardcoded arrays. Add `"image_transcription"` element containing `"detail"` inside `uiSchema`.
  - **Spec Sections**: New Configuration Tier Checklist.
  - **Status**: <PENDING>


### Phase 8: Tests

- [ ] **Task 29: Implement provider architecture/callback tests**
  - **Description**: Verify detail param omissions via kwarg extraction and `BaseChatModel` memory ref tracking.
  - **Spec Sections**: Test Expectations.
  - **Status**: <PENDING>

- [ ] **Task 30: Implement transcription normalization tests**
  - **Description**: Verify the specific mapping behaviours required when unwrapping nested Openai structures.
  - **Spec Sections**: Test Expectations.
  - **Status**: <PENDING>

- [ ] **Task 31: Implement processor format and timeout tests**
  - **Description**: Test new timeout structures, `job.placeholder_message` interaction, and Unprocessable boolean rules output formats.
  - **Spec Sections**: Test Expectations.
  - **Status**: <PENDING>

- [ ] **Task 32: Update existing content strings and signature tests**
  - **Description**: Mutate existing integration assertions expecting the old internal layout, update bot_id index signature test.
  - **Spec Sections**: Test Expectations.
  - **Status**: <PENDING>
