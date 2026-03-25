# Implementation Tasks: imageTranscriptSupport

## Task Summary Table

| Task ID | Description | Status |
|---------|-------------|--------|
| T1 | Add `image_transcription` to ConfigTier Literal type | <PENDING> |
| T2 | Create ImageTranscriptionProviderSettings class | <PENDING> |
| T3 | Create ImageTranscriptionProviderConfig class | <PENDING> |
| T4 | Update LLMConfigurations with image_transcription field | <PENDING> |
| T5 | Extend DefaultConfigurations with image_transcription settings | <PENDING> |
| T6 | Update get_bot_defaults to include image_transcription tier | <PENDING> |
| T7 | Add resolve_model_config overload for image_transcription tier | <PENDING> |
| T8 | Create resolve_bot_language function in resolver.py | <PENDING> |
| T9 | Update token_menu with image_transcription pricing | <PENDING> |
| T10 | Update get_configuration_schema for dynamic tier extraction | <PENDING> |
| T11 | Add unprocessable_media field to ProcessingResult | <PENDING> |
| T12 | Add image/gif to DEFAULT_POOL_DEFINITIONS | <PENDING> |
| T13 | Create migrate_pool_definitions_gif.py migration script | <PENDING> |
| T14 | Create ImageTranscriptionProvider abstract class | <PENDING> |
| T15 | Create OpenAiImageTranscriptionProvider concrete class | <PENDING> |
| T16 | Add LLMProvider abstract class to model_providers/base.py | <PENDING> |
| T17 | Refactor ChatCompletionProvider as empty type-marker | <PENDING> |
| T18 | Define OpenAiMixin for shared OpenAI logic | <PENDING> |
| T19 | Refactor OpenAiChatProvider to use OpenAiMixin | <PENDING> |
| T20 | Add module filter to find_provider_class | <PENDING> |
| T21 | Update create_model_provider return type and logic | <PENDING> |
| T22 | Implement format_processing_result function | <PENDING> |
| T23 | Remove caption parameter from process_media signature | <PENDING> |
| T24 | Update BaseMediaProcessor.process_job with new logic | <PENDING> |
| T25 | Update BaseMediaProcessor._handle_unhandled_exception | <PENDING> |
| T26 | Update CorruptMediaProcessor content format | <PENDING> |
| T27 | Update UnsupportedMediaProcessor content format | <PENDING> |
| T28 | Update StubSleepProcessor content format | <PENDING> |
| T29 | Update ImageVisionProcessor with transcription flow | <PENDING> |
| T30 | Create migrate_image_transcription.py migration script | <PENDING> |
| T31 | Update initialize_quota_and_bots.py with image_transcription tier | <PENDING> |
| T32 | Create migrate_token_menu_image_transcription.py script | <PENDING> |
| T33 | Delete unused LLMProviderSettings and LLMProviderConfig | <PENDING> |
| T34 | Add GET /api/internal/bots/tiers endpoint | <PENDING> |
| T35 | Update EditPage.js to fetch tiers dynamically | <PENDING> |
| T36 | Add image_transcription to EditPage.js uiSchema | <PENDING> |
| T37 | Add tests per spec section 5 | <PENDING> |

---

## Implementation Tasks

### T1: Add `image_transcription` to ConfigTier Literal type
**Spec Reference:** Requirements / Configuration, Section 4 / New Configuration Tier Checklist item 1  
**File:** `config_models.py`  
**Details:** Add `"image_transcription"` to ConfigTier Literal and add comment about this being the ONLY place where tier keys are defined.

---

### T2: Create ImageTranscriptionProviderSettings class
**Spec Reference:** Requirements / Configuration  
**File:** `config_models.py`  
**Details:** Create class inheriting from ChatCompletionProviderSettings with `detail: Literal["low", "high", "original", "auto"] = "auto"` field.

---

### T3: Create ImageTranscriptionProviderConfig class
**Spec Reference:** Requirements / Configuration  
**File:** `config_models.py`  
**Details:** Create class extending ChatCompletionProviderConfig with redefined `provider_config: ImageTranscriptionProviderSettings`.

---

### T4: Update LLMConfigurations with image_transcription field
**Spec Reference:** Requirements / Configuration  
**File:** `config_models.py`  
**Details:** Add `image_transcription: ImageTranscriptionProviderConfig = Field(...)` as required field.

---

### T5: Extend DefaultConfigurations with image_transcription settings
**Spec Reference:** Requirements / Configuration, Section 3 / Deployment Checklist item 2  
**File:** `config_models.py`  
**Details:** Add `model_provider_name_image_transcription = "openAiImageTranscription"`, `os.getenv("DEFAULT_MODEL_IMAGE_TRANSCRIPTION", "gpt-5-mini")`, `float(os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE", "0.05"))`, `os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT", "minimal")`.

---

### T6: Update get_bot_defaults to include image_transcription tier
**Spec Reference:** Requirements / Configuration, Section 3 / Deployment Checklist item 3  
**File:** `routers/bot_management.py`  
**Details:** Add image_transcription to LLMConfigurations in get_bot_defaults using ImageTranscriptionProviderConfig and DefaultConfigurations.

---

### T7: Add resolve_model_config overload for image_transcription tier
**Spec Reference:** Requirements / Configuration, Section 4 / New Configuration Tier Checklist item 2  
**File:** `services/resolver.py`  
**Details:** Add @overload for Literal["image_transcription"] returning ImageTranscriptionProviderConfig, and implement elif branch. Import ImageTranscriptionProviderConfig.

---

### T8: Create resolve_bot_language function in resolver.py
**Spec Reference:** Requirements / Configuration  
**File:** `services/resolver.py`  
**Details:** Create function that fetches language_code from bot's UserDetails config. Must use bare try/except Exception: return "en" block - never raise errors.

---

### T9: Update token_menu with image_transcription pricing
**Spec Reference:** Requirements / Configuration  
**File:** `scripts/migrations/initialize_quota_and_bots.py`, `scripts/migrations/migrate_token_menu_image_transcription.py`  
**Details:** Add image_transcription tier with pricing: input_tokens: 0.25, cached_input_tokens: 0.025, output_tokens: 2.0.

---

### T10: Update get_configuration_schema for dynamic tier extraction
**Spec Reference:** Requirements / Configuration, Section 4 / New Configuration Tier Checklist item 3  
**File:** `routers/bot_management.py`  
**Details:** Change hardcoded list to dynamic iteration: `for prop_name in llm_configs_defs['properties'].keys():`. Apply reasoning_effort title patches to both ChatCompletionProviderSettings AND ImageTranscriptionProviderSettings.

---

### T11: Add unprocessable_media field to ProcessingResult
**Spec Reference:** Requirements / Processing Flow  
**File:** `infrastructure/models.py`  
**Details:** Add `unprocessable_media: bool = False` to ProcessingResult dataclass with docstring explaining semantic.

---

### T12: Add image/gif to DEFAULT_POOL_DEFINITIONS
**Spec Reference:** Requirements / Processing Flow  
**File:** `services/media_processing_service.py`  
**Details:** Add "image/gif" to ImageVisionProcessor mime types list in DEFAULT_POOL_DEFINITIONS.

---

### T13: Create migrate_pool_definitions_gif.py migration script
**Spec Reference:** Requirements / Processing Flow  
**File:** `scripts/migrations/migrate_pool_definitions_gif.py`  
**Details:** Create migration script that deletes _mediaProcessorDefinitions document from MongoDB configurations collection to force pool recreation with GIF support.

---

### T14: Create ImageTranscriptionProvider abstract class
**Spec Reference:** Requirements / Transcription, Technical Details / Provider Architecture  
**File:** `model_providers/image_transcription.py` (new file)  
**Details:** Create abstract class extending LLMProvider with abstract async method `transcribe_image(base64_image, mime_type, language_code) -> str`.

---

### T15: Create OpenAiImageTranscriptionProvider concrete class
**Spec Reference:** Requirements / Transcription, Technical Details / Provider Architecture  
**File:** `model_providers/openAiImageTranscription.py` (new file)  
**Details:** Implement provider extending ImageTranscriptionProvider and OpenAiMixin. Use constructor-time initialization (ChatOpenAI in __init__). Implement transcribe_image with multimodal message, detail parameter handling, and response normalization.

---

### T16: Add LLMProvider abstract class to model_providers/base.py
**Spec Reference:** Technical Details / Provider Architecture  
**File:** `model_providers/base.py`  
**Details:** Create abstract class inheriting from BaseModelProvider with abstract method `get_llm() -> BaseChatModel`. Add comment to _resolve_api_key that it must remain strictly synchronous.

---

### T17: Refactor ChatCompletionProvider as empty type-marker
**Spec Reference:** Technical Details / Provider Architecture  
**File:** `model_providers/chat_completion.py`  
**Details:** Change to inherit from LLMProvider, remove @abstractmethod and abc imports, replace class body with `pass`.

---

### T18: Define OpenAiMixin for shared OpenAI logic
**Spec Reference:** Technical Details / Provider Architecture  
**File:** New mixin class in appropriate provider module  
**Details:** Create OpenAiMixin with _build_llm_params() method containing shared logic (model_dump, pop custom fields, resolve API key, filter None-valued fields).

---

### T19: Refactor OpenAiChatProvider to use OpenAiMixin
**Spec Reference:** Technical Details / Provider Architecture  
**File:** `model_providers/openAi.py`  
**Details:** Refactor to use OpenAiMixin. Remove print() debug statements. Move httpx logger config to main.py. Use constructor-time initialization (ChatOpenAI in __init__, store as self._llm). get_llm() returns self._llm.

---

### T20: Add module filter to find_provider_class
**Spec Reference:** Technical Details / Provider Architecture  
**File:** `utils/provider_utils.py`  
**Details:** Add `obj.__module__ == module.__name__` filter in getmembers loop. Keep existing not inspect.isabstract(obj) check.

---

### T21: Update create_model_provider return type and logic
**Spec Reference:** Technical Details / Provider Architecture  
**File:** `services/model_factory.py`  
**Details:** Update return type annotation to Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider]. Refactor to use isinstance(provider, LLMProvider) branch with ChatCompletionProvider subtype check.

---

### T22: Implement format_processing_result function
**Spec Reference:** Requirements / Output Format  
**File:** `media_processors/base.py`  
**Details:** Implement as module-level pure function. Unconditionally wrap content in brackets. Append caption if non-empty string.

---

### T23: Remove caption parameter from process_media signature
**Spec Reference:** Requirements / Output Format  
**File:** `media_processors/base.py` and all 7 subclasses  
**Details:** Update BaseMediaProcessor and all 7 subclasses to new signature: `async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:`

---

### T24: Update BaseMediaProcessor.process_job with new logic
**Spec Reference:** Requirements / Output Format  
**File:** `media_processors/base.py`  
**Details:** Implement full refactored process_job per spec snippet: extract caption from placeholder_message, handle timeout with unprocessable_media=True, prefix injection logic, format with format_processing_result, proper persistence and archive flow.

---

### T25: Update BaseMediaProcessor._handle_unhandled_exception
**Spec Reference:** Requirements / Output Format  
**File:** `media_processors/base.py`  
**Details:** Set unprocessable_media=True, change content to "Media processing failed" (no brackets), use format_processing_result first before persistence.

---

### T26: Update CorruptMediaProcessor content format
**Spec Reference:** Requirements / Output Format  
**File:** `media_processors/error_processors.py`  
**Details:** Return `ProcessingResult(content=f"Corrupted {media_type} media could not be downloaded", failed_reason=..., unprocessable_media=True)` - no caption, no brackets. Preserve media_type derivation logic.

---

### T27: Update UnsupportedMediaProcessor content format
**Spec Reference:** Requirements / Output Format  
**File:** `media_processors/error_processors.py`  
**Details:** Return `ProcessingResult(content=f"Unsupported media type: {mime_type}", failed_reason=..., unprocessable_media=True)` - no caption, no brackets.

---

### T28: Update StubSleepProcessor content format
**Spec Reference:** Requirements / Output Format  
**File:** `media_processors/stub_processors.py`  
**Details:** Return `ProcessingResult(content=f"multimedia message with guid='{...}'")` - no "Transcripted" phrasing, no brackets. Also update AudioTranscriptionProcessor, VideoDescriptionProcessor, DocumentProcessor.

---

### T29: Update ImageVisionProcessor with transcription flow
**Spec Reference:** Requirements / Transcription, Processing Flow  
**File:** `media_processors/image_vision_processor.py`  
**Details:** After moderation: if flagged return unprocessable_media=True with safety guidelines content. If not flagged: call resolve_bot_language inside the branch, then use image_transcription tier with create_model_provider, call transcribe_image with language_code, handle response normalization.

---

### T30: Create migrate_image_transcription.py migration script
**Spec Reference:** Section 3 / Deployment Checklist item 1  
**File:** `scripts/migrations/migrate_image_transcription.py`  
**Details:** Iterate existing bot configs, add image_transcription tier where missing using COLLECTION_BOT_CONFIGURATIONS and db_schema constants.

---

### T31: Update initialize_quota_and_bots.py with image_transcription tier
**Spec Reference:** Section 3 / Deployment Checklist item 5  
**File:** `scripts/migrations/initialize_quota_and_bots.py`  
**Details:** Add image_transcription to token_menu (3 tiers total: high, low, image_transcription). Add comment that image_moderation is intentionally omitted.

---

### T32: Create migrate_token_menu_image_transcription.py script
**Spec Reference:** Section 3 / Deployment Checklist item 6  
**File:** `scripts/migrations/migrate_token_menu_image_transcription.py`  
**Details:** Hard reset strategy: delete existing token_menu document and re-insert full 3-tier menu. Use db_schema constants.

---

### T33: Delete unused LLMProviderSettings and LLMProviderConfig
**Spec Reference:** Section 3 / Deployment Checklist item 10  
**File:** `config_models.py`  
**Details:** Remove dead code LLMProviderSettings and LLMProviderConfig classes.

---

### T34: Add GET /api/internal/bots/tiers endpoint
**Spec Reference:** Section 4 / New Configuration Tier Checklist item 4  
**File:** `routers/bot_management.py`  
**Details:** Create new endpoint returning available tiers by reading LLMConfigurations.model_fields.keys().

---

### T35: Update EditPage.js to fetch tiers dynamically
**Spec Reference:** Section 4 / New Configuration Tier Checklist item 4  
**File:** `frontend/src/pages/EditPage.js`  
**Details:** Fetch from new endpoint during fetchData, store in component state. Replace hardcoded tier arrays (line 135 and line 229) with dynamic list.

---

### T36: Add image_transcription to EditPage.js uiSchema
**Spec Reference:** Section 4 / New Configuration Tier Checklist item 5  
**File:** `frontend/src/pages/EditPage.js`  
**Details:** Add fourth entry to llm_configs uiSchema with title "Image Transcription Model", include provider_config with api_key_source, reasoning_effort, seed, AND detail field with title "Image Detail Level".

---

### T37: Add tests per spec section 5
**Spec Reference:** Section 5 / Test Expectations  
**File:** Test files  
**Details:** Add tests for: detail filtering, callback continuity, transcription normalization (all branches), flagged moderation returns correct ProcessingResult, format_processing_result behavior, caption handling, timeout returns unprocessable_media=True, unit-level process_media returns unbracketed content, integration-level process_job returns formatted string, update tests for renamed content strings, update test_process_media_bot_id_signature test.

---

## Implementation Notes

- All migration scripts must use `infrastructure/db_schema.py` constants (no hardcoded collection names)
- resolve_bot_language must never raise - always fallback to "en"
- image_moderation should NOT be in token_menu (no token cost calculation)
- Migration window risk: un-migrated bots will return 500 error during GET /{bot_id}
