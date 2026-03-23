# Implementation Tasks - Image Transcription Support

**Implementation Task ID**: `15_cr_gpt_5_3_codex`  
**Feature**: `imageTranscriptSupport`  
**Spec**: `docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`

---

## Task Summary Table

| Task ID | Task | Spec Root | Status |
|---|---|---|---|
| T01 | Remove dead `LLMProviderSettings` and `LLMProviderConfig` from `config_models.py` | Deployment Checklist #10 | <PENDING> |
| T02 | Add `ImageTranscriptionProviderSettings` (`detail`) and `ImageTranscriptionProviderConfig` | Requirements -> Configuration; Technical Details #1 | <PENDING> |
| T03 | Extend `ConfigTier` with `"image_transcription"` and add required tier-keys comment | Requirements -> Configuration; New Configuration Tier Checklist #1 | <PENDING> |
| T04 | Add required `LLMConfigurations.image_transcription: Field(...)` | Requirements -> Configuration; Deployment Checklist #4 | <PENDING> |
| T05 | Extend `DefaultConfigurations` with image-transcription provider/model/env defaults and explicit fallback values | Requirements -> Configuration; Deployment Checklist #2 | <PENDING> |
| T06 | Add resolver overload/branch for `image_transcription` returning `ImageTranscriptionProviderConfig` | Requirements -> Configuration; New Configuration Tier Checklist #2 | <PENDING> |
| T07 | Add `resolve_bot_language(bot_id) -> str` with direct config lookup and guaranteed `"en"` fallback on any exception | Requirements -> Configuration; Requirements -> Transcription | <PENDING> |
| T08 | Add `LLMProvider` abstract base in `model_providers/base.py` and synchronous-only constraint comment in `_resolve_api_key` | Technical Details #1 | <PENDING> |
| T09 | Refactor `ChatCompletionProvider` into empty type-marker inheriting from `LLMProvider` | Technical Details #1 | <PENDING> |
| T10 | Introduce shared `OpenAiMixin._build_llm_params()` and move OpenAI kwargs shaping there | Technical Details #1 | <PENDING> |
| T11 | Refactor `OpenAiChatProvider` to constructor-time `ChatOpenAI` init (`self._llm`) and remove debug prints/provider-side logger mutation | Technical Details #1 | <PENDING> |
| T12 | Create abstract `ImageTranscriptionProvider` with `transcribe_image(...)` contract | Technical Details #1 | <PENDING> |
| T13 | Create `OpenAiImageTranscriptionProvider` with constructor-time llm init, `detail` pop, multimodal payload, and normalization contract | Requirements -> Transcription; Technical Details #1/#2 | <PENDING> |
| T14 | Ensure transcription prompt text and language injection exactly match spec | Requirements -> Transcription | <PENDING> |
| T15 | Update `create_model_provider` return contract/docstring to include `ImageTranscriptionProvider` | Technical Details #1 | <PENDING> |
| T16 | Refactor `create_model_provider` to unified `isinstance(provider, LLMProvider)` token-tracking path with subtype-specific returns | Technical Details #1 | <PENDING> |
| T17 | Add defensive `obj.__module__ == module.__name__` filter in `find_provider_class` (keep non-abstract check) | Technical Details #1 | <PENDING> |
| T18 | Add `unprocessable_media: bool = False` to `ProcessingResult` with semantic docstring | Requirements -> Processing Flow | <PENDING> |
| T19 | Add module-level pure `format_processing_result(content, caption)` in `media_processors/base.py` | Requirements -> Output Format | <PENDING> |
| T20 | Refactor `BaseMediaProcessor.process_job()` to full spec lifecycle (caption extraction, timeout behavior, prefix-injection rules, unconditional format-before-persist) | Requirements -> Output Format; Requirements -> Transcription error handling | <PENDING> |
| T21 | Update timeout handling raw content to `"Processing timed out"` and set `unprocessable_media=True` while preserving `failed_reason` | Requirements -> Transcription (Error handling note) | <PENDING> |
| T22 | Refactor `_handle_unhandled_exception()` to `unprocessable_media=True`, raw `"Media processing failed"`, and first-step formatting | Requirements -> Output Format | <PENDING> |
| T23 | Remove `caption` parameter from abstract `process_media` and all 7 specified subclasses | Requirements -> Output Format | <PENDING> |
| T24 | Update `CorruptMediaProcessor` to new raw content contract, preserve `media_corrupt_` stripping, and set `unprocessable_media=True` | Requirements -> Output Format | <PENDING> |
| T25 | Update `UnsupportedMediaProcessor` to `Unsupported media type: {mime_type}` and set `unprocessable_media=True` | Requirements -> Output Format | <PENDING> |
| T26 | Update `StubSleepProcessor` and inheritors to raw `multimedia message with guid='...'` (no brackets, no "Transcripted" phrasing) | Requirements -> Output Format | <PENDING> |
| T27 | Add `"image/gif"` to `ImageVisionProcessor` pool definition in `DEFAULT_POOL_DEFINITIONS` | Requirements -> Processing Flow | <PENDING> |
| T28 | Create migration `migrate_pool_definitions_gif.py` to delete `_mediaProcessorDefinitions` so defaults reseed on boot | Requirements -> Processing Flow | <PENDING> |
| T29 | Implement `ImageVisionProcessor` moderation-first flow with flagged-path result (`unprocessable_media=True`, no failed reason) | Requirements -> Processing Flow | <PENDING> |
| T30 | Implement non-flagged path: resolve language in-branch, create transcription provider using feature name `"image_transcription"`, transcribe image bytes | Requirements -> Transcription | <PENDING> |
| T31 | Keep moderation provider call feature name `"media_processing"` and no try/except around transcription call | Requirements -> Transcription | <PENDING> |
| T32 | Extend token menu to independent `image_transcription` pricing entry (`0.25`, `0.025`, `2.0`) | Requirements -> Configuration | <PENDING> |
| T33 | Update `initialize_quota_and_bots.py` token_menu to 3 tiers with insert-if-not-exists behavior and explicit `image_moderation` omission comment | Deployment Checklist #5 | <PENDING> |
| T34 | Create `migrate_token_menu_image_transcription.py` hard-reset migration (delete token_menu, insert full 3-tier doc) | Deployment Checklist #6 | <PENDING> |
| T35 | Create `migrate_image_transcription.py` to backfill missing `llm_configs.image_transcription` in `COLLECTION_BOT_CONFIGURATIONS` | Deployment Checklist #1 | <PENDING> |
| T36 | Ensure all feature migration scripts use `infrastructure/db_schema.py` constants (no hardcoded collections) | Deployment Checklist #8 | <PENDING> |
| T37 | Keep `QuotaService.load_token_menu()` read-only (no self-healing writes) | Deployment Checklist #7 | <PENDING> |
| T38 | Update `get_bot_defaults` to include `image_transcription` defaults via new config types | Requirements -> Configuration; Deployment Checklist #3 | <PENDING> |
| T39 | Update `get_configuration_schema`: dynamic tier loop over `llm_configs_defs['properties'].keys()` and reasoning-effort patching for both provider settings classes | Requirements -> Configuration; New Configuration Tier Checklist #3 | <PENDING> |
| T40 | Add `GET /api/internal/bots/tiers` exposing `LLMConfigurations.model_fields.keys()` | New Configuration Tier Checklist #4 | <PENDING> |
| T41 | Update `frontend/src/pages/EditPage.js` to fetch tiers endpoint and replace hardcoded tier arrays in data normalization and form-change logic | New Configuration Tier Checklist #4 | <PENDING> |
| T42 | Add static `uiSchema.llm_configs.image_transcription` entry including full `provider_config` shape and `detail` title `"Image Detail Level"` | New Configuration Tier Checklist #5 | <PENDING> |
| T43 | Add provider tests: `detail` excluded from `ChatOpenAI(...)` kwargs and used only in image payload | Test Expectations | <PENDING> |
| T44 | Add callback continuity test ensuring factory-attached callback and transcription path share same llm object reference | Test Expectations | <PENDING> |
| T45 | Add transcription normalization tests for string, blocks, and fallback branch | Test Expectations | <PENDING> |
| T46 | Add processing tests for moderation-flagged output contract and timeout `unprocessable_media=True` path | Test Expectations | <PENDING> |
| T47 | Add formatting tests for unconditional bracket wrapping and caption append behavior on success and failure outcomes | Test Expectations | <PENDING> |
| T48 | Update unit tests to assert raw unbracketed `process_media()` returns; add integration assertions for final queue payload format `"[{MediaType} Transcription: {content}]"` | Test Expectations | <PENDING> |
| T49 | Update existing content-string assertions for unsupported/corrupt processors to new wording | Test Expectations | <PENDING> |
| T50 | Update `test_process_media_bot_id_signature` to robust key lookup (`"bot_id" in sig.parameters`) instead of index-based assertion | Test Expectations | <PENDING> |
| T51 | Prepare rollout verification checklist execution script/notes: pre/post counts, sample doc checks, and token menu validation | Deployment Checklist #9 | <PENDING> |
| T52 | Document accepted migration-window behavior (temporary 500 on unmigrated bot fetch) and enforce migration-before-code activation order | Deployment Checklist #4/#9 | <PENDING> |

---

## Flat Ordered Implementation Tasks

1. **T01** - Remove legacy dead code `LLMProviderSettings` and `LLMProviderConfig` from `config_models.py` to avoid parallel config abstractions. **Status:** <PENDING>  
   **Implements:** Deployment Checklist #10.

2. **T02** - Add `ImageTranscriptionProviderSettings` inheriting from `ChatCompletionProviderSettings` with `detail: Literal["low", "high", "original", "auto"] = "auto"`, and add `ImageTranscriptionProviderConfig` extending `ChatCompletionProviderConfig` with typed `provider_config`. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; Technical Details #1.

3. **T03** - Update `ConfigTier` to include `"image_transcription"` and add spec-mandated comment that `ConfigTier` + `LLMConfigurations` are the only tier-key definition points. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; New Configuration Tier Checklist #1.

4. **T04** - Add required `LLMConfigurations.image_transcription = Field(...)` (not optional) to enforce migration-first deployment behavior. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; Deployment Checklist #4.

5. **T05** - Extend `DefaultConfigurations` with `model_provider_name_image_transcription = "openAiImageTranscription"` and dedicated env-based defaults using explicit fallback values for temperature and reasoning effort. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; Deployment Checklist #2.

6. **T06** - Extend `resolve_model_config` overloads and implementation so `"image_transcription"` resolves as `ImageTranscriptionProviderConfig`. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; New Configuration Tier Checklist #2.

7. **T07** - Add `resolve_bot_language(bot_id)` using direct `get_global_state().configurations_collection.find_one(...)` and `config_data.configurations.user_details.language_code`, wrapped in `try/except Exception: return "en"` to never raise. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; Requirements -> Transcription.

8. **T08** - In `model_providers/base.py`, introduce abstract `LLMProvider` (`get_llm() -> BaseChatModel`) and add explicit synchronous/no-I-O constraint comment inside `_resolve_api_key()`. **Status:** <PENDING>  
   **Implements:** Technical Details #1.

9. **T09** - Refactor `model_providers/chat_completion.py` so `ChatCompletionProvider` is a pure type-marker subclass of `LLMProvider` with `pass` body (remove abstract get_llm declaration). **Status:** <PENDING>  
   **Implements:** Technical Details #1.

10. **T10** - Introduce centralized `OpenAiMixin._build_llm_params()` that performs model_dump/pop/filter flow and API-key resolution, without provider-specific side effects. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

11. **T11** - Refactor `OpenAiChatProvider` to constructor-time `ChatOpenAI` initialization (`self._llm`) and trivial `get_llm()`, removing debug prints and in-provider logger mutation. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

12. **T12** - Create `model_providers/image_transcription.py` with abstract `ImageTranscriptionProvider(LLMProvider, ABC)` and `async transcribe_image(base64_image, mime_type, language_code)`. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

13. **T13** - Create `model_providers/openAiImageTranscription.py` implementing constructor-time llm init, `self._detail = params.pop("detail", "auto")`, and `ChatOpenAI(**params)`. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; Technical Details #1/#2.

14. **T14** - Implement transcription request construction with multimodal `HumanMessage` payload (`image_url` data URI + `detail`) and exact hardcoded language-specific prompt text from spec. **Status:** <PENDING>  
    **Implements:** Requirements -> Transcription.

15. **T15** - Implement transcription normalization contract: string passthrough, deterministic text-block concatenation, and fallback `"Unable to transcribe image content"`. **Status:** <PENDING>  
    **Implements:** Requirements -> Transcription.

16. **T16** - Update `create_model_provider` return type and docstring to explicitly document subtype return behavior (`BaseChatModel` for chat completion, provider wrappers for moderation/transcription). **Status:** <PENDING>  
    **Implements:** Technical Details #1.

17. **T17** - Refactor `create_model_provider` flow to unified `isinstance(provider, LLMProvider)` token-tracking branch while preserving moderation no-tracking behavior. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

18. **T18** - Harden `find_provider_class` with `obj.__module__ == module.__name__` defensive filter while preserving `not inspect.isabstract(obj)` behavior and add explanatory doc note. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

19. **T19** - Add `unprocessable_media: bool = False` to `ProcessingResult` with spec-defined semantic docstring in `infrastructure/models.py`. **Status:** <PENDING>  
    **Implements:** Requirements -> Processing Flow.

20. **T20** - Implement pure module-level `format_processing_result(content, caption)` in `media_processors/base.py` to always bracket-wrap content and append caption suffix only when caption is non-empty. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

21. **T21** - Refactor `BaseMediaProcessor.process_job()` to the full spec lifecycle, including caption extraction once, timeout handling, prefix-injection gate (`not unprocessable_media and not failed_reason`), unconditional formatting before persistence/archive/delivery, and unchanged final cleanup semantics. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format; Requirements -> Transcription error handling.

22. **T22** - Update timeout branch result to raw `"Processing timed out"` plus `unprocessable_media=True` and preserved timeout `failed_reason` for `_failed` archival eligibility. **Status:** <PENDING>  
    **Implements:** Requirements -> Transcription (Error handling).

23. **T23** - Refactor `_handle_unhandled_exception` to raw `"Media processing failed"`, `unprocessable_media=True`, and enforce `format_processing_result(...)` as first mutation before persistence/archive/queue update. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

24. **T24** - Remove `caption` parameter from abstract `process_media` and all seven named subclasses: `ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

25. **T25** - Update `CorruptMediaProcessor` content contract to raw `Corrupted {media_type} media could not be downloaded`, preserve `mime_type.replace("media_corrupt_", "")`, and set `unprocessable_media=True`. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

26. **T26** - Update `UnsupportedMediaProcessor` to raw `Unsupported media type: {mime_type}` with `unprocessable_media=True`. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

27. **T27** - Update `StubSleepProcessor` family outputs to raw `multimedia message with guid='...'` (no brackets, no redundant wording), leaving `unprocessable_media` default success behavior. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

28. **T28** - Add `"image/gif"` support to `ImageVisionProcessor` pool MIME list in `services/media_processing_service.py` to match OpenAI non-animated GIF support. **Status:** <PENDING>  
    **Implements:** Requirements -> Processing Flow; External Resource (Image input requirements).

29. **T29** - Create `scripts/migrations/migrate_pool_definitions_gif.py` that deletes `_mediaProcessorDefinitions` from global configurations so next boot reseeds updated defaults. **Status:** <PENDING>  
    **Implements:** Requirements -> Processing Flow.

30. **T30** - Implement `ImageVisionProcessor` moderation-first sequence; flagged moderation returns `ProcessingResult(content="cannot process image as it violates safety guidelines", failed_reason=None, unprocessable_media=True)` and does not expose tags. **Status:** <PENDING>  
    **Implements:** Requirements -> Processing Flow.

31. **T31** - Implement non-flagged image path: call `resolve_bot_language(bot_id)` inside non-flagged branch, resolve image-transcription provider, call `await provider.transcribe_image(base64_image, mime_type, language_code)`. **Status:** <PENDING>  
    **Implements:** Requirements -> Transcription.

32. **T32** - Preserve feature-name split for token accounting: moderation call uses `"media_processing"` and transcription call uses `"image_transcription"`; avoid local try/except around transcription call. **Status:** <PENDING>  
    **Implements:** Requirements -> Transcription.

33. **T33** - Extend token menu schema/document to include dedicated `image_transcription` pricing (`input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`). **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration.

34. **T34** - Update `scripts/migrations/initialize_quota_and_bots.py` to include 3-tier token menu (`high`, `low`, `image_transcription`) with insert-if-not-exists semantics and code comment that `image_moderation` is intentionally omitted. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #5.

35. **T35** - Create `scripts/migrations/migrate_token_menu_image_transcription.py` hard-reset migration (delete existing `token_menu`, reinsert full menu). **Status:** <PENDING>  
    **Implements:** Deployment Checklist #6.

36. **T36** - Create `scripts/migrations/migrate_image_transcription.py` to backfill missing `config_data.configurations.llm_configs.image_transcription` for existing bot docs in `COLLECTION_BOT_CONFIGURATIONS`. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #1.

37. **T37** - Enforce migration contract across all new scripts: import collection constants from `infrastructure/db_schema.py` and avoid hardcoded collection names. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #8.

38. **T38** - Keep `QuotaService.load_token_menu()` behavior strictly read-only and avoid self-healing insert logic. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #7.

39. **T39** - Update `get_bot_defaults` in `routers/bot_management.py` to include `image_transcription` tier values from `DefaultConfigurations` via `ImageTranscriptionProviderConfig`. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; Deployment Checklist #3.

40. **T40** - Update `get_configuration_schema` surgery loop to iterate actual tier keys (`for prop_name in llm_configs_defs['properties'].keys():`) and apply reasoning-effort patching to both `ChatCompletionProviderSettings` and `ImageTranscriptionProviderSettings`. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; New Configuration Tier Checklist #3.

41. **T41** - Add lightweight endpoint `GET /api/internal/bots/tiers` that returns `LLMConfigurations.model_fields.keys()` for frontend consumption. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #4.

42. **T42** - Update `frontend/src/pages/EditPage.js` to fetch tiers during `fetchData`, store in state, and replace hardcoded tier arrays in both normalization and `handleFormChange`. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #4.

43. **T43** - Add `uiSchema.llm_configs.image_transcription` entry mirroring existing provider-config structure (`api_key_source`, `reasoning_effort`, `seed`, `FlatProviderConfigTemplate`) plus `detail` titled `"Image Detail Level"`. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #5.

44. **T44** - Add provider tests proving `detail` is excluded from `ChatOpenAI` constructor kwargs and used only when building transcription payload. **Status:** <PENDING>  
    **Implements:** Test Expectations.

45. **T45** - Add callback continuity tests verifying the same LLM object instance is used by both callback attachment in factory and transcription invocation. **Status:** <PENDING>  
    **Implements:** Test Expectations.

46. **T46** - Add transcription normalization tests for all three branches (string, content blocks, unsupported payload type). **Status:** <PENDING>  
    **Implements:** Test Expectations.

47. **T47** - Add processing tests for flagged moderation output contract and timeout contract (`unprocessable_media=True`). **Status:** <PENDING>  
    **Implements:** Test Expectations.

48. **T48** - Add formatting tests validating unconditional bracket wrapping and caption behavior for both success and failure outcomes. **Status:** <PENDING>  
    **Implements:** Test Expectations.

49. **T49** - Update unit/integration tests to align with caption-removal architecture: `process_media()` raw strings unbracketed, while `process_job()` delivered queue content is fully formatted with media-type transcription prefix in brackets. **Status:** <PENDING>  
    **Implements:** Test Expectations.

50. **T50** - Update existing assertion strings for unsupported/corrupt processors to new spec text and update `tests/test_image_vision_processor.py::test_process_media_bot_id_signature` to key-based signature assertion (`"bot_id" in sig.parameters`). **Status:** <PENDING>  
    **Implements:** Test Expectations.

51. **T51** - Add rollout verification execution tasks: pre/post counts for `COLLECTION_BOT_CONFIGURATIONS` and `COLLECTION_GLOBAL_CONFIGURATIONS`, sample bot-document verification, and token-menu verification for the new tier. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #9.

52. **T52** - Document/operationalize deployment ordering and accepted migration-window behavior (temporary 500s for unmigrated bots until migrations finish). **Status:** <PENDING>  
    **Implements:** Deployment Checklist #4/#9.

