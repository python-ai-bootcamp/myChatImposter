# Implementation Tasks: Audio Transcription Support

## Task Summary
| ID | Task | Status | Spec Sections |
|---|---|---|---|
| 1 | Configuration & Config Models | <PENDING> | Configuration, Deployment Checklist, New Configuration Tier Checklist |
| 2 | Provider Architecture Setup | <PENDING> | Configuration, Transcription, Provider Architecture |
| 3 | Model Factory Updates | <PENDING> | Provider Architecture |
| 4 | ProcessingResult & BaseMediaProcessor Updates | <PENDING> | Companion Fixes, Output Format |
| 5 | Cross-Processor Issue Mitigations | <PENDING> | Companion Fixes |
| 6 | AudioTranscriptionProcessor Implementation | <PENDING> | Processing Flow, Transcription |
| 7 | Service & Routing Layer Integration | <PENDING> | Processing Flow, Deployment Checklist, New Configuration Tier Checklist |
| 8 | Frontend Configuration Updates | <PENDING> | New Configuration Tier Checklist |
| 9 | Database Migration & Requirements | <PENDING> | Deployment Checklist |
| 10 | Testing & Validation | <PENDING> | Test Expectations |

## Task Details

### 1. Configuration & Config Models
**Status**: <PENDING>
**Implements Spec Sections**: Configuration, Deployment Checklist, New Configuration Tier Checklist
- Create `AudioTranscriptionProviderSettings` (with dummy `temperature: float = 0.0`) in `config_models.py`.
- Modify `AudioTranscriptionProviderConfig` to use `AudioTranscriptionProviderSettings` in `config_models.py`.
- Add `"audio_transcription"` to `ConfigTier` Literal type.
- Add `"audio_transcription"` to `LLMConfigurations`.
- Extend `DefaultConfigurations` with audio transcription variables and defaults (`model_audio_transcription`, `model_audio_transcription_temperature`).
- Define `LLMConfigurations.audio_transcription` as a strictly required field using `Field(...)`.

### 2. Provider Architecture Setup
**Status**: <PENDING>
**Implements Spec Sections**: Configuration, Provider Architecture
- In `model_providers/base.py`, add `async def initialize(self): pass` to `BaseModelProvider` (CRITICAL: commit before factory updates).
- Create `model_providers/audio_transcription.py` with abstract class `AudioTranscriptionProvider` featuring `set_token_tracker` and `transcribe_audio`.
- Create `model_providers/sonioxAudioTranscription.py` with `SonioxAudioTranscriptionProvider` containing `initialize` and the explicitly defined 4-step `transcribe_audio` method with complete try/finally loop (saving & tracking the async cleanup `_background_tasks` without GC wiping).

### 3. Model Factory Updates
**Status**: <PENDING>
**Implements Spec Sections**: Provider Architecture
- Update `create_model_provider` return type annotation in `services/model_factory.py`.
- Extract `TokenConsumptionService` instantiation out of the `LLMProvider` type-check branch.
- Add an explicit `elif isinstance(provider, AudioTranscriptionProvider):` branch to `create_model_provider` to bypass LangChain, injecting the token tracker carefully avoiding `None` crashes.
- Add `await provider.initialize()` post-instantiation in the factory. Ensure the system safely catches all exceptions throughout. Add `from model_providers.audio_transcription import AudioTranscriptionProvider` import at the top of the file.

### 4. ProcessingResult & BaseMediaProcessor Updates
**Status**: <PENDING>
**Implements Spec Sections**: Output Format, Companion Fixes
- Add `display_media_type: str = None` optional attribute to the `ProcessingResult` dataclass in `infrastructure/models.py`.
- Refactor `format_processing_result` in `media_processors/base.py` to declare required `mime_type` and optional `display_media_type` params. Implement prefix injection logic (`"{MediaType} Transcription: "`) conditioned precisely on `unprocessable_media = False`.
- Update `BaseMediaProcessor.process_job()` to pass `job.mime_type` and `result.display_media_type` to `format_processing_result` and apply `unprocessable_media=True` on `asyncio.TimeoutError`.
- Update `BaseMediaProcessor._handle_unhandled_exception()` to explicitly pass `unprocessable_media=True` and `mime_type=job.mime_type`.

### 5. Cross-Processor Issue Mitigations
**Status**: <PENDING>
**Implements Spec Sections**: Companion Fixes
- Update `ImageVisionProcessor` in `media_processors/image_vision_processor.py` to add `unprocessable_media=True` to both error-path returns.
- Update `ImageVisionProcessor` to pass `"image_moderation"` and `"image_transcription"` instead of `"media_processing"` when invoking `create_model_provider()`.
- Update `CorruptMediaProcessor` and `UnsupportedMediaProcessor` in `media_processors/error_processors.py` to explicitly set `unprocessable_media=True` in their returned `ProcessingResult`.

### 6. AudioTranscriptionProcessor Implementation
**Status**: <PENDING>
**Implements Spec Sections**: Processing Flow, Transcription
- Remove `AudioTranscriptionProcessor` stub from `media_processors/stub_processors.py`.
- Create `media_processors/audio_transcription_processor.py` referencing `"audio_transcription"` for fetching `create_model_provider` configuration. Implement logic inheriting from `BaseMediaProcessor` and executing `transcribe_audio`.
- Wrap `transcribe_audio` call in `try/except Exception as e:` block and return `ProcessingResult(..., unprocessable_media=True)`.
- Re-route `AudioTranscriptionProcessor` import in `media_processors/factory.py` to point to the new file.

### 7. Service & Routing Layer Integration
**Status**: <PENDING>
**Implements Spec Sections**: Processing Flow, Configuration, New Configuration Tier Checklist
- Expand `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` to route all specified Soniox-supported audio MIME types to `AudioTranscriptionProcessor`.
- Expand type hints in `resolve_model_config` (`services/resolver.py`) with `Literal["audio_transcription"]`, and refactor resolving body to dictionary-based mapping to firmly reject unknowns with Python exceptions.
- Add `"audio_transcription"` to hardcoded tier fallback logic and update `get_bot_defaults` within `routers/bot_management.py`. Note explicit `append` commands as requested via spec.

### 8. Frontend Configuration Updates
**Status**: <PENDING>
**Implements Spec Sections**: New Configuration Tier Checklist
- Manually append static `"audio_transcription"` tier into `uiSchema` within `frontend/src/pages/EditPage.js` specifying explicit title `"Audio Transcription Model"`.
- Insert `"audio_transcription"` into the multiple tier arrays inside `handleFormChange` loops and `useEffect` block in `frontend/src/pages/EditPage.js`. Adding required bypass note inside code comments validating its integration without `reasoning_effort` logic.

### 9. Database Migration & Requirements
**Status**: <PENDING>
**Implements Spec Sections**: Deployment Checklist
- Add `soniox` package pinning inside root repository `requirements.txt`.
- Develop the unified script `scripts/audioTranscriptionUpgradeScript.py` allocating default `"audio_transcription"` logic into previous models inside MongoDB. Create robust 4-tier token_menu configuration replacement for system billing usage (explicit custom pricing array).

### 10. Testing & Validation
**Status**: <PENDING>
**Implements Spec Sections**: Test Expectations
- Supply the `mime_type` stub argument inside `tests/test_image_transcription_support.py` within `format_processing_result` unit tests. Remove any stub-processor tests pointing to `AudioTranscriptionProcessor`.
- Define `tests/test_audio_transcription_support.py` specifically focusing around testing integration logic parsing the transcript strings safely with fallback variables properly generated.
- Extend `BaseMediaProcessor` tests with assertions pointing strictly towards `unprocessable_media=True` being forwarded to API output inside Timeout / Fallback contexts.
- Check `test_media_processing_service.py` ensuring new configurations length verification updates.
