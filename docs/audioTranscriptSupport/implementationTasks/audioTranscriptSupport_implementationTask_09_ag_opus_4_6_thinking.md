# Implementation Tasks Summary

| Task | Description | Status |
| --- | --- | --- |
| 1 | Add `initialize()` to `BaseModelProvider` | <PENDING> |
| 2 | Refactor `model_factory.py` initialization and tracking | <PENDING> |
| 3 | Update model configurations and default schemas | <PENDING> |
| 4 | Refactor `resolver.py` configuration mapping | <PENDING> |
| 5 | Update routing schemas and bot default config templates | <PENDING> |
| 6 | Update frontend `EditPage.js` to include the new tier | <PENDING> |
| 7 | Create `AudioTranscriptionProvider` abstract class | <PENDING> |
| 8 | Create `SonioxAudioTranscriptionProvider` implementation | <PENDING> |
| 9 | Update `ProcessingResult` and `format_processing_result` | <PENDING> |
| 10 | Update `BaseMediaProcessor` flow and error safety nets | <PENDING> |
| 11 | Implement `AudioTranscriptionProcessor` logic | <PENDING> |
| 12 | Adjust pool routing and remove old stub implementation | <PENDING> |
| 13 | Mitigate cross-processor impacts (Image & Error Processors) | <PENDING> |
| 14 | Create database migration script for configuration structure | <PENDING> |
| 15 | Update existing image transcription tests for new signature | <PENDING> |
| 16 | Create new test suite for audio transcription | <PENDING> |

---

## Detailed Implementation Tasks

### 1. Add `initialize()` to `BaseModelProvider`
- **Description:** Edit `model_providers/base.py` to add a no-op `async def initialize(self): pass` method to the `BaseModelProvider`. Ensure it is NOT marked with `@abstractmethod` so that existing providers inherit it safely without crashing.
- **Spec Mapping:** "1) Provider Architecture" => Refactor Initialization
- **Status:** <PENDING>

### 2. Refactor `model_factory.py` initialization and tracking
- **Description:** In `services/model_factory.py`:
  - Import `from model_providers.audio_transcription import AudioTranscriptionProvider`.
  - Extract the instantiation of `TokenConsumptionService` and its `get_global_state()` dictionary fetch outside of the type-check block so it is universally available to all provider branches, preserving the `if token_consumption_collection is not None:` guard exactly.
  - Add `elif isinstance(provider, AudioTranscriptionProvider): return provider` branch and replicate the exact tracking guard pattern to attach the token tracker.
  - Add an `await provider.initialize()` step immediately after instantiation for all providers.
  - Update `create_model_provider` return type annotation to include `AudioTranscriptionProvider`.
- **Spec Mapping:** "1) Provider Architecture" => Refactor Initialization
- **Status:** <PENDING>

### 3. Update model configurations and default schemas
- **Description:** In `config_models.py`:
  - Add `"audio_transcription"` to the `ConfigTier` Literal type.
  - Create `AudioTranscriptionProviderSettings` inheriting from `BaseModelProviderSettings` with `temperature: float = 0.0`.
  - Create `AudioTranscriptionProviderConfig` inheriting from `BaseModelProviderConfig` redefining `provider_config: AudioTranscriptionProviderSettings`.
  - Add the `audio_transcription: AudioTranscriptionProviderConfig` field to `LLMConfigurations`.
  - Update `DefaultConfigurations` to include `model_provider_name_audio_transcription`, `model_audio_transcription` from `os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "stt-async-v4")`, and `model_audio_transcription_temperature` from `os.getenv("DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE", "0.0")`.
- **Spec Mapping:** "Configuration" section, "2) Deployment Checklist", "3) New Configuration Tier Checklist"
- **Status:** <PENDING>

### 4. Refactor `resolver.py` configuration mapping
- **Description:** In `services/resolver.py`:
  - Add Literal overload for `"audio_transcription"` returning `AudioTranscriptionProviderConfig`.
  - Refactor `resolve_model_config` body replacing hardcoded if/elif logic with a dynamic dictionary-based registry mapping `ConfigTier` to Pydantic Models.
  - Enforce an explicit `if config_class is None:` raising `ValueError(f"Unknown config tier: {config_tier}")`.
- **Spec Mapping:** "Configuration", "3) New Configuration Tier Checklist"
- **Status:** <PENDING>

### 5. Update routing schemas and bot default config templates
- **Description:** In `routers/bot_management.py`:
  - In `get_configuration_schema`, manually append `"audio_transcription"` to the hardcoded array list for schema tier extraction (around line 365).
  - In `get_bot_defaults`, include `audio_transcription` using `AudioTranscriptionProviderConfig` and the new variables from `DefaultConfigurations`.
- **Spec Mapping:** "Configuration", "2) Deployment Checklist", "3) New Configuration Tier Checklist"
- **Status:** <PENDING>

### 6. Update frontend `EditPage.js` to include the new tier
- **Description:** In `frontend/src/pages/EditPage.js`:
  - Add `audio_transcription` object into `uiSchema.configurations.llm_configs` with title `"Audio Transcription Model"`. Omit the `reasoning_effort` and `seed` properties. Don't hide the dummy temperature field.
  - Manually append `"audio_transcription"` to the two hardcoded tier arrays inside `handleFormChange` loops and add a brief code comment explaining the bypass.
  - Append `"audio_transcription"` to the third array present inside the `useEffect` data fetching block.
- **Spec Mapping:** "3) New Configuration Tier Checklist"
- **Status:** <PENDING>

### 7. Create `AudioTranscriptionProvider` abstract class
- **Description:** Create a new file `model_providers/audio_transcription.py`. Define `AudioTranscriptionProvider` extending `BaseModelProvider` with `__init__` checking `super().__init__(config)`, initializing `self._token_tracker = None`, an abstract `async def transcribe_audio(self, file_path: str, mime_type: str) -> str`, and a concrete `def set_token_tracker(self, tracker_func)`.
- **Spec Mapping:** "1) Provider Architecture"
- **Status:** <PENDING>

### 8. Create `SonioxAudioTranscriptionProvider` implementation
- **Description:** Create a new file `model_providers/sonioxAudioTranscription.py`. Create `SonioxAudioTranscriptionProvider` implementing `AudioTranscriptionProvider`.
  - Implement `initialize` creating an `AsyncSonioxClient`.
  - Implement `transcribe_audio` with explicit 4-step async pattern (`upload`, `create`, `wait`, `get_transcript`), verify `file_id` use in `stt.create`.
  - Ensure token tracker injection callback receives estimated tokens: `input_tokens=int(audio_duration_ms/120)`, `output_tokens=int(len*0.3)`.
  - Use `try/finally` block to call an explicitly created `asyncio.create_task` closure that gracefully deletes the `transcription.id` and `file.id`, managing active tasks with a global tracking `set()` and `add_done_callback` to prevent garbage collection sweeps.
- **Spec Mapping:** "Transcription", "1) Provider Architecture"
- **Status:** <PENDING>

### 9. Update `ProcessingResult` and `format_processing_result`
- **Description:**
  - Add `display_media_type: str = None` optional field to `infrastructure/models.py`'s `ProcessingResult`.
  - Refactor `format_processing_result` in `media_processors/base.py` to declare a **required** `mime_type: str` parameter and an optional `display_media_type: str = None`.
  - Update formatter logic to logically prefix outputs as `"{MediaType} Transcription: "` (capitalizing the MIME prefix) unless `unprocessable_media` is `True`.
- **Spec Mapping:** "Output Format", "Relevant Background Information"
- **Status:** <PENDING>

### 10. Update `BaseMediaProcessor` flow and error safety nets
- **Description:** In `media_processors/base.py`:
  - Update calls to `format_processing_result` inside `process_job` adding `job.mime_type` and `result.display_media_type`.
  - Update `asyncio.TimeoutError` except block to pass `unprocessable_media=True` inside its `ProcessingResult`.
  - Update fallback error handling `_handle_unhandled_exception` to pass `unprocessable_media=True` and `mime_type=job.mime_type` to `format_processing_result`.
- **Spec Mapping:** "Companion Fixes (Cross-Processor Impact)"
- **Status:** <PENDING>

### 11. Implement `AudioTranscriptionProcessor` logic
- **Description:** Create `media_processors/audio_transcription_processor.py`. Define `AudioTranscriptionProcessor` extending `BaseMediaProcessor`.
  - Refactor `process_media` to resolve an `AudioTranscriptionProvider` using tier `"audio_transcription"` and feature name `"audio_transcription"`.
  - Invoke `transcribe_audio` directly.
  - For successful replies, return `ProcessingResult(content=transcript_text)`.
  - Ensure failure/empty strings explicitly track failure via `failed_reason` and `unprocessable_media=True`.
  - Wrap logic in a blanket `except Exception as e:` block (avoiding `BaseException`), returning `ProcessingResult(content="Unable to transcribe...", failed_reason=f"Transcription error: {e}", unprocessable_media=True)`.
- **Spec Mapping:** "Processing Flow", "Transcription"
- **Status:** <PENDING>

### 12. Adjust pool routing and remove old stub implementation
- **Description:**
  - In `media_processors/stub_processors.py`, delete the `AudioTranscriptionProcessor` stub class.
  - In `media_processors/factory.py`, update the import path from `stub_processors` to `media_processors.audio_transcription_processor`.
  - In `services/media_processing_service.py`, expand the pool definitions for `AudioTranscriptionProcessor` to encompass `audio/ogg`, `audio/mpeg`, `audio/wav`, `audio/webm`, `audio/mp4`, `audio/aac`, `audio/flac`, `audio/amr`, `audio/aiff`, `audio/x-m4a`, `audio/x-ms-asf`, `video/x-ms-asf`, and `application/vnd.ms-asf`.
- **Spec Mapping:** "Processing Flow", "2) Deployment Checklist"
- **Status:** <PENDING>

### 13. Mitigate cross-processor impacts (Image & Error Processors)
- **Description:**
  - In `media_processors/image_vision_processor.py`, explicitly set `unprocessable_media=True` on BOTH error-path `ProcessingResult` blocks (mod API crash and transcription API crash).
  - Also update `ImageVisionProcessor` to explicitly pass `"image_moderation"` and `"image_transcription"` as feature names instead of `"media_processing"` in `create_model_provider` calls.
  - In `media_processors/error_processors.py`, update `process_media` in both `CorruptMediaProcessor` and `UnsupportedMediaProcessor` to explicitly pass `unprocessable_media=True`.
- **Spec Mapping:** "Companion Fixes (Cross-Processor Impact)"
- **Status:** <PENDING>

### 14. Create database migration script for configuration structure
- **Description:** Create `scripts/audioTranscriptionUpgradeScript.py` that processes both structure components.
  - Add `audio_transcription` tier to `llm_configs` array inside MongoDB document states.
  - Replace `global_configurations`'s `token_menu` with a 4-tier list: `high`, `low`, `image_transcription`, and explicitly `audio_transcription` mapping strictly to `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`.
- **Spec Mapping:** "Configuration", "2) Deployment Checklist"
- **Status:** <PENDING>

### 15. Update existing image transcription tests for new signature
- **Description:** Edit `tests/test_image_transcription_support.py`.
  - Update all `format_processing_result()` unit tests to explicitly pass the new required argument `mime_type="image/jpeg"` to prevent immediate TypeError failures.
  - Deliberately delete tests related to `AudioTranscriptionProcessor` class signature checking, delegating them instead to a new test file.
- **Spec Mapping:** "4) Test Expectations"
- **Status:** <PENDING>

### 16. Create new test suite for audio transcription
- **Description:** Create `tests/test_audio_transcription_support.py`.
  - Assert the new `AudioTranscriptionProcessor` class structure strictly adheres to the parameterless signature.
  - Write test rendering fake audio content reading output string.
  - Verify formatting effectively handles returned string.
  - Add explicit unit tests tracking timeout behavior from `BaseMediaProcessor.process_job` successfully asserting `unprocessable_media=True`.
  - Add test asserting `_handle_unhandled_exception` successfully returns bare error messaging.
- **Spec Mapping:** "4) Test Expectations"
- **Status:** <PENDING>
