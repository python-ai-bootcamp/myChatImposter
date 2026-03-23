# Implementation Tasks - Image Transcription Support

**Implementation Task ID**: `18_cr_gpt_5_4_xhigh_improved`  
**Feature**: `imageTranscriptSupport`  
**Spec**: `docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`  
**Based on**: `16_cr_gpt_5_4_xhigh` (with phase structure, traceability annotations, and enriched descriptions)

---

## Task Summary Table

| Task ID | Phase | Task | Spec Root | Status |
|---|---|---|---|---|
| T01 | 1 | Remove dead `LLMProviderSettings` and `LLMProviderConfig` from `config_models.py` | Deployment Checklist #10 | <PENDING> |
| T02 | 1 | Add `ImageTranscriptionProviderSettings` and `ImageTranscriptionProviderConfig` | Requirements -> Configuration; Technical Details #1 | <PENDING> |
| T03 | 1 | Extend `ConfigTier` / `LLMConfigurations` with required `image_transcription` tier and source-of-truth comment | Requirements -> Configuration; Deployment Checklist #4; New Configuration Tier Checklist #1 | <PENDING> |
| T04 | 1 | Extend `DefaultConfigurations` with image-transcription provider/model/env defaults and explicit fallback values | Requirements -> Configuration; Deployment Checklist #2 | <PENDING> |
| T05 | 1 | Add resolver overload/branch for `image_transcription` returning `ImageTranscriptionProviderConfig` | Requirements -> Configuration; New Configuration Tier Checklist #2 | <PENDING> |
| T06 | 1 | Add non-throwing `resolve_bot_language(bot_id)` with direct config lookup and guaranteed `"en"` fallback | Requirements -> Configuration; Requirements -> Transcription | <PENDING> |
| T07 | 2 | Introduce abstract `LLMProvider` and add synchronous-only `_resolve_api_key()` constraint comment | Technical Details #1 | <PENDING> |
| T08 | 2 | Refactor `ChatCompletionProvider` into an empty `LLMProvider` type marker | Technical Details #1 | <PENDING> |
| T09 | 2 | Add shared `OpenAiMixin._build_llm_params()` for OpenAI chat/transcription providers | Technical Details #1 | <PENDING> |
| T10 | 2 | Refactor `OpenAiChatProvider` to constructor-time `ChatOpenAI` init and move `httpx` logger setup to `main.py` | Technical Details #1 | <PENDING> |
| T11 | 2 | Create abstract `ImageTranscriptionProvider` with `transcribe_image(...)` contract | Technical Details #1 | <PENDING> |
| T12 | 2 | Create `OpenAiImageTranscriptionProvider` constructor/init flow with `detail` pop and no model/detail guardrails | Requirements -> Configuration; Technical Details #1/#2 | <PENDING> |
| T13 | 2 | Implement transcription prompt, multimodal payload, and normalization contract | Requirements -> Transcription; Technical Details #1/#2 | <PENDING> |
| T14 | 2 | Update `create_model_provider` return annotation/docstring for chat, moderation, and transcription return contracts | Technical Details #1 | <PENDING> |
| T15 | 2 | Refactor `create_model_provider` to unified `isinstance(provider, LLMProvider)` tracking flow with subtype-specific returns | Technical Details #1 | <PENDING> |
| T16 | 2 | Harden `find_provider_class` with `obj.__module__ == module.__name__` filter and defensive doc note | Technical Details #1 | <PENDING> |
| T17 | 3 | Add `unprocessable_media: bool = False` to `ProcessingResult` with spec-defined semantic docstring | Requirements -> Processing Flow | <PENDING> |
| T18 | 3 | Add pure module-level `format_processing_result(content, caption)` helper in `media_processors/base.py` | Requirements -> Output Format | <PENDING> |
| T19 | 3 | Refactor `BaseMediaProcessor.process_job()` to the full shared lifecycle from the spec snippet | Requirements -> Output Format; Requirements -> Transcription (Error handling) | <PENDING> |
| T20 | 3 | Update timeout handling to raw `"Processing timed out"` plus `unprocessable_media=True` while preserving `failed_reason` | Requirements -> Transcription (Error handling) | <PENDING> |
| T21 | 3 | Refactor `_handle_unhandled_exception()` to format first, mark `unprocessable_media=True`, and avoid double wrapping | Requirements -> Output Format | <PENDING> |
| T22 | 3 | Remove the `caption` parameter from `process_media` across the base class and all 7 affected processors | Requirements -> Output Format | <PENDING> |
| T23 | 3 | Update `CorruptMediaProcessor` to the new raw-content contract while preserving `media_corrupt_` stripping | Requirements -> Output Format | <PENDING> |
| T24 | 3 | Update `UnsupportedMediaProcessor` to the new raw-content contract | Requirements -> Output Format | <PENDING> |
| T25 | 3 | Update `StubSleepProcessor` and inheriting stubs to the new raw-content contract | Requirements -> Output Format | <PENDING> |
| T26 | 3 | Add `"image/gif"` to `ImageVisionProcessor` pool definitions | Requirements -> Processing Flow; External Resource | <PENDING> |
| T27 | 3 | Create `migrate_pool_definitions_gif.py` to delete `_mediaProcessorDefinitions` so GIF support reseeds on boot | Requirements -> Processing Flow | <PENDING> |
| T28 | 3 | Implement the flagged-moderation outcome in `ImageVisionProcessor` | Requirements -> Processing Flow | <PENDING> |
| T29 | 3 | Implement the non-flagged transcription path in `ImageVisionProcessor` with in-branch language resolution and separate provider instances | Requirements -> Transcription | <PENDING> |
| T30 | 4 | Extend the token-menu/pricing contract so `image_transcription` is billed as its own tier | Requirements -> Configuration | <PENDING> |
| T31 | 4 | Create `migrate_image_transcription.py` to backfill missing bot-level `llm_configs.image_transcription` | Deployment Checklist #1 | <PENDING> |
| T32 | 4 | Update `initialize_quota_and_bots.py` to seed a 3-tier token menu and keep insert-if-not-exists behavior | Deployment Checklist #5 | <PENDING> |
| T33 | 4 | Create `migrate_token_menu_image_transcription.py` to hard-reset the `token_menu` document | Deployment Checklist #6 | <PENDING> |
| T34 | 4 | Preserve read-only `QuotaService.load_token_menu()` behavior and enforce `db_schema` constants across all new migrations | Deployment Checklist #7/#8 | <PENDING> |
| T35 | 5 | Update `get_bot_defaults()` to include `image_transcription` using the new config types/defaults | Requirements -> Configuration; Deployment Checklist #3 | <PENDING> |
| T36 | 5 | Update `get_configuration_schema()` to use dynamic tier surgery and patch `reasoning_effort` for both provider-settings models | Requirements -> Configuration; New Configuration Tier Checklist #3 | <PENDING> |
| T37 | 5 | Add `GET /api/internal/bots/tiers` backed by `LLMConfigurations.model_fields.keys()` | New Configuration Tier Checklist #4 | <PENDING> |
| T38 | 5 | Verify gateway generic proxy correctly relays `GET /api/external/bots/tiers` to the new backend endpoint | *Inferred from:* New Configuration Tier Checklist #4 | <PENDING> |
| T39 | 5 | Align `routers/bot_ui.py` creation defaults with the required `image_transcription` tier so restricted creation still builds valid `BotConfiguration` objects | *Inferred from:* Deployment Checklist #4 | <PENDING> |
| T40 | 5 | Update `EditPage.js` to fetch tiers and replace the hardcoded tier arrays in normalization/change handling | New Configuration Tier Checklist #4 | <PENDING> |
| T41 | 5 | Add `EditPage.js` `uiSchema.llm_configs.image_transcription` entry including the `detail` field | New Configuration Tier Checklist #5 | <PENDING> |
| T42 | 6 | Update backend schema/defaults/tiers API tests to cover new tier exposure and dynamic behavior | Requirements -> Configuration; New Configuration Tier Checklist #3/#4 | <PENDING> |
| T43 | 6 | Update `EditPage.test.js` mocks/assertions for the extra `/bots/tiers` fetch and fourth tier UI | *Inferred from:* New Configuration Tier Checklist #4/#5 | <PENDING> |
| T44 | 6 | Add provider tests proving `detail` is filtered out of `ChatOpenAI(...)` kwargs | Test Expectations | <PENDING> |
| T45 | 6 | Add callback continuity tests ensuring factory attachment and transcription use the same LLM instance | Test Expectations | <PENDING> |
| T46 | 6 | Add transcription normalization tests for string, content-block, and fallback branches | Test Expectations | <PENDING> |
| T47 | 6 | Add flagged moderation contract tests for `unprocessable_media=True` and static policy text | Test Expectations | <PENDING> |
| T48 | 6 | Add `format_processing_result` tests for unconditional brackets and caption append/omit behavior | Test Expectations | <PENDING> |
| T49 | 6 | Add timeout / unhandled-exception / final queue-format tests for the centralized media-processing flow | Test Expectations | <PENDING> |
| T50 | 6 | Update existing processor assertion strings and refactor the signature test to key-based lookup | Test Expectations | <PENDING> |
| T51 | 6 | Update existing backend/integration configuration fixtures to include required `image_transcription` data | *Inferred from:* Deployment Checklist #4/#9; Test Expectations | <PENDING> |
| T52 | 7 | Add rollout verification and deployment-order tasks covering counts, sample docs, token menu validation, and accepted temporary 500s | Deployment Checklist #9 | <PENDING> |

---

## Phase 1 — Configuration Models & Resolver (T01–T06)

Establishes the data model foundation: config types, tier definitions, defaults, and resolver functions that all downstream phases depend on.

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

6. **T06** - Add `resolve_bot_language(bot_id: str) -> str` to `services/resolver.py`. This function performs an explicit `get_global_state().configurations_collection.find_one(...)` lookup reading `config_data.configurations.user_details.language_code` from the bot's configuration document. **Critical constraint:** this function must **never raise an exception** under any circumstances. The entire database fetch block must be wrapped in a bare `try/except Exception: return "en"` so that any missing document, missing field, or unexpected error always falls back to `"en"`. Do not mirror `resolve_model_config`'s error-raising pattern. **Status:** <PENDING>  
   **Implements:** Requirements -> Configuration; Requirements -> Transcription.

---

## Phase 2 — Provider Architecture (T07–T16)

Builds the provider hierarchy (`LLMProvider`, `ImageTranscriptionProvider`, `OpenAiMixin`), the concrete `OpenAiImageTranscriptionProvider`, and the factory/utility changes. Depends on Phase 1 config types.

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

13. **T13** - Implement `OpenAiImageTranscriptionProvider.transcribe_image(...)`. The method must: (a) build a multimodal `HumanMessage` containing the exact hardcoded prompt — `"Describe the contents of this image explicitly in the following language: {language_code}, and concisely in 1-3 sentences. If there is text in the image, add the text inside image to description as well."` — with no system message; (b) include a base64 `image_url` data URI with `detail` from `self._detail`; (c) invoke the LLM via `ainvoke`; (d) normalize the response per the three-branch contract: if `response.content` is `str` return as-is, if content blocks extract text-bearing blocks and concatenate with single-space separator (trimmed), otherwise return `"Unable to transcribe image content"`. **Status:** <PENDING>  
    **Implements:** Requirements -> Transcription; Technical Details #1/#2.

14. **T14** - Update `services/model_factory.py` return annotations and docstring so the factory explicitly documents that chat tiers return raw `BaseChatModel`, while image moderation and image transcription return provider wrappers. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

15. **T15** - Refactor `create_model_provider(...)` to use the unified `isinstance(provider, LLMProvider)` callback-attachment path, keep moderation on the no-tracking branch, and return the raw LLM only for `ChatCompletionProvider` while returning the wrapper for `ImageTranscriptionProvider`. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

16. **T16** - Harden `utils/provider_utils.py::find_provider_class()` with `obj.__module__ == module.__name__` while preserving the `not inspect.isabstract(obj)` check, and add the defensive-note documentation requested by the spec. **Status:** <PENDING>  
    **Implements:** Technical Details #1.

---

## Phase 3 — Media Processing Pipeline (T17–T29)

Refactors `process_job()`, `_handle_unhandled_exception()`, `format_processing_result()`, all processor content contracts, GIF support, and the `ImageVisionProcessor` moderation/transcription branches. Depends on Phase 2 providers and Phase 1 config.

17. **T17** - Extend `infrastructure/models.py::ProcessingResult` with `unprocessable_media: bool = False` and the semantic docstring explaining that `True` suppresses success-prefix injection for non-meaningful media outcomes. **Status:** <PENDING>  
    **Implements:** Requirements -> Processing Flow.

18. **T18** - Add pure module-level `format_processing_result(content: str, caption: str) -> str` in `media_processors/base.py` so it always bracket-wraps content and appends `\n[Caption: ...]` only when `caption` is non-empty. **Status:** <PENDING>  
    **Implements:** Requirements -> Output Format.

19. **T19** - Refactor `BaseMediaProcessor.process_job()` to match the exhaustive shared-lifecycle snippet from the spec. The refactored method must execute the following 6 sequential steps:  
    **(1) Caption extraction** — extract `caption = job.placeholder_message.content` once at the top; remove `caption` from the `process_media(...)` call.  
    **(2) Timeout-guarded conversion** — `await asyncio.wait_for(self.process_media(file_path, job.mime_type, job.bot_id), timeout=self.processing_timeout)` with the `asyncio.TimeoutError` handler producing `ProcessingResult(content="Processing timed out", failed_reason=..., unprocessable_media=True)`.  
    **(3) Prefix injection** — only on classical success (`not result.unprocessable_media and not result.failed_reason`): derive `media_type = job.mime_type.replace("media_corrupt_", "").split("/")[0].capitalize()` and prepend `f"{media_type} Transcription: {result.content}"`.  
    **(4) Format** — unconditionally call `result.content = format_processing_result(result.content, caption)` before any persistence or delivery.  
    **(5) Persist + archive** — `_persist_result_first`, then conditionally `_archive_to_failed` (only when `result.failed_reason` is set; flagged images with `failed_reason=None` bypass this intentionally).  
    **(6) Best-effort delivery** — `update_message_by_media_id` if bot is active, else leave in `_holding` for reaping on reconnect.  
    Preserve the existing `except Exception` → `_handle_unhandled_exception` and `finally` → `delete_media_file` structure. **Status:** <PENDING>  
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

---

## Phase 4 — Pricing, Migrations & Deployment Scripts (T30–T34)

Handles token-menu pricing, database migrations for existing bots, and deployment-safety constraints. Grouped together because they share the same deployment-order dependency chain.

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

---

## Phase 5 — API & Frontend (T35–T43)

Exposes the new tier through API defaults, schema, endpoints, and frontend UI. Depends on Phase 1 config types and Phase 4 migrations being defined.

35. **T35** - Update `routers/bot_management.py::get_bot_defaults()` to construct `LLMConfigurations.image_transcription` using `ImageTranscriptionProviderConfig` plus the new `DefaultConfigurations` values. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; Deployment Checklist #3.

36. **T36** - Update `routers/bot_management.py::get_configuration_schema()` so the LLM tier surgery iterates `for prop_name in llm_configs_defs['properties'].keys():` and the `reasoning_effort` title patches run for both `ChatCompletionProviderSettings` and `ImageTranscriptionProviderSettings`. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; New Configuration Tier Checklist #3.

37. **T37** - Add `GET /api/internal/bots/tiers` to `routers/bot_management.py`, returning the available tier keys directly from `LLMConfigurations.model_fields.keys()`. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #4.

38. **T38** - Verify that the gateway's generic reverse-proxy in `gateway/routers/proxy.py` correctly relays `GET /api/external/bots/tiers` to the backend's `GET /api/internal/bots/tiers` without additional route registration. The existing proxy transforms `/api/external/*` → `/api/internal/*`, so this should work automatically — but confirm there are no path-specific allow/deny rules that would block it. If the proxy does require a change, apply it here. **Status:** <PENDING>  
    **Inferred from:** New Configuration Tier Checklist #4 — T37 creates the backend endpoint and T40 has the frontend calling it through the gateway, but nothing explicitly verifies the gateway relay works for this new path.

39. **T39** - Align the restricted bot-creation path in `routers/bot_ui.py` with the new required `image_transcription` tier so UI-created bots still build valid `BotConfiguration` objects after `LLMConfigurations.image_transcription` becomes required. **Status:** <PENDING>  
    **Inferred from:** Deployment Checklist #4 — making `image_transcription` a required field on `LLMConfigurations` means every code path that constructs a `BotConfiguration` must supply it, including `bot_ui.py`'s restricted creation flow.

40. **T40** - Update `frontend/src/pages/EditPage.js` so `fetchData()` retrieves the tier list from the new endpoint, stores it in component state, and replaces the current hardcoded `["high", "low", "image_moderation"]` arrays in both normalization and `handleFormChange()`. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #4.

41. **T41** - Add a static `uiSchema.llm_configs.image_transcription` entry in `EditPage.js` with the exact same `provider_config` structure as `high`/`low` (`FlatProviderConfigTemplate`, `api_key_source`, `reasoning_effort`, `seed`) plus `detail` titled `"Image Detail Level"`. **Status:** <PENDING>  
    **Implements:** New Configuration Tier Checklist #5.

42. **T42** - Update backend API tests so `/api/internal/bots/schema`, `/api/internal/bots/defaults`, and the new `/api/internal/bots/tiers` behavior are covered for the new tier and dynamic schema surgery path. **Status:** <PENDING>  
    **Implements:** Requirements -> Configuration; New Configuration Tier Checklist #3/#4.

43. **T43** - Update `frontend/src/pages/EditPage.test.js` so its fetch mocks account for the extra `/api/external/bots/tiers` request and its assertions cover the presence of the fourth LLM tier UI wiring. **Status:** <PENDING>  
    **Inferred from:** New Configuration Tier Checklist #4/#5 — adding a new fetch call and a fourth UI tier in `EditPage.js` (T40/T41) requires the corresponding test file to mock the new endpoint and assert the new tier renders.

---

## Phase 6 — Tests (T44–T51)

All new and updated test cases. Depends on all implementation phases being complete.

44. **T44** - Add provider-focused tests proving that `detail` is removed from the `ChatOpenAI(...)` constructor kwargs and is used only when constructing the multimodal image payload inside `transcribe_image(...)`. **Status:** <PENDING>  
    **Implements:** Test Expectations.

45. **T45** - Add callback continuity tests showing that the object receiving the `TokenTrackingCallback` in `create_model_provider(...)` is the exact same LLM instance used later by `OpenAiImageTranscriptionProvider.transcribe_image(...)`. **Status:** <PENDING>  
    **Implements:** Test Expectations.

46. **T46** - Add transcription normalization tests covering all three required branches: raw string passthrough, deterministic concatenation of text-bearing content blocks, and fallback to `"Unable to transcribe image content"`. **Status:** <PENDING>  
    **Implements:** Test Expectations.

47. **T47** - Add `ImageVisionProcessor` tests asserting that `moderation_result.flagged == True` returns the exact policy string with `unprocessable_media=True` and no `failed_reason`. **Status:** <PENDING>  
    **Implements:** Test Expectations.

48. **T48** - Add `format_processing_result(...)` tests that verify unconditional bracket wrapping plus correct caption omission/addition behavior for `None`, `""`, and populated captions. **Status:** <PENDING>  
    **Implements:** Test Expectations.

49. **T49** - Add end-to-end media-processing tests for timeout and unhandled-exception paths (`unprocessable_media=True`) and for final queue-delivered output showing the fully formatted bracketed message with the injected media-type transcription prefix on successful jobs. **Status:** <PENDING>  
    **Implements:** Test Expectations.

50. **T50** - Update existing processor assertions to the new raw string contracts for corrupt/unsupported/stub processors, and rewrite `tests/test_image_vision_processor.py::test_process_media_bot_id_signature` to use key-based lookup (`"bot_id" in sig.parameters`) instead of index offsets. **Status:** <PENDING>  
    **Implements:** Test Expectations.

51. **T51** - Sweep existing bot-configuration fixtures in `tests/test_api_bots.py`, `tests/test_main.py`, `tests/test_e2e.py`, and any other validation-heavy test payloads so they include the now-required `config_data.configurations.llm_configs.image_transcription` structure before `BotConfiguration.model_validate(...)` runs. **Status:** <PENDING>  
    **Inferred from:** Deployment Checklist #4/#9; Test Expectations — making `image_transcription` a required field causes `model_validate` to reject existing test fixtures that lack it, so all configuration-validating tests must be updated with the new tier data.

---

## Phase 7 — Rollout Verification (T52)

Post-deployment validation tasks to confirm migrations and runtime behavior.

52. **T52** - Add rollout-verification and deployment-order tasks covering pre/post document counts for `COLLECTION_BOT_CONFIGURATIONS` and `COLLECTION_GLOBAL_CONFIGURATIONS`, sample migrated bot checks, token-menu validation, and the accepted temporary `GET /{bot_id}` 500 behavior until migrations fully finish. **Status:** <PENDING>  
    **Implements:** Deployment Checklist #9.
