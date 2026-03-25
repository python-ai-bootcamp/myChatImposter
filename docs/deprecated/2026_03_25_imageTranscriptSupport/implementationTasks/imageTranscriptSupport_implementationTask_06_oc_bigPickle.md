# Implementation Tasks: imageTranscriptSupport

## Task Summary Table

| # | Task | Status |
|---|------|--------|
| 1 | Update `ProcessingResult` dataclass with `unprocessable_media` field | <PENDING> |
| 2 | Add GIF mime type to `DEFAULT_POOL_DEFINITIONS` in media_processing_service.py | <PENDING> |
| 3 | Create migration script to delete `_mediaProcessorDefinitions` for GIF support | <PENDING> |
| 4 | Create new `ImageTranscriptionProviderSettings` class in config_models.py | <PENDING> |
| 5 | Create new `ImageTranscriptionProviderConfig` class in config_models.py | <PENDING> |
| 6 | Update `ConfigTier` Literal with "image_transcription" | <PENDING> |
| 7 | Add `image_transcription` field to `LLMConfigurations` | <PENDING> |
| 8 | Update `DefaultConfigurations` with image_transcription settings and env vars | <PENDING> |
| 9 | Delete dead code `LLMProviderSettings` and `LLMProviderConfig` from config_models.py | <PENDING> |
| 10 | Add `resolve_bot_language` function to services/resolver.py | <PENDING> |
| 11 | Update `resolve_model_config` with image_transcription overload and implementation | <PENDING> |
| 12 | Create abstract `LLMProvider` base class in model_providers/base.py | <PENDING> |
| 13 | Refactor `ChatCompletionProvider` to empty type-marker inheriting from LLMProvider | <PENDING> |
| 14 | Create abstract `ImageTranscriptionProvider` class in model_providers/image_transcription.py | <PENDING> |
| 15 | Create `OpenAiMixin` class with shared `_build_llm_params()` logic | <PENDING> |
| 16 | Refactor `OpenAiChatProvider` to use `OpenAiMixin` and constructor-time LLM init | <PENDING> |
| 17 | Create `OpenAiImageTranscriptionProvider` class in model_providers/openAiImageTranscription.py | <PENDING> |
| 18 | Update `find_provider_class` in utils/provider_utils.py with module filter | <PENDING> |
| 19 | Update `create_model_provider` return type and unified isinstance logic | <PENDING> |
| 20 | Extract httpx logger config from providers to main.py startup | <PENDING> |
| 21 | Update `BaseMediaProcessor` abstract signature to remove `caption` parameter | <PENDING> |
| 22 | Implement `format_processing_result` helper function in media_processors/base.py | <PENDING> |
| 23 | Refactor `BaseMediaProcessor.process_job()` with full implementation per spec | <PENDING> |
| 24 | Update `BaseMediaProcessor._handle_unhandled_exception` with format call | <PENDING> |
| 25 | Update `CorruptMediaProcessor.process_media` with new content format | <PENDING> |
| 26 | Update `UnsupportedMediaProcessor.process_media` with new content format | <PENDING> |
| 27 | Update `StubSleepProcessor` and subclasses to remove caption from content | <PENDING> |
| 28 | Update `ImageVisionProcessor` to implement moderation → transcription flow | <PENDING> |
| 29 | Add `image_transcription` pricing to token_menu in migrate_token_menu_image_transcription.py | <PENDING> |
| 30 | Update `initialize_quota_and_bots.py` to include image_transcription tier | <PENDING> |
| 31 | Create migration script `migrate_image_transcription.py` | <PENDING> |
| 32 | Update `get_bot_defaults` in bot_management.py to include image_transcription | <PENDING> |
| 33 | Update `get_configuration_schema` schema surgery loop to iterate dynamically | <PENDING> |
| 34 | Update schema surgery to patch reasoning_effort for both ChatCompletionProviderSettings and ImageTranscriptionProviderSettings | <PENDING> |
| 35 | Add `GET /api/internal/bots/tiers` endpoint in bot_management.py | <PENDING> |
| 36 | Update EditPage.js to fetch tiers dynamically from new endpoint | <PENDING> |
| 37 | Add `image_transcription` uiSchema entry in EditPage.js | <PENDING> |
| 38 | Write tests for `detail` parameter filtering from ChatOpenAI kwargs | <PENDING> |
| 39 | Write tests for callback continuity between factory and transcription | <PENDING> |
| 40 | Write tests for transcription normalization (string, content blocks, unsupported) | <PENDING> |
| 41 | Write tests for flagged moderation returns unprocessable_media=True | <PENDING> |
| 42 | Write tests for format_processing_result with/without captions | <PENDING> |
| 43 | Write tests for asyncio.TimeoutError returns unprocessable_media=True | <PENDING> |
| 44 | Update existing tests for process_media return unbracketed content | <PENDING> |
| 45 | Add integration tests for final formatted output to bot queue | <PENDING> |
| 46 | Update existing tests for renamed content strings in error processors | <PENDING> |
| 47 | Update test_process_media_bot_id_signature to use dictionary key lookup | <PENDING> |

---

## Detailed Tasks

### Task 1: Update `ProcessingResult` dataclass with `unprocessable_media` field
**Spec Reference:** Processing Flow > Update `infrastructure/models.py`  
**Files:** `infrastructure/models.py`

Add `unprocessable_media: bool = False` to the `ProcessingResult` dataclass with docstring explaining semantic: *"True means the media could not be meaningfully transcribed, signaling `process_job` to skip prefix injection for the error payload."*

---

### Task 2: Add GIF mime type to `DEFAULT_POOL_DEFINITIONS` in media_processing_service.py
**Spec Reference:** Processing Flow > ImageVisionProcessor requirements  
**Files:** `services/media_processing_service.py`

Update `DEFAULT_POOL_DEFINITIONS` to include `"image/gif"` in the `ImageVisionProcessor` mime types list alongside JPEG, PNG, and WEBP.

---

### Task 3: Create migration script to delete `_mediaProcessorDefinitions` for GIF support
**Spec Reference:** Processing Flow > Migration script requirement  
**Files:** `scripts/migrations/migrate_pool_definitions_gif.py`

Create migration script that completely **deletes** the existing `_mediaProcessorDefinitions` document from the MongoDB `configurations` collection. On next server boot, the service will automatically recreate it from updated Python defaults.

---

### Task 4: Create new `ImageTranscriptionProviderSettings` class in config_models.py
**Spec Reference:** Configuration > ImageTranscriptionProviderSettings class  
**Files:** `config_models.py`

Create new class inheriting from `ChatCompletionProviderSettings`, adding the `detail: Literal["low", "high", "original", "auto"] = "auto"` field.

---

### Task 5: Create new `ImageTranscriptionProviderConfig` class in config_models.py
**Spec Reference:** Configuration > ImageTranscriptionProviderConfig class  
**Files:** `config_models.py`

Modify `ImageTranscriptionProviderConfig` to extend `ChatCompletionProviderConfig` and redefine `provider_config: ImageTranscriptionProviderSettings`.

---

### Task 6: Update `ConfigTier` Literal with "image_transcription"
**Spec Reference:** Configuration > ConfigTier update  
**Files:** `config_models.py`

Update `ConfigTier` to include `"image_transcription"`:
```python
ConfigTier = Literal["high", "low", "image_moderation", "image_transcription"]
```
Add comment: *"These two locations are the ONLY places in the code where the structure/keys of the tiers are defined."*

---

### Task 7: Add `image_transcription` field to `LLMConfigurations`
**Spec Reference:** Configuration > LLMConfigurations update  
**Files:** `config_models.py`

Add `image_transcription: ImageTranscriptionProviderConfig = Field(...)` as strictly required field. Add comment above class: *"These two locations are the ONLY places in the code where the structure/keys of the tiers are defined."*

---

### Task 8: Update `DefaultConfigurations` with image_transcription settings and env vars
**Spec Reference:** Deployment Checklist > DefaultConfigurations  
**Files:** `config_models.py`

Add:
- `model_provider_name_image_transcription = "openAiImageTranscription"`
- `model_image_transcription: str = os.getenv("DEFAULT_MODEL_IMAGE_TRANSCRIPTION", "gpt-5-mini")`
- `float(os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE", "0.05"))`
- `os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT", "minimal")`

---

### Task 9: Delete dead code `LLMProviderSettings` and `LLMProviderConfig` from config_models.py
**Spec Reference:** Deployment Checklist > Dead code removal  
**Files:** `config_models.py`

Remove the unused `LLMProviderSettings` and `LLMProviderConfig` classes entirely.

---

### Task 10: Add `resolve_bot_language` function to services/resolver.py
**Spec Reference:** Configuration > resolve_bot_language function  
**Files:** `services/resolver.py`

Create new resolving function that:
- Fetches `language_code` from bot's `UserDetails` configuration
- Uses `get_global_state().configurations_collection.find_one(...)` explicitly
- Falls back to `"en"` if document or field missing
- Wraps entire DB fetch block in bare `try/except Exception: return "en"` - must NEVER raise errors

---

### Task 11: Update `resolve_model_config` with image_transcription overload and implementation
**Spec Reference:** Configuration > resolve_model_config update  
**Files:** `services/resolver.py`

Add `@overload` for `"image_transcription"` returning `ImageTranscriptionProviderConfig` and add `elif` branch returning `ImageTranscriptionProviderConfig.model_validate(tier_data)`. Import `ImageTranscriptionProviderConfig` explicitly.

---

### Task 12: Create abstract `LLMProvider` base class in model_providers/base.py
**Spec Reference:** Provider Architecture > LLMProvider class  
**Files:** `model_providers/base.py`

Define new abstract base class `LLMProvider` inheriting from `BaseModelProvider` declaring abstract `get_llm() -> BaseChatModel` method. Add explicit comment in `_resolve_api_key()` defining it must remain strictly synchronous with no external I/O or async polling.

---

### Task 13: Refactor `ChatCompletionProvider` to empty type-marker inheriting from LLMProvider
**Spec Reference:** Provider Architecture > ChatCompletionProvider refactor  
**Files:** `model_providers/chat_completion.py`

Modify to inherit from `LLMProvider` instead of `BaseModelProvider`. Remove `@abstractmethod def get_llm(self)` declaration and `abc` imports. Replace class body with `pass` so it cleanly acts as empty type-marker.

---

### Task 14: Create abstract `ImageTranscriptionProvider` class in model_providers/image_transcription.py
**Spec Reference:** Provider Architecture > ImageTranscriptionProvider  
**Files:** `model_providers/image_transcription.py`

Create abstract class extending `LLMProvider` declaring `async def transcribe_image(base64_image: str, mime_type: str, language_code: str) -> str` as abstract method.

---

### Task 15: Create `OpenAiMixin` class with shared `_build_llm_params()` logic
**Spec Reference:** Provider Architecture > OpenAiMixin  
**Files:** `model_providers/openAi.py` (or separate file)

Define centralized `OpenAiMixin` containing only `_build_llm_params()` - the shared OpenAI kwargs building logic. Include comment clarifying it is designed strictly to be mixed into subclasses of `BaseModelProvider`.

---

### Task 16: Refactor `OpenAiChatProvider` to use `OpenAiMixin` and constructor-time LLM init
**Spec Reference:** Provider Architecture > OpenAiChatProvider refactor  
**Files:** `model_providers/openAi.py`

Refactor to:
- Use `OpenAiMixin` to reuse logic without duplicating
- Remove httpx logger configuration from `get_llm()` - move to main.py
- Remove print() debug statements
- Create `ChatOpenAI` instance inside `__init__` and store as `self._llm`
- Make `get_llm()` simply return `self._llm`

---

### Task 17: Create `OpenAiImageTranscriptionProvider` class in model_providers/openAiImageTranscription.py
**Spec Reference:** Provider Architecture > OpenAiImageTranscriptionProvider  
**Files:** `model_providers/openAiImageTranscription.py`

Create class extending `ImageTranscriptionProvider` and `OpenAiMixin`. In `__init__`:
- Call `self._build_llm_params()`
- Pop `detail` field: `self._detail = params.pop("detail", "auto")`
- Create `ChatOpenAI(**params)` and store as `self._llm`

Implement `transcribe_image`:
- Construct multimodal `HumanMessage` with text prompt incorporating `language_code` + `image_url` data URI + `detail`
- Invoke LLM via `ainvoke`
- Return normalized transcript string per normalization contract

---

### Task 18: Update `find_provider_class` in utils/provider_utils.py with module filter
**Spec Reference:** Provider Architecture > find_provider_class filter  
**Files:** `utils/provider_utils.py`

Add `obj.__module__ == module.__name__` filter in `inspect.getmembers` loop. Add documentation note clarifying this protects against edge-case concrete sibling imports. Ensure existing `not inspect.isabstract(obj)` check remains.

---

### Task 19: Update `create_model_provider` return type and unified isinstance logic
**Spec Reference:** Provider Architecture > create_model_provider refactor  
**Files:** `services/model_factory.py`

Update return type to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider]`. Implement unified `isinstance(provider, LLMProvider)` branch with `provider.get_llm()` for token tracking. For `ChatCompletionProvider`: return raw llm; for other LLMProviders: return provider wrapper directly.

---

### Task 20: Extract httpx logger config from providers to main.py startup
**Spec Reference:** Provider Architecture > httpx logger extraction  
**Files:** `main.py`, `model_providers/openAi.py`

Move httpx logger configuration from `OpenAiChatProvider.get_llm()` into main.py startup (after imports).

---

### Task 21: Update `BaseMediaProcessor` abstract signature to remove `caption` parameter
**Spec Reference:** Output Format > Caption removal  
**Files:** `media_processors/base.py`

Update abstract method signature from `process_media(self, file_path, mime_type, caption, bot_id)` to `process_media(self, file_path, mime_type, bot_id)`.

---

### Task 22: Implement `format_processing_result` helper function in media_processors/base.py
**Spec Reference:** Output Format > format_processing_result function  
**Files:** `media_processors/base.py`

Implement as module-level function that:
- Unconditionally wraps raw content in brackets `[<content>]`
- If `caption` is non-empty string: appends `\n[Caption: <caption_text>]`
- If `caption` is `None` or `""`: returns wrapped content as-is
- Must be pure function (no mutation of original arguments)

---

### Task 23: Refactor `BaseMediaProcessor.process_job()` with full implementation per spec
**Spec Reference:** Output Format > process_job refactoring  
**Files:** `media_processors/base.py`

Replace entire implementation with exhaustive snippet from spec:
1. Extract caption from `job.placeholder_message.content` once at start
2. Call `process_media` without caption parameter
3. Handle `asyncio.TimeoutError`: return `ProcessingResult(content="Processing timed out", failed_reason=..., unprocessable_media=True)`
4. Prefix injection: if not `unprocessable_media` and not `failed_reason`, prepend `{MediaType} Transcription: `
5. Format: `result.content = format_processing_result(result.content, caption)`
6. Persistence-first persistence
7. Archive to failed if `failed_reason` set
8. Best-effort delivery to bot queues

---

### Task 24: Update `BaseMediaProcessor._handle_unhandled_exception` with format call
**Spec Reference:** Output Format > _handle_unhandled_exception update  
**Files:** `media_processors/base.py`

Update to:
- Set `unprocessable_media=True`
- Change hardcoded content from `"[Media processing failed]"` to `"Media processing failed"`
- Call `format_processing_result` **first**, before `_persist_result_first` and `_archive_to_failed`
- Caption sourced from `job.placeholder_message.content`

---

### Task 25: Update `CorruptMediaProcessor.process_media` with new content format
**Spec Reference:** Output Format > CorruptMediaProcessor content  
**Files:** `media_processors/error_processors.py`

Return `ProcessingResult(content=f"Corrupted {media_type} media could not be downloaded", failed_reason=..., unprocessable_media=True)`. Preserve `media_type = mime_type.replace("media_corrupt_", "")` derivation. No caption, no brackets.

---

### Task 26: Update `UnsupportedMediaProcessor.process_media` with new content format
**Spec Reference:** Output Format > UnsupportedMediaProcessor content  
**Files:** `media_processors/error_processors.py`

Return `ProcessingResult(content=f"Unsupported media type: {mime_type}", failed_reason=..., unprocessable_media=True)`. No caption, no brackets.

---

### Task 27: Update `StubSleepProcessor` and subclasses to remove caption from content
**Spec Reference:** Output Format > StubSleepProcessor content  
**Files:** `media_processors/stub_processors.py`

Update all stub processors to return `ProcessingResult(content=f"{media_label} Transcription: multimedia message with guid='{...}'")`. Remove redundant "Transcripted" phrasing. `unprocessable_media` defaults to `False`.

---

### Task 28: Update `ImageVisionProcessor` to implement moderation → transcription flow
**Spec Reference:** Processing Flow > Transcription flow  
**Files:** `media_processors/image_vision_processor.py`

Implement full flow:
1. Load image as base64
2. Moderate image using `create_model_provider(bot_id, "media_processing", "image_moderation")`
3. If `moderation_result.flagged == True`: return `ProcessingResult(content="cannot process image as it violates safety guidelines", unprocessable_media=True)`
4. If `flagged == False`: call `resolve_bot_language(bot_id)` to get language
5. Create transcription provider: `create_model_provider(bot_id, "image_transcription", "image_transcription")`
6. Call `await provider.transcribe_image(base64_image, mime_type, language_code)`
7. Return result with transcription content

---

### Task 29: Add `image_transcription` pricing to token_menu in migrate_token_menu_image_transcription.py
**Spec Reference:** Deployment Checklist > migrate_token_menu_image_transcription.py  
**Files:** `scripts/migrations/migrate_token_menu_image_transcription.py`

Create migration script that:
- Completely deletes existing `token_menu` document
- Re-inserts full correct menu with 3 tiers: `high`, `low`, `image_transcription`
- Uses hard reset strategy (acceptable since no production data exists)
- Pricing for image_transcription: `input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`

---

### Task 30: Update `initialize_quota_and_bots.py` to include image_transcription tier
**Spec Reference:** Deployment Checklist > initialize_quota_and_bots.py update  
**Files:** `scripts/migrations/initialize_quota_and_bots.py`

Extend token_menu dictionary to include `image_transcription` tier (total 3 tiers). Add comment highlighting that `image_moderation` is intentionally omitted. Use "insert-if-not-exists" logic for safety.

---

### Task 31: Create migration script `migrate_image_transcription.py`
**Spec Reference:** Deployment Checklist > migrate_image_transcription.py  
**Files:** `scripts/migrations/migrate_image_transcription.py`

Create migration script that iterates existing bot configs and adds `config_data.configurations.llm_configs.image_transcription` where missing. Target `COLLECTION_BOT_CONFIGURATIONS`.

---

### Task 32: Update `get_bot_defaults` in bot_management.py to include image_transcription
**Spec Reference:** Deployment Checklist > get_bot_defaults update  
**Files:** `routers/bot_management.py`

Update `LLMConfigurations` in defaults to include `image_transcription` using `ImageTranscriptionProviderConfig` and `DefaultConfigurations`.

---

### Task 33: Update `get_configuration_schema` schema surgery loop to iterate dynamically
**Spec Reference:** Configuration > Schema surgery loop  
**Files:** `routers/bot_management.py`

Change hardcoded `['high', 'low', 'image_moderation']` list to dynamic iteration: `for prop_name in llm_configs_defs['properties'].keys():`

---

### Task 34: Update schema surgery to patch reasoning_effort for both settings classes
**Spec Reference:** Configuration > reasoning_effort patches  
**Files:** `routers/bot_management.py`

Ensure `reasoning_effort` title patches are applied to both `'ChatCompletionProviderSettings'` AND `'ImageTranscriptionProviderSettings'` in the schema surgery.

---

### Task 35: Add `GET /api/internal/bots/tiers` endpoint in bot_management.py
**Spec Reference:** New Configuration Tier Checklist > tiers endpoint  
**Files:** `routers/bot_management.py`

Create new endpoint that returns available tiers by reading `LLMConfigurations.model_fields.keys()` from Python model. Aligned with `/api/internal/bots` router prefix.

---

### Task 36: Update EditPage.js to fetch tiers dynamically from new endpoint
**Spec Reference:** New Configuration Tier Checklist > EditPage.js tiers  
**Files:** `frontend/src/pages/EditPage.js`

- Add fetch to new tiers endpoint during `fetchData`
- Store tiers in component state
- Replace all hardcoded tier arrays (`["high", "low", "image_moderation"]`) with dynamically fetched tier list
- Affects: api_key_source logic and handleFormChange

---

### Task 37: Add `image_transcription` uiSchema entry in EditPage.js
**Spec Reference:** New Configuration Tier Checklist > image_transcription uiSchema  
**Files:** `frontend/src/pages/EditPage.js`

Add fourth entry to `llm_configs` in uiSchema:
- `"ui:title": "Image Transcription Model"`
- Template config matches other tiers
- `provider_config` sub-object includes `api_key_source`, `reasoning_effort`, `seed`, and **`detail`** with `"ui:title": "Image Detail Level"`

---

### Task 38: Write tests for `detail` parameter filtering from ChatOpenAI kwargs
**Spec Reference:** Test Expectations  
**Files:** `tests/` (new or existing)

Add tests verifying `detail` is filtered from `ChatOpenAI(...)` constructor kwargs and only used in transcription payload construction.

---

### Task 39: Write tests for callback continuity between factory and transcription
**Spec Reference:** Test Expectations  
**Files:** `tests/` (new or existing)

Add tests verifying callback attachment in `create_model_provider` and transcription invocation in `transcribe_image()` use the same LLM object reference.

---

### Task 40: Write tests for transcription normalization (string, content blocks, unsupported)
**Spec Reference:** Test Expectations  
**Files:** `tests/` (new or existing)

Add tests for all normalization branches:
- String content -> returned as-is
- Content blocks -> concatenated deterministic string (single-space separator)
- Unsupported content type -> `"Unable to transcribe image content"`

---

### Task 41: Write tests for flagged moderation returns unprocessable_media=True
**Spec Reference:** Test Expectations  
**Files:** `tests/` (new or existing)

Add test that `moderation_result.flagged == True` returns `ProcessingResult(unprocessable_media=True, content="cannot process image as it violates safety guidelines")`.

---

### Task 42: Write tests for format_processing_result with/without captions
**Spec Reference:** Test Expectations  
**Files:** `tests/` (new or existing)

Add tests verifying:
- Unconditional bracket wrapping
- Caption correctly appended when non-empty
- Caption correctly omitted when None or ""

---

### Task 43: Write tests for asyncio.TimeoutError returns unprocessable_media=True
**Spec Reference:** Test Expectations  
**Files:** `tests/` (new or existing)

Add test that `asyncio.TimeoutError` path returns `ProcessingResult` with `unprocessable_media=True`.

---

### Task 44: Update existing tests for process_media return unbracketed content
**Spec Reference:** Test Expectations > Unit-level tests  
**Files:** `tests/test_image_vision_processor.py`

Update existing tests to assert that `process_media()` returns raw, unbracketed content strings (e.g., `"Transcripted audio multimedia message..."`).

---

### Task 45: Add integration tests for final formatted output to bot queue
**Spec Reference:** Test Expectations > Integration-level tests  
**Files:** `tests/` (new or existing)

Add new tests asserting final string delivered to bot queue via `update_message_by_media_id` is fully formatted `"[{MediaType} Transcription: {content}]"` form.

---

### Task 46: Update existing tests for renamed content strings in error processors
**Spec Reference:** Test Expectations > Content string updates  
**Files:** `tests/test_image_vision_processor.py`

Update any tests asserting old content strings:
- `UnsupportedMediaProcessor`: previously `"Unsupported {mime_type} media"` -> new: `f"Unsupported media type: {mime_type}"`
- `CorruptMediaProcessor`: previously with brackets -> new unbracketed

---

### Task 47: Update test_process_media_bot_id_signature to use dictionary key lookup
**Spec Reference:** Test Expectations > Signature test refactor  
**Files:** `tests/test_image_vision_processor.py`

Rewrite test assertion to use robust dictionary key lookup: `assert "bot_id" in sig.parameters` rather than asserting on hardcoded list index offsets like `params[3]`.

---
