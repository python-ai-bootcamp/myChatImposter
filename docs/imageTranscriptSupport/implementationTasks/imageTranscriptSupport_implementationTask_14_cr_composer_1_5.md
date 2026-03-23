# Implementation Tasks: Image Transcription Support

**Implementation Task ID**: 14_cr_composer_1_5  
**Feature**: imageTranscriptSupport  
**Spec File**: [imageTranscriptSupport_specFile.md](../imageTranscriptSupport_specFile.md)

---

## Summary Table

| Task ID | Description | Status |
|---------|-------------|--------|
| T01 | Add `unprocessable_media` to `ProcessingResult` in infrastructure | <PENDING> |
| T02 | Add `image_transcription` configuration models and ConfigTier | <PENDING> |
| T03 | Implement `resolve_model_config` and `resolve_bot_language` in resolver | <PENDING> |
| T04 | Refactor model provider base architecture (LLMProvider, OpenAiMixin) | <PENDING> |
| T05 | Create `ImageTranscriptionProvider` abstract and `OpenAiImageTranscriptionProvider` | <PENDING> |
| T06 | Update `create_model_provider` and `find_provider_class` | <PENDING> |
| T07 | Extract httpx logger from model providers to main.py startup | <PENDING> |
| T08 | Implement `format_processing_result` and refactor `BaseMediaProcessor.process_job` | <PENDING> |
| T09 | Remove caption param from `process_media` across all 7 processors | <PENDING> |
| T10 | Update error/stub processor content strings per spec | <PENDING> |
| T11 | Add `image/gif` to ImageVisionProcessor pool and create migration | <PENDING> |
| T12 | Implement ImageVisionProcessor moderation→transcription flow | <PENDING> |
| T13 | Token menu and migration scripts for image_transcription tier | <PENDING> |
| T14 | Update `get_configuration_schema` and `get_bot_defaults` in bot_management | <PENDING> |
| T15 | Create GET /api/internal/bots/tiers endpoint | <PENDING> |
| T16 | Update frontend EditPage with tiers API and image_transcription uiSchema | <PENDING> |
| T17 | Delete `LLMProviderSettings` and `LLMProviderConfig` from config_models | <PENDING> |
| T18 | Add/update tests per Test Expectations section | <PENDING> |

---

## Detailed Tasks

### T01: Add `unprocessable_media` to `ProcessingResult` in infrastructure
**Spec Reference**: Processing Flow (infrastructure/models.py)

- Add `unprocessable_media: bool = False` to the `ProcessingResult` dataclass in `infrastructure/models.py`.
- Add docstring: *"True means the media could not be meaningfully transcribed, signaling `process_job` to skip prefix injection for the error payload."*

**Status**: <PENDING>

---

### T02: Add `image_transcription` configuration models and ConfigTier
**Spec Reference**: Configuration, Technical Details §1 (Provider Architecture), Deployment Checklist §4

- Create `ImageTranscriptionProviderSettings` inheriting from `ChatCompletionProviderSettings`, adding `detail: Literal["low", "high", "original", "auto"] = "auto"`.
- Create `ImageTranscriptionProviderConfig` extending `ChatCompletionProviderConfig` with `provider_config: ImageTranscriptionProviderSettings`.
- Update `ConfigTier` to `Literal["high", "low", "image_moderation", "image_transcription"]`.
- Add `image_transcription: ImageTranscriptionProviderConfig = Field(...)` to `LLMConfigurations`.
- Add comment above `LLMConfigurations` and `ConfigTier`: *"These two locations are the ONLY places in the code where the structure/keys of the tiers are defined."*
- Extend `DefaultConfigurations` with: `model_provider_name_image_transcription = "openAiImageTranscription"`, `os.getenv("DEFAULT_MODEL_IMAGE_TRANSCRIPTION", "gpt-5-mini")`, `float(os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE", "0.05"))`, `os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT", "minimal")`.

**Status**: <PENDING>

---

### T03: Implement `resolve_model_config` and `resolve_bot_language` in resolver
**Spec Reference**: Configuration, Transcription

- Add `@overload` for `resolve_model_config(bot_id, Literal["image_transcription"]) -> ImageTranscriptionProviderConfig`.
- Add `elif config_tier == "image_transcription"` returning `ImageTranscriptionProviderConfig.model_validate(tier_data)` in `resolve_model_config`.
- Create `resolve_bot_language(bot_id: str) -> str` that fetches `config_data.configurations.user_details.language_code` from `get_global_state().configurations_collection.find_one(...)` with fallback `"en"`. Wrap entire DB fetch in `try/except Exception: return "en"` — must never raise.

**Status**: <PENDING>

---

### T04: Refactor model provider base architecture (LLMProvider, OpenAiMixin)
**Spec Reference**: Technical Details §1 (Provider Architecture)

- In `model_providers/base.py`: Define abstract `LLMProvider(BaseModelProvider)` with `get_llm() -> BaseChatModel`.
- In `model_providers/chat_completion.py`: Make `ChatCompletionProvider` inherit from `LLMProvider`, remove `@abstractmethod get_llm`, replace body with `pass` (type-marker).
- Create `OpenAiMixin` with shared `_build_llm_params()` (model_dump → pop api_key_source, record_llm_interactions → resolve API key → filter None-valued optional fields). `_resolve_api_key` stays in `BaseModelProvider`.
- Add comment in `BaseModelProvider._resolve_api_key()`: must remain strictly synchronous, no external I/O.
- Refactor `OpenAiChatProvider` to use `OpenAiMixin` and constructor-time `self._llm`; `get_llm()` returns `self._llm` only.
- Remove all `print()` debug statements from `OpenAiChatProvider`.

**Status**: <PENDING>

---

### T05: Create `ImageTranscriptionProvider` abstract and `OpenAiImageTranscriptionProvider`
**Spec Reference**: Transcription, Technical Details §1, Technical Details §2 (OpenAI Vision Parameter)

- Create `model_providers/image_transcription.py`: abstract `ImageTranscriptionProvider(LLMProvider, ABC)` with `async def transcribe_image(base64_image, mime_type, language_code) -> str`.
- Create `model_providers/openAiImageTranscription.py`: `OpenAiImageTranscriptionProvider(ImageTranscriptionProvider, OpenAiMixin)`.
- `__init__`: call `params = self._build_llm_params()`, pop `detail` into `self._detail`, instantiate `ChatOpenAI(**params)` as `self._llm`.
- Implement `transcribe_image`: build multimodal `HumanMessage` with prompt *"Describe the contents of this image explicitly in the following language: {language_code}, and concisely in 1-3 sentences. If there is text in the image, add the text inside image to description as well."* + image_url data URI with `detail` from config.
- Transcription response normalization: str → as-is; content blocks → concatenate text-bearing blocks (single-space, trim); otherwise → `"Unable to transcribe image content"`.
- `detail` must never be passed to `ChatOpenAI(...)` constructor; used only in multimodal payload.

**Status**: <PENDING>

---

### T06: Update `create_model_provider` and `find_provider_class`
**Spec Reference**: Configuration (feature_name), Technical Details §1

- Update return type: `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider]`.
- Refactor to unified `isinstance(provider, LLMProvider)` branch: get `llm`, attach `TokenTrackingCallback`, return `llm` if `ChatCompletionProvider` else return `provider`.
- For `ImageModerationProvider`: return provider directly (no LLM, no token tracking).
- In `utils/provider_utils.py` `find_provider_class`: add `obj.__module__ == module.__name__` filter in inspect loop; add docstring note on defensive measure. Keep `not inspect.isabstract(obj)`.

**Status**: <PENDING>

---

### T07: Extract httpx logger from model providers to main.py startup
**Spec Reference**: Technical Details §1 (Provider Architecture)

- Remove `httpx_logger` configuration block from `OpenAiChatProvider.get_llm()` (and any similar in other providers).
- Ensure `main.py` already configures httpx (line 37: `logging.getLogger("httpx").setLevel(logging.WARNING)`) — verify no provider mutates httpx; remove any provider-side httpx setup.

**Status**: <PENDING>

---

### T08: Implement `format_processing_result` and refactor `BaseMediaProcessor.process_job`
**Spec Reference**: Output Format, Processing Flow (TimeoutError, prefix injection)

- Add module-level `format_processing_result(content: str, caption: str) -> str` in `media_processors/base.py`: pure function, wrap content in `[<content>]`; if `caption` non-empty append `\n[Caption: <caption>]`.
- Refactor `process_job` per spec snippet: extract caption once; `process_media` without caption; TimeoutError returns `ProcessingResult(content="Processing timed out", failed_reason=..., unprocessable_media=True)`; prefix injection only when `not unprocessable_media and not failed_reason`; `media_type = job.mime_type.replace("media_corrupt_", "").split("/")[0].capitalize()`; `result.content = format_processing_result(result.content, caption)` before persist/archive/delivery.
- Update `_handle_unhandled_exception`: `ProcessingResult(content="Media processing failed", failed_reason=error, unprocessable_media=True)`; call `format_processing_result` first before `_persist_result_first`.

**Status**: <PENDING>

---

### T09: Remove caption param from `process_media` across all 7 processors
**Spec Reference**: Output Format

- Update abstract `process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult` in `BaseMediaProcessor`.
- Remove `caption` from signature in: `ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`.
- Update `process_job` call to `self.process_media(file_path, job.mime_type, job.bot_id)`.

**Status**: <PENDING>

---

### T10: Update error/stub processor content strings per spec
**Spec Reference**: Output Format (explicit content definitions)

- `CorruptMediaProcessor`: `ProcessingResult(content=f"Corrupted {media_type} media could not be downloaded", failed_reason=..., unprocessable_media=True)`; preserve `media_type = mime_type.replace("media_corrupt_", "")`.
- `UnsupportedMediaProcessor`: `ProcessingResult(content=f"Unsupported media type: {mime_type}", failed_reason=..., unprocessable_media=True)`.
- `StubSleepProcessor` (and inheriting): `ProcessingResult(content=f"multimedia message with guid='{...}'")` — no "Transcripted", no brackets, `unprocessable_media=False`.

**Status**: <PENDING>

---

### T11: Add `image/gif` to ImageVisionProcessor pool and create migration
**Spec Reference**: Processing Flow (ImageVisionProcessor requirements)

- Update `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py`: add `"image/gif"` to ImageVisionProcessor mime types list (alongside jpeg, png, webp).
- Create `scripts/migrations/migrate_pool_definitions_gif.py`: delete the `_mediaProcessorDefinitions` document from `configurations` collection (use `infrastructure/db_schema.py` constants). Script completely deletes the document so server recreates from defaults on next boot.

**Status**: <PENDING>

---

### T12: Implement ImageVisionProcessor moderation→transcription flow
**Spec Reference**: Processing Flow, Transcription

- Call `create_model_provider(bot_id, "media_processing", "image_moderation")` for moderation.
- If `moderation_result.flagged == True`: return `ProcessingResult(content="cannot process image as it violates safety guidelines", failed_reason=None, unprocessable_media=True)`.
- If `moderation_result.flagged == False`: call `resolve_bot_language(bot_id)`; call `create_model_provider(bot_id, "image_transcription", "image_transcription")`; `await provider.transcribe_image(base64_image, mime_type, language_code)`; return transcription as `ProcessingResult(content=transcript, failed_reason=None, unprocessable_media=False)`.
- No try/except around `transcribe_image`; let exceptions propagate to `BaseMediaProcessor.process_job`.

**Status**: <PENDING>

---

### T13: Token menu and migration scripts for image_transcription tier
**Spec Reference**: Configuration (global_configurations.token_menu), Deployment Checklist §1-8

- Extend `global_configurations.token_menu` with `"image_transcription"`: `input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`.
- Create `scripts/migrations/migrate_image_transcription.py`: iterate bot configs in `COLLECTION_BOT_CONFIGURATIONS`, add `config_data.configurations.llm_configs.image_transcription` where missing (use `infrastructure/db_schema.py` constants).
- Update `scripts/migrations/initialize_quota_and_bots.py`: add `image_transcription` tier to `token_menu` (3-tier menu: high, low, image_transcription). Add comment: `image_moderation` intentionally omitted from token_menu.
- Create `scripts/migrations/migrate_token_menu_image_transcription.py`: delete existing `token_menu` and re-insert full 3-tier menu.
- Migration contract: all scripts import and use `infrastructure/db_schema.py` constants (no hardcoded names).
- `QuotaService.load_token_menu()` remains read-only; no self-healing insert logic.

**Status**: <PENDING>

---

### T14: Update `get_configuration_schema` and `get_bot_defaults` in bot_management
**Spec Reference**: Configuration, Deployment Checklist §3, New Configuration Tier Checklist

- In `get_configuration_schema`: change surgery loop to `for prop_name in llm_configs_defs['properties'].keys():` (dynamic iteration).
- Apply `reasoning_effort` title patches to both `ChatCompletionProviderSettings` AND `ImageTranscriptionProviderSettings`.
- In `get_bot_defaults`: add `image_transcription` to `LLMConfigurations` using `ImageTranscriptionProviderConfig` and `DefaultConfigurations` values.

**Status**: <PENDING>

---

### T15: Create GET /api/internal/bots/tiers endpoint
**Spec Reference**: New Configuration Tier Checklist §4

- Add `GET /api/internal/bots/tiers` in `routers/bot_management.py` returning `list(str)` of `LLMConfigurations.model_fields.keys()`.
- Endpoint aligns with existing `/api/internal/bots` prefix; gateway generic proxy maps `/api/external/bots/tiers` → backend.

**Status**: <PENDING>

---

### T16: Update frontend EditPage with tiers API and image_transcription uiSchema
**Spec Reference**: New Configuration Tier Checklist §4-5

- Abandon `getAvailableTiers` JS helper; fetch tiers from `GET /api/external/bots/tiers` during `fetchData`, store in component state.
- Replace hardcoded `["high", "low", "image_moderation"]` (lines ~135, ~229) with dynamically fetched tier list.
- Add fourth `llm_configs` entry in `uiSchema` for `image_transcription`: `ui:title "Image Transcription Model"`, `NestedCollapsibleObjectFieldTemplate`, provider_config with `api_key_source`, `reasoning_effort`, `seed`, `detail` (ui:title "Image Detail Level"), `FlatProviderConfigTemplate` — matching high/low structure.

**Status**: <PENDING>

---

### T17: Delete `LLMProviderSettings` and `LLMProviderConfig` from config_models
**Spec Reference**: Deployment Checklist §10

- Remove `LLMProviderSettings` and `LLMProviderConfig` classes from `config_models.py` entirely.
- Update any imports/usages (if any); spec states they are unused dead code.

**Status**: <PENDING>

---

### T18: Add/update tests per Test Expectations section
**Spec Reference**: Test Expectations

- Test `detail` filtered from `ChatOpenAI(...)` constructor kwargs, used only in transcription payload.
- Test callback continuity: same LLM object reference in `create_model_provider` attachment and `transcribe_image` invocation.
- Transcription normalization: string→as-is; content blocks→concatenated; unsupported→`"Unable to transcribe image content"`.
- Test `moderation_result.flagged == True` → `ProcessingResult(unprocessable_media=True, content="cannot process image as it violates safety guidelines")`.
- Test `format_processing_result`: bracket wrapping; caption append when `job.placeholder_message.content` populated.
- Test `asyncio.TimeoutError` path returns `ProcessingResult(unprocessable_media=True)`.
- Unit: `process_media()` returns raw unbracketed strings (no legacy `[...]`).
- Integration: final string to queue is `"[{MediaType} Transcription: {content}]"` form.
- Update existing tests: `UnsupportedMediaProcessor` content `f"Unsupported media type: {mime_type}"`; `CorruptMediaProcessor` content `f"Corrupted {media_type} media could not be downloaded"` (unbracketed).
- Update `test_process_media_bot_id_signature`: use `assert "bot_id" in sig.parameters` (robust key lookup); remove hardcoded index assertion.
- Update `process_media` signature assertions: caption param removed (3 params: file_path, mime_type, bot_id).

**Status**: <PENDING>
