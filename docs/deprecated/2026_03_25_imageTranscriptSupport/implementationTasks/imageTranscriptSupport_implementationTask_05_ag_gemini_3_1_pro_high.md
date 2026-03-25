# Implementation Tasks Summary: Image Transcription Support

| Task ID | Task Description | Spec Section Reference | Status |
|---|---|---|---|
| T01 | Configuration Models Update | Configuration, Deployment Checklist, New Configuration Tier Checklist | <PENDING> |
| T02 | Frontend & API Setup for Dynamic Tiers | Configuration, New Configuration Tier Checklist | <PENDING> |
| T03 | Resolver Functions | Configuration | <PENDING> |
| T04 | Provider Sibling Architecture & Mixin Refactoring | Technical Details: 1) Provider Architecture | <PENDING> |
| T05 | Image Transcription Provider Implementation | Transcription, Technical Details: 1) Provider Architecture & 2) OpenAI Vision Parameter | <PENDING> |
| T06 | Factory & Class Resolution Updates | Processing Flow, Technical Details: 1) Provider Architecture | <PENDING> |
| T07 | Base Media Processor & Output Format Refactoring | Output Format | <PENDING> |
| T08 | ImageVisionProcessor Transcription Integration | Processing Flow, Transcription | <PENDING> |
| T09 | Database Migrations & Initializations | Configuration, Processing Flow, Technical Details: 3) Deployment Checklist | <PENDING> |
| T10 | Tests Implementation and Updates | Technical Details: 5) Test Expectations | <PENDING> |

---

## Detailed Implementation Tasks

### T01: Configuration Models Update
**Description:** 
- Implement `ImageTranscriptionProviderSettings` and `ImageTranscriptionProviderConfig` inheriting from their ChatCompletion counterparts and adding the `detail` config parameter. 
- Update `ConfigTier` Literal to include `"image_transcription"`. 
- Define `LLMConfigurations.image_transcription` as a strictly required field.
- Remove dead code objects `LLMProviderSettings` and `LLMProviderConfig`.
- Map new variables with fallback values into `DefaultConfigurations` (`DEFAULT_MODEL_IMAGE_TRANSCRIPTION`, `DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE`, `DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT`).
**Status:** <PENDING>

### T02: Frontend & API Setup for Dynamic Tiers
**Description:** 
- Expose a new lightweight `GET /api/internal/bots/tiers` endpoint in `routers/bot_management.py` yielding tiers dynamically.
- Refactor `frontend/src/pages/EditPage.js` to replace hardcoded tier arrays by reading from the new dynamically fetched tiers API endpoint, and inject the new `image_transcription` block containing the `detail` object exactly matching the `high`/`low` schemas.
- Update `get_configuration_schema()` dynamically to iterate over schema definitions using `for prop_name in llm_configs_defs['properties'].keys():` instead of hardcoded lists. Patch `reasoning_effort` schema bindings to apply to `ImageTranscriptionProviderSettings`.
**Status:** <PENDING>

### T03: Resolver Functions
**Description:** 
- Implement `@overload async def resolve_model_config` handling the `"image_transcription"` tier, enforcing `ImageTranscriptionProviderConfig` validation.
- Construct the `resolve_bot_language(bot_id: str) -> str` fallback resolver directly querying `get_global_state().configurations_collection`, ensuring safe extraction wrapped in broad try/catch clauses bypassing exceptions to silently fallback to `"en"`.
**Status:** <PENDING>

### T04: Provider Sibling Architecture & Mixin Refactoring
**Description:** 
- Create `LLMProvider` as a base type that mandates `get_llm()` return typed boundaries.
- Deprecate explicit state boundaries inside `ChatCompletionProvider`, mutating it into an empty abstract type-marker class.
- Abstract the OpenAI arguments compiler loop into `OpenAiMixin._build_llm_params()`, sharing dictionary configurations without exposing class coupling. Ensure `BaseModelProvider._resolve_api_key()` retains strictly synchronous definitions.
- Refactor `OpenAiChatProvider` via constructor-time initializations (`ChatOpenAI` initialized in `__init__`, `get_llm()` mapped to `self._llm`). Purge obsolete `httpx` logic logging and output statements from the method, relocating them to `main.py`.
**Status:** <PENDING>

### T05: Image Transcription Provider Implementation
**Description:** 
- Instantiate abstract `ImageTranscriptionProvider` demanding `transcribe_image(base64_image, mime_type, language_code)`.
- Draft `OpenAiImageTranscriptionProvider` mapping the `detail` parameter directly inside multimodal structures without forwarding it as `ChatOpenAI` kwargs.
- Enforce the textual normalization output formatting handling deterministic string generations regardless of explicit response block typings, wrapping unknown formats safely with `Unable to transcribe image content`.
**Status:** <PENDING>

### T06: Factory & Class Resolution Updates
**Description:** 
- Strengthen class reflection safety in `find_provider_class()` within `utils/provider_utils.py` by ensuring `obj.__module__ == module.__name__`.
- Rework `create_model_provider()` to intelligently bind `TokenTrackingCallback` to models enforcing standard `isinstance(provider, LLMProvider)` checks, ensuring correct tracking instances regardless of returned factory wrappers. Apply strict `feature_name` isolation for tracing.
**Status:** <PENDING>

### T07: Base Media Processor & Output Format Refactoring 
**Description:** 
- Strip `caption` from `process_media` abstracts inside `BaseMediaProcessor`, `ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, and `DocumentProcessor`.
- Develop `format_processing_result()` as a unified, decoupled pure formatting function appending static captions and brackets safely.
- Rework `process_job()` workflows explicitly controlling `Prefix Injection` unconditionally applying `format_processing_result` prior to any persistence mechanisms mimicking the detailed snippet defined in the spec.
- Propagate `unprocessable_media: bool = False` additions inside `infrastructure/models.py#ProcessingResult`. Revamp `_handle_unhandled_exception` definitions mitigating legacy wrapper strings.
**Status:** <PENDING>

### T08: ImageVisionProcessor Transcription Integration
**Description:** 
- Authorize `image/gif` configurations in `DEFAULT_POOL_DEFINITIONS` bindings inside `services/media_processing_service.py`.
- Enhance the `ImageVisionProcessor` to correctly yield unprocessable outcomes mapping static failure responses bypassing logs when `moderation_result.flagged` resolves to true. 
- Map successful moderation results explicitly invoking the sibling `transcribe_image` architectures mapped strictly without internal logic wrapping exceptions mirroring timeout dependencies.
**Status:** <PENDING>

### T09: Database Migrations & Initializations
**Description:** 
- Formulate scripts initializing missing config definitions: `scripts/migrations/migrate_image_transcription.py` covering standard payload extensions prioritizing DB schemas.
- Implement the comprehensive replacement mechanism: `scripts/migrations/migrate_token_menu_image_transcription.py` obliterating existing global menus replacing tokens cleanly mimicking the new three-tier structure and adjust `scripts/migrations/initialize_quota_and_bots.py` simultaneously. 
- Build `scripts/migrations/migrate_pool_definitions_gif.py` actively destroying MongoDB instances of `_mediaProcessorDefinitions` to mandate immediate runtime pool reloads.
**Status:** <PENDING>

### T10: Tests Implementation and Updates
**Description:** 
- Modify test suites enforcing strict parameter reflections matching modifications applied to `test_process_media_bot_id_signature` logic overriding hardcoded array evaluations.
- Rewrite legacy payload tests referencing old content derivations replacing asserts with refactored `UnsupportedMediaProcessor` and `CorruptMediaProcessor` string models conforming dynamically.
- Develop unit integration coverage mapping details parameters against constructors ensuring robust factory callbacks binding natively through normalization paths executing validations asserting formatting structures.
**Status:** <PENDING>
