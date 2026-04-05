# Implementation Tasks: Audio Transcription Support

## Task Summary

| #  | Task | Spec Section(s) | Status |
|----|------|-----------------|--------|
| 1  | Add `AudioTranscriptionProviderSettings` & `AudioTranscriptionProviderConfig` to `config_models.py` | Configuration (§Requirements) | PENDING |
| 2  | Add `"audio_transcription"` to `ConfigTier` Literal | Configuration (§Requirements), New Configuration Tier Checklist §3.1 | PENDING |
| 3  | Add `audio_transcription` field to `LLMConfigurations` | Configuration (§Requirements), New Configuration Tier Checklist §3.1 | PENDING |
| 4  | Add audio transcription defaults to `DefaultConfigurations` | Deployment Checklist §2 | PENDING |
| 5  | Add `display_media_type` attribute to `ProcessingResult` dataclass | Output Format (§Requirements), Project Files (`infrastructure/models.py`) | PENDING |
| 6  | Add no-op `async def initialize(self)` to `BaseModelProvider` | Provider Architecture §1 | PENDING |
| 7  | Create abstract `AudioTranscriptionProvider` in `model_providers/audio_transcription.py` | Provider Architecture §1 | PENDING |
| 8  | Create `SonioxAudioTranscriptionProvider` in `model_providers/sonioxAudioTranscription.py` | Provider Architecture §1, Transcription (§Requirements) | PENDING |
| 9  | Update `resolve_model_config` in `services/resolver.py` | Configuration (§Requirements), New Configuration Tier Checklist §3.2 | PENDING |
| 10 | Update `create_model_provider` in `services/model_factory.py` | Provider Architecture §1 (return type, initialization, AudioTranscriptionProvider branch, tracking injection) | PENDING |
| 11 | Refactor `format_processing_result` in `media_processors/base.py` — add `mime_type`, `display_media_type`, prefix injection | Output Format (§Requirements) | PENDING |
| 12 | Update `BaseMediaProcessor.process_job()` call sites for `format_processing_result` | Output Format (§Requirements) | PENDING |
| 13 | Update `BaseMediaProcessor.process_job()` timeout handler — add `unprocessable_media=True` | Companion Fixes: Base Processor Global Update (§Requirements) | PENDING |
| 14 | Update `BaseMediaProcessor._handle_unhandled_exception` — add `unprocessable_media=True` & `mime_type` | Companion Fixes: Unhandled Exception Handling (§Requirements) | PENDING |
| 15 | Create `AudioTranscriptionProcessor` in `media_processors/audio_transcription_processor.py` | Processing Flow (§Requirements), Transcription (§Requirements) | PENDING |
| 16 | Remove `AudioTranscriptionProcessor` stub from `media_processors/stub_processors.py` | Processing Flow (§Requirements) | PENDING |
| 17 | Update import in `media_processors/factory.py` | Deployment Checklist §6 | PENDING |
| 18 | Expand `DEFAULT_POOL_DEFINITIONS` MIME types in `services/media_processing_service.py` | Processing Flow (§Requirements) | PENDING |
| 19 | Fix `ImageVisionProcessor` — add `unprocessable_media=True` to error-path returns | Companion Fixes: ImageVisionProcessor (§Requirements) | PENDING |
| 20 | Fix `ImageVisionProcessor` — pass correct `feature_name` values to `create_model_provider` | Companion Fixes: Token Metrics Alignment (§Requirements) | PENDING |
| 21 | Fix `CorruptMediaProcessor` & `UnsupportedMediaProcessor` — add `unprocessable_media=True` | Companion Fixes: Error Processors (§Requirements) | PENDING |
| 22 | Update `get_bot_defaults` in `routers/bot_management.py` — include `audio_transcription` tier | Deployment Checklist §3 | PENDING |
| 23 | Update `get_configuration_schema` hardcoded tier list in `routers/bot_management.py` | New Configuration Tier Checklist §3.3 | PENDING |
| 24 | Update `global_configurations.token_menu` pricing — add `audio_transcription` entry | Configuration (§Requirements) | PENDING |
| 25 | Create `scripts/audioTranscriptionUpgradeScript.py` migration script | Deployment Checklist §1 | PENDING |
| 26 | Add `soniox` to `requirements.txt` | Deployment Checklist §0 | PENDING |
| 27 | Update frontend `EditPage.js` — add `audio_transcription` uiSchema entry | New Configuration Tier Checklist §3.4 | PENDING |
| 28 | Update frontend `EditPage.js` — add `audio_transcription` to `handleFormChange` & `useEffect` arrays | New Configuration Tier Checklist §3.5 | PENDING |
| 29 | Update existing `format_processing_result` tests in `tests/test_image_transcription_support.py` | Test Expectations (§Requirements) | PENDING |
| 30 | Remove `AudioTranscriptionProcessor` stub tests from `tests/test_image_transcription_support.py` | Test Expectations (§Requirements) | PENDING |
| 31 | Create `tests/test_audio_transcription_support.py` with processor & provider tests | Test Expectations (§Requirements) | PENDING |
| 32 | Update `DEFAULT_POOL_DEFINITIONS` tests if applicable | Test Expectations (§Requirements) | PENDING |
| 33 | Add unit test for `BaseMediaProcessor.process_job` timeout `unprocessable_media=True` | Test Expectations (§Requirements) | PENDING |
| 34 | Add unit test for `BaseMediaProcessor._handle_unhandled_exception` `unprocessable_media=True` | Test Expectations (§Requirements) | PENDING |
| 35 | Ensure `SONIOX_API_KEY` environment variable documentation | Deployment Checklist §7 | PENDING |

---

## Detailed Task Descriptions

### Task 1: Add `AudioTranscriptionProviderSettings` & `AudioTranscriptionProviderConfig` to `config_models.py`
**Spec Section:** Configuration (§Requirements)

Create a new `AudioTranscriptionProviderSettings` class inheriting from `BaseModelProviderSettings` (NOT from `ChatCompletionProviderSettings`), adding only `temperature: float = 0.0`. This class deliberately omits chat parameters like `reasoning_effort` and `seed`.

Create a new `AudioTranscriptionProviderConfig` class extending `BaseModelProviderConfig`, redefining `provider_config: AudioTranscriptionProviderSettings`.

**Key Detail:** The `temperature` field is a dummy variable intentionally ignored by the Soniox provider, kept for future-proofing.

---

### Task 2: Add `"audio_transcription"` to `ConfigTier` Literal
**Spec Section:** Configuration (§Requirements), New Configuration Tier Checklist §3.1

Update the `ConfigTier` Literal type in `config_models.py` from:
```python
ConfigTier = Literal["high", "low", "image_moderation", "image_transcription"]
```
to:
```python
ConfigTier = Literal["high", "low", "image_moderation", "image_transcription", "audio_transcription"]
```

---

### Task 3: Add `audio_transcription` field to `LLMConfigurations`
**Spec Section:** Configuration (§Requirements), New Configuration Tier Checklist §3.1

Add a strictly required field to `LLMConfigurations`:
```python
audio_transcription: AudioTranscriptionProviderConfig = Field(..., title="Audio Transcription Model")
```

---

### Task 4: Add audio transcription defaults to `DefaultConfigurations`
**Spec Section:** Deployment Checklist §2

Add the following to the `DefaultConfigurations` class:
- `model_provider_name_audio_transcription = "sonioxAudioTranscription"`
- `model_audio_transcription: str = os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "stt-async-v4")`
- `model_audio_transcription_temperature: float = float(os.getenv("DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE", "0.0"))`

**Key Detail:** The fallback values `"0.0"` and `"stt-async-v4"` MUST always be specified to prevent startup crashes when env vars are not set.

---

### Task 5: Add `display_media_type` attribute to `ProcessingResult` dataclass
**Spec Section:** Output Format (§Requirements)

Add an optional `display_media_type: str = None` field to the `ProcessingResult` dataclass in `infrastructure/models.py`. This is a transient, processing-time-only variable for consumption by `format_processing_result` and is NOT persisted to the database.

---

### Task 6: Add no-op `async def initialize(self)` to `BaseModelProvider`
**Spec Section:** Provider Architecture §1

Add `async def initialize(self): pass` to `BaseModelProvider` in `model_providers/base.py`. This MUST NOT be marked `@abstractmethod` — existing providers safely inherit the empty method. This prevents factory instantiation crashes when `create_model_provider` calls `await provider.initialize()`.

**CRITICAL:** This must be added before (or atomically with) the `create_model_provider` factory update.

---

### Task 7: Create abstract `AudioTranscriptionProvider`
**Spec Section:** Provider Architecture §1

Create `model_providers/audio_transcription.py` with:
- `AudioTranscriptionProvider` extending `BaseModelProvider` (NOT `LLMProvider`)
- Constructor calling `super().__init__(config)` then setting `self._token_tracker = None`
- `def set_token_tracker(self, tracker_func: Callable[..., Awaitable[None]])` method
- `@abstractmethod async def transcribe_audio(self, file_path: str, mime_type: str) -> str`

---

### Task 8: Create `SonioxAudioTranscriptionProvider`
**Spec Section:** Provider Architecture §1, Transcription (§Requirements)

Create `model_providers/sonioxAudioTranscription.py` implementing the concrete provider:
- Use `AsyncSonioxClient` from the Soniox Python SDK (NOT the synchronous `SonioxClient`)
- Implement the explicit 4-step async pattern: upload → create → wait → get_transcript
- DO NOT use the `transcribe()` convenience wrapper
- `async def initialize(self)` — instantiate `AsyncSonioxClient` with resolved API key
- Token estimation: `input_tokens = int((audio_duration_ms or 0) / 120)`, `output_tokens = int(len(transcript.text) * 0.3)`
- `try/finally` cleanup with `asyncio.create_task(_cleanup())` pattern and `_background_tasks` set for GC safety
- Use `delete_if_exists` for both transcription and file cleanup (2-step, NOT `destroy()`)
- Verify `stt.create` call signature accepts `file_id` as a direct parameter

---

### Task 9: Update `resolve_model_config` in `services/resolver.py`
**Spec Section:** Configuration (§Requirements), New Configuration Tier Checklist §3.2

- Add `@overload` for `Literal["audio_transcription"] -> AudioTranscriptionProviderConfig`
- Refactor the function body away from hardcoded if/elif statements to a dynamic dictionary-based registry mapping `ConfigTier` to Pydantic model classes
- Add explicit `if config_class is None: raise ValueError(f"Unknown config tier: {config_tier}")` guard
- Import `AudioTranscriptionProviderConfig` from `config_models`

---

### Task 10: Update `create_model_provider` in `services/model_factory.py`
**Spec Section:** Provider Architecture §1

Multiple changes:
1. Update return type annotation to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider, AudioTranscriptionProvider]`
2. Import `AudioTranscriptionProvider` from `model_providers.audio_transcription`
3. **Refactor Initialization:** Extract `TokenConsumptionService` instantiation out of the `if isinstance(provider, LLMProvider):` block — it must be initialized universally before type checks. Preserve the `if token_consumption_collection is not None:` guard and its `else: logger.warning(...)` fallback
4. Add `elif isinstance(provider, AudioTranscriptionProvider):` branch with tracking closure injection via `set_token_tracker()`, respecting the `None` guard
5. Add `await provider.initialize()` call immediately after instantiation for ALL providers
6. The tracking closure follows the snippet pattern: creates an async `token_tracker` function that calls `token_service.record_event(...)`

---

### Task 11: Refactor `format_processing_result` — add prefix injection
**Spec Section:** Output Format (§Requirements)

Refactor `format_processing_result` in `media_processors/base.py`:
- Add **required** `mime_type: str` parameter
- Add **optional** `display_media_type: str = None` parameter
- Add logic: if `unprocessable_media` is `False`, dynamically capitalize the media type from `mime_type` (e.g., `"audio"` → `"Audio"`) and prepend `"{MediaType} Transcription: "` to the content
- If `display_media_type` is provided, use it directly instead of parsing `mime_type`
- This is an intentionally GLOBAL change affecting all successful processors

---

### Task 12: Update `BaseMediaProcessor.process_job()` call sites for `format_processing_result`
**Spec Section:** Output Format (§Requirements)

Update the `format_processing_result` call in `BaseMediaProcessor.process_job()` to pass:
- `mime_type=job.mime_type`
- `display_media_type=result.display_media_type`

This must be done atomically with Task 11 to avoid runtime crashes.

---

### Task 13: Update `BaseMediaProcessor.process_job()` timeout handler
**Spec Section:** Companion Fixes: Base Processor Global Update (§Requirements)

In the `asyncio.TimeoutError` handler, add `unprocessable_media=True` to the `ProcessingResult`. This enforces timeout suppression of prefix injection system-wide.

---

### Task 14: Update `BaseMediaProcessor._handle_unhandled_exception`
**Spec Section:** Companion Fixes: Unhandled Exception Handling (§Requirements)

Modify `_handle_unhandled_exception` to pass `unprocessable_media=True` and `mime_type=job.mime_type` to `format_processing_result`. The `display_media_type` does not need to be forwarded since `unprocessable_media=True` suppresses prefix injection entirely.

---

### Task 15: Create `AudioTranscriptionProcessor`
**Spec Section:** Processing Flow (§Requirements), Transcription (§Requirements)

Create `media_processors/audio_transcription_processor.py`:
- Inherits from `BaseMediaProcessor`
- `process_media(self, file_path, mime_type, bot_id) -> ProcessingResult`
- Resolves `AudioTranscriptionProvider` via `create_model_provider(bot_id, "audio_transcription", "audio_transcription")`
- Calls `await provider.transcribe_audio(file_path, mime_type)`
- Wraps the call in `try/except Exception as e:` (NOT `BaseException`) — returns `ProcessingResult(content="Unable to transcribe audio content", failed_reason=f"Transcription error: {e}", unprocessable_media=True)` on error
- Returns `ProcessingResult(content=transcript_text)` on success
- If API returns empty string or unexpected format: return `ProcessingResult(content="Unable to transcribe audio content", failed_reason="Unexpected format from Soniox API", unprocessable_media=True)`
- No explicit bracket wrapping — formatting is centralized in `format_processing_result()`
- No initial moderation step required

---

### Task 16: Remove `AudioTranscriptionProcessor` stub from `stub_processors.py`
**Spec Section:** Processing Flow (§Requirements)

Delete the `AudioTranscriptionProcessor` class from `media_processors/stub_processors.py`. Only `StubSleepProcessor`, `VideoDescriptionProcessor`, and `DocumentProcessor` should remain.

---

### Task 17: Update import in `media_processors/factory.py`
**Spec Section:** Deployment Checklist §6

Change the `AudioTranscriptionProcessor` import from `media_processors.stub_processors` to `media_processors.audio_transcription_processor`.

---

### Task 18: Expand `DEFAULT_POOL_DEFINITIONS` MIME types
**Spec Section:** Processing Flow (§Requirements)

Update the `AudioTranscriptionProcessor` entry in `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` to include all Soniox-supported audio MIME types:
`["audio/ogg", "audio/mpeg", "audio/wav", "audio/webm", "audio/mp4", "audio/aac", "audio/flac", "audio/amr", "audio/aiff", "audio/x-m4a", "audio/x-ms-asf", "video/x-ms-asf", "application/vnd.ms-asf"]`

---

### Task 19: Fix `ImageVisionProcessor` — add `unprocessable_media=True` to error paths
**Spec Section:** Companion Fixes: ImageVisionProcessor (§Requirements)

Add `unprocessable_media=True` to BOTH `except` block `ProcessingResult` returns in `image_vision_processor.py`:
1. Moderation API crash (line ~52-55)
2. Transcription API crash (line ~71-74)

The existing `flagged=True` moderation return at line ~46 already correctly sets `unprocessable_media=True` and requires no change.

---

### Task 20: Fix `ImageVisionProcessor` — `feature_name` alignment
**Spec Section:** Companion Fixes: Token Metrics Alignment (§Requirements)

Update `ImageVisionProcessor.process_media` to pass:
- `"image_moderation"` as `feature_name` for the moderation call (instead of `"media_processing"`)
- `"image_transcription"` as `feature_name` for the transcription call (instead of `"media_processing"`)

---

### Task 21: Fix `CorruptMediaProcessor` & `UnsupportedMediaProcessor`
**Spec Section:** Companion Fixes: Error Processors (§Requirements)

Add `unprocessable_media=True` to the `ProcessingResult` return in both `CorruptMediaProcessor.process_media` and `UnsupportedMediaProcessor.process_media` in `media_processors/error_processors.py`.

---

### Task 22: Update `get_bot_defaults` — include `audio_transcription` tier
**Spec Section:** Deployment Checklist §3

Add the `audio_transcription` entry to the `LLMConfigurations` construction inside `get_bot_defaults` in `routers/bot_management.py`, using `AudioTranscriptionProviderConfig` and `AudioTranscriptionProviderSettings` with values from `DefaultConfigurations`. Also add the necessary imports.

In addition, define `LLMConfigurations.audio_transcription` as a strictly required field using `Field(...)` (already done in Task 3).

---

### Task 23: Update `get_configuration_schema` hardcoded tier list
**Spec Section:** New Configuration Tier Checklist §3.3

Manually append `"audio_transcription"` to the hardcoded tier fallback list in `get_configuration_schema` at the `for prop_name in [...]` loop (~line 365 in `bot_management.py`).

---

### Task 24: Define `audio_transcription` token_menu pricing
**Spec Section:** Configuration (§Requirements)

The `global_configurations.token_menu` must include `"audio_transcription"` with pricing: `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`. This is handled by the migration script (Task 25) which replaces the existing 3-tier token_menu with a full 4-tier version.

---

### Task 25: Create `scripts/audioTranscriptionUpgradeScript.py` migration script
**Spec Section:** Deployment Checklist §1

Create a single combined migration script that:
1. Updates existing bot configs in MongoDB — adds `config_data.configurations.llm_configs.audio_transcription` where missing
2. Replaces the existing `token_menu` (3 tiers) with ALL 4 tiers: `high`, `low`, `image_transcription`, `audio_transcription`. The `audio_transcription` entry uses pricing `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`
3. `image_moderation` is intentionally excluded from `token_menu`

**OPERATIONAL:** This script MUST run before deploying new backend code.

---

### Task 26: Add `soniox` to `requirements.txt`
**Spec Section:** Deployment Checklist §0

Append the `soniox` package (preferably version-pinned) to the root `requirements.txt` file.

---

### Task 27: Update frontend `EditPage.js` — add `audio_transcription` uiSchema
**Spec Section:** New Configuration Tier Checklist §3.4

Add a fifth entry to the `llm_configs` object in `uiSchema` for `audio_transcription`:
- `"ui:title"` should be `"Audio Transcription Model"`
- Deliberately omit `reasoning_effort` and `seed` sub-entries (not a Chat Completion provider)
- The `temperature: float = 0.0` backend field will materialize as a visible dummy field — this is known, desired behavior

---

### Task 28: Update frontend `EditPage.js` — `handleFormChange` & `useEffect` arrays
**Spec Section:** New Configuration Tier Checklist §3.5

Manually append `"audio_transcription"` to:
1. The tier array inside `handleFormChange` loop (~line 229): `['high', 'low', 'image_moderation', 'image_transcription', 'audio_transcription']`
2. The tier array inside the `useEffect` data fetching block (~line 135): `['high', 'low', 'image_moderation', 'image_transcription', 'audio_transcription']`

Add a code comment inside the `handleFormChange` loop: `// Note: audio_transcription safely bypasses the reasoning_effort logic because it is undefined`

---

### Task 29: Update existing `format_processing_result` tests
**Spec Section:** Test Expectations (§Requirements)

Update the four existing `format_processing_result` unit test fixtures in `tests/test_image_transcription_support.py` by providing a dummy string for the newly required `mime_type` parameter (e.g., `mime_type="image/jpeg"`) to prevent signature-related `TypeError` crashes.

---

### Task 30: Remove `AudioTranscriptionProcessor` stub tests
**Spec Section:** Test Expectations (§Requirements)

Remove the `AudioTranscriptionProcessor` import and its associated signature verification check from `tests/test_image_transcription_support.py` (currently included in the `test_process_media_no_caption_parameter` test's class list).

---

### Task 31: Create `tests/test_audio_transcription_support.py`
**Spec Section:** Test Expectations (§Requirements)

Create a dedicated test file including:
- Processor signature verification (migrated from stub test)
- `AudioTranscriptionProcessor` reads audio file and yields transcribed strings
- Final string is properly formatted through `format_processing_result`
- Provider hierarchy assertions (AudioTranscriptionProvider inherits BaseModelProvider, not LLMProvider)
- Config model assertions (ConfigTier includes `audio_transcription`, LLMConfigurations requires it)
- Error handling test: transcription failure returns correct `ProcessingResult` with `unprocessable_media=True`

---

### Task 32: Update `DEFAULT_POOL_DEFINITIONS` tests if applicable
**Spec Section:** Test Expectations (§Requirements)

If `test_media_processing_service.py` or similar test files contain length-checks for predefined factory definitions, update assertions to account for the expanded MIME type list.

**Note:** No such test file was found in the project, so this task may be N/A. Mark as DONE after verification.

---

### Task 33: Add unit test for `BaseMediaProcessor.process_job` timeout
**Spec Section:** Test Expectations (§Requirements)

Create a unit test verifying that `BaseMediaProcessor.process_job` correctly handles `asyncio.TimeoutError` by setting `unprocessable_media=True` on the `ProcessingResult`, confirming prefix injection is suppressed.

---

### Task 34: Add unit test for `BaseMediaProcessor._handle_unhandled_exception`
**Spec Section:** Test Expectations (§Requirements)

Create a unit test verifying that `_handle_unhandled_exception` correctly sets `unprocessable_media=True` and produces the expected output formatting (no prefix is incorrectly prepended to the system error message).

---

### Task 35: Ensure `SONIOX_API_KEY` environment variable documentation
**Spec Section:** Deployment Checklist §7

Document that the `SONIOX_API_KEY` environment variable must be provisioned in the deployment environment. The Soniox SDK does not fail gracefully if it is missing and `api_key_source` is set to `"environment"`. This can be noted in the migration script header, a README, or deployment documentation.
