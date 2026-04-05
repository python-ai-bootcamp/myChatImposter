# Audio Transcription Support Implementation Tasks

| Task ID | Task Name | Status | Spec Dependencies |
|---------|-----------|--------|-------------------|
| 01 | Dependencies & Migrations | <PENDING> | Deployment Checklist |
| 02 | Configuration Models | <PENDING> | Configuration, Deployment Checklist, New Configuration Tier Checklist |
| 03 | Output Format Centralization & Testing Fixes | <PENDING> | Output Format, Test Expectations |
| 04 | Cross-Processor Error Fixes | <PENDING> | Companion Fixes, Test Expectations |
| 05 | Base Provider & Abstract Provider | <PENDING> | Provider Architecture |
| 06 | Concrete Soniox Provider | <PENDING> | Provider Architecture, Transcription |
| 07 | Provider Factory & Resolver Updates | <PENDING> | Provider Architecture, Configuration, New Configuration Tier Checklist |
| 08 | Frontend & Management Integration | <PENDING> | Configuration, New Configuration Tier Checklist |
| 09 | Audio Transcription Processor | <PENDING> | Processing Flow, Transcription |
| 10 | Testing: Audio Provider & Feature Tests | <PENDING> | Test Expectations |

## Task 01: Dependencies & Migrations
**Status:** <PENDING>
**Spec Section Implemented:** Deployment Checklist
**Description:** 
- Add `soniox` to `requirements.txt` environment constraints.
- Create a single DB migration script `scripts/audioTranscriptionUpgradeScript.py` to accomplish two goals: retroactively update existing bots' `llm_configs` to safely include missing `audio_transcription` metadata, and entirely replace the current system-wide 3-tier `token_menu` with a 4-tier map explicitly defining the `audio_transcription` fractional costs exactly as provided (`1.5`/`3.5`/`0`).

## Task 02: Configuration Models
**Status:** <PENDING>
**Spec Section Implemented:** Configuration, Deployment Checklist, New Configuration Tier Checklist
**Description:**
- Update `infrastructure/models.py` `ProcessingResult` to dynamically incorporate the transient Optional `display_media_type` field.
- Upgrade `config_models.py` by registering `AudioTranscriptionProviderSettings` and the wrapping `AudioTranscriptionProviderConfig`. Extend the global `ConfigTier` literals enum and `DefaultConfigurations` values providing standard failsafe backups natively.

## Task 03: Output Format Centralization & Testing Fixes
**Status:** <PENDING>
**Spec Section Implemented:** Output Format, Test Expectations
**Description:**
- Modify the global `format_processing_result` string formatter (in `media_processors/base.py`) to enforce a strictly required `mime_type` param and purely optional `display_media_type`. Establish semantic injection prepend logic generating prefixes like `[Audio Transcription: ...]` occurring strictly only if `unprocessable_media=False`.
- Update all existing `format_processing_result` mocked test assertions inside `tests/test_image_transcription_support.py` deliberately passing dummy strings to bypass identical breaking API signature changes. Remove broken stub tests there.

## Task 04: Cross-Processor Error Fixes
**Status:** <PENDING>
**Spec Section Implemented:** Companion Fixes, Test Expectations
**Description:**
- Inject runtime safeties dynamically injecting `unprocessable_media=True` when trapped inside the BaseMediaProcessor timeout handlers and fallback exception traps (`_handle_unhandled_exception`). Make sure `mime_type` correctly routes backwards towards formaters properly preventing `[Media Transcription: Timeout]` visual bleeding.
- Ensure `CorruptMediaProcessor` and `UnsupportedMediaProcessor` globally suppress formats when issuing their ProcessingResult (`processable_media=True`).
- Fix `ImageVisionProcessor` error trapping returning flag correctly to prevent injection leakages and patch the invocation of `create_model_provider` so it correctly identifies specific granular tracking tiers instead of pooling them generally under `media_processing`.

## Task 05: Base Provider & Abstract Provider
**Status:** <PENDING>
**Spec Section Implemented:** Provider Architecture
**Description:**
- Declare the abstract default placeholder operation `async def initialize(self): pass` within `model_providers/base.py`.
- Stand up `model_providers/audio_transcription.py` outlining the required `AudioTranscriptionProvider` architecture asserting asynchronous `transcribe_audio` constraints, alongside standard instantiation of generic tracker mechanisms via parameter assignment.

## Task 06: Concrete Soniox Provider
**Status:** <PENDING>
**Spec Section Implemented:** Provider Architecture, Transcription
**Description:**
- Provision `SonioxAudioTranscriptionProvider` in `model_providers/sonioxAudioTranscription.py`.
- Formulate external Soniox network operations routing securely across the explicit 4-step (`upload`->`create`->`wait`->`get_transcript`) SDK procedure.
- Construct the internal duration math calculating correct estimation costs passed out towards the injected callback. Lock network memory leaks inside strict two-phase `finally` block closures escaping runtime exception interruptions executing via class instance tracked `_background_tasks`.

## Task 07: Provider Factory & Resolver Updates
**Status:** <PENDING>
**Spec Section Implemented:** Provider Architecture, Configuration, New Configuration Tier Checklist
**Description:**
- Alter `services/resolver.py` dictating Tier dictionary dispatch lookups failing early using `ValueError`. Add the `audio_transcription` tier logic mapped seamlessly together natively.
- Upgrade `services/model_factory.py` to lift up global `TokenConsumptionService` instantiations universally visible. Include branching paths returning the raw wrapper instance correctly matching parameter boundaries while asserting active background client initiation logic mapping properly against the tracking logic.

## Task 08: Frontend & Management Integration
**Status:** <PENDING>
**Spec Section Implemented:** Configuration, New Configuration Tier Checklist
**Description:**
- Register `audio_transcription` string literals identically inside dynamic config fetching functions in `routers/bot_management.py`.
- Modify `frontend/src/pages/EditPage.js` registering statically the UI form objects omitting non-supported options like reason fields while manually iterating `audio_transcription` inside its form payload handler verifications ensuring full functional coverage. Add requested code comments.

## Task 09: Audio Transcription Processor
**Status:** <PENDING>
**Spec Section Implemented:** Processing Flow, Transcription 
**Description:**
- Create `media_processors/audio_transcription_processor.py` establishing direct `BaseMediaProcessor` inheriting integration initiating audio operations correctly capturing failed events mapping `unprocessable_media`.
- Delete previous native internal references referencing old Stub variants (`media_processors/stub_processors.py`, `media_processors/factory.py`).
- Implement mime route directives linking core processor against `.ogg`, `.mpeg` audio extensions actively within `services/media_processing_service.py`.

## Task 10: Testing: Audio Provider & Feature Tests
**Status:** <PENDING>
**Spec Section Implemented:** Test Expectations
**Description:** 
- Scaffold `tests/test_audio_transcription_support.py` simulating core Soniox HTTP mocked assertions guaranteeing callbacks match standard output mathematical bounds and closure cleanup events register.
- Create timeout unit-testing confirming `_handle_unhandled_exception` flags and `TimeoutError` exceptions reliably forward expected structure payloads safely masking output visual prefix text.
