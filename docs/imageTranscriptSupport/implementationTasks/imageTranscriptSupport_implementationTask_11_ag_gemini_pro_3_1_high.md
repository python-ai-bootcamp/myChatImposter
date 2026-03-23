# Implementation Tasks: Image Transcription Support

| Task ID | Description | Spec Sections Covered | Status |
|---|---|---|---|
| TASK-01 | Configuration Models & Resolver Updates | Configuration, Deployment Checklist, New Configuration Tier Checklist | <PENDING> |
| TASK-02 | API Routing Updates | Configuration, Deployment Checklist, New Configuration Tier Checklist | <PENDING> |
| TASK-03 | Frontend Updates | New Configuration Tier Checklist | <PENDING> |
| TASK-04 | Database Migration Scripts | Processing Flow, Deployment Checklist | <PENDING> |
| TASK-05 | Model Providers Architecture Refactoring | Provider Architecture | <PENDING> |
| TASK-06 | Image Transcription Provider Implementation | Transcription, Provider Architecture, OpenAI Vision Parameter | <PENDING> |
| TASK-07 | Model Factory & Utils Updates | Provider Architecture | <PENDING> |
| TASK-08 | Base Media Processor Logic & Signature Refactoring | Output Format, Processing Flow | <PENDING> |
| TASK-09 | Image Vision Processor Specific Logic Updates | Processing Flow, Transcription | <PENDING> |
| TASK-10 | Testing Updates | Test Expectations | <PENDING> |

## Detailed Tasks

### TASK-01: Configuration Models & Resolver Updates
**Description**: 
- Update `config_models.py` to parse and store the new `image_transcription` tier by extending `ConfigTier`, creating `ImageTranscriptionProviderSettings`, `ImageTranscriptionProviderConfig`, appending into `LLMConfigurations`, and adding default vars inside `DefaultConfigurations`.
- Delete unused legacy models `LLMProviderSettings` and `LLMProviderConfig`.
- Update `services/resolver.py` with the overloaded `resolve_model_config` handling the new tier type validation.
- Implement database retrieval fallback logic inside `resolve_bot_language` in `services/resolver.py`.
**Spec Sections Covered**: Configuration, Deployment Checklist, New Configuration Tier Checklist
**Status**: <PENDING>

### TASK-02: API Routing Updates
**Description**: 
- Overhaul schema extraction loop in `routers/bot_management.py` `get_configuration_schema` to dynamically iterate over `llm_configs_defs['properties'].keys()`.
- Inject `reasoning_effort` schema UI title patches dynamically for `ImageTranscriptionProviderSettings`.
- Expand `get_bot_defaults` merging `image_transcription` configurations logically.
- Develop a new endpoint `GET /api/internal/bots/tiers` returning keys mapped over `LLMConfigurations.model_fields.keys()`.
**Spec Sections Covered**: Configuration, Deployment Checklist, New Configuration Tier Checklist
**Status**: <PENDING>

### TASK-03: Frontend Updates
**Description**: 
- Rewrite `frontend/src/pages/EditPage.js` removing `getAvailableTiers` logic reliant on hardcoded schemas arrays.
- Make components await array contents via `GET /api/internal/bots/tiers` directly.
- Include static formatting entries modeling `image_transcription` inside `uiSchema` matching `high`/`low` styling setups, incorporating the custom `detail` element binding.
**Spec Sections Covered**: New Configuration Tier Checklist
**Status**: <PENDING>

### TASK-04: Database Migration Scripts
**Description**: 
- Prepare explicit database update utility spanning `scripts/migrations/migrate_image_transcription.py`.
- Patch `initialize_quota_and_bots.py` seeding `token_menu` dynamically reflecting `image_transcription` quotas.
- Draft reset mechanism dropping legacy structures in `scripts/migrations/migrate_token_menu_image_transcription.py`.
- Introduce MongoDB document deletion routine inside `scripts/migrations/migrate_pool_definitions_gif.py` forcing system to read initializations.
**Spec Sections Covered**: Processing Flow, Deployment Checklist
**Status**: <PENDING>

### TASK-05: Model Providers Architecture Refactoring
**Description**: 
- Organize strict typing layouts: construct `LLMProvider` abstractions within `model_providers/base.py`.
- Deprecate operational commands from `ChatCompletionProvider` into empty interfaces.
- Specify abstractions dictating methods like `transcribe_image` within abstract `ImageTranscriptionProvider`.
- Isolate repetitive kwargs building techniques migrating them toward `OpenAiMixin`.
- Remove rogue external logging assignments transferring `httpx` initializations towards `main.py`.
- Align initialization steps locking `ChatOpenAI` into constructors over method derivations, asserting synchrony through `BaseModelProvider._resolve_api_key`.
**Spec Sections Covered**: Provider Architecture
**Status**: <PENDING>

### TASK-06: Image Transcription Provider Implementation
**Description**: 
- Formulate concrete variant `OpenAiImageTranscriptionProvider` leveraging `OpenAiMixin` configurations.
- Parse `detail` logic independently avoiding unsupported kwargs conflicts.
- Implement strictly formatted multimodal requests (`transcribe_image`) parsing normalized output standards across varying content block arrays dictating `"Unable to transcribe image content"` constraints where required.
**Spec Sections Covered**: Transcription, Provider Architecture, OpenAI Vision Parameter
**Status**: <PENDING>

### TASK-07: Model Factory & Utils Updates
**Description**: 
- Optimize conditional structures mapping tracking abstractions in `services/model_factory.py` applying hooks natively tracking token distributions against `isinstance(provider, LLMProvider)`.
- Reassign varying interface variables resolving pure provider wrappers versus extracted subclasses.
- Lock strict member lookup paths utilizing `obj.__module__ == module.__name__` defensive filters bypassing generalized abstract evaluations across `utils/provider_utils.py`.
**Spec Sections Covered**: Provider Architecture
**Status**: <PENDING>

### TASK-08: Base Media Processor Logic & Signature Refactoring
**Description**: 
- Supply descriptive fallback logic altering `ProcessingResult` flags encompassing `unprocessable_media = False` by default.
- Integrate missing `image/gif` bindings within internal pool definitions matching OpenAI implementations natively.
- Deploy centralized `format_processing_result` functions managing bracket allocations.
- Remove redundant properties across subclasses (`caption` fields) matching strict implementations on `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`.
- Reconstruct `BaseMediaProcessor.process_job()` copying the definitive snippet provided, enforcing lifecycle persistence bindings mapping timeouts appropriately.
**Spec Sections Covered**: Processing Flow, Output Format
**Status**: <PENDING>

### TASK-09: Image Vision Processor Specific Logic Updates
**Description**: 
- Integrate execution mappings initiating moderation plugins conditionally inside `ImageVisionProcessor`.
- Suppress transcription steps producing formatted overrides (`unprocessable_media=True`) against explicitly flagged moderation checks.
- Handle dynamic language mapping fallbacks gracefully triggering localized generation queries encapsulating tokens strictly reflecting `"image_transcription"` namespaces.
**Spec Sections Covered**: Processing Flow, Transcription
**Status**: <PENDING>

### TASK-10: Testing Updates
**Description**: 
- Write expansive tests validating unprocessable mapping paths spanning moderation blockers alongside processing timeouts ensuring retention metrics trigger appropriate archive tracking routines.
- Overturn outdated mock structures applying deterministic tuple indexing against dictionary searches reflecting `assert "bot_id" in sig.parameters` directly inside `tests/test_image_vision_processor.py`.
- Assert unified formatting functions enforce trailing bracket formats wrapping dynamically applied payloads regardless of internal exceptions checking.
**Spec Sections Covered**: Test Expectations
**Status**: <PENDING>
