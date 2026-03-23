# Implementation Tasks - Image Transcription Support

**Implementation Task ID**: `16_cr_gpt_5_4_xhigh`  
**Feature**: `imageTranscriptSupport`  
**Spec**: `docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`

---

## Task Summary Table

| Task ID | Task | Spec Root | Status |
|---|---|---|---|
| T01 | Remove dead `LLMProviderSettings` and `LLMProviderConfig` from `config_models.py` | Deployment Checklist #10 | <PENDING> |
| T02 | Add `ImageTranscriptionProviderSettings` and `ImageTranscriptionProviderConfig` | Requirements -> Configuration; Technical Details #1 | <PENDING> |
| T03 | Extend `ConfigTier` / `LLMConfigurations` with required `image_transcription` tier and source-of-truth comment | Requirements -> Configuration; Deployment Checklist #4; New Configuration Tier Checklist #1 | <PENDING> |
| T04 | Extend `DefaultConfigurations` with image-transcription provider/model/env defaults and explicit fallback values | Requirements -> Configuration; Deployment Checklist #2 | <PENDING> |
| T05 | Add resolver overload/branch for `image_transcription` returning `ImageTranscriptionProviderConfig` | Requirements -> Configuration; New Configuration Tier Checklist #2 | <PENDING> |
| T06 | Add non-throwing `resolve_bot_language(bot_id)` with direct config lookup and guaranteed `"en"` fallback | Requirements -> Configuration; Requirements -> Transcription | <PENDING> |
| T07 | Introduce abstract `LLMProvider` and add synchronous-only `_resolve_api_key()` constraint comment | Technical Details #1 | <PENDING> |
| T08 | Refactor `ChatCompletionProvider` into an empty `LLMProvider` type marker | Technical Details #1 | <PENDING> |
| T09 | Add shared `OpenAiMixin._build_llm_params()` for OpenAI chat/transcription providers | Technical Details #1 | <PENDING> |
| T10 | Refactor `OpenAiChatProvider` to constructor-time `ChatOpenAI` init and move `httpx` logger setup to `main.py` | Technical Details #1 | <PENDING> |
| T11 | Create abstract `ImageTranscriptionProvider` with `transcribe_image(...)` contract | Technical Details #1 | <PENDING> |
| T12 | Create `OpenAiImageTranscriptionProvider` constructor/init flow with `detail` pop and no model/detail guardrails | Requirements -> Configuration; Technical Details #1/#2 | <PENDING> |
| T13 | Implement transcription prompt, multimodal payload, and normalization contract | Requirements -> Transcription; Technical Details #1/#2 | <PENDING> |
| T14 | Update `create_model_provider` return annotation/docstring for chat, moderation, and transcription return contracts | Technical Details #1 | <PENDING> |
| T15 | Refactor `create_model_provider` to unified `isinstance(provider, LLMProvider)` tracking flow with subtype-specific returns | Technical Details #1 | <PENDING> |
| T16 | Harden `find_provider_class` with `obj.__module__ == module.__name__` filter and defensive doc note | Technical Details #1 | <PENDING> |
| T17 | Add `unprocessable_media: bool = False` to `ProcessingResult` with spec-defined semantic docstring | Requirements -> Processing Flow | <PENDING> |
| T18 | Add pure module-level `format_processing_result(content, caption)` helper in `media_processors/base.py` | Requirements -> Output Format | <PENDING> |
| T19 | Refactor `BaseMediaProcessor.process_job()` to the full shared lifecycle from the spec snippet | Requirements -> Output Format; Requirements -> Transcription (Error handling) | <PENDING> |
| T20 | Update timeout handling to raw `"Processing timed out"` plus `unprocessable_media=True` while preserving `failed_reason` | Requirements -> Transcription (Error handling) | <PENDING> |
| T21 | Refactor `_handle_unhandled_exception()` to format first, mark `unprocessable_media=True`, and avoid double wrapping | Requirements -> Output Format | <PENDING> |
| T22 | Remove the `caption` parameter from `process_media` across the base class and all 7 affected processors | Requirements -> Output Format | <PENDING> |
| T23 | Update `CorruptMediaProcessor` to the new raw-content contract while preserving `media_corrupt_` stripping | Requirements -> Output Format | <PENDING> |
| T24 | Update `UnsupportedMediaProcessor` to the new raw-content contract | Requirements -> Output Format | <PENDING> |
| T25 | Update `StubSleepProcessor` and inheriting stubs to the new raw-content contract | Requirements -> Output Format | <PENDING> |
| T26 | Add `"image/gif"` to `ImageVisionProcessor` pool definitions | Requirements -> Processing Flow; External Resource | <PENDING> |
| T27 | Create `migrate_pool_definitions_gif.py` to delete `_mediaProcessorDefinitions` so GIF support reseeds on boot | Requirements -> Processing Flow | <PENDING> |
| T28 | Implement the flagged-moderation outcome in `ImageVisionProcessor` | Requirements -> Processing Flow | <PENDING> |
| T29 | Implement the non-flagged transcription path in `ImageVisionProcessor` with in-branch language resolution and separate provider instances | Requirements -> Transcription | <PENDING> |
| T30 | Extend the token-menu/pricing contract so `image_transcription` is billed as its own tier | Requirements -> Configuration | <PENDING> |
| T31 | Create `migrate_image_transcription.py` to backfill missing bot-level `llm_configs.image_transcription` | Deployment Checklist #1 | <PENDING> |
| T32 | Update `initialize_quota_and_bots.py` to seed a 3-tier token menu and keep insert-if-not-exists behavior | Deployment Checklist #5 | <PENDING> |
| T33 | Create `migrate_token_menu_image_transcription.py` to hard-reset the `token_menu` document | Deployment Checklist #6 | <PENDING> |
| T34 | Preserve read-only `QuotaService.load_token_menu()` behavior and enforce `db_schema` constants across all new migrations | Deployment Checklist #7/#8 | <PENDING> |
| T35 | Update `get_bot_defaults()` to include `image_transcription` using the new config types/defaults | Requirements -> Configuration; Deployment Checklist #3 | <PENDING> |
| T36 | Update `get_configuration_schema()` to use dynamic tier surgery and patch `reasoning_effort` for both provider-settings models | Requirements -> Configuration; New Configuration Tier Checklist #3 | <PENDING> |
| T37 | Add `GET /api/internal/bots/tiers` backed by `LLMConfigurations.model_fields.keys()` | New Configuration Tier Checklist #4 | <PENDING> |
| T38 | Align `routers/bot_ui.py` creation defaults with the required `image_transcription` tier so restricted creation still builds valid `BotConfiguration` objects | Requirements -> Configuration; Deployment Checklist #4 | <PENDING> |
| T39 | Update `EditPage.js` to fetch tiers and replace the hardcoded tier arrays in normalization/change handling | New Configuration Tier Checklist #4 | <PENDING> |
| T40 | Add `EditPage.js` `uiSchema.llm_configs.image_transcription` entry including the `detail` field | New Configuration Tier Checklist #5 | <PENDING> |
| T41 | Update backend schema/defaults/tiers API tests to cover new tier exposure and dynamic behavior | Requirements -> Configuration; New Configuration Tier Checklist #3/#4 | <PENDING> |
| T42 | Update `EditPage.test.js` mocks/assertions for the extra `/bots/tiers` fetch and fourth tier UI | New Configuration Tier Checklist #4/#5 | <PENDING> |
| T43 | Add provider tests proving `detail` is filtered out of `ChatOpenAI(...)` kwargs | Test Expectations | <PENDING> |
| T44 | Add callback continuity tests ensuring factory attachment and transcription use the same LLM instance | Test Expectations | <PENDING> |
| T45 | Add transcription normalization tests for string, content-block, and fallback branches | Test Expectations | <PENDING> |
| T46 | Add flagged moderation contract tests for `unprocessable_media=True` and static policy text | Test Expectations | <PENDING> |
| T47 | Add `format_processing_result` tests for unconditional brackets and caption append/omit behavior | Test Expectations | <PENDING> |
| T48 | Add timeout / unhandled-exception / final queue-format tests for the centralized media-processing flow | Test Expectations | <PENDING> |
| T49 | Update existing processor assertion strings and refactor the signature test to key-based lookup | Test Expectations | <PENDING> |
| T50 | Update existing backend/integration configuration fixtures to include required `image_transcription` data | Deployment Checklist #4/#9; Test Expectations | <PENDING> |
| T51 | Add rollout verification and deployment-order tasks covering counts, sample docs, token menu validation, and accepted temporary 500s | Deployment Checklist #9 | <PENDING> |

---

## Flat Ordered Implementation Tasks

1. **T01** - Remove the unused dead-code models `LLMProviderSettings` and `LLMProviderConfig` from `config_models.py` so the new image-transcription config family has a single unambiguous hierarchy. **Status:** <PENDING>  
   **Implements:** Deployment Checklist #10.

2. **T02** - Add `ImageTranscriptionProviderSettings` (inherits `ChatCompletionProviderSettings`, adds `detail: Literal["low", "high", "original", "auto"] = "auto"`) and `ImageTranscriptionProviderConfig` (inherits `ChatCompletionProviderConfig`, retypes `provider_config`) in `config_models.py`. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; Technical Details #1.

3. **T03** - Extend `ConfigTier` with `"image_transcription"`, add the spec-mandated comment above both `ConfigTier` and `LLMConfigurations`, and make `LLMConfigurations.image_transcription` a required field so the model shape is authoritative and migration-first. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; Deployment Checklist #4; New Configuration Tier Checklist #1.

4. **T04** - Extend `DefaultConfigurations` with `model_provider_name_image_transcription = "openAiImageTranscription"` plus `DEFAULT_MODEL_IMAGE_TRANSCRIPTION`, `DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE`, and `DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT`, all with the exact fallback values from the spec. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; Deployment Checklist #2.

5. **T05** - Add the `resolve_model_config(bot_id, "image_transcription") -> ImageTranscriptionProviderConfig` overload and implementation branch in `services/resolver.py`, importing `ImageTranscriptionProviderConfig` explicitly for precise typing. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; New Configuration Tier Checklist #2.

6. **T06** - Add `resolve_bot_language(bot_id: str) -> str` to `services/resolver.py`, performing the explicit `get_global_state().configurations_collection.find_one(...)` lookup of `config_data.configurations.user_details.language_code` and wrapping the whole block in `try/except Exception: return "en"` so it never raises. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; Requirements -> Transcription.

7. **T07** - In `model_providers/base.py`, introduce abstract `LLMProvider` (`get_llm() -> BaseChatModel`) and add the explicit comment that `_resolve_api_key()` must remain strictly synchronous and perform no external I/O. **Status:** <PENDING>  
   **Implements:** Technical Details #1.

8. **T08** - Refactor `model_providers/chat_completion.py` so `ChatCompletionProvider` becomes an empty type-marker subclass of `LLMProvider` with a `pass` body and no local abstract `get_llm()` declaration. **Status:** <PENDING>  
   **Implements:** Technical Details #1.

9. **T09** - Introduce a shared `OpenAiMixin._build_llm_params()` that centralizes the `model_dump()` / pop custom fields / resolve API key / drop `None` optional values flow, while keeping `_resolve_api_key()` in `BaseModelProvider`. **Status:** <PENDING>  
   **Implements:** Technical Details #1.

10. **T10** - Refactor `OpenAiChatProvider` to build and store `self._llm = ChatOpenAI(...)` during `__init__`, make `get_llm()` a trivial accessor, remove the debug `print()` calls, and move provider-side `httpx` logger mutation into backend startup configuration in `main.py`. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

11. **T11** - Create `model_providers/image_transcription.py` with the abstract `ImageTranscriptionProvider(LLMProvider, ABC)` contract declaring `async transcribe_image(base64_image, mime_type, language_code) -> str`. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

12. **T12** - Create `model_providers/openAiImageTranscription.py` so `OpenAiImageTranscriptionProvider` uses `OpenAiMixin`, constructor-time `ChatOpenAI` initialization, `self._detail = params.pop("detail", "auto")`, and deliberately does not add model/detail compatibility validation beyond the config schema. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; Technical Details #1/#2.

13. **T13** - Implement `OpenAiImageTranscriptionProvider.transcribe_image(...)` to build the exact hardcoded language-aware prompt with no system message, send a multimodal `HumanMessage` containing a base64 `image_url` data URI plus `detail`, and normalize the response exactly per the three-branch string/content-block/fallback contract. **Status:** <PENDING>  
    **Implements:** Requirements -> Transcription; Technical Details #1/#2.

14. **T14** - Update `services/model_factory.py` return annotations and docstring so the factory explicitly documents that chat tiers return raw `BaseChatModel`, while image moderation and image transcription return provider wrappers. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

15. **T15** - Refactor `create_model_provider(...)` to use the unified `isinstance(provider, LLMProvider)` callback-attachment path, keep moderation on the no-tracking branch, and return the raw LLM only for `ChatCompletionProvider` while returning the wrapper for `ImageTranscriptionProvider`. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

16. **T16** - Harden `utils/provider_utils.py::find_provider_class()` with `obj.__module__ == module.__name__` while preserving the `not inspect.isabstract(obj)` check, and add the defensive-note documentation requested by the spec. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

17. **T17** - Extend `infrastructure/models.py::ProcessingResult` with `unprocessable_media: bool = False` and the semantic docstring explaining that `True` suppresses success-prefix injection for non-meaningful media outcomes. **Status:** <PENDING>  
    **Implements:** Requirements -> Processing Flow.

18. **T18** - Add pure module-level `format_processing_result(content: str, caption: str) -> str` in `media_processors/base.py` so it always bracket-wraps content and appends `\n[Caption: ...]` only when `caption` is non-empty. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

19. **T19** - Refactor `BaseMediaProcessor.process_job()` to match the exhaustive shared-lifecycle snippet from the spec: extract caption once, remove `caption` from `process_media(...)`, centralize timeout handling, gate prefix injection on `not result.unprocessable_media and not result.failed_reason`, format before persistence, and preserve the existing persistence/archive/delivery ordering. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format; Requirements -> Transcription (Error handling).

20. **T20** - Update the `asyncio.TimeoutError` branch in `BaseMediaProcessor.process_job()` to return raw `"Processing timed out"` (no brackets), set `unprocessable_media=True`, and keep the timeout `failed_reason` so the job still archives into `_failed`. **Status:** <PENDING>  
    **Implements:** Requirements -> Transcription (Error handling).

21. **T21** - Refactor `BaseMediaProcessor._handle_unhandled_exception()` so it uses raw `"Media processing failed"`, sets `unprocessable_media=True`, and runs `format_processing_result(...)` before `_persist_result_first`, `_archive_to_failed`, and best-effort queue delivery. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

22. **T22** - Remove the `caption` parameter from `BaseMediaProcessor.process_media(...)` and from all 7 explicitly named subclasses: `ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, and `DocumentProcessor`. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

23. **T23** - Update `CorruptMediaProcessor` to return raw `ProcessingResult(content=f"Corrupted {media_type} media could not be downloaded", failed_reason=..., unprocessable_media=True)` while preserving the existing `mime_type.replace("media_corrupt_", "")` derivation. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

24. **T24** - Update `UnsupportedMediaProcessor` to return raw `ProcessingResult(content=f"Unsupported media type: {mime_type}", failed_reason=..., unprocessable_media=True)` with no caption concatenation and no bracket formatting inside the processor. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

25. **T25** - Update `StubSleepProcessor` and its inheritors to return raw `ProcessingResult(content=f"multimedia message with guid='{...}'")` strings, removing bracket formatting and the redundant `"Transcripted"` wording so `process_job()` becomes the sole owner of the success prefix. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

26. **T26** - Add `"image/gif"` to the `ImageVisionProcessor` MIME list in `services/media_processing_service.py::DEFAULT_POOL_DEFINITIONS`, matching the OpenAI docs' support for non-animated GIF inputs. **Status:** <PENDING>  
    **Implements:** Requirements -> Processing Flow; External Resource.

27. **T27** - Create `scripts/migrations/migrate_pool_definitions_gif.py` that deletes the existing `_mediaProcessorDefinitions` document from the global configurations collection so the next boot reseeds the updated pool definitions from Python defaults. **Status:** <PENDING>  
    **Implements:** Requirements -> Processing Flow.

28. **T28** - Implement the flagged moderation branch in `ImageVisionProcessor` so `moderation_result.flagged == True` returns `ProcessingResult(content="cannot process image as it violates safety guidelines", failed_reason=None, unprocessable_media=True)` and intentionally avoids exposing category tags. **Status:** <PENDING>  
    **Implements:** Requirements -> Processing Flow.

29. **T29** - Implement the non-flagged `ImageVisionProcessor` path so it calls `resolve_bot_language(bot_id)` only inside the non-flagged branch, instantiates a separate image-transcription provider via `create_model_provider(bot_id, "image_transcription", "image_transcription")`, keeps moderation on `create_model_provider(bot_id, "media_processing", "image_moderation")`, and does not add local `try/except` around `transcribe_image(...)`. **Status:** <PENDING>  
    **Implements:** Requirements -> Transcription.

30. **T30** - Extend the token-menu/pricing contract so `image_transcription` is tracked as its own billable tier with `input_tokens: 0.25`, `cached_input_tokens: 0.025`, and `output_tokens: 2.0`, rather than piggybacking on `low`. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration.

31. **T31** - Create `scripts/migrations/migrate_image_transcription.py` to iterate existing bot configs in `COLLECTION_BOT_CONFIGURATIONS` and backfill `config_data.configurations.llm_configs.image_transcription` where it is missing, following the project's established migration patterns. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #1.

32. **T32** - Update `scripts/migrations/initialize_quota_and_bots.py` so its `token_menu` seed contains exactly the 3 billable tiers (`high`, `low`, `image_transcription`), retains explicit insert-if-not-exists behavior, and includes the code comment that `image_moderation` is intentionally excluded because it has no token-cost billing. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #5.

33. **T33** - Create `scripts/migrations/migrate_token_menu_image_transcription.py` that hard-resets the `token_menu` document by deleting the existing one and re-inserting the full 3-tier pricing structure from scratch. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #6.

34. **T34** - Preserve `QuotaService.load_token_menu()` as a read-only fetch (no self-healing writes) and ensure every new migration created for this feature imports collection constants from `infrastructure/db_schema.py` instead of hardcoding collection names. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #7/#8.

35. **T35** - Update `routers/bot_management.py::get_bot_defaults()` to construct `LLMConfigurations.image_transcription` using `ImageTranscriptionProviderConfig` plus the new `DefaultConfigurations` values. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; Deployment Checklist #3.

36. **T36** - Update `routers/bot_management.py::get_configuration_schema()` so the LLM tier surgery iterates `for prop_name in llm_configs_defs['properties'].keys():` and the `reasoning_effort` title patches run for both `ChatCompletionProviderSettings` and `ImageTranscriptionProviderSettings`. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; New Configuration Tier Checklist #3.

37. **T37** - Add `GET /api/internal/bots/tiers` to `routers/bot_management.py`, returning the available tier keys directly from `LLMConfigurations.model_fields.keys()`. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #4.

38. **T38** - Align the restricted bot-creation path in `routers/bot_ui.py` with the new required `image_transcription` tier so UI-created bots still build valid `BotConfiguration` objects after `LLMConfigurations.image_transcription` becomes required. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; Deployment Checklist #4.

39. **T39** - Update `frontend/src/pages/EditPage.js` so `fetchData()` retrieves the tier list from the new endpoint, stores it in component state, and replaces the current hardcoded `["high", "low", "image_moderation"]` arrays in both normalization and `handleFormChange()`. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #4.

40. **T40** - Add a static `uiSchema.llm_configs.image_transcription` entry in `EditPage.js` with the exact same `provider_config` structure as `high`/`low` (`FlatProviderConfigTemplate`, `api_key_source`, `reasoning_effort`, `seed`) plus `detail` titled `"Image Detail Level"`. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #5.

41. **T41** - Update backend API tests so `/api/internal/bots/schema`, `/api/internal/bots/defaults`, and the new `/api/internal/bots/tiers` behavior are covered for the new tier and dynamic schema surgery path. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; New Configuration Tier Checklist #3/#4.

42. **T42** - Update `frontend/src/pages/EditPage.test.js` so its fetch mocks account for the extra `/api/external/bots/tiers` request and its assertions cover the presence of the fourth LLM tier UI wiring. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #4/#5.

43. **T43** - Add provider-focused tests proving that `detail` is removed from the `ChatOpenAI(...)` constructor kwargs and is used only when constructing the multimodal image payload inside `transcribe_image(...)`. **Status:** <PENDING>  
    **Implements:** Test Expectations.

44. **T44** - Add callback continuity tests showing that the object receiving the `TokenTrackingCallback` in `create_model_provider(...)` is the exact same LLM instance used later by `OpenAiImageTranscriptionProvider.transcribe_image(...)`. **Status:** <PENDING>  
    **Implements:** Test Expectations.

45. **T45** - Add transcription normalization tests covering all three required branches: raw string passthrough, deterministic concatenation of text-bearing content blocks, and fallback to `"Unable to transcribe image content"`. **Status:** <PENDING>  
    **Implements:** Test Expectations.

46. **T46** - Add `ImageVisionProcessor` tests asserting that `moderation_result.flagged == True` returns the exact policy string with `unprocessable_media=True` and no `failed_reason`. **Status:** <PENDING>  
    **Implements:** Test Expectations.

47. **T47** - Add `format_processing_result(...)` tests that verify unconditional bracket wrapping plus correct caption omission/addition behavior for `None`, `""`, and populated captions. **Status:** <PENDING>  
    **Implements:** Test Expectations.

48. **T48** - Add end-to-end media-processing tests for timeout and unhandled-exception paths (`unprocessable_media=True`) and for final queue-delivered output showing the fully formatted bracketed message with the injected media-type transcription prefix on successful jobs. **Status:** <PENDING>  
    **Implements:** Test Expectations.

49. **T49** - Update existing processor assertions to the new raw string contracts for corrupt/unsupported/stub processors, and rewrite `tests/test_image_vision_processor.py::test_process_media_bot_id_signature` to use key-based lookup (`"bot_id" in sig.parameters`) instead of index offsets. **Status:** <PENDING>  
    **Implements:** Test Expectations.

50. **T50** - Sweep existing bot-configuration fixtures in `tests/test_api_bots.py`, `tests/test_main.py`, `tests/test_e2e.py`, and any other validation-heavy test payloads so they include the now-required `config_data.configurations.llm_configs.image_transcription` structure before `BotConfiguration.model_validate(...)` runs. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #4/#9; Test Expectations.

51. **T51** - Add rollout-verification and deployment-order tasks covering pre/post document counts for `COLLECTION_BOT_CONFIGURATIONS` and `COLLECTION_GLOBAL_CONFIGURATIONS`, sample migrated bot checks, token-menu validation, and the accepted temporary `GET /{bot_id}` 500 behavior until migrations fully finish. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #9.
