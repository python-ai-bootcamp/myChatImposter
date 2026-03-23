# Implementation Tasks — Image Transcription Support

**Task ID:** `13_cr_composer_2`  
**Spec:** `docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`  
**Purpose:** Flat, ordered checklist to implement the feature end-to-end. Each item maps to explicit spec sections. Status values: `<PENDING>`, `<IN_PROGRESS>`, `<DONE>`.

---

## Task Summary Table

| ID | Task (short) | Spec anchor | Status |
|----|----------------|-------------|--------|
| T01 | Remove dead `LLMProviderSettings` / `LLMProviderConfig` from `config_models.py` | Requirements → Configuration; Deployment Checklist §10 | <PENDING> |
| T02 | Add `ImageTranscriptionProviderSettings` (with `detail` literal) extending `ChatCompletionProviderSettings` | Requirements → Configuration; Technical Details §1 (Config hierarchy) | <PENDING> |
| T03 | Refactor `ImageTranscriptionProviderConfig` to extend `ChatCompletionProviderConfig` with `provider_config: ImageTranscriptionProviderSettings` | Requirements → Configuration; Technical Details §1 | <PENDING> |
| T04 | Extend `ConfigTier` with `"image_transcription"`; add comment that `ConfigTier` + `LLMConfigurations` are the only tier-key sources | New Config Tier Checklist §4.1 | <PENDING> |
| T05 | Add `image_transcription: ImageTranscriptionProviderConfig = Field(...)` to `LLMConfigurations` (required tier) | Requirements → Configuration; Deployment Checklist §4 | <PENDING> |
| T06 | Extend `DefaultConfigurations` with `model_provider_name_image_transcription`, env-driven defaults (`DEFAULT_MODEL_IMAGE_TRANSCRIPTION`, `DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE` with `float(..., "0.05")`, `DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT` with `"minimal"`) | Requirements → Configuration; Deployment Checklist §2 | <PENDING> |
| T07 | Add synchronous-I/O comment on `BaseModelProvider._resolve_api_key()` per spec | Technical Details §1 | <PENDING> |
| T08 | Introduce abstract `LLMProvider` in `model_providers/base.py` with abstract `get_llm() -> BaseChatModel` | Technical Details §1 | <PENDING> |
| T09 | Refactor `ChatCompletionProvider` to empty type-marker inheriting `LLMProvider`; strip abstract `get_llm` / `abc` imports from `chat_completion.py` | Technical Details §1 | <PENDING> |
| T10 | Add `OpenAiMixin` with `_build_llm_params()` only; refactor `OpenAiChatProvider` to `__init__` + `self._llm` + trivial `get_llm()` | Technical Details §1 | <PENDING> |
| T11 | Move `httpx` logger configuration from `OpenAiChatProvider.get_llm()` to app startup (e.g. `main.py`); remove `print()` debug | Technical Details §1 | <PENDING> |
| T12 | Add `ImageTranscriptionProvider` abstract class (`image_transcription.py`) with `transcribe_image(...)` | Technical Details §1; Relevant Background | <PENDING> |
| T13 | Implement `OpenAiImageTranscriptionProvider` (`openAiImageTranscription.py`): multimodal message, `detail` only in payload not `ChatOpenAI` kwargs, normalization contract, hardcoded prompt with `language_code` | Requirements → Transcription; Technical Details §1–§2 | <PENDING> |
| T14 | Add `obj.__module__ == module.__name__` filter (+ doc note) in `find_provider_class` (`utils/provider_utils.py`) | Technical Details §1 | <PENDING> |
| T15 | Update `create_model_provider`: return type `Union[..., ImageTranscriptionProvider]`; unified `isinstance(provider, LLMProvider)` branch; `ChatCompletionProvider` → raw LLM; else wrapper; docstring contract | Technical Details §1 | <PENDING> |
| T16 | Add `@overload` + implementation branch in `resolve_model_config` for `Literal["image_transcription"]` → `ImageTranscriptionProviderConfig` | Requirements → Configuration; New Config Tier Checklist §4.2 | <PENDING> |
| T17 | Implement `resolve_bot_language(bot_id) -> str` with bare `try/except Exception: return "en"` and `get_global_state().configurations_collection.find_one` path | Requirements → Configuration; Transcription | <PENDING> |
| T18 | Add `unprocessable_media: bool = False` to `ProcessingResult` in `infrastructure/models.py` with docstring | Requirements → Processing Flow | <PENDING> |
| T19 | Add `"image/gif"` to `ImageVisionProcessor` pool in `DEFAULT_POOL_DEFINITIONS` (`services/media_processing_service.py`) | Requirements → Processing Flow | <PENDING> |
| T20 | New migration `scripts/migrations/migrate_pool_definitions_gif.py`: delete `_mediaProcessorDefinitions` doc; use `db_schema` constants | Requirements → Processing Flow; Deployment Checklist §8 | <PENDING> |
| T21 | Implement module-level `format_processing_result(content, caption)` in `media_processors/base.py` (pure, brackets + optional caption suffix) | Requirements → Output Format | <PENDING> |
| T22 | Remove `caption` from `process_media` / `process_job`; update abstract signature; update all 7 subclasses (`ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`) | Requirements → Output Format; Relevant Background | <PENDING> |
| T23 | Refactor `BaseMediaProcessor.process_job` exactly per spec snippet (timeout → `unprocessable_media`, prefix injection rules, `format_processing_result` before persist/archive/delivery) | Requirements → Output Format | <PENDING> |
| T24 | Update `_handle_unhandled_exception`: `unprocessable_media=True`, content `"Media processing failed"`, `format_processing_result` first | Requirements → Output Format | <PENDING> |
| T25 | `CorruptMediaProcessor`: preserve `media_type` strip; `ProcessingResult` content + `unprocessable_media=True` per spec | Requirements → Output Format | <PENDING> |
| T26 | `UnsupportedMediaProcessor`: new content string + `unprocessable_media=True` per spec | Requirements → Output Format | <PENDING> |
| T27 | `StubSleepProcessor` (and stubs): content string per spec; `unprocessable_media` default False | Requirements → Output Format | <PENDING> |
| T28 | `ImageVisionProcessor`: moderate first; flagged → `unprocessable_media=True`, static message, `failed_reason=None`; else `resolve_bot_language` then `create_model_provider(..., "image_transcription")` + `await transcribe_image(...)`; moderation feature_name `"media_processing"`; no try/except around `transcribe_image` | Requirements → Overview; Processing Flow; Transcription | <PENDING> |
| T29 | Ensure `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor` align with caption removal and raw content rules (no legacy brackets in `process_media` returns) | Requirements → Output Format | <PENDING> |
| T30 | Extend `global_configurations` token menu with `image_transcription` pricing (`input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`) via migrations / init scripts | Requirements → Configuration; Deployment Checklist §5–§7 | <PENDING> |
| T31 | Update `scripts/migrations/initialize_quota_and_bots.py`: insert-if-not-exists `token_menu` with three tiers + comment re omitting `image_moderation` | Deployment Checklist §5 | <PENDING> |
| T32 | New `scripts/migrations/migrate_token_menu_image_transcription.py`: hard-delete `token_menu` doc and re-insert full menu; use `db_schema` constants | Deployment Checklist §6, §8 | <PENDING> |
| T33 | New `scripts/migrations/migrate_image_transcription.py`: backfill `config_data.configurations.llm_configs.image_transcription` for existing bots (`COLLECTION_BOT_CONFIGURATIONS`) | Deployment Checklist §1, §4 | <PENDING> |
| T34 | Confirm `QuotaService.load_token_menu()` stays read-only (no self-heal); document reliance on pre-boot migrations | Deployment Checklist §7 | <PENDING> |
| T35 | Update `get_bot_defaults` in `routers/bot_management.py` for `image_transcription` tier | Deployment Checklist §3 | <PENDING> |
| T36 | `get_configuration_schema`: dynamic `for prop_name in llm_configs_defs['properties'].keys()`; patch `reasoning_effort` titles on both `ChatCompletionProviderSettings` and `ImageTranscriptionProviderSettings` | Requirements → Configuration; New Config Tier Checklist §4.3 | <PENDING> |
| T37 | Add `GET /api/internal/bots/tiers` returning `LLMConfigurations.model_fields.keys()` | New Config Tier Checklist §4.4 | <PENDING> |
| T38 | Register/review backend route in `main.py` if needed; verify gateway generic `/api/external/bots/...` proxy serves `GET .../bots/tiers` | New Config Tier Checklist §4.4; `gateway/routers/proxy.py` | <PENDING> |
| T39 | `frontend/src/pages/EditPage.js`: fetch tiers from new endpoint; replace hardcoded tier arrays; add static `image_transcription` uiSchema block including `detail` (“Image Detail Level”) matching other tiers’ `provider_config` structure | New Config Tier Checklist §4.4–§4.5 | <PENDING> |
| T40 | Rollout verification: pre/post counts, sample bot docs, token menu doc; document accepted 500 window for unmigrated bots | Deployment Checklist §9 | <PENDING> |
| T41 | Tests: `detail` not in `ChatOpenAI` kwargs; only in transcription payload | Test Expectations | <PENDING> |
| T42 | Tests: `TokenTrackingCallback` same LLM reference for factory + `transcribe_image` | Test Expectations | <PENDING> |
| T43 | Tests: transcription response normalization (str / blocks / fallback string) | Test Expectations | <PENDING> |
| T44 | Test: moderation flagged → `ProcessingResult` with `unprocessable_media=True` and safety message | Test Expectations | <PENDING> |
| T45 | Tests: `format_processing_result` brackets + caption rules; caption on success and failure paths | Test Expectations | <PENDING> |
| T46 | Test: timeout path `unprocessable_media=True`, content `"Processing timed out"`, `failed_reason` populated | Test Expectations | <PENDING> |
| T47 | Update unit tests: `process_media` returns raw unbracketed strings | Test Expectations | <PENDING> |
| T48 | Integration tests: `process_job` → `update_message_by_media_id` receives fully formatted `[{MediaType} Transcription: ...]` | Test Expectations | <PENDING> |
| T49 | Update tests for `UnsupportedMediaProcessor` / `CorruptMediaProcessor` new content strings | Test Expectations | <PENDING> |
| T50 | Update `test_process_media_bot_id_signature` to `assert "bot_id" in sig.parameters` | Test Expectations | <PENDING> |

---

## Flat Task List (ordered)

1. **T01** — Delete unused `LLMProviderSettings` and `LLMProviderConfig` from `config_models.py`. *(Deployment Checklist §10; avoids confusion with chat-completion config types.)* **Status:** <PENDING>

2. **T02** — Add `ImageTranscriptionProviderSettings(ChatCompletionProviderSettings)` with `detail: Literal["low", "high", "original", "auto"] = "auto"`. *(Requirements → Configuration; Technical Details §1.)* **Status:** <PENDING>

3. **T03** — Define `ImageTranscriptionProviderConfig` extending `ChatCompletionProviderConfig` with `provider_config: ImageTranscriptionProviderSettings`. *(Requirements → Configuration.)* **Status:** <PENDING>

4. **T04** — Set `ConfigTier = Literal["high", "low", "image_moderation", "image_transcription"]` and add the spec-mandated comment that `ConfigTier` and `LLMConfigurations` are the only tier-structure definitions. *(New Config Tier Checklist §4.1.)* **Status:** <PENDING>

5. **T05** — Add required `image_transcription` field to `LLMConfigurations` using `Field(...)`. *(Requirements → Configuration; Deployment Checklist §4.)* **Status:** <PENDING>

6. **T06** — Extend `DefaultConfigurations`: `model_provider_name_image_transcription = "openAiImageTranscription"` and env defaults with explicit fallbacks (`gpt-5-mini`, `0.05`, `minimal`). *(Deployment Checklist §2; Requirements → Configuration.)* **Status:** <PENDING>

7. **T07** — Document in `BaseModelProvider._resolve_api_key()` that it must stay synchronous and I/O-free. *(Technical Details §1.)* **Status:** <PENDING>

8. **T08** — Add `LLMProvider` ABC with abstract `get_llm()` in `model_providers/base.py`. *(Technical Details §1.)* **Status:** <PENDING>

9. **T09** — Make `ChatCompletionProvider` an empty subclass of `LLMProvider`; remove abstract `get_llm` from `chat_completion.py`. *(Technical Details §1.)* **Status:** <PENDING>

10. **T10** — Extract `OpenAiMixin._build_llm_params()`; refactor `OpenAiChatProvider` to constructor-initialized `self._llm` and trivial `get_llm()`. *(Technical Details §1.)* **Status:** <PENDING>

11. **T11** — Relocate `httpx` logging side effects to application startup (`main.py`); remove debug `print()` from providers. *(Technical Details §1.)* **Status:** <PENDING>

12. **T12** — Create `model_providers/image_transcription.py` with `ImageTranscriptionProvider(LLMProvider, ABC)` and abstract `transcribe_image`. *(Technical Details §1; contract skeleton.)* **Status:** <PENDING>

13. **T13** — Implement `OpenAiImageTranscriptionProvider`: pop `detail` before `ChatOpenAI(**params)`, build multimodal `HumanMessage` per OpenAI vision docs ([Images and vision — base64](https://developers.openai.com/api/docs/guides/images-vision?format=base64-encoded)), `ainvoke`, apply normalization contract. *(Technical Details §1–§2; Requirements → Transcription.)* **Status:** <PENDING>

14. **T14** — Harden `find_provider_class` with `__module__` filter and keep `not inspect.isabstract(obj)`. *(Technical Details §1.)* **Status:** <PENDING>

15. **T15** — Refactor `services/model_factory.py` `create_model_provider` per unified `LLMProvider` flow and updated return/docstring. *(Technical Details §1.)* **Status:** <PENDING>

16. **T16** — Add resolver overload and `elif` for `image_transcription` returning `ImageTranscriptionProviderConfig.model_validate(...)`. *(Requirements → Configuration; New Config Tier Checklist §4.2.)* **Status:** <PENDING>

17. **T17** — Implement `resolve_bot_language` using `configurations_collection.find_one` and `user_details.language_code`, never raising; always fallback `"en"`. *(Requirements → Configuration; Transcription.)* **Status:** <PENDING>

18. **T18** — Add `unprocessable_media` to `ProcessingResult` with semantic docstring. *(Requirements → Processing Flow.)* **Status:** <PENDING>

19. **T19** — Include `image/gif` in `DEFAULT_POOL_DEFINITIONS` for `ImageVisionProcessor`. *(Requirements → Processing Flow.)* **Status:** <PENDING>

20. **T20** — Add `migrate_pool_definitions_gif.py` to delete `_mediaProcessorDefinitions` so defaults re-seed; import collection names from `infrastructure/db_schema.py`. *(Requirements → Processing Flow; Deployment Checklist §8.)* **Status:** <PENDING>

21. **T21** — Implement `format_processing_result` at module level in `media_processors/base.py`. *(Requirements → Output Format.)* **Status:** <PENDING>

22. **T22** — Remove `caption` from `process_media` everywhere; update `BaseMediaProcessor` and seven concrete processors. *(Requirements → Output Format.)* **Status:** <PENDING>

23. **T23** — Replace `BaseMediaProcessor.process_job` body with the spec’s exhaustive version (timeout handling, prefix injection, formatting order, persistence, archive, delivery). *(Requirements → Output Format.)* **Status:** <PENDING>

24. **T24** — Align `_handle_unhandled_exception` with spec (content without brackets, `format_processing_result` first). *(Requirements → Output Format.)* **Status:** <PENDING>

25. **T25** — Implement `CorruptMediaProcessor` result shape and preserved `media_corrupt_` stripping. *(Requirements → Output Format.)* **Status:** <PENDING>

26. **T26** — Implement `UnsupportedMediaProcessor` per new content template. *(Requirements → Output Format.)* **Status:** <PENDING>

27. **T27** — Implement `StubSleepProcessor` (and inheritors) per spec. *(Requirements → Output Format.)* **Status:** <PENDING>

28. **T28** — Implement full `ImageVisionProcessor` flow: moderate → flagged vs transcribe; `resolve_bot_language` only in non-flagged branch; `create_model_provider` with feature names `"media_processing"` vs `"image_transcription"`; `await transcribe_image` with base64 + mime + language. *(Overview; Processing Flow; Transcription.)* **Status:** <PENDING>

29. **T29** — Adjust remaining processors (`AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`) for new signature and raw string contract. *(Requirements → Output Format.)* **Status:** <PENDING>

30. **T30** — Ensure MongoDB `token_menu` document includes independent `image_transcription` tier pricing as specified (via init/migrations). *(Requirements → Configuration; note: `COLLECTION_GLOBAL_CONFIGURATIONS`.)* **Status:** <PENDING>

31. **T31** — Update `initialize_quota_and_bots.py` for three-tier `token_menu` and `image_moderation` omission comment. *(Deployment Checklist §5.)* **Status:** <PENDING>

32. **T32** — Add `migrate_token_menu_image_transcription.py` hard-reset script. *(Deployment Checklist §6.)* **Status:** <PENDING>

33. **T33** — Add `migrate_image_transcription.py` bot-config backfill. *(Deployment Checklist §1.)* **Status:** <PENDING>

34. **T34** — Verify `services/quota_service.py` remains read-only for `load_token_menu` (no behavior change beyond confirmation). *(Deployment Checklist §7.)* **Status:** <PENDING>

35. **T35** — Wire `get_bot_defaults` to include `ImageTranscriptionProviderConfig` defaults. *(Deployment Checklist §3.)* **Status:** <PENDING>

36. **T36** — Implement dynamic schema surgery and dual `reasoning_effort` patches in `get_configuration_schema`. *(Requirements → Configuration; New Config Tier Checklist §4.3.)* **Status:** <PENDING>

37. **T37** — Expose `GET /api/internal/bots/tiers` listing `LLMConfigurations.model_fields.keys()`. *(New Config Tier Checklist §4.4.)* **Status:** <PENDING>

38. **T38** — Confirm routing: backend app includes router; gateway proxies `GET /api/external/bots/tiers` to internal path. *(New Config Tier Checklist §4.4; external gateway behavior.)* **Status:** <PENDING>

39. **T39** — Frontend: dynamic tiers + `uiSchema` for `image_transcription` including nested `provider_config` and `detail` field. *(New Config Tier Checklist §4.4–§4.5.)* **Status:** <PENDING>

40. **T40** — Execute deployment verification checklist (counts, samples, document accepted API 500 during migration window). *(Deployment Checklist §9.)* **Status:** <PENDING>

41. **T41**–**T50** — Implement and update automated tests per **Test Expectations** (detail kwargs, callback continuity, normalization, moderation flagged, formatting, timeout, unit vs integration, content string migrations, signature test). **Status:** <PENDING> (each)

---

## Coverage notes

- **Overview & Requirements:** Covered by T28 and cross-cutting config/processing tasks.
- **External resource (OpenAI vision / base64):** Addressed in T13 (implementation follows linked guide for image payload).
- **Project files not listed in spec but required:** `main.py` (T11), `gateway/routers/proxy.py` (T38), `frontend/src/pages/EditPage.js` (T39), optional `media_processors/__init__.py` / factory imports if new processors are registered—verify during T22/T28.
