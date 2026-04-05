# Audio Transcription Support — Implementation Tasks

## Task Summary

| #  | Task | Spec Section(s) | Status |
|----|------|------------------|--------|
| 1  | Add `AudioTranscriptionProviderSettings` and `AudioTranscriptionProviderConfig` to `config_models.py` | Configuration, Technical §1 | PENDING |
| 2  | Add `"audio_transcription"` to `ConfigTier` Literal | Configuration, New Config Tier §1 | PENDING |
| 3  | Add `audio_transcription` field to `LLMConfigurations` | Configuration, New Config Tier §1 | PENDING |
| 4  | Add `DefaultConfigurations` entries for audio transcription | Deployment §2 | PENDING |
| 5  | Add `display_media_type` attribute to `ProcessingResult` dataclass | Output Format, Infrastructure models | PENDING |
| 6  | Add no-op `async def initialize(self)` to `BaseModelProvider` | Technical §1, Deployment §1 | PENDING |
| 7  | Create abstract `AudioTranscriptionProvider` in `model_providers/audio_transcription.py` | Technical §1 | PENDING |
| 8  | Create `SonioxAudioTranscriptionProvider` in `model_providers/sonioxAudioTranscription.py` | Technical §1, Transcription | PENDING |
| 9  | Update `resolve_model_config` in `services/resolver.py` | Configuration, New Config Tier §2 | PENDING |
| 10 | Update `create_model_provider` in `services/model_factory.py` | Technical §1, Configuration | PENDING |
| 11 | Refactor `AudioTranscriptionProcessor` out of stubs into `media_processors/audio_transcription_processor.py` | Processing Flow | PENDING |
| 12 | Update `media_processors/factory.py` imports | Processing Flow, Deployment §6 | PENDING |
| 13 | Expand `DEFAULT_POOL_DEFINITIONS` with additional audio MIME types | Processing Flow | PENDING |
| 14 | Refactor `format_processing_result` with `mime_type` and `display_media_type` params | Output Format | PENDING |
| 15 | Update all `format_processing_result` call sites in `BaseMediaProcessor` | Output Format | PENDING |
| 16 | Update `BaseMediaProcessor.process_job` timeout handler — add `unprocessable_media=True` | Companion Fixes — Base Processor | PENDING |
| 17 | Update `BaseMediaProcessor._handle_unhandled_exception` — add `unprocessable_media=True` and `mime_type` | Companion Fixes — Base Processor | PENDING |
| 18 | Fix `ImageVisionProcessor` error paths — add `unprocessable_media=True` | Companion Fixes — ImageVisionProcessor | PENDING |
| 19 | Fix `ImageVisionProcessor` `feature_name` values (`"image_moderation"` / `"image_transcription"`) | Companion Fixes — Token Metrics | PENDING |
| 20 | Fix `CorruptMediaProcessor` and `UnsupportedMediaProcessor` — add `unprocessable_media=True` | Companion Fixes — Error Processors | PENDING |
| 21 | Update `get_configuration_schema` hardcoded tier list in `routers/bot_management.py` | New Config Tier §3 | PENDING |
| 22 | Update `get_bot_defaults` to include `audio_transcription` in `LLMConfigurations` | Deployment §3 | PENDING |
| 23 | Add `audio_transcription` entry to frontend `EditPage.js` uiSchema | New Config Tier §4 | PENDING |
| 24 | Update frontend `EditPage.js` `handleFormChange` and `useEffect` tier arrays | New Config Tier §5 | PENDING |
| 25 | Extend `global_configurations.token_menu` with `audio_transcription` pricing entry | Configuration | PENDING |
| 26 | Create migration script `scripts/audioTranscriptionUpgradeScript.py` | Deployment §1 | PENDING |
| 27 | Add `soniox` to `requirements.txt` | Deployment §0 | PENDING |
| 28 | Update existing `format_processing_result` unit tests with `mime_type` param | Test Expectations §1 | PENDING |
| 29 | Remove `AudioTranscriptionProcessor` stub references from `test_image_transcription_support.py` | Test Expectations §2 | PENDING |
| 30 | Create `tests/test_audio_transcription_support.py` with audio processor tests | Test Expectations §2–§3 | PENDING |
| 31 | Add `BaseMediaProcessor.process_job` timeout unit test (`unprocessable_media=True`) | Test Expectations §5 | PENDING |
| 32 | Add `BaseMediaProcessor._handle_unhandled_exception` unit test (`unprocessable_media=True`) | Test Expectations §6 | PENDING |
| 33 | Update `DEFAULT_POOL_DEFINITIONS` test assertions if applicable | Test Expectations §4 | PENDING |
| 34 | Provision `SONIOX_API_KEY` environment variable documentation | Deployment §7 | PENDING |

---

## Task Details

### Task 1 — Add `AudioTranscriptionProviderSettings` and `AudioTranscriptionProviderConfig` to `config_models.py`
**Spec:** Configuration (line 12-13), Technical §1 Provider Architecture  
**Status:** PENDING

- Create `AudioTranscriptionProviderSettings` inheriting from `BaseModelProviderSettings` (NOT `ChatCompletionProviderSettings`), adding only `temperature: float = 0.0`.
- Create `AudioTranscriptionProviderConfig` extending `BaseModelProviderConfig`, redefining `provider_config: AudioTranscriptionProviderSettings`.
- These classes deliberately omit `reasoning_effort`, `seed`, and other chat-specific fields since audio transcription is not a ChatCompletion provider.

---

### Task 2 — Add `"audio_transcription"` to `ConfigTier` Literal
**Spec:** Configuration (line 14), New Config Tier Checklist §1  
**Status:** PENDING

- Update the `ConfigTier` Literal type in `config_models.py` from `Literal["high", "low", "image_moderation", "image_transcription"]` to include `"audio_transcription"`.

---

### Task 3 — Add `audio_transcription` field to `LLMConfigurations`
**Spec:** Configuration (line 13), Deployment §4  
**Status:** PENDING

- Add `audio_transcription: AudioTranscriptionProviderConfig = Field(..., title="Audio Transcription Model")` to `LLMConfigurations`.
- The field uses `Field(...)` (strictly required, no default).

---

### Task 4 — Add `DefaultConfigurations` entries for audio transcription
**Spec:** Deployment Checklist §2 (line 205)  
**Status:** PENDING

- Add `model_provider_name_audio_transcription = "sonioxAudioTranscription"` to `DefaultConfigurations`.
- Add `model_audio_transcription: str = os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "stt-async-v4")`.
- Add `model_audio_transcription_temperature: float = float(os.getenv("DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE", "0.0"))`.
- Fallback values `"stt-async-v4"` and `"0.0"` are mandatory to prevent startup crashes.

---

### Task 5 — Add `display_media_type` attribute to `ProcessingResult` dataclass
**Spec:** Output Format (line 46), Infrastructure models (line 65)  
**Status:** PENDING

- Add `display_media_type: Optional[str] = None` to the `ProcessingResult` dataclass in `infrastructure/models.py`.
- This is a transient, processing-time-only variable for `format_processing_result` consumption; NOT persisted to DB.

---

### Task 6 — Add no-op `async def initialize(self)` to `BaseModelProvider`
**Spec:** Technical §1 (line 181)  
**Status:** PENDING

- Add `async def initialize(self): pass` to `BaseModelProvider` in `model_providers/base.py`.
- Must NOT be `@abstractmethod` — existing providers must safely inherit the no-op.
- **CRITICAL:** Must be added before or atomically with `create_model_provider` update (Task 10) to prevent runtime crashes.

---

### Task 7 — Create abstract `AudioTranscriptionProvider` in `model_providers/audio_transcription.py`
**Spec:** Technical §1 (lines 113-118, 127)  
**Status:** PENDING

- New file: `model_providers/audio_transcription.py`.
- Class `AudioTranscriptionProvider` extends `BaseModelProvider` (NOT `LLMProvider` — Soniox is not a ChatCompletion model).
- Declares abstract method `async def transcribe_audio(self, file_path: str, mime_type: str) -> str`.
- Constructor calls `super().__init__(config)`, then sets `self._token_tracker = None`.
- Declares `def set_token_tracker(self, tracker_func)` to enforce the async tracking contract.
- Includes `async def initialize(self): pass` override point.

---

### Task 8 — Create `SonioxAudioTranscriptionProvider` in `model_providers/sonioxAudioTranscription.py`
**Spec:** Technical §1 (lines 120-176, 128-131)  
**Status:** PENDING

- New file: `model_providers/sonioxAudioTranscription.py`.
- Implements `AudioTranscriptionProvider.transcribe_audio` using `AsyncSonioxClient` from `soniox` SDK (bypasses LangChain).
- `async def initialize(self)` creates `self.client = AsyncSonioxClient(api_key=self._resolve_api_key())`.
- Uses the **explicit 4-step** async pattern: (1) `files.upload`, (2) `stt.create`, (3) `stt.wait`, (4) `stt.get_transcript`.
- Must **NOT** use the `transcribe()` convenience wrapper.
- Token tracking via injected callback using arithmetic estimation: `input_tokens = int((audio_duration_ms or 0) / 120)`, `output_tokens = int(len(transcript.text) * 0.3)`.
- `try/finally` cleanup: wrap cleanup in async closure + `asyncio.create_task(...)`.
- Module-level `_background_tasks = set()` for GC protection with `add_done_callback(_background_tasks.discard)`.
- Explicit 2-step cleanup (`stt.delete_if_exists` + `files.delete_if_exists`); reject `.destroy()` convenience method.
- Must verify `stt.create` call signature for `file_id` parameter acceptance during implementation.

---

### Task 9 — Update `resolve_model_config` in `services/resolver.py`
**Spec:** Configuration (line 15), New Config Tier Checklist §2 (line 214)  
**Status:** PENDING

- Add `@overload` for `Literal["audio_transcription"] -> AudioTranscriptionProviderConfig`.
- Refactor the function body from hardcoded `if/elif` to a **dynamic dictionary-based registry** mapping `ConfigTier` to Pydantic model classes.
- Add explicit `if config_class is None: raise ValueError(f"Unknown config tier: {config_tier}")` guard — no silent fallback with `.get()`.
- Import `AudioTranscriptionProviderConfig` from `config_models`.

---

### Task 10 — Update `create_model_provider` in `services/model_factory.py`
**Spec:** Technical §1 (lines 178-196)  
**Status:** PENDING

- Update return type annotation to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider, AudioTranscriptionProvider]`.
- Import `AudioTranscriptionProvider` from `model_providers.audio_transcription`.
- **Refactor initialization**: Extract `TokenConsumptionService` instantiation out of the `if isinstance(provider, LLMProvider)` block — initialize universally before type checks. Preserve the existing `if token_consumption_collection is not None:` guard and `else: logger.warning(...)` fallback.
- Add `await provider.initialize()` call immediately after instantiation for ALL providers.
- Add `elif isinstance(provider, AudioTranscriptionProvider):` branch that:
  - Creates `token_tracker` async closure matching spec snippet.
  - Calls `provider.set_token_tracker(token_tracker)` (respecting `None` guard).
  - Returns `provider`.
- The fallback `else: raise TypeError(...)` remains as the last branch.

---

### Task 11 — Refactor `AudioTranscriptionProcessor` out of stubs
**Spec:** Processing Flow (line 21-23)  
**Status:** PENDING

- Create new file `media_processors/audio_transcription_processor.py`.
- `AudioTranscriptionProcessor` inherits from `BaseMediaProcessor` (NOT `StubSleepProcessor`).
- Implements `async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult`.
- Resolves `audio_transcription` tier via `create_model_provider(bot_id, "audio_transcription", "audio_transcription")`.
- Calls `await provider.transcribe_audio(file_path, mime_type)`.
- Wraps call in `try/except Exception as e:` (NOT `BaseException`) — returns `ProcessingResult(content="Unable to transcribe audio content", failed_reason=f"Transcription error: {e}", unprocessable_media=True)` on error.
- On success: returns `ProcessingResult(content=transcript_text)`.
- Handles empty/unexpected API response: returns `ProcessingResult(content="Unable to transcribe audio content", failed_reason="Unexpected format from Soniox API", unprocessable_media=True)`.
- No moderation step required.
- Delete the `AudioTranscriptionProcessor` class from `stub_processors.py`.

---

### Task 12 — Update `media_processors/factory.py` imports
**Spec:** Processing Flow, Deployment §6 (line 209)  
**Status:** PENDING

- Change `AudioTranscriptionProcessor` import from `media_processors.stub_processors` to `media_processors.audio_transcription_processor`.
- Verify `PROCESSOR_CLASS_MAP` entry points to the new class.

---

### Task 13 — Expand `DEFAULT_POOL_DEFINITIONS` with additional audio MIME types
**Spec:** Processing Flow (line 22)  
**Status:** PENDING

- Update the audio pool entry in `services/media_processing_service.py` `DEFAULT_POOL_DEFINITIONS` to include: `audio/ogg`, `audio/mpeg`, `audio/wav`, `audio/webm`, `audio/mp4`, `audio/aac`, `audio/flac`, `audio/amr`, `audio/aiff`, `audio/x-m4a`, `audio/x-ms-asf`, `video/x-ms-asf`, `application/vnd.ms-asf`.

---

### Task 14 — Refactor `format_processing_result` with `mime_type` and `display_media_type` params
**Spec:** Output Format (line 46)  
**Status:** PENDING

- Add **required** `mime_type: str` parameter to `format_processing_result` in `media_processors/base.py`.
- Add optional `display_media_type: str = None` parameter.
- Add logic: when `unprocessable_media` is `False`, dynamically capitalize media type from `mime_type` (e.g., `"audio"` → `"Audio"`) and prepend `"{MediaType} Transcription: "` to the content.
- If `display_media_type` is provided, use it directly instead of parsing `mime_type`.
- Prefix injection must ONLY occur when `unprocessable_media` is `False`.

---

### Task 15 — Update all `format_processing_result` call sites in `BaseMediaProcessor`
**Spec:** Output Format (line 46)  
**Status:** PENDING

- In `BaseMediaProcessor.process_job()`: pass `job.mime_type` and `result.display_media_type` to `format_processing_result`.
- In `BaseMediaProcessor._handle_unhandled_exception()`: pass `job.mime_type` to `format_processing_result`.
- All call sites must be updated atomically to avoid runtime crashes.

---

### Task 16 — Update `BaseMediaProcessor.process_job` timeout handler — add `unprocessable_media=True`
**Spec:** Companion Fixes — Base Processor Global Update (line 40)  
**Status:** PENDING

- In the `except asyncio.TimeoutError:` block in `process_job`, add `unprocessable_media=True` to the `ProcessingResult`.
- This suppresses prefix injection system-wide for timed-out jobs.

---

### Task 17 — Update `BaseMediaProcessor._handle_unhandled_exception` — add `unprocessable_media=True` and `mime_type`
**Spec:** Companion Fixes — Unhandled Exception Handling (line 41)  
**Status:** PENDING

- Modify `_handle_unhandled_exception` to pass `unprocessable_media=True` and `mime_type=job.mime_type` to `format_processing_result`.
- `display_media_type` does not need forwarding since `unprocessable_media=True` suppresses prefix injection entirely.

---

### Task 18 — Fix `ImageVisionProcessor` error paths — add `unprocessable_media=True`
**Spec:** Companion Fixes — ImageVisionProcessor (line 37)  
**Status:** PENDING

- Add `unprocessable_media=True` to BOTH `except` block `ProcessingResult` returns in `image_vision_processor.py`:
  - Moderation API crash (line 52-55): `ProcessingResult(content="Image could not be moderated", ..., unprocessable_media=True)`.
  - Transcription API crash (line 71-74): `ProcessingResult(content="Image could not be transcribed", ..., unprocessable_media=True)`.
- The existing `flagged=True` moderation return (line 46) already sets `unprocessable_media=True` — no change needed.

---

### Task 19 — Fix `ImageVisionProcessor` `feature_name` values
**Spec:** Companion Fixes — Token Metrics Alignment (line 38)  
**Status:** PENDING

- Change `create_model_provider(bot_id, "media_processing", "image_moderation")` to `create_model_provider(bot_id, "image_moderation", "image_moderation")`.
- Change `create_model_provider(bot_id, "media_processing", "image_transcription")` to `create_model_provider(bot_id, "image_transcription", "image_transcription")`.
- This enables granular, per-feature token tracking tags.

---

### Task 20 — Fix `CorruptMediaProcessor` and `UnsupportedMediaProcessor` — add `unprocessable_media=True`
**Spec:** Companion Fixes — Error Processors (line 39)  
**Status:** PENDING

- In `error_processors.py`, add `unprocessable_media=True` to `ProcessingResult` returns in both `CorruptMediaProcessor.process_media` and `UnsupportedMediaProcessor.process_media`.

---

### Task 21 — Update `get_configuration_schema` hardcoded tier list
**Spec:** New Config Tier Checklist §3 (line 215)  
**Status:** PENDING

- In `routers/bot_management.py`, append `"audio_transcription"` to the hardcoded tier list around line 365: `['high', 'low', 'image_moderation', 'image_transcription', 'audio_transcription']`.

---

### Task 22 — Update `get_bot_defaults` to include `audio_transcription`
**Spec:** Deployment Checklist §3 (line 206)  
**Status:** PENDING

- In the `get_bot_defaults` function in `routers/bot_management.py`, add `audio_transcription=AudioTranscriptionProviderConfig(...)` to the `LLMConfigurations` constructor.
- Use `DefaultConfigurations.model_provider_name_audio_transcription` for provider name.
- Use `AudioTranscriptionProviderSettings` with `model=DefaultConfigurations.model_audio_transcription`, `api_key_source=DefaultConfigurations.model_api_key_source`, `temperature=DefaultConfigurations.model_audio_transcription_temperature`.
- Import `AudioTranscriptionProviderConfig` and `AudioTranscriptionProviderSettings` at the top of the file.

---

### Task 23 — Add `audio_transcription` entry to frontend `EditPage.js` uiSchema
**Spec:** New Config Tier Checklist §4 (line 216)  
**Status:** PENDING

- Add a fifth `audio_transcription` entry in the `llm_configs` section of `uiSchema` in `EditPage.js`.
- Set `"ui:title": "Audio Transcription Model"`.
- Deliberately omit `reasoning_effort` and `seed` sub-entries (not a ChatCompletion provider).
- The backend `temperature: float = 0.0` will materialize as a visible dummy field — this is known desired behavior.

---

### Task 24 — Update frontend `EditPage.js` `handleFormChange` and `useEffect` tier arrays
**Spec:** New Config Tier Checklist §5 (line 217)  
**Status:** PENDING

- Append `"audio_transcription"` to the hardcoded tier array in `handleFormChange` (line 229): `['high', 'low', 'image_moderation', 'image_transcription', 'audio_transcription']`.
- Append `"audio_transcription"` to the `useEffect` data fetching array (around line 135): `['high', 'low', 'image_moderation', 'image_transcription', 'audio_transcription']`.
- Add developer comment: `// Note: audio_transcription safely bypasses the reasoning_effort logic because it is undefined`.

---

### Task 25 — Extend `global_configurations.token_menu` with `audio_transcription` pricing
**Spec:** Configuration (line 16)  
**Status:** PENDING

- Ensure token menu includes `"audio_transcription": {"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`.
- This is handled via the migration script (Task 26), but must also be documented as the target state.

---

### Task 26 — Create migration script `scripts/audioTranscriptionUpgradeScript.py`
**Spec:** Deployment Checklist §1 (lines 200-204)  
**Status:** PENDING

- Single combined migration script that:
  1. Updates existing bot configs in MongoDB — adds `config_data.configurations.llm_configs.audio_transcription` where missing.
  2. Replaces the existing `token_menu` (3 tiers) with a new one containing ALL 4 tiers: `high`, `low`, `image_transcription`, `audio_transcription`. The new `audio_transcription` entry: `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`. (`image_moderation` intentionally excluded from token_menu.)
- **OPERATIONAL:** Must be run **before** deploying backend code to prevent unbilled usage.

---

### Task 27 — Add `soniox` to `requirements.txt`
**Spec:** Deployment Checklist §0 (line 199)  
**Status:** PENDING

- Append the `soniox` package (preferably pinned version) to the root `requirements.txt`.

---

### Task 28 — Update existing `format_processing_result` unit tests with `mime_type` param
**Spec:** Test Expectations §1 (line 220)  
**Status:** PENDING

- Update the four existing `format_processing_result` test fixtures in `tests/test_image_transcription_support.py` by adding `mime_type="image/jpeg"` (or any dummy string) parameter to prevent `TypeError` from the new required parameter.

---

### Task 29 — Remove `AudioTranscriptionProcessor` stub references from `test_image_transcription_support.py`
**Spec:** Test Expectations §2 (line 221)  
**Status:** PENDING

- Remove the `AudioTranscriptionProcessor` import from `tests/test_image_transcription_support.py`.
- Remove any signature verification checks for `AudioTranscriptionProcessor` in the test (currently in `test_process_media_no_caption_parameter` which imports it from `stub_processors`).
- The processor is no longer a stub; its tests now belong in the dedicated test file (Task 30).

---

### Task 30 — Create `tests/test_audio_transcription_support.py`
**Spec:** Test Expectations §2-§3 (lines 221-223)  
**Status:** PENDING

- New file: `tests/test_audio_transcription_support.py`.
- Implement signature verification assertions for `AudioTranscriptionProcessor` (moved from image transcription test).
- Test reading an audio file and yielding transcribed strings.
- Verify the final string is returned and formatted through `format_processing_result` properly.
- Mock `create_model_provider` and `AudioTranscriptionProvider` for unit testing.
- Test error handling: exception path returns `ProcessingResult` with `unprocessable_media=True`.
- Test empty/unexpected API response handling.

---

### Task 31 — Add `BaseMediaProcessor.process_job` timeout unit test
**Spec:** Test Expectations §5 (line 225)  
**Status:** PENDING

- Add unit test verifying `BaseMediaProcessor.process_job` correctly handles `asyncio.TimeoutError` by setting `unprocessable_media=True`, thereby suppressing prefix injection across all processor types.
- Can be added to `test_audio_transcription_support.py` or a dedicated base processor test file.

---

### Task 32 — Add `BaseMediaProcessor._handle_unhandled_exception` unit test
**Spec:** Test Expectations §6 (line 226)  
**Status:** PENDING

- Add unit test verifying `BaseMediaProcessor._handle_unhandled_exception` correctly sets `unprocessable_media=True` and produces expected output formatting (no prefix incorrectly prepended).
- Can be added to `test_audio_transcription_support.py` or a dedicated base processor test file.

---

### Task 33 — Update `DEFAULT_POOL_DEFINITIONS` test assertions
**Spec:** Test Expectations §4 (line 224)  
**Status:** PENDING

- If `test_media_processing_service.py` contains length-checks for predefined factories, update them to reflect the expanded MIME type list.
- Verify no hard-coded counts break due to the additional MIME types.

---

### Task 34 — Provision `SONIOX_API_KEY` environment variable documentation
**Spec:** Deployment Checklist §7 (line 210)  
**Status:** PENDING

- Document that `SONIOX_API_KEY` must be provisioned in the deployment environment.
- The Soniox SDK does not fail gracefully if it is missing and `api_key_source` is set to `"environment"`.
- This can be a note in the migration script, a README update, or deployment runbook entry.
