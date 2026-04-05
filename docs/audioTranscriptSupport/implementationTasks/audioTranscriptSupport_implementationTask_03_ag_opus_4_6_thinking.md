# Audio Transcription Support — Implementation Tasks

## Task Summary

| # | Task | Spec Section(s) | Status |
|---|------|-----------------|--------|
| 1 | Add `AudioTranscriptionProviderSettings` and `AudioTranscriptionProviderConfig` to `config_models.py` | Configuration, Provider Architecture §1 | PENDING |
| 2 | Add `"audio_transcription"` to `ConfigTier` literal | Configuration, New Configuration Tier Checklist §3.1 | PENDING |
| 3 | Add `audio_transcription` field to `LLMConfigurations` | Configuration, New Configuration Tier Checklist §3.1 | PENDING |
| 4 | Add audio transcription defaults to `DefaultConfigurations` | Configuration, Deployment Checklist §2.2 | PENDING |
| 5 | Add `display_media_type` attribute to `ProcessingResult` dataclass | Output Format, Infrastructure §models.py | PENDING |
| 6 | Add no-op `async def initialize()` to `BaseModelProvider` | Provider Architecture §1 (create_model_provider) | PENDING |
| 7 | Create abstract `AudioTranscriptionProvider` in `model_providers/audio_transcription.py` | Provider Architecture §1 | PENDING |
| 8 | Create `SonioxAudioTranscriptionProvider` in `model_providers/sonioxAudioTranscription.py` | Provider Architecture §1, Transcription | PENDING |
| 9 | Refactor `format_processing_result` — add `mime_type` and `display_media_type` params, prefix injection logic | Output Format | PENDING |
| 10 | Update all `format_processing_result` call sites in `BaseMediaProcessor.process_job()` | Output Format | PENDING |
| 11 | Update `BaseMediaProcessor._handle_unhandled_exception` — pass `unprocessable_media=True` and `mime_type` | Companion Fixes (Base Processor Global Update, Unhandled Exception) | PENDING |
| 12 | Update `BaseMediaProcessor.process_job()` timeout handler — add `unprocessable_media=True` | Companion Fixes (Base Processor Global Update) | PENDING |
| 13 | Update `ImageVisionProcessor` error paths — add `unprocessable_media=True` | Companion Fixes (ImageVisionProcessor) | PENDING |
| 14 | Update `ImageVisionProcessor` — change `feature_name` values for moderation and transcription | Companion Fixes (Token Metrics Alignment) | PENDING |
| 15 | Update `CorruptMediaProcessor` and `UnsupportedMediaProcessor` — add `unprocessable_media=True` | Companion Fixes (Error Processors) | PENDING |
| 16 | Create `AudioTranscriptionProcessor` in `media_processors/audio_transcription_processor.py` | Processing Flow, Transcription | PENDING |
| 17 | Remove `AudioTranscriptionProcessor` stub from `stub_processors.py` | Processing Flow | PENDING |
| 18 | Update `media_processors/factory.py` — re-import from new module | Processing Flow, Deployment Checklist §2.6 | PENDING |
| 19 | Expand `DEFAULT_POOL_DEFINITIONS` with additional audio MIME types | Processing Flow | PENDING |
| 20 | Update `services/resolver.py` — add `audio_transcription` overload + refactor to dictionary registry | New Configuration Tier Checklist §3.2 | PENDING |
| 21 | Update `services/model_factory.py` — refactor initialization, add `AudioTranscriptionProvider` branch, call `initialize()` | Provider Architecture §1 (create_model_provider) | PENDING |
| 22 | Update `token_menu` pricing — add `audio_transcription` tier | Configuration (token_menu) | PENDING |
| 23 | Update `routers/bot_management.py` — `get_configuration_schema` hardcoded tier list | New Configuration Tier Checklist §3.3 | PENDING |
| 24 | Update `routers/bot_management.py` — `get_bot_defaults` with `audio_transcription` tier | Deployment Checklist §2.3 | PENDING |
| 25 | Update `frontend/src/pages/EditPage.js` — add `audio_transcription` to `uiSchema` | New Configuration Tier Checklist §3.4 | PENDING |
| 26 | Update `frontend/src/pages/EditPage.js` — add `audio_transcription` to hardcoded tier arrays | New Configuration Tier Checklist §3.5 | PENDING |
| 27 | Create migration script `scripts/audioTranscriptionUpgradeScript.py` | Deployment Checklist §2.1 | PENDING |
| 28 | Add `soniox` package to `requirements.txt` | Deployment Checklist §2.0 | PENDING |
| 29 | Update existing `format_processing_result` tests in `test_image_transcription_support.py` | Test Expectations (format_processing_result signature) | PENDING |
| 30 | Remove `AudioTranscriptionProcessor` stub references from `test_image_transcription_support.py` | Test Expectations (AudioProcessor Unit Tests) | PENDING |
| 31 | Create `tests/test_audio_transcription_support.py` | Test Expectations (AudioProcessor Unit Tests) | PENDING |
| 32 | Add `BaseMediaProcessor.process_job` timeout test (`unprocessable_media=True`) | Test Expectations (Timeout) | PENDING |
| 33 | Add `BaseMediaProcessor._handle_unhandled_exception` test (`unprocessable_media=True`) | Test Expectations (Unhandled Exception) | PENDING |
| 34 | Update `DEFAULT_POOL_DEFINITIONS` test assertions (if applicable) | Test Expectations (pool definitions) | PENDING |
| 35 | Ensure `SONIOX_API_KEY` environment variable is documented | Deployment Checklist §2.7 | PENDING |

---

## Task Details

---

### Task 1: Add `AudioTranscriptionProviderSettings` and `AudioTranscriptionProviderConfig` to `config_models.py`

**Spec Sections:** Configuration, Provider Architecture §1

**Description:**
Create a new `AudioTranscriptionProviderSettings` class that inherits from `BaseModelProviderSettings` (NOT `ChatCompletionProviderSettings`), adding only `temperature: float = 0.0`. This class intentionally omits chat-specific fields like `reasoning_effort`, `seed`, and `record_llm_interactions`. Then create `AudioTranscriptionProviderConfig` extending `BaseModelProviderConfig`, redefining `provider_config: AudioTranscriptionProviderSettings`. Both classes must be placed in `config_models.py` alongside the existing configuration models.

**Key Constraint:** The `temperature` field is a dummy variable ignored by the Soniox provider, kept for future-proofing.

---

### Task 2: Add `"audio_transcription"` to `ConfigTier` literal

**Spec Sections:** Configuration, New Configuration Tier Checklist §3.1

**Description:**
Update the `ConfigTier` Literal type in `config_models.py` to include `"audio_transcription"` as a fifth valid tier value. The current value is `Literal["high", "low", "image_moderation", "image_transcription"]` and must become `Literal["high", "low", "image_moderation", "image_transcription", "audio_transcription"]`.

---

### Task 3: Add `audio_transcription` field to `LLMConfigurations`

**Spec Sections:** Configuration, New Configuration Tier Checklist §3.1

**Description:**
Add a new field `audio_transcription: AudioTranscriptionProviderConfig = Field(...)` to the `LLMConfigurations` class, making it a strictly required field (using `Field(...)`). Add an appropriate title like `"Audio Transcription Model"`.

---

### Task 4: Add audio transcription defaults to `DefaultConfigurations`

**Spec Sections:** Configuration, Deployment Checklist §2.2

**Description:**
Extend `DefaultConfigurations` in `config_models.py` with:
- `model_provider_name_audio_transcription = "sonioxAudioTranscription"`
- `model_audio_transcription: str = os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "stt-async-v4")`
- `model_audio_transcription_temperature: float = float(os.getenv("DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE", "0.0"))`

The fallback values `"0.0"` and `"stt-async-v4"` must always be specified to prevent startup crashes.

---

### Task 5: Add `display_media_type` attribute to `ProcessingResult` dataclass

**Spec Sections:** Output Format, Infrastructure §models.py

**Description:**
Add an optional `display_media_type: Optional[str] = None` field to the `ProcessingResult` dataclass in `infrastructure/models.py`. This is a transient, processing-time-only variable used by `format_processing_result` and intentionally NOT persisted to the database.

---

### Task 6: Add no-op `async def initialize()` to `BaseModelProvider`

**Spec Sections:** Provider Architecture §1 (create_model_provider)

**Description:**
Add `async def initialize(self): pass` to the `BaseModelProvider` base class in `model_providers/base.py`. This must NOT be marked as `@abstractmethod`. Existing providers safely inherit the empty method. The `SonioxAudioTranscriptionProvider` will override it to initialize its `AsyncSonioxClient`.

**CRITICAL:** This method MUST be added before (or atomically with) the `create_model_provider` factory update (Task 21) to prevent runtime crashes in existing providers.

---

### Task 7: Create abstract `AudioTranscriptionProvider` in `model_providers/audio_transcription.py`

**Spec Sections:** Provider Architecture §1

**Description:**
Create a new file `model_providers/audio_transcription.py` containing the abstract `AudioTranscriptionProvider` class that extends `BaseModelProvider`. It must:
- Declare `__init__(self, config)` that calls `super().__init__(config)` then sets `self._token_tracker = None`
- Declare `def set_token_tracker(self, tracker_func: Callable[..., Awaitable[None]])` method
- Declare `async def transcribe_audio(self, file_path: str, mime_type: str) -> str` as an `@abstractmethod`

This provider does NOT inherit from `LLMProvider` since Soniox is not a ChatCompletion model.

---

### Task 8: Create `SonioxAudioTranscriptionProvider` in `model_providers/sonioxAudioTranscription.py`

**Spec Sections:** Provider Architecture §1, Transcription

**Description:**
Create a new file `model_providers/sonioxAudioTranscription.py` implementing the `SonioxAudioTranscriptionProvider` class (extends `AudioTranscriptionProvider`). Must implement:
- `async def initialize(self)`: Creates `self.client = AsyncSonioxClient(api_key=self._resolve_api_key())`
- `async def transcribe_audio(self, audio_path, mime_type)`: Executes the explicit 4-step async pattern (upload → create → wait → get_transcript), with:
  - Token tracking via injected `_token_tracker` callback using arithmetic estimation (`input_tokens = audio_duration_ms / 120`, `output_tokens = len(text) * 0.3`)
  - `try/finally` cleanup using `asyncio.create_task()` with `_background_tasks` set for GC protection
  - Explicit 2-step cleanup (delete transcription, then delete file) — NOT using convenience `.destroy()` method
  - Error handling for empty/unexpected responses

Must use `AsyncSonioxClient` (not synchronous), `CreateTranscriptionConfig`, and verify `file_id` parameter location in `stt.create()`.

---

### Task 9: Refactor `format_processing_result` — add `mime_type` and `display_media_type` params, prefix injection logic

**Spec Sections:** Output Format

**Description:**
Modify `format_processing_result` in `media_processors/base.py` to:
1. Add a **required** `mime_type: str` parameter
2. Add an optional `display_media_type: str = None` parameter
3. Add prefix injection logic: dynamically capitalize the media type from `mime_type` (e.g., `"audio"` → `"Audio"`) and conditionally prepend `"{MediaType} Transcription: "` to the content BEFORE bracket wrapping
4. Prefix injection must **only** occur if `unprocessable_media` is `False`
5. If `display_media_type` is provided, use it directly instead of parsing `mime_type`

This is an intentionally global change affecting all successful media processors.

---

### Task 10: Update all `format_processing_result` call sites in `BaseMediaProcessor.process_job()`

**Spec Sections:** Output Format

**Description:**
Update the call to `format_processing_result` inside `BaseMediaProcessor.process_job()` to pass `mime_type=job.mime_type` and `display_media_type=result.display_media_type`. This must be an atomic update with Task 9 to avoid runtime crashes.

---

### Task 11: Update `BaseMediaProcessor._handle_unhandled_exception` — pass `unprocessable_media=True` and `mime_type`

**Spec Sections:** Companion Fixes (Base Processor Global Update, Unhandled Exception Handling)

**Description:**
Modify `_handle_unhandled_exception` to:
1. Pass `unprocessable_media=True` (currently `False`) in the `format_processing_result` call
2. Pass `mime_type=job.mime_type` to `format_processing_result`
3. `display_media_type` does NOT need to be forwarded since `unprocessable_media=True` suppresses prefix injection entirely

This prevents unhandled system errors from receiving misleading success prefixes and avoids `TypeError` crashes from the new required `mime_type` parameter.

---

### Task 12: Update `BaseMediaProcessor.process_job()` timeout handler — add `unprocessable_media=True`

**Spec Sections:** Companion Fixes (Base Processor Global Update)

**Description:**
Update the `asyncio.TimeoutError` exception block in `process_job()` to include `unprocessable_media=True` in the `ProcessingResult` construction. This ensures timeouts are system-wide recognized as unprocessable, suppressing prefix injection across all processor types.

---

### Task 13: Update `ImageVisionProcessor` error paths — add `unprocessable_media=True`

**Spec Sections:** Companion Fixes (ImageVisionProcessor)

**Description:**
Add `unprocessable_media=True` to BOTH error-path `ProcessingResult` returns in `image_vision_processor.py`:
1. The moderation API crash `except` block (line ~52) — `content="Image could not be moderated"`
2. The transcription API crash `except` block (line ~71) — `content="Image could not be transcribed"`

Note: The existing `flagged=True` moderation return at line ~46 already correctly sets `unprocessable_media=True` and requires no change.

---

### Task 14: Update `ImageVisionProcessor` — change `feature_name` values

**Spec Sections:** Companion Fixes (Token Metrics Alignment)

**Description:**
Modify the `create_model_provider` calls in `ImageVisionProcessor.process_media` to use granular `feature_name` values:
1. Moderation call: change `"media_processing"` → `"image_moderation"`
2. Transcription call: change `"media_processing"` → `"image_transcription"`

This enables per-feature token tracking tags across all media processors.

---

### Task 15: Update `CorruptMediaProcessor` and `UnsupportedMediaProcessor` — add `unprocessable_media=True`

**Spec Sections:** Companion Fixes (Error Processors)

**Description:**
Update the `ProcessingResult` returns in both `CorruptMediaProcessor.process_media()` and `UnsupportedMediaProcessor.process_media()` (in `media_processors/error_processors.py`) to explicitly include `unprocessable_media=True`. This prevents nonsensical prefixes from being injected when processing corrupted or unsupported files.

---

### Task 16: Create `AudioTranscriptionProcessor` in `media_processors/audio_transcription_processor.py`

**Spec Sections:** Processing Flow, Transcription

**Description:**
Create a new file `media_processors/audio_transcription_processor.py` containing the real `AudioTranscriptionProcessor` class that inherits from `BaseMediaProcessor`. The `process_media` method must:
1. Use the bot's `audio_transcription` tier to resolve an `AudioTranscriptionProvider` via `create_model_provider(bot_id, "audio_transcription", "audio_transcription")`
2. Call `await provider.transcribe_audio(file_path, mime_type)`
3. Wrap the call in `try/except Exception as e:` (NOT `BaseException`) to avoid catching `asyncio.CancelledError`
4. On success: return `ProcessingResult(content=transcript_text)`
5. On failure: return `ProcessingResult(content="Unable to transcribe audio content", failed_reason=f"Transcription error: {e}", unprocessable_media=True)`
6. On empty/unexpected API response: return `ProcessingResult(content="Unable to transcribe audio content", failed_reason="Unexpected format from Soniox API", unprocessable_media=True)`

Do NOT add explicit brackets — formatting is centralized in `format_processing_result`.

---

### Task 17: Remove `AudioTranscriptionProcessor` stub from `stub_processors.py`

**Spec Sections:** Processing Flow

**Description:**
Delete the `AudioTranscriptionProcessor` class from `media_processors/stub_processors.py`. The other stub processors (`VideoDescriptionProcessor`, `DocumentProcessor`) remain unchanged.

---

### Task 18: Update `media_processors/factory.py` — re-import from new module

**Spec Sections:** Processing Flow, Deployment Checklist §2.6

**Description:**
Update the import of `AudioTranscriptionProcessor` in `media_processors/factory.py` to import from `media_processors.audio_transcription_processor` instead of `media_processors.stub_processors`. Delete `AudioTranscriptionProcessor` from the `stub_processors` import block.

---

### Task 19: Expand `DEFAULT_POOL_DEFINITIONS` with additional audio MIME types

**Spec Sections:** Processing Flow

**Description:**
Expand the `AudioTranscriptionProcessor` entry in `DEFAULT_POOL_DEFINITIONS` (in `services/media_processing_service.py`) to include all Soniox-supported MIME types: `audio/ogg`, `audio/mpeg`, `audio/wav`, `audio/webm`, `audio/mp4`, `audio/aac`, `audio/flac`, `audio/amr`, `audio/aiff`, `audio/x-m4a`, `audio/x-ms-asf`, `video/x-ms-asf`, and `application/vnd.ms-asf`.

Currently only `["audio/ogg", "audio/mpeg"]` are listed.

---

### Task 20: Update `services/resolver.py` — add `audio_transcription` overload + refactor to dictionary registry

**Spec Sections:** New Configuration Tier Checklist §3.2

**Description:**
1. Add `from config_models import AudioTranscriptionProviderConfig` import
2. Add overload: `@overload async def resolve_model_config(bot_id: str, config_tier: Literal["audio_transcription"]) -> AudioTranscriptionProviderConfig: ...`
3. Refactor the function body away from hardcoded `if/elif` statements to a dynamic dictionary-based registry mapping `ConfigTier` to Pydantic Models
4. Add explicit `if config_class is None: raise ValueError(f"Unknown config tier: {config_tier}")` check (not silent `.get()` fallback)

---

### Task 21: Update `services/model_factory.py` — refactor initialization, add `AudioTranscriptionProvider` branch, call `initialize()`

**Spec Sections:** Provider Architecture §1 (create_model_provider)

**Description:**
Major refactor of `create_model_provider`:
1. Add import: `from model_providers.audio_transcription import AudioTranscriptionProvider`
2. Update return type annotation to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider, AudioTranscriptionProvider]`
3. **Refactor Initialization**: Extract `TokenConsumptionService` and `get_global_state()` dictionary fetch OUT of the `if isinstance(provider, LLMProvider):` block. Initialize universally before type checks. Preserve the existing `if token_consumption_collection is not None:` guard and `else: logger.warning(...)` fallback.
4. Add `elif isinstance(provider, AudioTranscriptionProvider):` branch:
   - Inside this branch, create the async `token_tracker` closure
   - Call `provider.set_token_tracker(token_tracker)` respecting the `None` guard on `token_consumption_collection`
   - Return provider
5. Call `await provider.initialize()` for ALL providers immediately after instantiation
6. Also ensure `ImageModerationProvider` benefits from the `initialize()` call

---

### Task 22: Update `token_menu` pricing — add `audio_transcription` tier

**Spec Sections:** Configuration (token_menu)

**Description:**
Ensure `global_configurations.token_menu` includes an `"audio_transcription"` pricing entry with the exact JSON: `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`. This will be handled by the migration script (Task 27) for existing deployments.

---

### Task 23: Update `routers/bot_management.py` — `get_configuration_schema` hardcoded tier list

**Spec Sections:** New Configuration Tier Checklist §3.3

**Description:**
In `get_configuration_schema()`, locate the hardcoded tier list around line 365 (`['high', 'low', 'image_moderation', 'image_transcription']`) and manually append `'audio_transcription'` to it.

---

### Task 24: Update `routers/bot_management.py` — `get_bot_defaults` with `audio_transcription` tier

**Spec Sections:** Deployment Checklist §2.3

**Description:**
Update `get_bot_defaults()` to include `audio_transcription` in the `LLMConfigurations` construction:
1. Import `AudioTranscriptionProviderConfig` and `AudioTranscriptionProviderSettings`
2. Add the `audio_transcription` field within the `LLMConfigurations(...)` constructor using `AudioTranscriptionProviderConfig` with settings sourced from `DefaultConfigurations` (model name, temperature, api_key_source)

---

### Task 25: Update `frontend/src/pages/EditPage.js` — add `audio_transcription` to `uiSchema`

**Spec Sections:** New Configuration Tier Checklist §3.4

**Description:**
Add a fifth entry to the `llm_configs` object in the `uiSchema` for `audio_transcription`. The `ui:title` should be `"Audio Transcription Model"`. This entry must deliberately omit `reasoning_effort` and `seed` sub-entries since this provider is not a Chat Completion provider. The `temperature: float = 0.0` will intentionally materialize as a visible dummy field (known, desired behavior for future-proofing).

---

### Task 26: Update `frontend/src/pages/EditPage.js` — add `audio_transcription` to hardcoded tier arrays

**Spec Sections:** New Configuration Tier Checklist §3.5

**Description:**
Manually append `"audio_transcription"` to three hardcoded tier arrays:
1. The `handleFormChange` loop around line 229: `['high', 'low', 'image_moderation', 'image_transcription']`
2. A second `handleFormChange` loop (if applicable — check for validation arrays)
3. The `useEffect` data fetching block around line 135: `['high', 'low', 'image_moderation', 'image_transcription']`

Add a code comment inside the `handleFormChange` loop: `// Note: audio_transcription safely bypasses the reasoning_effort logic because it is undefined`

---

### Task 27: Create migration script `scripts/audioTranscriptionUpgradeScript.py`

**Spec Sections:** Deployment Checklist §2.1

**Description:**
Create a single combined migration script that:
1. Updates existing bot configs in MongoDB, adding `config_data.configurations.llm_configs.audio_transcription` where missing (using `DefaultConfigurations` values)
2. Replaces the existing `token_menu` (3 tiers) with a new one containing ALL 4: `high`, `low`, `image_transcription`, `audio_transcription`. The `audio_transcription` tier uses exact pricing: `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`
3. Note: `image_moderation` is intentionally excluded from `token_menu`

**OPERATIONAL REQUIREMENT:** This script MUST be executed before deploying the backend to prevent unbilled usage.

---

### Task 28: Add `soniox` package to `requirements.txt`

**Spec Sections:** Deployment Checklist §2.0

**Description:**
Append the `soniox` package (preferably pinning a specific tested version) to the root `requirements.txt` file.

---

### Task 29: Update existing `format_processing_result` tests in `test_image_transcription_support.py`

**Spec Sections:** Test Expectations (format_processing_result signature change)

**Description:**
Update the four existing `format_processing_result` unit test fixtures (T47 tests: `test_format_processing_result_basic`, `test_format_processing_result_with_filename`, `test_format_processing_result_empty_caption`, `test_format_processing_result_unprocessable`) by providing a dummy string for the newly required `mime_type` parameter (e.g., `mime_type="image/jpeg"`) to prevent `TypeError` crashes. Also update expected output strings to account for the new prefix injection behavior.

---

### Task 30: Remove `AudioTranscriptionProcessor` stub references from `test_image_transcription_support.py`

**Spec Sections:** Test Expectations (AudioProcessor Unit Tests)

**Description:**
Remove the `AudioTranscriptionProcessor` import from `test_image_transcription_support.py` (line 32) and remove it from the `test_process_media_no_caption_parameter` test's class list. The processor is no longer a stub and will have its own dedicated test file.

---

### Task 31: Create `tests/test_audio_transcription_support.py`

**Spec Sections:** Test Expectations (AudioProcessor Unit Tests)

**Description:**
Create a dedicated test file implementing:
- Signature verification for `AudioTranscriptionProcessor.process_media` (self, file_path, mime_type, bot_id)
- Test reading an audio file and yielding transcribed strings via `AudioTranscriptionProcessor`
- Test the final string is returned and formatted through `format_processing_result` properly (with prefix injection)
- Provider hierarchy tests: `AudioTranscriptionProvider` inherits `BaseModelProvider` but NOT `LLMProvider`
- `SonioxAudioTranscriptionProvider` implements `AudioTranscriptionProvider`
- Config model tests: `AudioTranscriptionProviderSettings` inherits `BaseModelProviderSettings`, has `temperature` default
- `AudioTranscriptionProviderConfig` type verification

---

### Task 32: Add `BaseMediaProcessor.process_job` timeout test

**Spec Sections:** Test Expectations (Timeout)

**Description:**
Add a unit test verifying that `BaseMediaProcessor.process_job` correctly handles `asyncio.TimeoutError` by setting `unprocessable_media=True` in the result, thereby suppressing prefix injection across all processor types.

---

### Task 33: Add `BaseMediaProcessor._handle_unhandled_exception` test

**Spec Sections:** Test Expectations (Unhandled Exception)

**Description:**
Add a unit test verifying that `_handle_unhandled_exception` correctly sets `unprocessable_media=True` and produces the expected output formatting (no prefix incorrectly prepended to the system error message).

---

### Task 34: Update `DEFAULT_POOL_DEFINITIONS` test assertions

**Spec Sections:** Test Expectations (pool definitions)

**Description:**
Check if `test_media_processing_service.py` contains length-checks for predefined factories. If so, update assertions to account for the expanded MIME type list in the `AudioTranscriptionProcessor` pool definition.

---

### Task 35: Ensure `SONIOX_API_KEY` environment variable is documented

**Spec Sections:** Deployment Checklist §2.7

**Description:**
Document that the `SONIOX_API_KEY` environment variable must be provisioned in the deployment environment. The Soniox SDK does not fail gracefully when `api_key_source` is `"environment"` and the key is missing. This can be documented in the migration script header or a deployment README.
