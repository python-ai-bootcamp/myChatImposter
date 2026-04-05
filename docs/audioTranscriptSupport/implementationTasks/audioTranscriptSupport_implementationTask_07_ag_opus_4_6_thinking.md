# Audio Transcription Support Implementation Tasks

| Task | Description | Status |
| :--- | :--- | :--- |
| **01. Prerequisites** | Add Soniox dependency and `initialize()` method to base provider | `<PENDING>` |
| **02. Config Models** | Introduce ConfigTier and Audio Transcription settings schema | `<PENDING>` |
| **03. Migration Script** | Create script to upgrade global token_menu and bot LLMConfigs | `<PENDING>` |
| **04. Backend Resolver** | Update `resolve_model_config` to dynamic dictionary mapping | `<PENDING>` |
| **05. Settings Router** | Inject new tier in `/defaults` and `/schema` logic | `<PENDING>` |
| **06. Frontend Editor** | Add `audio_transcription` form schemas and UI validations | `<PENDING>` |
| **07. Formatting System** | Refactor `format_processing_result` for dynamic prefixes | `<PENDING>` |
| **08. Processor Mitigations** | Update existing base, error, and image processors to properly trigger/suppress injection | `<PENDING>` |
| **09. Model Provider Setup** | Create Base `AudioTranscriptionProvider` and `model_factory` routes | `<PENDING>` |
| **10. Soniox Adapter** | Implement 4-step Async transcription logic with token injection | `<PENDING>` |
| **11. Audio Processor** | Create `AudioTranscriptionProcessor` pipeline and remove old stub | `<PENDING>` |
| **12. Service Routing** | Update `factory.py` and MIME type lists in `MediaProcessingService` | `<PENDING>` |
| **13. Existing Tests Refactor** | Update `test_image_transcription_support.py` processing signatures tests | `<PENDING>` |
| **14. New Unit Tests** | Author `test_audio_transcription_support.py` coverage and base error tests | `<PENDING>` |

---

## Task Details

### 01. Prerequisites
- [ ] Requirements: Open `requirements.txt` and append `soniox`.
- [ ] BaseModelProvider: Open `model_providers/base.py`, add `async def initialize(self): pass` without the `@abstractmethod` decorator so child classes don't break.

### 02. Config Models
- [ ] Update `config_models.py`:
    - Add `"audio_transcription"` to the `ConfigTier` Literal.
    - Create `AudioTranscriptionProviderSettings(BaseModelProviderSettings)` with `temperature: float = 0.0`.
    - Create `AudioTranscriptionProviderConfig(BaseModelProviderConfig)` holding the `provider_config`.
    - Update `LLMConfigurations` to add `audio_transcription: AudioTranscriptionProviderConfig = Field(...)`.
    - Modify `DefaultConfigurations` to include dummy initialization attributes for `os.getenv` overrides (`"DEFAULT_MODEL_AUDIO_TRANSCRIPTION"`, `"DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE"`, etc.).

### 03. Migration Script
- [ ] Create Single Script `scripts/audioTranscriptionUpgradeScript.py`:
    - Process global configurations to upgrade the 3-tier `token_menu` to a 4-tier menu containing `high, low, image_transcription, audio_transcription`. Set `audio_transcription` pricing strictly to `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`.
    - Iterate `bot_config_collection` to ensure `config_data.configurations.llm_configs.audio_transcription` is populated for existing bots.

### 04. Backend Resolver
- [ ] Modify `services/resolver.py`:
    - Add overloaded type `Literal["audio_transcription"]` pointing to `AudioTranscriptionProviderConfig`.
    - Refactor `resolve_model_config` logic mapping string to objects via dictionary instead of hardcoded if/elif. Add an explicit error raising loop if tier is unregistered (`ValueError(f"Unknown config tier: {config_tier}")`).

### 05. Settings Router
- [ ] Modify `routers/bot_management.py`:
    - Manually append `"audio_transcription"` in `get_configuration_schema` array loops to prevent `$ref` crash.
    - Setup dummy entries in `get_bot_defaults` for `AudioTranscriptionProviderConfig`.

### 06. Frontend Editor
- [ ] Modify `frontend/src/pages/EditPage.js`:
    - `uiSchema`: Append `audio_transcription` properties under `llm_configs` to render naturally. State the "Dummy field" intentionally included. Note: Keep out `seed` and `reasoning_effort`.
    - Array Injection: Append `"audio_transcription"` to the nested loops in `handleFormChange` and the `useEffect` data hydration block to prevent validation resets. Add explanatory comment regarding undefined `reasoning_effort`.

### 07. Formatting System
- [ ] Models: Add `display_media_type: str = None` optional parameter to `ProcessingResult` inside `infrastructure/models.py`.
- [ ] Formatter Refactor (`media_processors/base.py`):
    - Redefine `format_processing_result` signature to mandate `mime_type: str` and `display_media_type: str = None`.
    - Implement the logic: dynamically parse or assign capitalize media type (`audio`, `image`, etc.) and prepend `"{MediaType} Transcription: "` ONLY IF `unprocessable_media=False`.

### 08. Processor Mitigations
- [ ] ImageVisionProcessor (`media_processors/image_vision_processor.py`):
    - Pass `unprocessable_media=True` inside its exception catches for moderation & transcription API crashes to block prefix prepending.
    - Adjust `create_model_provider` invocation feature names to precisely pass `"image_moderation"` and `"image_transcription"` instead of `"media_processing"`.
- [ ] Error Processors (`media_processors/error_processors.py`):
    - Update completions of `CorruptMediaProcessor` and `UnsupportedMediaProcessor` to assert `unprocessable_media=True`.
- [ ] Base Processor Updates (`media_processors/base.py`):
    - Update `TimeoutError` in `process_job` to pass `unprocessable_media=True`.
    - Update `_handle_unhandled_exception` to feed `mime_type=job.mime_type` and `unprocessable_media=True` when formatting raw results, to ensure safe formatting.
    - Synchronize parameter changes to `format_processing_result` across the file.

### 09. Model Provider Setup
- [ ] Abstract Layer: Create `model_providers/audio_transcription.py`:
    - Inherit `BaseModelProvider`. Define abstract `transcribe_audio`. Create `set_token_tracker` injection.
- [ ] Factory Updates: Modify `services/model_factory.py`:
    - Bump return type `Union`.
    - Lift `TokenConsumptionService` initialization upward cleanly.
    - Setup `elif isinstance(provider, AudioTranscriptionProvider):` path alongside LLMProvider, avoiding LangChain interfaces. Verify `.initialize()` invocations.

### 10. Soniox Adapter
- [ ] Concrete Soniox Class: Create `model_providers/sonioxAudioTranscription.py`:
    - Establish `AsyncSonioxClient` connection in `initialize()`.
    - Design the 4-step explicit transcription process (upload, create, wait, fetch).
    - Map accurate math-based token calculations for `token_tracker` metric aggregation.
    - Emulate cleanup workflow: wrap final explicit `file.delete_if_exists()` and job removal using `asyncio.create_task` with a global memory set `_background_tasks` to protect unlinked destruction from parental cancellation.

### 11. Audio Processor
- [ ] Rename/Replace Stub: Delete `AudioTranscriptionProcessor` from `media_processors/stub_processors.py`.
- [ ] Build Processor (`media_processors/audio_transcription_processor.py`):
    - Subclass `BaseMediaProcessor`.
    - Try to instantiate `feature_name="audio_transcription"` provider, call `transcribe_audio`.
    - Gracefully block `Exception` with returning `"Unable to transcribe audio content"` + `unprocessable_media=True` + `failed_reason="{e}"`. Use generic Exception specifically to omit `CancelledError`.

### 12. Service Routing
- [ ] Factory Register: Update `media_processors/factory.py` imports and `PROCESSOR_CLASS_MAP` for `AudioTranscriptionProcessor`.
- [ ] Media Router Configuration: Modify `services/media_processing_service.py` extending `DEFAULT_POOL_DEFINITIONS`:
    - Add `audio/ogg`, `audio/mpeg`, `audio/wav`, `audio/webm`, `audio/mp4`, `audio/aac`, `audio/flac`, `audio/amr`, `audio/aiff`, `audio/x-m4a`, `audio/x-ms-asf`, `video/x-ms-asf`, `application/vnd.ms-asf` mapped to `AudioTranscriptionProcessor`.

### 13. Existing Tests Refactor
- [ ] Fix Iteration Tests: Open `tests/test_image_transcription_support.py`.
    - Remove stub checks for `AudioTranscriptionProcessor`.
    - Fix all current mock interactions testing `format_processing_result` to now furnish `mime_type="image/jpeg"`.

### 14. New Unit Tests
- [ ] Coverage Buildout: Add `tests/test_audio_transcription_support.py`.
    - Test Soniox provider network operations layout.
    - Test Base processor unhandled exception mitigations enforcing `unprocessable_media=True`.
    - Test Provider factory tracking injections & exception safety.
