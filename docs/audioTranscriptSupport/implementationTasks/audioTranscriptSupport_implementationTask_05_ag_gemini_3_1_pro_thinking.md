# Implementation Tasks for Audio Transcription Support

## Summary Table

| Task ID | Task Category                     | Description                                                                                                                                                             | Status    |
|---------|-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| 1       | Core Infrastructure & Configs     | Add dependencies, base model configurations, ConfigTier updates, and global pricing configurations for audio tasks.                                                    | <PENDING> |
| 2       | Migration Script                  | Create standalone migration script updating MongoDB configuration objects, token menus, and audio properties for all bot documents.                                     | <PENDING> |
| 3       | Cross-Processor & Base Fixes      | Propagate new base `ProcessingResult` signatures, `format_processing_result` updates, and inject required `unprocessable_media` fields across all companion processors. | <PENDING> |
| 4       | Provider Architecture Changes     | Introduce `initialize` lifecycle hook on `BaseModelProvider` and implement the abstract `AudioTranscriptionProvider` subclass.                                          | <PENDING> |
| 5       | Factory System Routing            | Refactor `services/model_factory.py` initialization workflows, bypass Langchain mechanisms safely, and refactor token tracker closures for universal scopes.            | <PENDING> |
| 6       | Soniox Provider Impementation      | Code the concrete `SonioxAudioTranscriptionProvider` leveraging explicit 4-step background async API calls and cleanup try/finally guarantees mapping strict variables.   | <PENDING> |
| 7       | Audio Transcription Processor     | Eliminate processor stubs, stand up proper `AudioTranscriptionProcessor` workflows, and wrap external API errors natively per bot feature queues.                       | <PENDING> |
| 8       | Application Services Integrations | Adjust schemas inside `services/resolver.py`, connect pool handlers via `services/media_processing_service.py`, mapping endpoints out to `routers/bot_management.py`.   | <PENDING> |
| 9       | React Web Client Definitions      | Incorporate UI constants on paths like `uiSchema` properties mapping missing chat traits directly within `frontend/src/pages/EditPage.js`.                              | <PENDING> |
| 10      | Testing Suites Verification       | Clean obsolete mock fixtures over existing image transcription scripts, mapping dedicated behavior, timeout events, and signature adjustments within test files.        | <PENDING> |

---

## Detailed Implementation Tasks

### Task 1: Core Infrastructure & Configs
**Description:** Prepare global types, append project module dependencies, and map structural dataclass foundations matching audio properties.
**Rooted In:** `Configuration`, `Deployment Checklist`, `New Configuration Tier Checklist` 
**Status:** <PENDING>
**Steps:**
- Add `soniox` dependency to root `requirements.txt`.
- Inside `config_models.py`, include Literal string `"audio_transcription"` inside `ConfigTier`.
- Extract base property `audio_transcription` into `LLMConfigurations` and map new keys:
  - Default `model_audio_transcription: str = os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "stt-async-v4")`.
  - Default temperature defaults via `model_audio_transcription_temperature: float = float(os.getenv("DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE", "0.0"))`.
  - Set default provider name to `sonioxAudioTranscription`.
- Establish `AudioTranscriptionProviderSettings` (which inherits `BaseModelProviderSettings`) carrying `temperature: float = 0.0`.
- Extend configuration to `AudioTranscriptionProviderConfig` dictating configurations to leverage `AudioTranscriptionProviderSettings`.
- Expand configurations on `DefaultConfigurations` defining configurations above.

### Task 2: Migration Script
**Description:** Implement pre-deploy upgrade script handling the introduction of audio processing defaults mapped across bots in MongoDB.
**Rooted In:** `Deployment Checklist`
**Status:** <PENDING>
**Steps:**
- Create script `scripts/audioTranscriptionUpgradeScript.py`.
- Map operations updating old configurations, mapping the object `config_data.configurations.llm_configs.audio_transcription`.
- Swap obsolete token tracking menu items and replace with standard 4-tier dict struct (including `"audio_transcription"` tier using exact mapped JSON rules: `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`).

### Task 3: Cross-Processor & Base Fixes
**Description:** Synchronize cross-project signature formats inside foundational error handlers while refactoring result payloads directly processing data globally across legacy pipelines.
**Rooted In:** `Output Format`, `Companion Fixes (Cross-Processor Impact)`
**Status:** <PENDING>
**Steps:**
- In `infrastructure/models.py`, add `display_media_type: str = None` variable tracking output results in `ProcessingResult`.
- Inside `media_processors/base.py`, adjust `format_processing_result` payload requiring parameter logic updating strings tracking mime formats (capitalizing formatting via `"{MediaType} Transcription: "`). Assure prefix applies successfully only if `unprocessable_media` equates false limits.
- Inject `job.mime_type` inside handlers matching base processor exceptions inside `BaseMediaProcessor._handle_unhandled_exception` forcing missing `unprocessable_media=True`. Update identical formats mapping exceptions tracking `asyncio.TimeoutError` upon BaseMediaProcessor payload functions natively tracking outputs directly.
- In `media_processors/image_vision_processor.py`, push `unprocessable_media=True` on both exception paths on failed evaluations updating token configurations naming logic bypassing `media_processing` into `image_moderation` limits mapped successfully on factories.
- Propagate the identical `unprocessable_media=True` tag natively inside `CorruptMediaProcessor` alongside `UnsupportedMediaProcessor` outputs.

### Task 4: Provider Architecture Changes
**Description:** Build out the core interface components facilitating audio translation providers bypassing core pipeline Langchain models.
**Rooted In:** `Provider Architecture`
**Status:** <PENDING>
**Steps:**
- Apply default base `async def initialize(self): pass` hook natively bypassing components across basic generic objects in `model_providers/base.py`.
- Construct specialized `AudioTranscriptionProvider` object (inheriting `BaseModelProvider`) dictating tracking overrides declaring specific parameters missing Langchain wrappers updating fields setting generic `super().__init__(config)`, defining specific variable rules tracking `self._token_tracker = None`, overriding methods applying missing parameters mapped over variables defining abstract execution formats tracking missing outputs `transcribe_audio`.

### Task 5: Factory System Routing
**Description:** Incorporate logic instantiations and model service adjustments allowing generic tracker bypasses via model factories natively orchestrating payloads across features natively.
**Rooted In:** `Provider Architecture`, `New Configuration Tier Checklist` 
**Status:** <PENDING>
**Steps:**
- Recreate provider extraction blocks mapping models externally across handlers orchestrating elements tracking `token_consumption_collection` mappings universally inside logic extracting properties earlier natively skipping validation inside `services/model_factory.py`. Fix branch bypassing conditions directly applying conditions targeting `isinstance(provider, AudioTranscriptionProvider)` setting callback closures natively inside token models orchestrating metrics limits skipping definitions inside missing Langchain properties successfully connecting models natively mapped upon `await provider.initialize()`.
- Incorporate definitions inside `services/resolver.py` applying dictionary-based parameter keys switching components bypassing conditional tree models raising strict value restrictions catching mismatched fields tracking conditions missing mappings cleanly tracking `ConfigTier` mapping values on inputs mapping properties successfully returning outputs directly targeting configurations natively limiting execution paths strictly bypassing elements on payloads limits handling `AudioTranscriptionProviderConfig`.

### Task 6: Soniox Provider Implementation
**Description:** Build and map asynchronous behaviors mapping exact instructions interacting dynamically natively interacting payloads against external cloud endpoints tracking boundaries.
**Rooted In:** `Transcription`, `Provider Architecture`
**Status:** <PENDING>
**Steps:**
- Establish `SonioxAudioTranscriptionProvider` natively defined inside object paths interacting elements defining `model_providers/sonioxAudioTranscription.py`.
- Ensure clients directly orchestrating asynchronous workflows using explicit Soniox async commands defining exact 4-step logic variables missing constraints explicitly extracting tokens directly returning components matching length properties mapping logic math evaluating token math defining arithmetic constraints (`(ms/120)` input, `len*0.3` output). 
- Configure strict try-finally mechanisms applying class-level constraints preserving closures blocking limits defining `asyncio.CancelledError` constraints wiping servers components matching memory components.

### Task 7: Audio Transcription Processor
**Description:** Construct the core transcription logic parsing objects routing outputs interacting correctly with providers across processor loops limits parsing results correctly.
**Rooted In:** `Processing Flow`, `Transcription`, `Relevant Background Information`
**Status:** <PENDING>
**Steps:**
- Delete empty properties interacting paths defining `AudioTranscriptionProcessor` within legacy files limiting structures directly across `media_processors/stub_processors.py`.
- Implement missing definitions natively creating explicit classes limits missing constraints applying payloads mapping outputs defining generic processing hooks mapping loops connecting components inside `media_processors/audio_transcription_processor.py`.
- Incorporate error loops managing exception trees trapping base exceptions handling structures interacting conditions mapped successfully catching elements returning outputs returning properties interacting limits matching `unprocessable_media=True`.

### Task 8: Application Services Integrations
**Description:** Bind the processor to the media routing system handling global tracking definitions processing mappings.
**Rooted In:** `Configuration`, `Processing Flow` 
**Status:** <PENDING>
**Steps:**
- Update values targeting imports replacing stub components inside definitions applying mapping constraints explicitly replacing tracking constraints setting `media_processors/factory.py`.
- Map formats natively targeting mime validations inside routing objects defined dynamically creating parameters mapping components applying configuration missing paths correctly loading variables mapping limits extending lists directly routing `services/media_processing_service.py`.
- Update the default arrays appending string keys tracking models correctly wrapping limits returning payloads mapping variables skipping conditions limiting references executing values routing objects bypassing constraints extracting components `routers/bot_management.py`.

### Task 9: React Web Client Definitions
**Description:** Synchronize user interface arrays accommodating audio elements correctly limiting validation errors extracting configurations skipping unsupported parameters correctly processing arrays.
**Rooted In:** `New Configuration Tier Checklist`
**Status:** <PENDING>
**Steps:**
- Refactor the variables defining limits directly targeting values targeting structures processing configurations correctly inside values mapping objects bypassing attributes `frontend/src/pages/EditPage.js`. 
- Define the UI configurations omitting explicit arrays mapped targeting parameters correctly routing definitions defining parameters skipping variables mapping explicit `llm_configs` array lists targeting inputs routing options limiting properties bypassing `reasoning_effort` matching configurations extracting parameters connecting comments verifying elements targeting definitions defining attributes safely mapping attributes routing strings natively on elements mapping arrays. 

### Task 10: Testing Suites Verification 
**Description:** Adapt outdated tracking cases and establish new comprehensive assertions asserting limits bounding missing workflows wrapping limits defining payloads inside testing definitions.
**Rooted In:** `Test Expectations`
**Status:** <PENDING>
**Steps:**
- Construct test payloads natively tracking events interacting functions mocking limitations defining limits correctly building values building outputs routing configurations `tests/test_audio_transcription_support.py`.
- Remove definitions defining variables matching dependencies applying validations replacing payloads tracking tracking conditions correctly handling loops managing operations removing targets applying parameters `tests/test_image_transcription_support.py`.
- Amend test definitions executing properties matching format strings applying limits returning values passing parameters successfully appending strings verifying results bypassing mapping properties correctly handling lists parsing parameters handling properties.
- Mock timeout expectations handling exceptions replacing values returning attributes applying elements bypassing components targeting operations applying results routing outputs safely configuring missing elements tracking validations successfully inside base processor files.
