# Implementation Tasks: audioTranscriptSupport

| Task ID | Description | Status |
|---|---|---|
| 1 | core configuration & model updates | PENDING |
| 2 | media processing flow & routing updates | PENDING |
| 3 | provider architecture implementation | PENDING |
| 4 | transcription logic & cleanup | PENDING |
| 5 | companion fixes & prefix injection refactoring | PENDING |
| 6 | migration & deployment preparation | PENDING |
| 7 | frontend UI updates | PENDING |
| 8 | testing & verification | PENDING |

---

### 1. Core Configuration & Model Updates
- **Update ConfigTier**: Add `"audio_transcription"` to `ConfigTier` Literal in `config_models.py`. (Spec: Configuration #14, New Configuration Tier Checklist #1)
- **Update LLMConfigurations**: Add `audio_transcription: AudioTranscriptionProviderConfig` as a required field in `LLMConfigurations` class in `config_models.py`. (Spec: Configuration #13, #207)
- **Add AudioTranscriptionProviderSettings**: Create `AudioTranscriptionProviderSettings` inheriting from `BaseModelProviderSettings` with `temperature: float = 0.0`. (Spec: Configuration #12)
- **Add AudioTranscriptionProviderConfig**: Create `AudioTranscriptionProviderConfig` extending `BaseModelProviderConfig` with `provider_config: AudioTranscriptionProviderSettings`. (Spec: Configuration #13)
- **Update DefaultConfigurations**: Add `model_provider_name_audio_transcription`, `model_audio_transcription`, and `model_audio_transcription_temperature` with appropriate `os.getenv` fallbacks (e.g., `"stt-async-v4"`, `"0.0"`) to `DefaultConfigurations` in `config_models.py`. (Spec: Deployment Checklist #2)
- **Update ProcessingResult Model**: Add optional `display_media_type: str = None` attribute to `ProcessingResult` dataclass in `infrastructure/models.py`. (Spec: Prefix Injection Refactoring #46, Background Information #65)

### 2. Media Processing Flow & Routing Updates
- **Refactor AudioTranscriptionProcessor**: Move `AudioTranscriptionProcessor` from `media_processors/stub_processors.py` to its own file `media_processors/audio_transcription_processor.py`. Delete the old stub. (Spec: Processing Flow #21)
- **Update Processor Factory**: Update `media_processors/factory.py` to import `AudioTranscriptionProcessor` from its new location and ensure it's in `PROCESSOR_CLASS_MAP`. (Spec: Deployment Checklist #6)
- **Expand Supported MIME Types**: Update `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` to include Soniox-supported audio types (e.g., `audio/mpeg`, `audio/wav`, `audio/webm`, etc.) and route them to `AudioTranscriptionProcessor`. (Spec: Processing Flow #22)

### 3. Provider Architecture Implementation
- **BaseModelProvider Update**: Add a no-op `async def initialize(self): pass` to `BaseModelProvider` in `model_providers/base.py`. (Spec: Provider Architecture #181)
- **Abstract AudioTranscriptionProvider**: Create `model_providers/audio_transcription.py` defining the abstract `AudioTranscriptionProvider` class with `transcribe_audio` method and tracking setup. (Spec: Provider Architecture #127)
- **Concrete SonioxAudioTranscriptionProvider**: Create `model_providers/sonioxAudioTranscription.py` implementing the `SonioxAudioTranscriptionProvider` using the explicit 4-step async pattern for Soniox. (Spec: Transcription #29, Provider Architecture #130)
- **Update Model Factory**:
    - Update `create_model_provider` return type annotation. (Spec: Provider Architecture #178)
    - Fix `TokenConsumptionService` initialization to be universal. (Spec: Provider Architecture #179)
    - Add `AudioTranscriptionProvider` branch and inject tracking closure. (Spec: Provider Architecture #180)
    - Call `await provider.initialize()` for all providers. (Spec: Provider Architecture #181)

### 4. Transcription Logic & Cleanup
- **Implement transcribe_audio**: In `SonioxAudioTranscriptionProvider`, implement the logic for upload, transcribe, wait, and get_transcript. (Spec: Transcription #29)
- **Math-based Token Estimation**: Implement token estimation in `SonioxAudioTranscriptionProvider` using `audio_duration_ms` and transcript text length. (Spec: Transcription #30, Provider Architecture #156)
- **Background Cleanup Task**: Implement the `try/finally` block in `transcribe_audio` that creates an `asyncio.task` for background cleanup (deleting file and transcription) to avoid leaks and bypass timeouts. Maintain strong references in a set. (Spec: Transcription #31)
- **Processor implementation**: Implement `process_media` in `AudioTranscriptionProcessor` to call the provider and handle errors as structured `ProcessingResult` with `unprocessable_media=True`. (Spec: Transcription #34)

### 5. Companion Fixes & Prefix Injection Refactoring
- **Refactor format_processing_result**:
    - Add required `mime_type` and optional `display_media_type` parameters to `format_processing_result` in `media_processors/base.py`. (Spec: Prefix Injection Refactoring #46)
    - Implement dynamic capitalization and conditional prefixing (`"{MediaType} Transcription: "`) only if `unprocessable_media` is `False`. (Spec: Prefix Injection Refactoring #46)
- **Update Base Processor Lifecycle**: Update `BaseMediaProcessor.process_job()` to pass `job.mime_type` and `result.display_media_type` to `format_processing_result`. (Spec: Prefix Injection Refactoring #46)
- **Update Global Exception Handling**: Update `BaseMediaProcessor._handle_unhandled_exception` to pass `job.mime_type` and set `unprocessable_media=True`. (Spec: Companion Fixes #41, Prefix Injection Refactoring #46)
- **Update Timeout Handling**: Update `BaseMediaProcessor.process_job()` timeout block to set `unprocessable_media=True`. (Spec: Companion Fixes #40)
- **Update Other Processors**:
    - Update `ImageVisionProcessor` to set `unprocessable_media=True` in error paths and pass correct `feature_name` to `create_model_provider`. (Spec: Companion Fixes #37, #38)
    - Update `CorruptMediaProcessor` and `UnsupportedMediaProcessor` to set `unprocessable_media=True`. (Spec: Companion Fixes #39)

### 6. Migration & Deployment Preparation
- **Requirements Update**: Add `soniox` package to `requirements.txt`. (Spec: Deployment Checklist #0)
- **Migration Script**: Create `scripts/audioTranscriptionUpgradeScript.py` that accomplishments ALL of the following: (1) Updates existing bot configs (add `audio_transcription` tier and `token_menu` update) and (2) Replaces `token_menu` with full 4-tier menu and pricing. (Spec: Deployment Checklist #1)

### 7. Frontend UI Updates
- **EditPage logic**: Update `frontend/src/pages/EditPage.js` to include `audio_transcription` in `useEffect` (for explicit/environment source normalization) and `handleFormChange` (to bypass reasoning effort logic). (Spec: New Configuration Tier Checklist #4, #5)
- **uiSchema Update**: Add `audio_transcription` entry to `uiSchema` in `EditPage.js` with correct title and omitting irrelevant fields. (Spec: New Configuration Tier Checklist #4)

### 8. Testing & Verification
- **Update Image Transcription Tests**: Fix existing `format_processing_result` test fixtures in `tests/test_image_transcription_support.py` with the new `mime_type` parameter. (Spec: Test Expectations #220)
- **New Audio Transcription Tests**: Create `tests/test_audio_transcription_support.py` and implement comprehensive tests for the new processor, including signature verification and timeout/exception logic. (Spec: Test Expectations #221, #225, #226)
- **Verify Prefix Injection**: Verify that prefixes are correctly injected for successful transcriptions and suppressed for failures/corrupt media. (Spec: Test Expectations #223, #225, #226)
