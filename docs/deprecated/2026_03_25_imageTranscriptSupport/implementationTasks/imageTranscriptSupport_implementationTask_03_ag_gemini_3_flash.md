# Implementation Tasks for Image Transcription Support

| Task ID | Component | Description | Status |
| :--- | :--- | :--- | :--- |
| 1 | Provider Architecture | Define `LLMProvider` and `ImageTranscriptionProvider` abstract bases. | <PENDING> |
| 2 | Provider Architecture | Implement `OpenAiMixin` and refactor `OpenAiChatProvider`. | <PENDING> |
| 3 | Provider Architecture | Implement `OpenAiImageTranscriptionProvider` with normalization. | <PENDING> |
| 4 | Configuration | Update `config_models.py` (Tiers, Settings, Configs, Defaults). | <PENDING> |
| 5 | Resolver | Update `resolve_model_config` and implement `resolve_bot_language`. | <PENDING> |
| 6 | Factory | Refactor `create_model_provider` for polymorphic token tracking. | <PENDING> |
| 7 | Utils | Update `find_provider_class` with module filter defence. | <PENDING> |
| 8 | Media Processing | Update `ProcessingResult` model with `unprocessable_media`. | <PENDING> |
| 9 | Media Processing | Refactor `BaseMediaProcessor.process_job` lifecycle and formatting. | <PENDING> |
| 10 | Media Processing | Implement GIF support in `ImageVisionProcessor` and defaults. | <PENDING> |
| 11 | Media Processing | Update `ImageVisionProcessor.process_media` with transcription logic. | <PENDING> |
| 12 | Media Processing | Update signature of all 7 `process_media` subclasses and return raw content. | <PENDING> |
| 13 | API/Frontend | Add `/api/internal/bots/tiers` endpoint and dynamic schema updates. | <PENDING> |
| 14 | API/Frontend | Update `EditPage.js` to use dynamic tiers and new `uiSchema` for transcription. | <PENDING> |
| 15 | Migrations | Create `migrate_image_transcription.py` (bot configs). | <PENDING> |
| 16 | Migrations | Create `migrate_token_menu_image_transcription.py` (global reset). | <PENDING> |
| 17 | Migrations | Create `migrate_pool_definitions_gif.py` (force GIF recreation). | <PENDING> |
| 18 | Verification | Update existing tests and add integration tests for end-to-end flow. | <PENDING> |

---

## Detailed Task Descriptions

### 1. Define Provider Base Classes
- **Description:** Introduce `LLMProvider` in `model_providers/base.py` and `ImageTranscriptionProvider` in `model_providers/image_transcription.py`. Refactor `ChatCompletionProvider` to be a type marker.
- **Spec Section:** [Provider Architecture]

### 2. Implement OpenAI Mixin & Refactor Chat Provider
- **Description:** Extract shared OpenAI logic into `OpenAiMixin`. Refactor `OpenAiChatProvider` to use the mixin and constructor-time LLM initialization. Move `httpx` logging to startup.
- **Spec Section:** [Provider Architecture]

### 3. Implement OpenAI Image Transcription Provider
- **Description:** Create `OpenAiImageTranscriptionProvider`. Implement `transcribe_image` with multimodal payload construction and result normalization.
- **Spec Section:** [Transcription], [Provider Architecture]

### 4. Update Configuration Models
- **Description:** Update `ConfigTier`, `LLMConfigurations`, and `DefaultConfigurations` in `config_models.py`. Introduce `ImageTranscriptionProviderSettings/Config`.
- **Spec Section:** [Configuration], [Deployment Checklist], [New Configuration Tier Checklist]

### 5. Update Resolvers
- **Description:** Update `resolve_model_config` overloads. Implement `resolve_bot_language` with global state fetch and `Exception` fallback.
- **Spec Section:** [Configuration], [Transcription]

### 6. Refactor Model Factory
- **Description:** Refactor `create_model_provider` in `services/model_factory.py` to handle polymorphic provider types and unified token tracking using `LLMProvider`.
- **Spec Section:** [Transcription], [Provider Architecture]

### 7. Update Provider Utils
- **Description:** Add `obj.__module__ == module.__name__` filter to `find_provider_class` in `utils/provider_utils.py`.
- **Spec Section:** [Provider Architecture]

### 8. Update Processing Result Model
- **Description:** Add `unprocessable_media: bool = False` to `ProcessingResult` in `infrastructure/models.py`.
- **Spec Section:** [Processing Flow]

### 9. Refactor Base Media Processor Lifecycle
- **Description:** completely rewrite `BaseMediaProcessor.process_job()` with the provided snippet. Implement `format_processing_result` for centralized bracket wrapping and caption injection.
- **Spec Section:** [Output Format], [`BaseMediaProcessor.process_job()` Refactoring]

### 10. Implement GIF Support Pool
- **Description:** Update `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` to include `"image/gif"` for `ImageVisionProcessor`.
- **Spec Section:** [Processing Flow]

### 11. Update Image Vision Processor Logic
- **Description:** Implement the moderation-then-transcription flow in `ImageVisionProcessor.process_media`. Handle flagged images and resolved language input.
- **Spec Section:** [Processing Flow], [Transcription]

### 12. Update All Processor Signatures
- **Description:** Remove `caption` from `process_media` across all 7 affected processor subclasses and return raw, unbracketed content strings.
- **Spec Section:** [Output Format]

### 13. Dynamic Tier API and Schema Update
- **Description:** Add `GET /api/internal/bots/tiers` in `bot_management.py`. Update `get_configuration_schema` surgery loop to be dynamic and patch `ImageTranscriptionProviderSettings`.
- **Spec Section:** [Configuration], [New Configuration Tier Checklist]

### 14. Update Frontend UI
- **Description:** Update `EditPage.js` to fetch tiers from the new API. Update `uiSchema` to include `image_transcription` with correct collapsing templates and `detail` field.
- **Spec Section:** [New Configuration Tier Checklist]

### 15. Bot Configuration Migration
- **Description:** implement `migrate_image_transcription.py` to backfill the `image_transcription` tier in existing bot documents.
- **Spec Section:** [Deployment Checklist]

### 16. Global Token Menu Migration
- **Description:** Implement `migrate_token_menu_image_transcription.py` to perform a hard reset on the global `token_menu` configuration.
- **Spec Section:** [Deployment Checklist]

### 17. GIF Pool Definition Migration
- **Description:** Implement `migrate_pool_definitions_gif.py` to delete the existing MongoDB doc, forcing a recreation with GIF support on next boot.
- **Spec Section:** [Processing Flow]

### 18. Verification and Test Suite
- **Description:** implement new tests for `detail` filtering, callback continuity, normalization, and end-to-end processing. Update existing tests for new signatures and unbracketed results.
- **Spec Section:** [Test Expectations]
