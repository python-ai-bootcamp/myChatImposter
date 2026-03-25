# Implementation Task: Image Transcription Support
## Implementation Task ID: 07_oc_mimo_v2_pro
## Feature: imageTranscriptSupport
## Status: PENDING

### Summary Table
| Task ID | Description | Spec Section | Status |
|---------|-------------|--------------|--------|
| 1.1 | Add `image_transcription` to `ConfigTier` and add comment | Configuration (lines 12-19) | PENDING |
| 1.2 | Create `ImageTranscriptionProviderSettings` class with `detail` field | Configuration (line 13) | PENDING |
| 1.3 | Create `ImageTranscriptionProviderConfig` extending `ChatCompletionProviderConfig` | Configuration (line 14) | PENDING |
| 1.4 | Add required `image_transcription` field to `LLMConfigurations` | Configuration (line 14), Deployment (line 352) | PENDING |
| 1.5 | Update `DefaultConfigurations` with image transcription env-var defaults | Configuration (line 12), Deployment (line 350) | PENDING |
| 1.6 | Add `resolve_model_config` overload and branch for `image_transcription` | Configuration (line 16), Tier Checklist (line 371) | PENDING |
| 1.7 | Create `resolve_bot_language` function with safe fallback | Configuration (line 17), Transcription (line 33) | PENDING |
| 1.8 | Extend `get_configuration_schema` dynamic tier iteration + title patches | Configuration (line 19), Tier Checklist (line 372) | PENDING |
| 2.1 | Add `unprocessable_media: bool = False` to `ProcessingResult` | Processing Flow (line 22) | PENDING |
| 2.2 | Add `"image/gif"` to `DEFAULT_POOL_DEFINITIONS` ImageVisionProcessor | Processing Flow (line 23) | PENDING |
| 2.3 | Create migration script `migrate_pool_definitions_gif.py` | Processing Flow (line 25) | PENDING |
| 3.1 | Define `LLMProvider` abstract class in `model_providers/base.py` | Provider Architecture (line 296) | PENDING |
| 3.2 | Refactor `model_providers/chat_completion.py` to empty type-marker | Provider Architecture (line 296) | PENDING |
| 3.3 | Create `model_providers/image_transcription.py` with `ImageTranscriptionProvider` | Provider Architecture (lines 297-314) | PENDING |
| 3.4 | Create `OpenAiMixin` in `model_providers/openAi.py` + refactor `OpenAiChatProvider` | Provider Architecture (lines 298-301) | PENDING |
| 3.5 | Create `model_providers/openAiImageTranscription.py` | Provider Architecture (lines 301-302) | PENDING |
| 3.6 | Update `create_model_provider` return type and branching logic | Provider Architecture (lines 316-341) | PENDING |
| 3.7 | Update `find_provider_class` with `__module__` filter | Provider Architecture (line 343) | PENDING |
| 3.8 | Add `_resolve_api_key` sync comment in `model_providers/base.py` | Provider Architecture (line 299) | PENDING |
| 4.1 | Remove `caption` from `process_media` signature across all 8 classes | Output Format (lines 43-48) | PENDING |
| 4.2 | Implement `format_processing_result` pure function in `media_processors/base.py` | Output Format (lines 52-53) | PENDING |
| 4.3 | Refactor `BaseMediaProcessor.process_job` with prefix injection + formatting | Output Format (lines 54-131) | PENDING |
| 4.4 | Refactor `BaseMediaProcessor._handle_unhandled_exception` | Output Format (lines 132-140) | PENDING |
| 4.5 | Update `CorruptMediaProcessor` content definition | Output Format (line 49) | PENDING |
| 4.6 | Update `UnsupportedMediaProcessor` content definition | Output Format (line 50) | PENDING |
| 4.7 | Update `StubSleepProcessor` content definition | Output Format (line 51) | PENDING |
| 5.1 | Implement full `ImageVisionProcessor.process_media` with moderation + transcription | Processing Flow (lines 27-40), Transcription (lines 31-41) | PENDING |
| 5.2 | Handle flagged images in `ImageVisionProcessor` | Processing Flow (lines 28-29) | PENDING |
| 5.3 | Handle timeout path: `unprocessable_media=True` + remove brackets | Output Format (lines 39-40) | PENDING |
| 6.1 | Create migration script `migrate_image_transcription.py` | Deployment (line 349) | PENDING |
| 6.2 | Update `initialize_quota_and_bots.py` token_menu with `image_transcription` tier | Deployment (line 353) | PENDING |
| 6.3 | Create migration script `migrate_token_menu_image_transcription.py` | Deployment (line 354) | PENDING |
| 6.4 | Delete dead code `LLMProviderSettings` and `LLMProviderConfig` | Deployment (line 362) | PENDING |
| 7.1 | Add API endpoint `GET /api/internal/bots/tiers` | Tier Checklist (line 374) | PENDING |
| 7.2 | Update `EditPage.js`: dynamic tiers fetch + `image_transcription` UI schema | Tier Checklist (lines 375-378) | PENDING |
| 8.1 | Add tests for `detail` filtering from ChatOpenAI kwargs | Test Expectations (line 380) | PENDING |
| 8.2 | Add tests for callback continuity | Test Expectations (line 381) | PENDING |
| 8.3 | Add tests for transcription normalization (3 branches) | Test Expectations (lines 382-385) | PENDING |
| 8.4 | Add test for flagged images returning correct ProcessingResult | Test Expectations (line 386) | PENDING |
| 8.5 | Add tests for `format_processing_result` bracket wrapping + captions | Test Expectations (lines 387-388) | PENDING |
| 8.6 | Add test for timeout returning `unprocessable_media=True` | Test Expectations (line 389) | PENDING |
| 8.7 | Update existing tests: raw content assertions, new strings, signature index | Test Expectations (lines 390-393) | PENDING |

---

## Detailed Tasks

### Phase 1: Configuration Models (`config_models.py` + `services/resolver.py`)

#### Task 1.1: Add `image_transcription` to `ConfigTier`
- **File**: `config_models.py`
- **Description**: Update `ConfigTier = Literal["high", "low", "image_moderation"]` to `Literal["high", "low", "image_moderation", "image_transcription"]`. Add a comment directly above the `LLMConfigurations` model and the `ConfigTier` Literal: *"These two locations are the ONLY places in the code where the structure/keys of the tiers are defined."*
- **Spec Ref**: Configuration (line 12), Tier Checklist (line 366-370).
- **Status**: PENDING

#### Task 1.2: Create `ImageTranscriptionProviderSettings` class
- **File**: `config_models.py`
- **Description**: Create a new class inheriting from `ChatCompletionProviderSettings` adding `detail: Literal["low", "high", "original", "auto"] = "auto"` field.
- **Spec Ref**: Configuration (line 13).
- **Status**: PENDING

#### Task 1.3: Create `ImageTranscriptionProviderConfig`
- **File**: `config_models.py`
- **Description**: Create a new config class extending `ChatCompletionProviderConfig` and redefine `provider_config: ImageTranscriptionProviderSettings`. The `LLMConfigurations.image_transcription` field type is `ImageTranscriptionProviderConfig`.
- **Spec Ref**: Configuration (line 14).
- **Status**: PENDING

#### Task 1.4: Add required `image_transcription` field to `LLMConfigurations`
- **File**: `config_models.py`
- **Description**: Add `image_transcription: ImageTranscriptionProviderConfig = Field(..., title="Image Transcription Model")` to `LLMConfigurations`. Use `Field(...)` to make it strictly required, consistent with the other tiers.
- **Spec Ref**: Configuration (line 14), Deployment (line 352).
- **Status**: PENDING

#### Task 1.5: Update `DefaultConfigurations` with image transcription defaults
- **File**: `config_models.py`
- **Description**: Add to `DefaultConfigurations`:
  - `model_provider_name_image_transcription = "openAiImageTranscription"` (must match provider module name)
  - `model_image_transcription = os.getenv("DEFAULT_MODEL_IMAGE_TRANSCRIPTION", "gpt-5-mini")`
  - `model_image_transcription_temperature = float(os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE", "0.05"))`
  - `model_image_transcription_reasoning_effort = os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT", "minimal")`
  Fallback values `"0.05"` and `"minimal"` match the existing `low` tier defaults and must always be specified to prevent startup crashes.
- **Spec Ref**: Configuration (line 12), Deployment (line 350).
- **Status**: PENDING

#### Task 1.6: Update `resolve_model_config` with `image_transcription` tier
- **File**: `services/resolver.py`
- **Description**: Add `@overload async def resolve_model_config(bot_id: str, config_tier: Literal["image_transcription"]) -> ImageTranscriptionProviderConfig` type hint. Add `elif config_tier == "image_transcription":` branch in the implementation returning `ImageTranscriptionProviderConfig.model_validate(tier_data)`. Import `ImageTranscriptionProviderConfig` explicitly. Keep the existing `image_moderation` branch returning `BaseModelProviderConfig`.
- **Spec Ref**: Configuration (line 16), Tier Checklist (line 371).
- **Status**: PENDING

#### Task 1.7: Create `resolve_bot_language` function
- **File**: `services/resolver.py`
- **Description**: Create `async def resolve_bot_language(bot_id: str) -> str` that fetches `config_data.configurations.user_details.language_code` using `get_global_state().configurations_collection.find_one(...)`. Must **never raise an error** — fall back to `"en"` on any missing document, missing field, or any exception. Wrap the entire DB fetch block in bare `try/except Exception: return "en"`. Do NOT mirror `resolve_model_config`'s error-raising pattern.
- **Spec Ref**: Configuration (line 17), Transcription (line 33).
- **Status**: PENDING

#### Task 1.8: Update `get_configuration_schema` dynamic tier iteration + title patches
- **File**: `routers/bot_management.py`
- **Description**: Replace hardcoded `['high', 'low', 'image_moderation']` list in schema surgery loop with dynamic iteration: `for prop_name in llm_configs_defs['properties'].keys():`. Also add `reasoning_effort` title patches for `'ImageTranscriptionProviderSettings'` alongside existing `'ChatCompletionProviderSettings'` patches (same logic applied to both).
- **Spec Ref**: Configuration (line 19), Tier Checklist (line 372).
- **Status**: PENDING

---

### Phase 2: Processing Flow Infrastructure

#### Task 2.1: Add `unprocessable_media` field to `ProcessingResult`
- **File**: `infrastructure/models.py`
- **Description**: Add `unprocessable_media: bool = False` to the `ProcessingResult` dataclass. Add a docstring: *"True means the media could not be meaningfully transcribed, signaling `process_job` to skip prefix injection for the error payload."*
- **Spec Ref**: Processing Flow (line 22).
- **Status**: PENDING

#### Task 2.2: Add `"image/gif"` to `DEFAULT_POOL_DEFINITIONS`
- **File**: `services/media_processing_service.py`
- **Description**: Update `DEFAULT_POOL_DEFINITIONS` to include `"image/gif"` in the `ImageVisionProcessor` mime types list (alongside `image/jpeg`, `image/png`, `image/webp`).
- **Spec Ref**: Processing Flow (line 23).
- **Status**: PENDING

#### Task 2.3: Create migration script `migrate_pool_definitions_gif.py`
- **File**: `scripts/migrations/migrate_pool_definitions_gif.py` (new)
- **Description**: Create a script that completely **deletes** the existing `_mediaProcessorDefinitions` document from the MongoDB `configurations` collection. Existing environments seed pool definitions into MongoDB on first run and subsequently read from DB — a code-only change to `DEFAULT_POOL_DEFINITIONS` will not affect already-initialized environments. On next server boot, the service will auto-recreate from updated Python defaults. Import and use `infrastructure/db_schema.py` constants (no hardcoded collection names).
- **Spec Ref**: Processing Flow (line 25), Deployment (line 357).
- **Status**: PENDING

---

### Phase 3: Provider Architecture

#### Task 3.1: Define `LLMProvider` abstract class
- **File**: `model_providers/base.py`
- **Description**: Define a new abstract base class `LLMProvider` inheriting from `BaseModelProvider` that declares `@abstractmethod def get_llm(self) -> BaseChatModel`. Import `BaseChatModel` from `langchain_core.language_models.chat_models`. Also add a comment inside `BaseModelProvider._resolve_api_key()` defining that it must remain strictly synchronous and perform no external I/O or background async polling, relying strictly on pre-resolved synchronous `self.config` properties.
- **Spec Ref**: Provider Architecture (lines 296, 299).
- **Status**: PENDING

#### Task 3.2: Refactor `model_providers/chat_completion.py` to empty type-marker
- **File**: `model_providers/chat_completion.py`
- **Description**: Make `ChatCompletionProvider` inherit from `LLMProvider` instead of `BaseModelProvider`. Remove the `@abstractmethod def get_llm(self)` declaration and `abc` imports. Replace the class body with `pass` so it cleanly acts as an empty type-marker class.
- **Spec Ref**: Provider Architecture (line 296).
- **Status**: PENDING

#### Task 3.3: Create `model_providers/image_transcription.py`
- **File**: `model_providers/image_transcription.py` (new)
- **Description**: Create `ImageTranscriptionProvider(LLMProvider, ABC)` with abstract method `async def transcribe_image(self, base64_image: str, mime_type: str, language_code: str) -> str`. It inherits `get_llm() -> BaseChatModel` from `LLMProvider`.
- **Spec Ref**: Provider Architecture (lines 297-314).
- **Status**: PENDING

#### Task 3.4: Create `OpenAiMixin` + refactor `OpenAiChatProvider`
- **File**: `model_providers/openAi.py`
- **Description**:
  1. Create `OpenAiMixin` class containing `_build_llm_params()` — the shared OpenAI kwargs building logic (`model_dump()` → pop `api_key_source`, `record_llm_interactions` → resolve API key → filter `None`-valued optional fields like `reasoning_effort`, `seed`). Remove print debug statements.
  2. Refactor `OpenAiChatProvider` to inherit from `ChatCompletionProvider` and `OpenAiMixin`. Use constructor-time initialization: create `ChatOpenAI` instance inside `__init__` and store as `self._llm`. Make `get_llm()` simply `return self._llm`. Each subclass pops its own extra fields before passing kwargs to `ChatOpenAI(...)`.
  3. Extract the `httpx` logger configuration from `get_llm()` — move it to `main.py` (already has `logging.getLogger("httpx").setLevel(logging.WARNING)` on line 36).
- **Spec Ref**: Provider Architecture (lines 298-300).
- **Status**: PENDING

#### Task 3.5: Create `model_providers/openAiImageTranscription.py`
- **File**: `model_providers/openAiImageTranscription.py` (new)
- **Description**: Create `OpenAiImageTranscriptionProvider(ImageTranscriptionProvider, OpenAiMixin)`:
  - `__init__`: call `params = self._build_llm_params()`, then `self._detail = params.pop("detail", "auto")`, then `self._llm = ChatOpenAI(**params)`.
  - `get_llm()`: return `self._llm`.
  - `transcribe_image(base64_image, mime_type, language_code)`: construct a multimodal `HumanMessage` with text prompt *"Describe the contents of this image explicitly in the following language: {language_code}, and concisely in 1-3 sentences. If there is text in the image, add the text inside image to description as well."* + `image_url` data URI with `detail` from config. Invoke via `ainvoke`. Normalize response per contract:
    - If `response.content` is `str`: return as-is.
    - If content blocks: extract text-bearing blocks in original order, concatenate with single-space separator, trim outer whitespace.
    - Otherwise: return `"Unable to transcribe image content"`.
- **Spec Ref**: Provider Architecture (lines 301-302), Transcription (lines 34-38).
- **Status**: PENDING

#### Task 3.6: Update `create_model_provider` return type and branching
- **File**: `services/model_factory.py`
- **Description**: Update return type annotation to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider]`. Refactor branching:
  1. `isinstance(provider, LLMProvider)` → `llm = provider.get_llm()`, attach `TokenTrackingCallback(llm)`.
  2. Inside that branch: `isinstance(provider, ChatCompletionProvider)` → return `llm` (raw); else → return `provider` (wrapper, i.e. `ImageTranscriptionProvider`).
  3. `isinstance(provider, ImageModerationProvider)` → return `provider` (no LLM, no token tracking).
  Import `LLMProvider` and `ImageTranscriptionProvider`.
- **Spec Ref**: Provider Architecture (lines 316-341).
- **Status**: PENDING

#### Task 3.7: Update `find_provider_class` with `__module__` filter
- **File**: `utils/provider_utils.py`
- **Description**: Add `obj.__module__ == module.__name__` filter in the `inspect.getmembers` loop alongside the existing `not inspect.isabstract(obj)` check. This ensures only the class defined in that specific file is picked, ignoring imported base classes. Add a docstring note explaining this is a defensive measure.
- **Spec Ref**: Provider Architecture (line 343).
- **Status**: PENDING

#### Task 3.8: Add `_resolve_api_key` sync constraint comment
- **File**: `model_providers/base.py`
- **Description**: Add an explicit comment inside `BaseModelProvider._resolve_api_key()` stating it must remain strictly synchronous and perform no external I/O, relying strictly on pre-resolved synchronous `self.config` properties (required because `ChatOpenAI` instantiation happens inside synchronous `__init__` constructors).
- **Spec Ref**: Provider Architecture (line 299).
- **Status**: PENDING

---

### Phase 4: Output Format Refactoring (`media_processors/`)

#### Task 4.1: Remove `caption` from `process_media` across all 8 classes
- **Files**: `media_processors/base.py`, `media_processors/image_vision_processor.py`, `media_processors/stub_processors.py`, `media_processors/error_processors.py`
- **Description**: Update the abstract method signature and all 7 affected subclasses (`ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`) to remove the `caption` parameter. New signature:
  ```python
  @abstractmethod
  async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:
  ```
  Update `BaseMediaProcessor.process_job()` to pass `file_path, job.mime_type, job.bot_id` instead of including `caption`.
- **Spec Ref**: Output Format (lines 43-48).
- **Status**: PENDING

#### Task 4.2: Implement `format_processing_result` pure function
- **File**: `media_processors/base.py`
- **Description**: Implement as a module-level function:
  ```python
  def format_processing_result(content: str, caption: str) -> str:
  ```
  - Unconditionally wrap content in brackets: `[{content}]`
  - If `caption` is a non-empty string (`if caption:`): append `\n[Caption: {caption_text}]`
  - If `caption` is `None` or `""`: return as-is after bracket-wrapping
  - Must be a pure function (no mutation of arguments).
- **Spec Ref**: Output Format (lines 52-53).
- **Status**: PENDING

#### Task 4.3: Refactor `BaseMediaProcessor.process_job`
- **File**: `media_processors/base.py`
- **Description**: Replace the current implementation with the complete spec-provided logic:
  1. Extract `caption = job.placeholder_message.content` once at top.
  2. Call `self.process_media(file_path, job.mime_type, job.bot_id)` (caption removed).
  3. On `asyncio.TimeoutError`: set `result = ProcessingResult(content="Processing timed out", failed_reason=..., unprocessable_media=True)`.
  4. Prefix injection: only when `not result.unprocessable_media and not result.failed_reason` — prepend `"{MediaType} Transcription: "` (media_type derived from `job.mime_type.replace("media_corrupt_", "").split("/")[0].capitalize()`).
  5. Call `result.content = format_processing_result(result.content, caption)` — MUST happen before any persistence or delivery.
  6. Then persist, archive, queue delivery as before.
- **Spec Ref**: Output Format (lines 54-131).
- **Status**: PENDING

#### Task 4.4: Refactor `_handle_unhandled_exception`
- **File**: `media_processors/base.py`
- **Description**: Update to:
  1. Extract `caption = job.placeholder_message.content`.
  2. Create `result = ProcessingResult(content="Media processing failed", failed_reason=error, unprocessable_media=True)`.
  3. Call `result.content = format_processing_result(result.content, caption)` FIRST, before persistence.
  4. Then call `_persist_result_first`, `_archive_to_failed`, and best-effort queue delivery.
  The content string must be `"Media processing failed"` (no brackets) — `format_processing_result` adds them.
- **Spec Ref**: Output Format (lines 132-140).
- **Status**: PENDING

#### Task 4.5: Update `CorruptMediaProcessor` content definition
- **File**: `media_processors/error_processors.py`
- **Description**: Update `process_media` to return `ProcessingResult(content=f"Corrupted {media_type} media could not be downloaded", failed_reason=..., unprocessable_media=True)` — no caption handling, no brackets. Preserve existing `media_type = mime_type.replace("media_corrupt_", "")` derivation.
- **Spec Ref**: Output Format (line 49).
- **Status**: PENDING

#### Task 4.6: Update `UnsupportedMediaProcessor` content definition
- **File**: `media_processors/error_processors.py`
- **Description**: Update `process_media` to return `ProcessingResult(content=f"Unsupported media type: {mime_type}", failed_reason=..., unprocessable_media=True)` — no caption handling, no brackets.
- **Spec Ref**: Output Format (line 50).
- **Status**: PENDING

#### Task 4.7: Update `StubSleepProcessor` content definition
- **File**: `media_processors/stub_processors.py`
- **Description**: Update `process_media` to return `ProcessingResult(content=f"{self.media_label} multimedia message with guid='{os.path.basename(file_path)}'")` — no redundant "Transcripted" phrasing, no brackets. `unprocessable_media` defaults to `False` (success path). `process_job` will now automatically prepend the transcription prefix.
- **Spec Ref**: Output Format (line 51).
- **Status**: PENDING

---

### Phase 5: ImageVisionProcessor Transcription Flow

#### Task 5.1: Implement full `ImageVisionProcessor.process_media` with transcription
- **File**: `media_processors/image_vision_processor.py`
- **Description**: Update `process_media(file_path, mime_type, bot_id)` (caption removed):
  1. Load base64 image via `asyncio.to_thread(_load_image_base64, file_path)`.
  2. Create moderation provider via `create_model_provider(bot_id, "media_processing", "image_moderation")`, call `moderate_image(base64_image, mime_type)`.
  3. If `moderation_result.flagged == False`:
     - Call `resolve_bot_language(bot_id)` to get language_code (inside this branch only, to avoid unnecessary DB queries on flagged images).
     - Create transcription provider via `create_model_provider(bot_id, "image_transcription", "image_transcription")` — note: `feature_name` must be `"image_transcription"` for fine-grained token tracking.
     - If provider is `ImageTranscriptionProvider` instance: call `await provider.transcribe_image(base64_image, mime_type, language_code)`.
     - Return `ProcessingResult(content=transcript)` — raw content, no brackets, no prefix (prefix added by `process_job`).
  4. No custom error handling (`try/except`) around `transcribe_image` — exceptions propagate to `process_job`.
- **Spec Ref**: Processing Flow (lines 27-40), Transcription (lines 31-38).
- **Status**: PENDING

#### Task 5.2: Handle flagged images
- **File**: `media_processors/image_vision_processor.py`
- **Description**: If `moderation_result.flagged == True`, return `ProcessingResult(content="cannot process image as it violates safety guidelines", failed_reason=None, unprocessable_media=True)`. Do not return specific flagged tags. Flagged images are a successful detection, not a system failure — they bypass the `_failed` archive collection intentionally (because `failed_reason=None`).
- **Spec Ref**: Processing Flow (lines 28-29).
- **Status**: PENDING

#### Task 5.3: Handle timeout path correctly
- **File**: `media_processors/base.py` (in `process_job`)
- **Description**: The `asyncio.TimeoutError` handler must return `ProcessingResult(content="Processing timed out", failed_reason=f"TIMEOUT: processing exceeded {self.processing_timeout}s", unprocessable_media=True)`. Content has no brackets (added by `format_processing_result`). `failed_reason` is set so timeout jobs are archived to `_failed` for operator monitoring. The final delivered string will be `[Processing timed out]` after formatting.
- **Spec Ref**: Output Format (lines 39-40).
- **Status**: PENDING

---

### Phase 6: Deployment and Migration

#### Task 6.1: Create migration script `migrate_image_transcription.py`
- **File**: `scripts/migrations/migrate_image_transcription.py` (new)
- **Description**: Iterate existing bot configs in MongoDB and add `config_data.configurations.llm_configs.image_transcription` where missing, using `DefaultConfigurations` values. Follow existing migration patterns. Target `infrastructure/db_schema.py::COLLECTION_BOT_CONFIGURATIONS`. Use `db_schema` constants (no hardcoded collection names).
- **Spec Ref**: Deployment (line 349).
- **Status**: PENDING

#### Task 6.2: Update `initialize_quota_and_bots.py` with `image_transcription` token menu tier
- **File**: `scripts/migrations/initialize_quota_and_bots.py`
- **Description**: Add `image_transcription` tier to the `token_menu` dictionary with values: `input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`. Bring total to 3 tiers (`high`, `low`, `image_transcription`). Keep internal logic "insert-if-not-exists". Add a comment highlighting that `image_moderation` is intentionally omitted from the `token_menu` because it has no model-token cost calculation.
- **Spec Ref**: Deployment (line 353), Configuration (line 18).
- **Status**: PENDING

#### Task 6.3: Create migration script `migrate_token_menu_image_transcription.py`
- **File**: `scripts/migrations/migrate_token_menu_image_transcription.py` (new)
- **Description**: Completely delete any existing `token_menu` document and re-insert the full correct menu from scratch (hard reset). This is acceptable because there is currently no actual production environment. Use `db_schema` constants.
- **Spec Ref**: Deployment (line 354).
- **Status**: PENDING

#### Task 6.4: Delete dead code `LLMProviderSettings` and `LLMProviderConfig`
- **File**: `config_models.py`
- **Description**: Remove the unused `LLMProviderSettings` and `LLMProviderConfig` classes entirely from `config_models.py` to prevent confusion with the active `ChatCompletionProviderConfig` family of classes.
- **Spec Ref**: Deployment (line 362).
- **Status**: PENDING

---

### Phase 7: Frontend Updates

#### Task 7.1: Add API endpoint `GET /api/internal/bots/tiers`
- **File**: `routers/bot_management.py`
- **Description**: Create a new endpoint that directly returns the available tiers by reading `LLMConfigurations.model_fields.keys()` from the Python model. This correctly aligns with the existing `/api/internal/bots` router prefix.
- **Spec Ref**: Tier Checklist (line 374).
- **Status**: PENDING

#### Task 7.2: Update `EditPage.js`: dynamic tiers + `image_transcription` UI schema
- **File**: `frontend/src/pages/EditPage.js`
- **Description**:
  1. Fetch from new endpoint (`/api/internal/bots/tiers` or mapped equivalent via gateway) during `fetchData` and store in component state.
  2. Replace every occurrence of the hardcoded tier array `["high", "low", "image_moderation"]` (around line 135 for `api_key_source` and line 229 for `handleFormChange`) with the dynamically fetched tier list.
  3. Add a fourth entry to the `llm_configs` object in `uiSchema` for `image_transcription`:
     - `"ui:title": "Image Transcription Model"`
     - `provider_config` sub-object identical to `high`/`low` tiers (including `FlatProviderConfigTemplate`, `api_key_source`, `reasoning_effort`, `seed` UI title properties).
     - Include `detail` field inside `provider_config` with `"ui:title": "Image Detail Level"`.
- **Spec Ref**: Tier Checklist (lines 375-378).
- **Status**: PENDING

---

### Phase 8: Testing

#### Task 8.1: Add tests for `detail` parameter filtering
- **File**: `tests/test_image_vision_processor.py` (or new test file)
- **Description**: Verify `detail` is filtered from `ChatOpenAI(...)` constructor kwargs and only used in transcription payload construction.
- **Spec Ref**: Test Expectations (line 380).
- **Status**: PENDING

#### Task 8.2: Add tests for callback continuity
- **Description**: Verify callback attachment in `create_model_provider` and transcription invocation in `transcribe_image(...)` use the same LLM object reference.
- **Spec Ref**: Test Expectations (line 381).
- **Status**: PENDING

#### Task 8.3: Add tests for transcription normalization
- **Description**: Cover all 3 branches: string content → returned as-is, content blocks → concatenated deterministic string, unsupported content type → `"Unable to transcribe image content"`.
- **Spec Ref**: Test Expectations (lines 382-385).
- **Status**: PENDING

#### Task 8.4: Add test for flagged images handling
- **Description**: Test that `moderation_result.flagged == True` returns `ProcessingResult(unprocessable_media=True, content="cannot process image as it violates safety guidelines", failed_reason=None)`.
- **Spec Ref**: Test Expectations (line 386).
- **Status**: PENDING

#### Task 8.5: Add tests for `format_processing_result`
- **Description**: Test bracket wrapping is unconditional. Test caption appending when `job.placeholder_message.content` is populated. Test no caption suffix when caption is `None` or `""`.
- **Spec Ref**: Test Expectations (lines 387-388).
- **Status**: PENDING

#### Task 8.6: Add test for timeout returning `unprocessable_media=True`
- **Description**: Test that `asyncio.TimeoutError` path returns `ProcessingResult` with `unprocessable_media=True`, `failed_reason` set, content `"Processing timed out"`.
- **Spec Ref**: Test Expectations (line 389).
- **Status**: PENDING

#### Task 8.7: Update existing tests for new content strings and signatures
- **Description**:
  - Update `test_process_media_bot_id_signature`: use robust `assert "bot_id" in sig.parameters` dict lookup instead of hardcoded list index `params[3]`.
  - Update any tests asserting old content strings for `UnsupportedMediaProcessor` (was `"Unsupported {mime_type} media"`) → `"Unsupported media type: {mime_type}"`.
  - Update any tests asserting old content strings for `CorruptMediaProcessor` → `"Corrupted {media_type} media could not be downloaded"`.
  - Update `process_media()` assertions to expect raw, unbracketed content (no legacy `[...]` wrapper).
  - Add integration-level tests for `process_job` end-to-end asserting final delivered string is `"[{MediaType} Transcription: {content}]"`.
- **Spec Ref**: Test Expectations (lines 390-393).
- **Status**: PENDING
