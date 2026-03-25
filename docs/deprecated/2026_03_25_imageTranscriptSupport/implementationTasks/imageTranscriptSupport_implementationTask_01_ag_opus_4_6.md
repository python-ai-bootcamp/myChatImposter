# Implementation Tasks — Image Transcription Support

## Task Summary Table

| #  | Task | Spec Section(s) | Status |
|----|------|------------------|--------|
| 1  | Add `unprocessable_media` field to `ProcessingResult` | Processing Flow | PENDING |
| 2  | Delete dead code `LLMProviderSettings` & `LLMProviderConfig` from `config_models.py` | Deployment Checklist §10 | PENDING |
| 3  | Create `ImageTranscriptionProviderSettings` & `ImageTranscriptionProviderConfig` in `config_models.py` | Configuration; Provider Architecture §1 | PENDING |
| 4  | Add `image_transcription` to `ConfigTier` Literal & `LLMConfigurations` model | Configuration; New Config Tier Checklist §4.1 | PENDING |
| 5  | Add `DefaultConfigurations` entries for image transcription | Deployment Checklist §2 | PENDING |
| 6  | Add `LLMProvider` abstract class & refactor `ChatCompletionProvider` | Provider Architecture §1 | PENDING |
| 7  | Create `OpenAiMixin` & refactor `OpenAiChatProvider` (constructor-time init, remove `print`/`httpx` logger) | Provider Architecture §1 | PENDING |
| 8  | Move `httpx` logger configuration to `main.py` | Provider Architecture §1 | PENDING |
| 9  | Create abstract `ImageTranscriptionProvider` in `model_providers/image_transcription.py` | Provider Architecture §1 | PENDING |
| 10 | Create concrete `OpenAiImageTranscriptionProvider` in `model_providers/openAiImageTranscription.py` | Provider Architecture §1; Transcription | PENDING |
| 11 | Add `_resolve_api_key()` synchronous constraint comment in `BaseModelProvider` | Provider Architecture §1 | PENDING |
| 12 | Add `__module__` filter to `find_provider_class` in `utils/provider_utils.py` | Provider Architecture §1 | PENDING |
| 13 | Refactor `create_model_provider` in `services/model_factory.py` (unified `LLMProvider` branch, return type) | Provider Architecture §1 | PENDING |
| 14 | Add `resolve_bot_language` function to `services/resolver.py` | Transcription; Configuration | PENDING |
| 15 | Add `image_transcription` overload to `resolve_model_config` in `services/resolver.py` | New Config Tier Checklist §4.2 | PENDING |
| 16 | Add `image/gif` to `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` | Processing Flow | PENDING |
| 17 | Create `format_processing_result` function in `media_processors/base.py` | Output Format | PENDING |
| 18 | Remove `caption` parameter from `process_media` signature (base + all 7 subclasses) | Output Format | PENDING |
| 19 | Update `CorruptMediaProcessor.process_media` (new content string, `unprocessable_media=True`) | Output Format | PENDING |
| 20 | Update `UnsupportedMediaProcessor.process_media` (new content string, `unprocessable_media=True`) | Output Format | PENDING |
| 21 | Update `StubSleepProcessor.process_media` (new content string, no brackets, `unprocessable_media=False`) | Output Format | PENDING |
| 22 | Refactor `BaseMediaProcessor.process_job()` per spec snippet (caption extraction, prefix injection, formatting, `TimeoutError` changes) | Output Format; Processing Flow | PENDING |
| 23 | Update `BaseMediaProcessor._handle_unhandled_exception` (use `format_processing_result`, `unprocessable_media=True`, remove brackets) | Output Format | PENDING |
| 24 | Implement `ImageVisionProcessor.process_media` (moderation flow, flagged handling, transcription call) | Processing Flow; Transcription | PENDING |
| 25 | Update `get_bot_defaults` in `routers/bot_management.py` to include `image_transcription` tier | Deployment Checklist §3 | PENDING |
| 26 | Make schema surgery loop dynamic & patch `ImageTranscriptionProviderSettings` reasoning_effort in `get_configuration_schema` | Configuration; New Config Tier Checklist §4.3 | PENDING |
| 27 | Create new `GET /api/internal/bots/tiers` endpoint in `bot_management.py` | New Config Tier Checklist §4.4 | PENDING |
| 28 | Update `frontend/EditPage.js` — add `image_transcription` uiSchema entry (static) | New Config Tier Checklist §4.5 | PENDING |
| 29 | Update `frontend/EditPage.js` — fetch tiers dynamically, replace hardcoded tier arrays | New Config Tier Checklist §4.4 | PENDING |
| 30 | Update `initialize_quota_and_bots.py` — add `image_transcription` tier to `token_menu` | Deployment Checklist §5 | PENDING |
| 31 | Create `scripts/migrations/migrate_image_transcription.py` (backfill bot configs) | Deployment Checklist §1 | PENDING |
| 32 | Create `scripts/migrations/migrate_token_menu_image_transcription.py` (hard-reset token menu) | Deployment Checklist §6 | PENDING |
| 33 | Create `scripts/migrations/migrate_pool_definitions_gif.py` (delete `_mediaProcessorDefinitions`) | Processing Flow | PENDING |
| 34 | Extend `global_configurations.token_menu` with `image_transcription` pricing entry | Configuration | PENDING |
| 35 | Add tests: `detail` filtered from `ChatOpenAI` kwargs, used only in transcription payload | Test Expectations | PENDING |
| 36 | Add tests: callback continuity (same LLM object in factory & transcription) | Test Expectations | PENDING |
| 37 | Add tests: transcription response normalization (string, content blocks, unsupported) | Test Expectations | PENDING |
| 38 | Add test: `moderation_result.flagged == True` returns `ProcessingResult(unprocessable_media=True, ...)` | Test Expectations | PENDING |
| 39 | Add test: `format_processing_result` bracket wrapping & caption logic | Test Expectations | PENDING |
| 40 | Add test: caption correctly appended regardless of success/failure | Test Expectations | PENDING |
| 41 | Add test: `asyncio.TimeoutError` returns `ProcessingResult(unprocessable_media=True)` | Test Expectations | PENDING |
| 42 | Update existing unit tests: `process_media` returns raw unbracketed content | Test Expectations | PENDING |
| 43 | Add integration tests: `process_job` end-to-end final formatted string delivered to queue | Test Expectations | PENDING |
| 44 | Update existing tests: renamed content strings for `UnsupportedMediaProcessor` & `CorruptMediaProcessor` | Test Expectations | PENDING |
| 45 | Update `test_process_media_bot_id_signature` to use dict key lookup instead of index offsets | Test Expectations | PENDING |

---

## Detailed Task Descriptions

### Task 1 — Add `unprocessable_media` field to `ProcessingResult`
**Spec:** Processing Flow (§ "Update `infrastructure/models.py`")

Add `unprocessable_media: bool = False` to the `ProcessingResult` dataclass in `infrastructure/models.py`. Include a docstring comment explaining: *"True means the media could not be meaningfully transcribed, signaling `process_job` to skip prefix injection for the error payload."*

---

### Task 2 — Delete dead code `LLMProviderSettings` & `LLMProviderConfig`
**Spec:** Deployment Checklist §10

Remove the unused `LLMProviderSettings` class (lines 63–92) and `LLMProviderConfig` class (lines 94–96) entirely from `config_models.py`.

---

### Task 3 — Create `ImageTranscriptionProviderSettings` & `ImageTranscriptionProviderConfig`
**Spec:** Configuration; Provider Architecture §1

In `config_models.py`:
- Create `ImageTranscriptionProviderSettings(ChatCompletionProviderSettings)` adding `detail: Literal["low", "high", "original", "auto"] = "auto"`.
- Create `ImageTranscriptionProviderConfig(ChatCompletionProviderConfig)` redefining `provider_config: ImageTranscriptionProviderSettings`.

---

### Task 4 — Add `image_transcription` to `ConfigTier` & `LLMConfigurations`
**Spec:** Configuration; New Config Tier Checklist §4.1

- Update `ConfigTier = Literal["high", "low", "image_moderation", "image_transcription"]`.
- Add `image_transcription: ImageTranscriptionProviderConfig = Field(...)` as a required field on `LLMConfigurations`.
- Add the comment above both `LLMConfigurations` and `ConfigTier` stating they are the ONLY places where tier structure/keys are defined.

---

### Task 5 — Add `DefaultConfigurations` entries for image transcription
**Spec:** Deployment Checklist §2

Add to `DefaultConfigurations`:
- `model_provider_name_image_transcription = "openAiImageTranscription"`
- `model_image_transcription = os.getenv("DEFAULT_MODEL_IMAGE_TRANSCRIPTION", "gpt-5-mini")`
- `model_image_transcription_temperature = float(os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE", "0.05"))`
- `model_image_transcription_reasoning_effort = os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT", "minimal")`

---

### Task 6 — Add `LLMProvider` abstract class & refactor `ChatCompletionProvider`
**Spec:** Provider Architecture §1

In `model_providers/base.py`:
- Define `LLMProvider(BaseModelProvider, ABC)` with `@abstractmethod def get_llm(self) -> BaseChatModel`.

In `model_providers/chat_completion.py`:
- Change `ChatCompletionProvider` to inherit from `LLMProvider` (not `BaseModelProvider`).
- Remove the `@abstractmethod def get_llm` declaration and `abc` imports.
- Replace the class body with `pass` (empty type-marker).

---

### Task 7 — Create `OpenAiMixin` & refactor `OpenAiChatProvider`
**Spec:** Provider Architecture §1

- Extract `_build_llm_params()` into a centralized `OpenAiMixin` class (can live in `model_providers/openAi.py` or a new file).
- Refactor `OpenAiChatProvider` to use `OpenAiMixin` + constructor-time `ChatOpenAI` initialization (`self._llm` in `__init__`, `get_llm()` returns `self._llm`).
- Remove the `print()` debug statements.

---

### Task 8 — Move `httpx` logger configuration to `main.py`
**Spec:** Provider Architecture §1

Extract the `httpx` logger setup from `OpenAiChatProvider.get_llm()` and place it in the application startup file (`main.py`). This removes process-state side-effects from the provider.

---

### Task 9 — Create abstract `ImageTranscriptionProvider`
**Spec:** Provider Architecture §1

Create `model_providers/image_transcription.py` containing `ImageTranscriptionProvider(LLMProvider, ABC)` with `@abstractmethod async def transcribe_image(self, base64_image: str, mime_type: str, language_code: str) -> str`.

---

### Task 10 — Create concrete `OpenAiImageTranscriptionProvider`
**Spec:** Provider Architecture §1; Transcription; OpenAI Vision Parameter §2

Create `model_providers/openAiImageTranscription.py`:
- `OpenAiImageTranscriptionProvider(ImageTranscriptionProvider, OpenAiMixin)`.
- In `__init__`: call `_build_llm_params()`, pop `detail` into `self._detail`, create `self._llm = ChatOpenAI(**params)`.
- Implement `transcribe_image`: construct multimodal `HumanMessage` (text prompt with `language_code`, `image_url` data URI with `detail`), invoke LLM via `ainvoke`, normalize response per the spec's normalization contract.

---

### Task 11 — Add synchronous constraint comment in `BaseModelProvider._resolve_api_key()`
**Spec:** Provider Architecture §1

Add an explicit comment inside `_resolve_api_key()` stating it must remain strictly synchronous with no external I/O.

---

### Task 12 — Add `__module__` filter to `find_provider_class`
**Spec:** Provider Architecture §1

In `utils/provider_utils.py`, add `obj.__module__ == module.__name__` to the `inspect.getmembers` filter. Add a documentation note explaining this is a defensive measure against sibling imports. Keep the existing `not inspect.isabstract(obj)` check.

---

### Task 13 — Refactor `create_model_provider` in `services/model_factory.py`
**Spec:** Provider Architecture §1

- Update return type to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider]`.
- Refactor to use unified `isinstance(provider, LLMProvider)` branch for token tracking. For `ChatCompletionProvider` return `llm` (raw), for `ImageTranscriptionProvider` return `provider` (wrapper).
- `ImageModerationProvider` keeps its existing branch (no token tracking).
- Update docstring to document the return contract per spec.

---

### Task 14 — Add `resolve_bot_language` function
**Spec:** Transcription; Configuration

Create `resolve_bot_language(bot_id: str) -> str` in `services/resolver.py`:
- Reads `config_data.configurations.user_details.language_code` from the bot configuration document using `get_global_state().configurations_collection.find_one(...)`.
- Falls back to `"en"` if the document or field is missing.
- The entire DB fetch block is wrapped in `try/except Exception: return "en"` — must never raise.

---

### Task 15 — Add `image_transcription` overload to `resolve_model_config`
**Spec:** New Config Tier Checklist §4.2

In `services/resolver.py`:
- Add `@overload` for `Literal["image_transcription"] -> ImageTranscriptionProviderConfig`.
- Add `elif config_tier == "image_transcription": return ImageTranscriptionProviderConfig.model_validate(tier_data)` in the implementation.
- Import `ImageTranscriptionProviderConfig`.

---

### Task 16 — Add `image/gif` to `DEFAULT_POOL_DEFINITIONS`
**Spec:** Processing Flow

Update the `ImageVisionProcessor` entry in `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` to include `"image/gif"` alongside JPEG, PNG, WEBP.

---

### Task 17 — Create `format_processing_result` function
**Spec:** Output Format

Implement `format_processing_result(content: str, caption: str) -> str` as a **module-level pure function** in `media_processors/base.py`:
- Unconditionally wraps content in brackets: `[<content>]`.
- If `caption` is a non-empty string, appends `\n[Caption: <caption_text>]`.
- If `caption` is `None` or `""`, returns the bracket-wrapped content as-is.

---

### Task 18 — Remove `caption` from `process_media` signature
**Spec:** Output Format

Update the `process_media` abstract method signature in `BaseMediaProcessor` and all 7 subclasses (`ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`) to remove the `caption` parameter. New signature:
```python
async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:
```
Also remove `caption` from the `process_media` call in `process_job`.

---

### Task 19 — Update `CorruptMediaProcessor.process_media`
**Spec:** Output Format

Return `ProcessingResult(content=f"Corrupted {media_type} media could not be downloaded", failed_reason=..., unprocessable_media=True)`. No caption, no brackets. Preserve the `media_type = mime_type.replace("media_corrupt_", "")` derivation.

---

### Task 20 — Update `UnsupportedMediaProcessor.process_media`
**Spec:** Output Format

Return `ProcessingResult(content=f"Unsupported media type: {mime_type}", failed_reason=..., unprocessable_media=True)`. No caption, no brackets.

---

### Task 21 — Update `StubSleepProcessor.process_media`
**Spec:** Output Format

Return `ProcessingResult(content=f"multimedia message with guid='{...}'")`. No "Transcripted" phrasing, no brackets, `unprocessable_media` defaults to `False`.

---

### Task 22 — Refactor `BaseMediaProcessor.process_job()`
**Spec:** Output Format; Processing Flow

Replace the current `process_job` body with the exhaustive snippet from the spec:
- Extract `caption = job.placeholder_message.content` at the top.
- Remove `caption` from the `process_media` call.
- `asyncio.TimeoutError` now produces `ProcessingResult(content="Processing timed out", failed_reason=..., unprocessable_media=True)` — no brackets.
- Add prefix injection (§ step 2): only when `not result.unprocessable_media and not result.failed_reason`.
- Add unconditional `format_processing_result(result.content, caption)` call (§ step 3) before persistence.
- All downstream persistence/delivery remains unchanged.

---

### Task 23 — Update `_handle_unhandled_exception`
**Spec:** Output Format

- Set `unprocessable_media=True` on the `ProcessingResult`.
- Change content from `"[Media processing failed]"` to `"Media processing failed"` (no brackets).
- Source caption from `job.placeholder_message.content`.
- Call `result.content = format_processing_result(result.content, caption)` **before** any persistence.

---

### Task 24 — Implement `ImageVisionProcessor.process_media` (full flow)
**Spec:** Processing Flow; Transcription

- Load image as base64 (existing `_load_image_base64` via `asyncio.to_thread`).
- Moderate using `create_model_provider(bot_id, "media_processing", "image_moderation")`.
- If `moderation_result.flagged == True`: return `ProcessingResult(content="cannot process image as it violates safety guidelines", unprocessable_media=True)`. Set `failed_reason=None`.
- If `moderation_result.flagged == False`:
  - Call `resolve_bot_language(bot_id)`.
  - Call `create_model_provider(bot_id, "image_transcription", "image_transcription")` to get the transcription provider.
  - Call `await provider.transcribe_image(base64_image, mime_type, language_code)`.
  - Return `ProcessingResult(content=transcript)`.
- No custom error handling around `transcribe_image`.

---

### Task 25 — Update `get_bot_defaults` for `image_transcription`
**Spec:** Deployment Checklist §3

Add `image_transcription=ImageTranscriptionProviderConfig(...)` to the `LLMConfigurations` construction in `get_bot_defaults`, using `DefaultConfigurations` values. Import the necessary config classes.

---

### Task 26 — Make schema surgery loop dynamic & patch `ImageTranscriptionProviderSettings`
**Spec:** Configuration; New Config Tier Checklist §4.3

In `get_configuration_schema` in `routers/bot_management.py`:
- Replace the hardcoded `['high', 'low', 'image_moderation']` in the schema surgery loop with `llm_configs_defs['properties'].keys()`.
- Add `reasoning_effort` title patches for `'ImageTranscriptionProviderSettings'` in addition to `'ChatCompletionProviderSettings'`.

---

### Task 27 — Create `GET /api/internal/bots/tiers` endpoint
**Spec:** New Config Tier Checklist §4.4

Add a lightweight endpoint in `bot_management.py` returning `list(LLMConfigurations.model_fields.keys())`.

---

### Task 28 — Add `image_transcription` uiSchema entry in `EditPage.js`
**Spec:** New Config Tier Checklist §4.5

Statically add a fourth `image_transcription` entry to the `llm_configs` uiSchema:
- `"ui:title": "Image Transcription Model"`.
- `"ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate`.
- Include full `provider_config` sub-object matching `high`/`low` tiers (with `api_key_source`, `reasoning_effort`, `seed`), plus `detail` field with `ui:title` of `"Image Detail Level"`.

---

### Task 29 — Fetch tiers dynamically & replace hardcoded tier arrays in `EditPage.js`
**Spec:** New Config Tier Checklist §4.4

- Fetch from `GET /api/internal/bots/tiers` (or mapped gateway equivalent) during `fetchData`.
- Store in component state.
- Replace every occurrence of the hardcoded `['high', 'low', 'image_moderation']` array (around line 135 for `api_key_source` and line 229 for `handleFormChange`) with the dynamically fetched tier list.

---

### Task 30 — Update `initialize_quota_and_bots.py` with `image_transcription` tier
**Spec:** Deployment Checklist §5

Add `"image_transcription": { "input_tokens": 0.25, "cached_input_tokens": 0.025, "output_tokens": 2.0 }` to the `token_menu` dictionary (total 3 tiers). Keep the existing insert-if-not-exists logic. Add a comment noting `image_moderation` is intentionally omitted.

---

### Task 31 — Create `migrate_image_transcription.py`
**Spec:** Deployment Checklist §1

Create `scripts/migrations/migrate_image_transcription.py`:
- Iterate existing bot configs in `COLLECTION_BOT_CONFIGURATIONS`.
- Add `config_data.configurations.llm_configs.image_transcription` where missing.
- Use `infrastructure/db_schema.py` constants (no hardcoded collection names).
- Follow existing migration patterns.

---

### Task 32 — Create `migrate_token_menu_image_transcription.py`
**Spec:** Deployment Checklist §6

Create `scripts/migrations/migrate_token_menu_image_transcription.py`:
- Completely deletes any existing `token_menu` document and re-inserts the full correct 3-tier menu from scratch ("hard reset").
- Use `infrastructure/db_schema.py` constants.

---

### Task 33 — Create `migrate_pool_definitions_gif.py`
**Spec:** Processing Flow

Create `scripts/migrations/migrate_pool_definitions_gif.py`:
- Deletes the existing `_mediaProcessorDefinitions` document from `COLLECTION_GLOBAL_CONFIGURATIONS`.
- On next boot, `MediaProcessingService` will recreate it from updated defaults (including `image/gif`).
- Use `infrastructure/db_schema.py` constants.

---

### Task 34 — Extend `global_configurations.token_menu` with `image_transcription` pricing
**Spec:** Configuration

This task is fulfilled by Tasks 30 and 32 (the migration scripts). The pricing values are `input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`. This task is a verification checkpoint to ensure the token_menu document in MongoDB will contain the `image_transcription` entry after migrations run.

---

### Task 35 — Test: `detail` filtered from `ChatOpenAI` kwargs
**Spec:** Test Expectations

Add tests verifying `detail` is popped from `ChatOpenAI(...)` constructor kwargs and only used in transcription payload construction inside `transcribe_image`.

---

### Task 36 — Test: callback continuity
**Spec:** Test Expectations

Add tests verifying that the callback attachment in `create_model_provider` and the LLM invocation in `transcribe_image(...)` use the same `self._llm` object reference.

---

### Task 37 — Test: transcription response normalization
**Spec:** Test Expectations

Add tests covering all three normalization branches:
- `response.content` is `str` → returned as-is.
- `response.content` is content blocks → concatenated via single-space separator, trimmed.
- `response.content` is unsupported type → `"Unable to transcribe image content"`.

---

### Task 38 — Test: moderation flagged returns `unprocessable_media=True`
**Spec:** Test Expectations

Add test verifying `moderation_result.flagged == True` returns `ProcessingResult(unprocessable_media=True, content="cannot process image as it violates safety guidelines")`.

---

### Task 39 — Test: `format_processing_result` formatting logic
**Spec:** Test Expectations

Add test verifying:
- Unconditional bracket wrapping.
- Caption appended when non-empty.
- Caption omitted when `None` or `""`.

---

### Task 40 — Test: caption correctly appended in both success and failure paths
**Spec:** Test Expectations

Add test that caption from `job.placeholder_message.content` is correctly appended regardless of processing outcome.

---

### Task 41 — Test: `asyncio.TimeoutError` returns `unprocessable_media=True`
**Spec:** Test Expectations

Add test verifying the `asyncio.TimeoutError` path produces `ProcessingResult` with `unprocessable_media=True` and content `"Processing timed out"` (no brackets).

---

### Task 42 — Update existing unit tests for raw unbracketed content
**Spec:** Test Expectations

Update existing tests to assert `process_media()` returns raw, unbracketed content strings (e.g., `"Transcripted audio multimedia message..."`). Verifies removal of legacy bracket wrapping.

---

### Task 43 — Add integration tests for `process_job` end-to-end
**Spec:** Test Expectations

Add tests asserting the final string delivered to the bot queue via `update_message_by_media_id` is the fully formatted `"[{MediaType} Transcription: {content}]"` form.

---

### Task 44 — Update existing tests for renamed content strings
**Spec:** Test Expectations

Update tests asserting old content strings for `UnsupportedMediaProcessor` (previously `"Unsupported {mime_type} media"`) and `CorruptMediaProcessor` to match new spec-defined strings: `f"Unsupported media type: {mime_type}"` and `f"Corrupted {media_type} media could not be downloaded"` (unbracketed).

---

### Task 45 — Update `test_process_media_bot_id_signature`
**Spec:** Test Expectations

Rewrite the test assertion in `tests/test_image_vision_processor.py` to use dictionary key lookup (e.g., `assert "bot_id" in sig.parameters`) instead of hardcoded list index offsets like `params[4]`.
