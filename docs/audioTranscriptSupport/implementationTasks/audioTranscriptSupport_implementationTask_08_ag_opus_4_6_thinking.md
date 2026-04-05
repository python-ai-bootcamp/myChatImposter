# Implementation Tasks: Audio Transcription Support

## Task Summary

| Task ID | Task Name | Description | Status |
| :--- | :--- | :--- | :--- |
| **TASK-01** | Dependency & Script Setup | Add Soniox dependency and create database migration script | <PENDING> |
| **TASK-02** | Configuration Models Update | Update Pydantic models for new config tier and API payload | <PENDING> |
| **TASK-03** | Service & Router Integration | Update backend resolvers and bot management endpoints for the new tier | <PENDING> |
| **TASK-04** | Frontend UI Expansion | Update the EditPage frontend logic and schema mappings | <PENDING> |
| **TASK-05** | Base Model Provider Pre-reqs | Add `initialize()` stub to `BaseModelProvider` before factories break | <PENDING> |
| **TASK-06** | Abstract Audio Provider | Create base `AudioTranscriptionProvider` with token callback interface | <PENDING> |
| **TASK-07** | Concrete Soniox Implementation | Implement `SonioxAudioTranscriptionProvider` with precise resource cleanup | <PENDING> |
| **TASK-08** | Factory Pattern Refactoring | Refactor `model_factory.py` for token trackers, intialization, and bypassing LangChain | <PENDING> |
| **TASK-09** | Central Processing Refactoring | Modify `BaseMediaProcessor` formatting logic, timeout handling, and exception parsing | <PENDING> |
| **TASK-10** | Error Processors Updates | Amend `CorruptMediaProcessor` and `UnsupportedMediaProcessor` for `unprocessable_media=True` | <PENDING> |
| **TASK-11** | ImageVision Companion Fixes | Add `unprocessable_media` to image error processors; scope their model feature names | <PENDING> |
| **TASK-12** | Core Audio Processor Class | Build native `AudioTranscriptionProcessor` explicitly executing the transcription | <PENDING> |
| **TASK-13** | Factory & Service Registration | Add `AudioTranscriptionProcessor` bindings; expand MIME types in Media Service definitions | <PENDING> |
| **TASK-14** | Test Modifications & Additions | Fix image processor tests; implement audio unit tests; verify exception processing coverage | <PENDING> |

---

## Task Details

### TASK-01: Dependency & Script Setup
- **Status:** <PENDING>
- **Spec Section:** Deployment Checklist
- **Description:** 
  1. Append the `soniox` python SDK to the root `requirements.txt`.
  2. Create a single migration script `scripts/audioTranscriptionUpgradeScript.py`. The script will independently migrate global config (`token_menu` expanded with all 4 tiers, setting exact `audio_transcription` pricing to `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`), and update existing user bot configs in MongoDB to merge missing `llm_configs.audio_transcription` data.
  3. Ensure the deployment manual is updated to configure `SONIOX_API_KEY`.

### TASK-02: Configuration Models Update
- **Status:** <PENDING>
- **Spec Section:** Configuration, Deployment Checklist, New Configuration Tier Checklist
- **Description:** 
  1. Modify `config_models.py` by adding `"audio_transcription"` to the `ConfigTier` Literal array.
  2. Introduce an `AudioTranscriptionProviderSettings` class inheriting from `BaseModelProviderSettings` holding `temperature: float = 0.0`.
  3. Introduce `AudioTranscriptionProviderConfig` extending `BaseModelProviderConfig` pointing `provider_config` to `AudioTranscriptionProviderSettings`.
  4. Expand `LLMConfigurations` introducing `audio_transcription` as a strictly required `Field(...)` utilizing `AudioTranscriptionProviderConfig`.
  5. Expand `DefaultConfigurations` establishing default values (using OS environment vars): `DEFAULT_MODEL_AUDIO_TRANSCRIPTION` ("stt-async-v4") and `DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE` ("0.0").
  6. Modify `infrastructure/models.py` by adding `display_media_type: str = None` as an optional string variable to the `ProcessingResult` dataclass.

### TASK-03: Service & Router Integration
- **Status:** <PENDING>
- **Spec Section:** Configuration, New Configuration Tier Checklist, Deployment Checklist
- **Description:** 
  1. In `services/resolver.py`, add literal overloads for `"audio_transcription"`. Refactor `resolve_model_config` body logic from a hard-coded mapping approach into a strict lookup mapping dictionary indexing `ConfigTier` to classes, intentionally using `raise ValueError` if an unknown tier is supplied.
  2. In `routers/bot_management.py`, amend `get_bot_defaults` merging new `audio_transcription` properties populated off `DefaultConfigurations`. Append the string `"audio_transcription"` manually to the `get_configuration_schema` hardcoded tier manipulation fallback lists.

### TASK-04: Frontend UI Expansion
- **Status:** <PENDING>
- **Spec Section:** New Configuration Tier Checklist
- **Description:** 
  1. Update `frontend/src/pages/EditPage.js`. Statically inject a 5th entry to the `llm_configs` object within `uiSchema` targeting `audio_transcription` mapping title (`"Audio Transcription Model"`) while cleanly omitting `reasoning_effort` and `seed` attributes.
  2. Append `"audio_transcription"` to the nested hardcoded tier loop-array references within `handleFormChange` (attach a developer inline code comment acknowledging logically bypassed reasoning properties) and inside the data retrieval array block of `useEffect`.

### TASK-05: Base Model Provider Pre-reqs
- **Status:** <PENDING>
- **Spec Section:** Provider Architecture
- **Description:** 
  1. Navigate to `model_providers/base.py` and implement a concrete, empty `async def initialize(self): pass` method on the `BaseModelProvider` base class. This avoids immediate factory breakage allowing future polymorphism. **Critical**: This must not be tagged with `@abstractmethod`.

### TASK-06: Abstract Audio Provider
- **Status:** <PENDING>
- **Spec Section:** Provider Architecture, Technical Details
- **Description:** 
  1. Construct new abstract `AudioTranscriptionProvider` class within `model_providers/audio_transcription.py` inheriting off `BaseModelProvider`. 
  2. Guarantee explicitly declared `__init__(self, config)` invoking `super()` and setting `self._token_tracker = None`.
  3. Include an empty abstract signature `async def transcribe_audio(self, file_path: str, mime_type: str) -> str`.
  4. Include a explicit injection function `def set_token_tracker(self, tracker_func: Callable[..., Awaitable[None]]):`.

### TASK-07: Concrete Soniox Implementation
- **Status:** <PENDING>
- **Spec Section:** Provider Architecture, Transcription
- **Description:** 
  1. Establish `model_providers/sonioxAudioTranscription.py` mapping `SonioxAudioTranscriptionProvider` to its new `AudioTranscriptionProvider` parent.
  2. Fully override `initialize()` constructing an `AsyncSonioxClient` utilizing resolved API keys.
  3. In `transcribe_audio`: Perform the 4-phase async execution pattern exactly (`client.files.upload` -> `client.stt.create` -> `client.stt.wait` -> `client.stt.get_transcript`). Do not use convenience wrappers. 
  4. Evaluate token metric inputs against maths constraints manually (`audio_duration_ms / 120` & `transcript.text length * 0.3`) prior to dispatching the injected token tracking callback function.
  5. Employ an explicit `try/finally` block creating a decoupled background closure mapped to a class-level global `_background_tasks(set)` calling explicit API delete statements against both remote Soniox `file` and remote Soniox `transcription.id` artifacts bypassing `CancelledError` resource leaks.

### TASK-08: Factory Pattern Refactoring
- **Status:** <PENDING>
- **Spec Section:** Configuration, Provider Architecture
- **Description:** 
  1. Inside `services/model_factory.py`, rewrite type hinting to legally include `AudioTranscriptionProvider`. Add the explicit import at the top of the file.
  2. Decouple and re-hoist `State()`, `TokenConsumptionService`, and the `token_consumption_collection is None` conditional evaluation logic above the polymorphic type checks making it safely and uniformly available.
  3. Inject `elif isinstance(provider, AudioTranscriptionProvider):` branch to explicitly bypass LangChain completely whilst passing a callback invoking the universal token tracking sequence explicitly mimicking prior guards and returning `provider`.
  4. Explicitly run `await provider.initialize()` post-instantiation sequentially matching all providers.

### TASK-09: Central Processing Refactoring 
- **Status:** <PENDING>
- **Spec Section:** Output Format, Companion Fixes (Cross-Processor Impact)
- **Description:** 
  1. In `media_processors/base.py`, rewrite the `format_processing_result()` function enforcing `mime_type: str` along with optional `display_media_type: str`. Implement explicit logic that derives Title Prefix injection formatting dynamically while conditionally verifying `unprocessable_media = False`. 
  2. Ensure `BaseMediaProcessor.process_job()` inherently passes out both `job.mime_type` and `result.display_media_type` targeting sequential `format_processing_result` invocations. Update `asyncio.TimeoutError` except blocks forcing `unprocessable_media=True`. 
  3. Update overall unhandled exception routing parameters `_handle_unhandled_exception` dispatching the new args identically.

### TASK-10: Error Processors Updates
- **Status:** <PENDING>
- **Spec Section:** Companion Fixes (Cross-Processor Impact)
- **Description:** 
  1. In `media_processors/error_processors.py`, explicitly update both `process_media` methods in `CorruptMediaProcessor` and `UnsupportedMediaProcessor` to consistently pass `unprocessable_media=True` preventing formatting prefixes from improperly attaching themselves to standard failure returns.

### TASK-11: ImageVision Companion Fixes
- **Status:** <PENDING>
- **Spec Section:** Companion Fixes (Cross-Processor Impact)
- **Description:** 
  1. Navigate to `media_processors/image_vision_processor.py` expanding upon `except Exception as e:` blocks enforcing explicit implementations overriding outputs enforcing `unprocessable_media=True` against generalized moderation API pipeline failures or transcription API connection crashes.
  2. Alter native Factory `create_model_provider` pipeline calls setting the explicit label definitions passing `"image_moderation"` and `"image_transcription"` natively instead of the generalized `"media_processing"` value.

### TASK-12: Core Audio Processor Class
- **Status:** <PENDING>
- **Spec Section:** Processing Flow, Transcription
- **Description:** 
  1. Purge the existing stub processor from `media_processors/stub_processors.py`.
  2. Implement actual target processor `media_processors/audio_transcription_processor.py` linking purely into `BaseMediaProcessor`.
  3. Generate `create_model_provider` instance utilizing exactly `"audio_transcription"` context identifier routing through an awaiting `provider.transcribe_audio`.
  4. Create rigid handler capturing generalized Python `Exception as e:` ensuring safety across standard workers. Ensure tracking via outputs triggering generic errors and empty limits issuing generalized defaults ensuring strict implementation via `unprocessable_media=True` and `failed_reason` assignment.

### TASK-13: Factory & Service Registration
- **Status:** <PENDING>
- **Spec Section:** Processing Flow, Deployment Checklist
- **Description:** 
  1. Explicitly update `media_processors/factory.py` replacing the legacy `stub_processors` import pointer with `media_processors.audio_transcription_processor`.
  2. Explore `services/media_processing_service.py` extending the top level `DEFAULT_POOL_DEFINITIONS` expanding `"mimeTypes"` target values across `"AudioTranscriptionProcessor"` implicitly including mappings for audio subsets spanning (`audio/ogg`, `audio/mpeg`, `audio/wav`, `audio/webm`, `audio/mp4`, `audio/aac`, `audio/flac`, `audio/amr`, `audio/aiff`, `audio/x-m4a`, `audio/x-ms-asf`, `video/x-ms-asf`, and `application/vnd.ms-asf`).

### TASK-14: Test Modifications & Additions
- **Status:** <PENDING>
- **Spec Section:** Test Expectations
- **Description:** 
  1. Drill into `tests/test_image_transcription_support.py`, reformat parameter mismatches addressing `format_processing_result` signature changes manually assigning dummy variables (`mime_type=...`). Manually detach stub evaluations removing outdated Audio signature tests.
  2. Implement an isolated `tests/test_audio_transcription_support.py` driving signature validations ensuring workflow stability.
  3. Implement specific assertions for `BaseMediaProcessor` verifying internal exception handling mechanisms gracefully skip formatting injection bypassing prefix titles securely routing failure structures properly mapped through default unhandled exceptions and native timeouts.
