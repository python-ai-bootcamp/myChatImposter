# Audio Transcription Support — Implementation Tasks

## Summary Table

| # | Task | Spec Section | Status |
|---|------|--------------|--------|
| 1 | Add `soniox` to `requirements.txt` | Deployment Checklist §0 | PENDING |
| 2 | Add `AudioTranscriptionProviderSettings` and `AudioTranscriptionProviderConfig` to `config_models.py` | Configuration | PENDING |
| 3 | Extend `ConfigTier`, `LLMConfigurations`, and `DefaultConfigurations` in `config_models.py` | Configuration, Deployment Checklist §2,4 | PENDING |
| 4 | Add `display_media_type` to `ProcessingResult` dataclass in `infrastructure/models.py` | Output Format | PENDING |
| 5 | Refactor `format_processing_result` in `media_processors/base.py` to add `mime_type` + `display_media_type` + prefix injection logic | Output Format | PENDING |
| 6 | Update `BaseMediaProcessor.process_job()` call sites to pass `mime_type` and `display_media_type` | Output Format | PENDING |
| 7 | Update `BaseMediaProcessor.process_job()` `asyncio.TimeoutError` block to set `unprocessable_media=True` | Companion Fixes | PENDING |
| 8 | Update `BaseMediaProcessor._handle_unhandled_exception()` to pass `unprocessable_media=True` and `mime_type` | Companion Fixes | PENDING |
| 9 | Fix `ImageVisionProcessor` error paths to set `unprocessable_media=True` on both `except` blocks | Companion Fixes | PENDING |
| 10 | Fix `ImageVisionProcessor` `create_model_provider` calls to use `"image_moderation"` and `"image_transcription"` as `feature_name` | Companion Fixes | PENDING |
| 11 | Fix `CorruptMediaProcessor` and `UnsupportedMediaProcessor` to pass `unprocessable_media=True` | Companion Fixes | PENDING |
| 12 | Add no-op `async def initialize(self): pass` to `BaseModelProvider` in `model_providers/base.py` | Provider Architecture | PENDING |
| 13 | Create abstract `AudioTranscriptionProvider` in `model_providers/audio_transcription.py` | Provider Architecture | PENDING |
| 14 | Create `SonioxAudioTranscriptionProvider` in `model_providers/sonioxAudioTranscription.py` | Provider Architecture, Transcription | PENDING |
| 15 | Refactor `create_model_provider` in `services/model_factory.py`: extract token infra, add `initialize()` call, add `AudioTranscriptionProvider` branch | Provider Architecture | PENDING |
| 16 | Refactor `resolve_model_config` in `services/resolver.py` to use dict-based registry and add `audio_transcription` overload | New Configuration Tier Checklist §2 | PENDING |
| 17 | Move `AudioTranscriptionProcessor` out of `stub_processors.py` into `media_processors/audio_transcription_processor.py` | Processing Flow | PENDING |
| 18 | Implement `AudioTranscriptionProcessor.process_media()` with Soniox provider integration and error handling | Transcription, Processing Flow | PENDING |
| 19 | Update `media_processors/factory.py` to import `AudioTranscriptionProcessor` from new module | Processing Flow, Deployment Checklist §6 | PENDING |
| 20 | Expand `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` with all Soniox-supported audio MIME types | Processing Flow | PENDING |
| 21 | Update `get_configuration_schema` in `routers/bot_management.py` hardcoded tier list to include `"audio_transcription"` | New Configuration Tier Checklist §3, Configuration | PENDING |
| 22 | Update `get_bot_defaults` in `routers/bot_management.py` to include `audio_transcription` tier | Deployment Checklist §3 | PENDING |
| 23 | Update `frontend/src/pages/EditPage.js`: add `audio_transcription` to `uiSchema` | New Configuration Tier Checklist §4 | PENDING |
| 24 | Update `frontend/src/pages/EditPage.js`: add `"audio_transcription"` to hardcoded tier arrays | New Configuration Tier Checklist §5 | PENDING |
| 25 | Create MongoDB migration script `scripts/audioTranscriptionUpgradeScript.py` (includes `token_menu` 4-tier replacement) | Deployment Checklist §1, Configuration | PENDING |
| 26 | Update existing `format_processing_result` unit test fixtures and expected output strings in `tests/test_image_transcription_support.py` for new `mime_type` param and prefix injection | Test Expectations | PENDING |
| 27 | Remove `AudioTranscriptionProcessor` import and stub signature checks from `tests/test_image_transcription_support.py` | Test Expectations | PENDING |
| 28 | Update `DEFAULT_POOL_DEFINITIONS` length-check assertions in `tests/test_media_processing_service.py` if applicable | Test Expectations | PENDING |
| 29 | Create `tests/test_audio_transcription_support.py` with full unit test suite | Test Expectations | PENDING |
| 30 | Ensure `SONIOX_API_KEY` environment variable documentation | Deployment Checklist §7 | PENDING |

---

## Detailed Task Descriptions

### Task 1 — Add `soniox` to `requirements.txt`
**Spec:** Deployment Checklist §0  
**Action:** Append `soniox==<tested-version>` to the root `requirements.txt` file. Pin to the specific version used during development to prevent future SDK drift.  
**Status:** PENDING

---

### Task 2 — Add `AudioTranscriptionProviderSettings` and `AudioTranscriptionProviderConfig` to `config_models.py`
**Spec:** Configuration §1 ("Create a new `AudioTranscriptionProviderSettings` class…"), ("Modify `AudioTranscriptionProviderConfig`…")  
**Action:**
- Create `AudioTranscriptionProviderSettings(BaseModelProviderSettings)` with `temperature: float = 0.0` field. Document that `temperature` is a dummy variable intentionally ignored by the Soniox provider, kept for future-proofing.
- Create `AudioTranscriptionProviderConfig(BaseModelProviderConfig)` redefining `provider_config: AudioTranscriptionProviderSettings`.  
**Status:** PENDING

---

### Task 3 — Extend `ConfigTier`, `LLMConfigurations`, and `DefaultConfigurations` in `config_models.py`
**Spec:** Configuration §1 (`ConfigTier` includes `"audio_transcription"`), (`LLMConfigurations.audio_transcription` required field using `Field(...)`), Deployment Checklist §2 (`DefaultConfigurations` new fields), §4 (`Field(...)` required)  
**Action:**
- Add `"audio_transcription"` to the `ConfigTier` Literal type.
- Add `audio_transcription: AudioTranscriptionProviderConfig = Field(..., title="Audio Transcription Model")` to `LLMConfigurations`.
- Add to `DefaultConfigurations`:
  - `model_provider_name_audio_transcription: str = "sonioxAudioTranscription"`
  - `model_audio_transcription: str = os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "stt-async-v4")`
  - `model_audio_transcription_temperature: float = float(os.getenv("DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE", "0.0"))`  
**Status:** PENDING

---

### Task 4 — Add `display_media_type` to `ProcessingResult` in `infrastructure/models.py`
**Spec:** Output Format ("Add an optional `display_media_type: str = None` attribute to the `ProcessingResult` dataclass")  
**Action:** Add `display_media_type: Optional[str] = None` to the `ProcessingResult` dataclass. Add docstring noting this field is transient/processing-time-only and intentionally not persisted to the database.  
**Status:** PENDING

---

### Task 5 — Refactor `format_processing_result` in `media_processors/base.py`
**Spec:** Output Format ("Prefix Injection Refactoring")  
**Action:**
- Add required `mime_type: str` parameter.
- Add optional `display_media_type: str = None` parameter.
- Add prefix injection logic: only if `unprocessable_media is False`, dynamically build `"{MediaType} Transcription: "` prefix. If `display_media_type` is provided, use it directly; otherwise extract from `mime_type` (e.g., `mime_type.split("/")[0].capitalize()`).
- Prepend the prefix to `content` before bracket-wrapping.
- Update the docstring to reflect the new contract.  
**Status:** PENDING

---

### Task 6 — Update all `format_processing_result` call sites in `BaseMediaProcessor`
**Spec:** Output Format ("atomically update all call sites")  
**Action:**
- In `BaseMediaProcessor.process_job()`: update the `format_processing_result` call (success path) to pass `job.mime_type` and `result.display_media_type`.
- In `BaseMediaProcessor._handle_unhandled_exception()`: update the `format_processing_result` call to pass `job.mime_type` (no `display_media_type` needed here per spec).  
**Status:** PENDING

---

### Task 7 — Update `asyncio.TimeoutError` block in `BaseMediaProcessor.process_job()` to set `unprocessable_media=True`
**Spec:** Companion Fixes ("Base Processor Global Update")  
**Action:** In the `except asyncio.TimeoutError:` block in `process_job()`, add `unprocessable_media=True` to the `ProcessingResult(...)` being created (currently creates it without this flag).  
**Note:** This overlaps partially with Task 6's call-site update. Ensure the `ProcessingResult` for the timeout path carries `unprocessable_media=True`.  
**Status:** PENDING

---

### Task 8 — Update `BaseMediaProcessor._handle_unhandled_exception()` to pass `unprocessable_media=True` and `mime_type`
**Spec:** Companion Fixes ("Unhandled Exception Handling")  
**Action:**
- Change the `ProcessingResult(content="Media processing failed", failed_reason=error)` to include `unprocessable_media=True`.
- Pass `mime_type=job.mime_type` to `format_processing_result` in this method.
- Do NOT forward `display_media_type` in this path (per spec note).  
**Status:** PENDING

---

### Task 9 — Fix `ImageVisionProcessor` error paths to add `unprocessable_media=True`
**Spec:** Companion Fixes ("ImageVisionProcessor")  
**Action:** In `media_processors/image_vision_processor.py`, add `unprocessable_media=True` to BOTH error-path `ProcessingResult` returns:
- The `except Exception` block for moderation failure (currently missing `unprocessable_media=True`).
- The `except Exception` block for transcription failure (currently missing `unprocessable_media=True`).
- The existing `flagged=True` moderation path already has `unprocessable_media=True` — leave it unchanged.  
**Status:** PENDING

---

### Task 10 — Fix `ImageVisionProcessor` token tracking `feature_name` values
**Spec:** Companion Fixes ("Token Metrics Alignment")  
**Action:** In `media_processors/image_vision_processor.py`, update `create_model_provider` calls:
- Change `feature_name="media_processing"` (first call, moderation) → `feature_name="image_moderation"`.
- Change `feature_name="media_processing"` (second call, transcription) → `feature_name="image_transcription"`.  
**Status:** PENDING

---

### Task 11 — Fix `CorruptMediaProcessor` and `UnsupportedMediaProcessor` to pass `unprocessable_media=True`
**Spec:** Companion Fixes ("Error Processors")  
**Action:** In `media_processors/error_processors.py`, update both `process_media` methods to add `unprocessable_media=True` to their `ProcessingResult` returns. This prevents nonsensical prefix injection on corrupt/unsupported file errors.  
**Status:** PENDING

---

### Task 12 — Add no-op `initialize()` to `BaseModelProvider`
**Spec:** Provider Architecture ("Instruct the developer to add a no-op `async def initialize(self): pass` method…to the abstract `BaseModelProvider` base class")  
**Action:** Add `async def initialize(self): pass` to `model_providers/base.py`. Must NOT be marked `@abstractmethod`. This prevents crashes in existing providers when the factory calls `await provider.initialize()`.  
**CRITICAL:** This MUST be added before or atomically with Task 15 (factory refactor) to prevent runtime crashes.  
**Status:** PENDING

---

### Task 13 — Create abstract `AudioTranscriptionProvider` in `model_providers/audio_transcription.py`
**Spec:** Provider Architecture ("AudioTranscriptionProvider (in `model_providers/audio_transcription.py`) extends `BaseModelProvider`…")  
**Action:** Create new file `model_providers/audio_transcription.py`:
- Declare `AudioTranscriptionProvider(BaseModelProvider, ABC)`.
- Implement `__init__(self, config)` calling `super().__init__(config)` and setting `self._token_tracker = None`.
- Implement `def set_token_tracker(self, tracker_func: Callable[..., Awaitable[None]]):` to enforce the async callback contract.
- Declare `async def transcribe_audio(self, file_path: str, mime_type: str) -> str` as `@abstractmethod`.
- Override `async def initialize(self): pass` (no-op at this level; concrete class overrides).  
**Status:** PENDING

---

### Task 14 — Create `SonioxAudioTranscriptionProvider` in `model_providers/sonioxAudioTranscription.py`
**Spec:** Provider Architecture (Snippet for `SonioxAudioTranscriptionProvider`), Transcription (full 4-step async pattern, cleanup, token estimation)  
**Action:** Create new file `model_providers/sonioxAudioTranscription.py`:
- Import `AsyncSonioxClient` and `CreateTranscriptionConfig` from the Soniox SDK.
- Declare module-level `_background_tasks = set()` for GC-safe task retention.
- Implement `async def initialize(self):` — creates `self.client = AsyncSonioxClient(api_key=self._resolve_api_key())`.
- Implement `async def transcribe_audio(self, audio_path: str, mime_type: str) -> str`:
  - Full 4-step explicit async pattern: upload → `stt.create` → `stt.wait` → `stt.get_transcript`.
  - **MUST NOT** use the `transcribe()` convenience wrapper.
  - Verify `stt.create` signature against Soniox SDK source to confirm `file_id` placement.
  - Invoke `_token_tracker` with estimated tokens (`audio_duration_ms / 120` for input, `len(text) * 0.3` for output) via `stt.get()` for job info.
  - In `finally` block: create async `_cleanup()` closure that calls `stt.delete_if_exists(transcription.id)` and `files.delete_if_exists(file.id)` with individual try/except. Execute via `asyncio.create_task(_cleanup())`, add to `_background_tasks`, attach `.add_done_callback(_background_tasks.discard)`.
- Return `transcript.text`.  
**Status:** PENDING

---

### Task 15 — Refactor `create_model_provider` in `services/model_factory.py`
**Spec:** Provider Architecture ("Refactor Initialization", "Add `elif isinstance(provider, AudioTranscriptionProvider)`", "ensure all providers call `await provider.initialize()`")  
**Action:**
- Add `from model_providers.audio_transcription import AudioTranscriptionProvider` import.
- Extract `TokenConsumptionService` instantiation and `get_global_state()` fetch out of the `if isinstance(provider, LLMProvider):` block — move before all type checks so it is universally available.
- Preserve the `if token_consumption_collection is not None:` guard and its `else: logger.warning(...)` fallback.
- Add `await provider.initialize()` immediately after instantiation (before type checks). This applies to all providers.
- Add new `elif isinstance(provider, AudioTranscriptionProvider):` branch that:
  - Injects `token_tracker` async closure (using existing `user_id`, `bot_id`, `feature_name`, `config_tier`) via `provider.set_token_tracker(token_tracker)` inside the `token_consumption_collection is not None` guard.
  - Returns `provider` directly (bypassing LangChain).
- Update return type annotation to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider, AudioTranscriptionProvider]`.  
**Status:** PENDING

---

### Task 16 — Refactor `resolve_model_config` in `services/resolver.py`
**Spec:** New Configuration Tier Checklist §2  
**Action:**
- Add `from config_models import AudioTranscriptionProviderConfig` import.
- Add overloaded type `@overload async def resolve_model_config(bot_id: str, config_tier: Literal["audio_transcription"]) -> AudioTranscriptionProviderConfig: ...`.
- Replace the existing `if/elif` chain in the function body with a dictionary-based registry mapping `ConfigTier` strings to Pydantic model classes.
- Add an explicit `if config_class is None: raise ValueError(f"Unknown config tier: {config_tier}")` check — do NOT use `.get()` with a silent fallback.  
**Status:** PENDING

---

### Task 17 — Move `AudioTranscriptionProcessor` out of `stub_processors.py`
**Spec:** Processing Flow ("Move it to its own file `media_processors/audio_transcription_processor.py` (and delete the old stub from `stub_processors.py`)")  
**Action:**
- Create new file `media_processors/audio_transcription_processor.py`.
- Remove the `AudioTranscriptionProcessor` class from `media_processors/stub_processors.py` (the stub class body).
- The new class skeleton starts as `class AudioTranscriptionProcessor(BaseMediaProcessor)` inheriting from `BaseMediaProcessor`, not `StubSleepProcessor`.
- Ensure `StubSleepProcessor`, `VideoDescriptionProcessor`, and `DocumentProcessor` remain in `stub_processors.py` — only `AudioTranscriptionProcessor` is removed.  
**Status:** PENDING

---

### Task 18 — Implement `AudioTranscriptionProcessor.process_media()` in `media_processors/audio_transcription_processor.py`
**Spec:** Transcription (all sub-sections), Processing Flow  
**Action:**
- Import `create_model_provider` and `AudioTranscriptionProvider`.
- `process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult`:
  - Resolve provider via `await create_model_provider(bot_id, "audio_transcription", "audio_transcription")`.
  - Call `await provider.transcribe_audio(file_path, mime_type)`.
  - Check for empty/unexpected result: if `not transcript_text.strip()`, return `ProcessingResult(content="Unable to transcribe audio content", failed_reason="Unexpected format from Soniox API", unprocessable_media=True)`.
  - On success: return `ProcessingResult(content=transcript_text)` (raw text, no brackets — formatting delegated to `format_processing_result`).
  - Wrap the whole logic in `try/except Exception as e:` (NOT `BaseException`) → return `ProcessingResult(content="Unable to transcribe audio content", failed_reason=f"Transcription error: {e}", unprocessable_media=True)`.  
**Status:** PENDING

---

### Task 19 — Update `media_processors/factory.py` import for `AudioTranscriptionProcessor`
**Spec:** Deployment Checklist §6, Processing Flow  
**Action:**
- Remove `AudioTranscriptionProcessor` from the `from media_processors.stub_processors import (...)` block.
- Add new import: `from media_processors.audio_transcription_processor import AudioTranscriptionProcessor`.
- Ensure `PROCESSOR_CLASS_MAP` still maps `"AudioTranscriptionProcessor"` to the class.  
**Status:** PENDING

---

### Task 20 — Expand `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py`
**Spec:** Processing Flow ("Ensure `DEFAULT_POOL_DEFINITIONS` is expanded to route additional Soniox-supported audio MIME types")  
**Action:** Expand the `"mimeTypes"` list for `AudioTranscriptionProcessor` in `DEFAULT_POOL_DEFINITIONS` to include all Soniox-supported types:
`["audio/ogg", "audio/mpeg", "audio/wav", "audio/webm", "audio/mp4", "audio/aac", "audio/flac", "audio/amr", "audio/aiff", "audio/x-m4a", "audio/x-ms-asf", "video/x-ms-asf", "application/vnd.ms-asf"]`  
(Currently only has `"audio/ogg"` and `"audio/mpeg"`.)  
**Status:** PENDING

---

### Task 21 — Update hardcoded tier list in `routers/bot_management.py` `get_configuration_schema`
**Spec:** New Configuration Tier Checklist §3, Configuration ("manually append `"audio_transcription"` to the hardcoded tier fallback list around line 365")  
**Action:** In `get_configuration_schema`, locate the loop over `['high', 'low', 'image_moderation', 'image_transcription']` (line 365) and append `'audio_transcription'` to this list so the schema surgery also processes the new tier.  
**Status:** PENDING

---

### Task 22 — Update `get_bot_defaults` in `routers/bot_management.py`
**Spec:** Deployment Checklist §3 ("Update `get_bot_defaults`…to include `audio_transcription` in `LLMConfigurations`")  
**Action:**
- Add `from config_models import AudioTranscriptionProviderConfig, AudioTranscriptionProviderSettings` to imports.
- Inside `get_bot_defaults`, add `audio_transcription=AudioTranscriptionProviderConfig(provider_name=DefaultConfigurations.model_provider_name_audio_transcription, provider_config=AudioTranscriptionProviderSettings(model=DefaultConfigurations.model_audio_transcription, api_key_source=DefaultConfigurations.model_api_key_source, temperature=DefaultConfigurations.model_audio_transcription_temperature))` to the `LLMConfigurations(...)` instantiation.  
**Status:** PENDING

---

### Task 23 — Update `frontend/src/pages/EditPage.js` `uiSchema` for `audio_transcription`
**Spec:** New Configuration Tier Checklist §4  
**Action:** Inside the `uiSchema.configurations.llm_configs` object, add a fifth entry:
```js
audio_transcription: {
  "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
  "ui:title": "Audio Transcription Model",
  provider_name: { "ui:title": "Provider Name" },
  provider_config: {
    "ui:ObjectFieldTemplate": FlatProviderConfigTemplate,
    "ui:title": " ",
    api_key_source: { "ui:title": "API Key Source" }
    // Intentionally omits reasoning_effort and seed — AudioTranscription is not a ChatCompletion provider
    // temperature will materialize as a visible dummy field — this is known/desired behavior
  }
}
```  
**Status:** PENDING

---

### Task 24 — Update `frontend/src/pages/EditPage.js` hardcoded tier arrays
**Spec:** New Configuration Tier Checklist §5  
**Action:** Append `"audio_transcription"` to two locations in `EditPage.js`:
1. **`handleFormChange` loop** (line ~229): the `['high', 'low', 'image_moderation', 'image_transcription'].forEach(...)` array. Add a code comment: `// Note: audio_transcription safely bypasses the reasoning_effort logic because it is undefined`.
2. **`useEffect` data fetching block** (line ~135): the `['high', 'low', 'image_moderation', 'image_transcription'].forEach(...)` array that populates `api_key_source`.  
**Status:** PENDING

---

### Task 25 — Create MongoDB migration script `scripts/audioTranscriptionUpgradeScript.py`
**Spec:** Deployment Checklist §1, Configuration ("global_configurations.token_menu is extended with an `"audio_transcription"` pricing entry…")  
**Action:** Create `scripts/audioTranscriptionUpgradeScript.py` that:
1. Iterates over all bot configs in MongoDB and upserts `config_data.configurations.llm_configs.audio_transcription` using the `sonioxAudioTranscription` provider defaults where missing.
2. Replaces the existing `token_menu` in the `global_configurations` MongoDB collection (3-tier) with a new full 4-tier menu: `high`, `low`, `image_transcription`, `audio_transcription`. The new `audio_transcription` entry uses exact JSON: `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`. Note: `image_moderation` is intentionally excluded from `token_menu`.
- Include a clear comment: **"OPERATIONAL DEPLOYMENT REQUIREMENT: This script MUST be executed against the database BEFORE deploying and restarting the backend code."**
- Note: `global_configurations.token_menu` is a MongoDB collection resource — there is no source-code definition to modify. This migration script is the sole mechanism for updating it.  
**Status:** PENDING

---

### Task 26 — Update `format_processing_result` test fixtures and expected output strings in `tests/test_image_transcription_support.py`
**Spec:** Test Expectations ("Update the four existing `format_processing_result` unit test fixtures…by providing a dummy string for the newly required `mime_type` parameter")  
**Action:** Find all four `format_processing_result(...)` calls in the `T47` test section and:
1. Add `mime_type="image/jpeg"` to each call to prevent `TypeError` from the new required parameter.
2. Update the **expected output strings** in these test assertions to account for the new prefix injection behavior — successful (non-`unprocessable_media`) results will now be prefixed with `"Image Transcription: "` before bracket wrapping, so the expected formatted output must reflect this change.  
**Status:** PENDING

---

### Task 27 — Remove `AudioTranscriptionProcessor` stub import/assertions from `tests/test_image_transcription_support.py`
**Spec:** Test Expectations ("Explicitly remove the `AudioTranscriptionProcessor` import and its associated signature verification checks from `tests/test_image_transcription_support.py`")  
**Action:**
- Remove `AudioTranscriptionProcessor` from the import in line 32 (`from media_processors.stub_processors import ...`).
- Remove any test assertions that verify `AudioTranscriptionProcessor`'s signature (e.g., within `test_process_media_no_caption_parameter`'s processor list, remove `AudioTranscriptionProcessor`).  
**Status:** PENDING

---

### Task 28 — Update `DEFAULT_POOL_DEFINITIONS` length-check assertions in `tests/test_media_processing_service.py` if applicable
**Spec:** Test Expectations ("Update `DEFAULT_POOL_DEFINITIONS` handling logic assertions if `test_media_processing_service.py` contains length-checks for predefined factories")  
**Action:** If `tests/test_media_processing_service.py` contains assertions that check the count of `DEFAULT_POOL_DEFINITIONS`, update those assertions to account for the expanded MIME type list in the audio pool (the pool count stays at 6, but the audio pool's `mimeTypes` list grows from 2 to 13 entries). Update any count-based length assertions accordingly.  
**Status:** PENDING

---

### Task 29 — Create `tests/test_audio_transcription_support.py` with full unit test suite
**Spec:** Test Expectations (all sub-bullets)  
**Action:** Create a new test file `tests/test_audio_transcription_support.py` covering:
1. **`AudioTranscriptionProcessor` signature verification:** `process_media(self, file_path, mime_type, bot_id)` — no `caption` param, correct param types.
2. **Successful transcription flow:** Mock `create_model_provider` to return a mock `AudioTranscriptionProvider`. Mock `provider.transcribe_audio` to return a non-empty string. Assert `ProcessingResult.content == transcript_text` and `unprocessable_media is False`.
3. **Empty transcript failure:** Mock `transcribe_audio` to return `""`. Assert `unprocessable_media=True`, `failed_reason` contains `"Unexpected format"`.
4. **Exception handling:** Mock `transcribe_audio` to raise `Exception("API down")`. Assert `unprocessable_media=True`, `failed_reason` contains `"Transcription error"`.
5. **`format_processing_result` prefix injection (success):** Call `format_processing_result(content="hello world", caption="cap", mime_type="audio/ogg")`. Assert output starts with `[Audio Transcription: hello world]`.
6. **`format_processing_result` prefix suppressed for unprocessable:** Call with `unprocessable_media=True`. Assert NO prefix is prepended.
7. **`BaseMediaProcessor.process_job` timeout sets `unprocessable_media=True`:** Mock `process_media` to sleep forever, trigger `asyncio.TimeoutError`, verify the persisted result has `unprocessable_media=True` (prefix suppressed).
8. **`BaseMediaProcessor._handle_unhandled_exception` sets `unprocessable_media=True`:** Call `_handle_unhandled_exception` and verify the result has `unprocessable_media=True` and no prefix is injected.
9. **`ConfigTier` includes `"audio_transcription"`:** `get_args(ConfigTier)` contains `"audio_transcription"`.
10. **`LLMConfigurations` requires `audio_transcription`:** Instantiating without it raises `ValidationError`.
11. **`AudioTranscriptionProviderSettings` defaults:** `temperature` defaults to `0.0`.
12. **Factory maps `AudioTranscriptionProcessor`:** `PROCESSOR_CLASS_MAP["AudioTranscriptionProcessor"]` points to the new class from `audio_transcription_processor` (not stub).  
**Status:** PENDING

---

### Task 30 — Ensure `SONIOX_API_KEY` environment variable documentation
**Spec:** Deployment Checklist §7
**Action:** Document that the `SONIOX_API_KEY` environment variable must be explicitly provisioned in the deployment environment. Add a comment into `audioTranscriptionUpgradeScript.py` and ensure operators are made aware, as the Soniox SDK crashes ungracefully when lacking this key during app instantiation.
**Status:** PENDING
