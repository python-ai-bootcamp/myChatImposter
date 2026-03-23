# Implementation Tasks: Image Transcription Support

## Summary Table

| # | Task | Spec Section(s) | Status |
|---|------|-----------------|--------|
| 1 | Add `unprocessable_media` field to `ProcessingResult` dataclass | Processing Flow | PENDING |
| 2 | Create `ImageTranscriptionProviderSettings` and `ImageTranscriptionProviderConfig` in `config_models.py` | Configuration, Technical Details §1 | PENDING |
| 3 | Update `ConfigTier` to include `"image_transcription"` with tier-definition comments | Configuration, New Configuration Tier Checklist §1 | PENDING |
| 4 | Add `image_transcription` required field to `LLMConfigurations` | Configuration, Deployment Checklist §4 | PENDING |
| 5 | Extend `DefaultConfigurations` with image transcription defaults and env vars | Configuration, Deployment Checklist §2 | PENDING |
| 6 | Delete unused dead code `LLMProviderSettings` and `LLMProviderConfig` | Deployment Checklist §10 | PENDING |
| 7 | Create `LLMProvider` abstract base class in `model_providers/base.py` | Technical Details §1 (Provider Architecture) | PENDING |
| 8 | Add synchronous constraint comment to `BaseModelProvider._resolve_api_key()` | Technical Details §1 (Provider Architecture) | PENDING |
| 9 | Refactor `ChatCompletionProvider` to inherit from `LLMProvider` as empty type-marker | Technical Details §1 (Provider Architecture) | PENDING |
| 10 | Create `OpenAiMixin` with shared `_build_llm_params()` logic | Technical Details §1 (Provider Architecture) | PENDING |
| 11 | Refactor `OpenAiChatProvider` to use `OpenAiMixin` with constructor-time `ChatOpenAI` init | Technical Details §1 (Provider Architecture) | PENDING |
| 12 | Move `httpx` logger config from `OpenAiChatProvider` to `main.py`; remove `print()` debug stmts | Technical Details §1 (Provider Architecture) | PENDING |
| 13 | Create abstract `ImageTranscriptionProvider` in `model_providers/image_transcription.py` | Technical Details §1 (Provider Architecture), Transcription | PENDING |
| 14 | Create concrete `OpenAiImageTranscriptionProvider` in `model_providers/openAiImageTranscription.py` | Technical Details §1 (Provider Architecture), Transcription, OpenAI Vision Parameter §2 | PENDING |
| 15 | Add `__module__` filter to `find_provider_class` in `utils/provider_utils.py` | Technical Details §1 (Provider Architecture) | PENDING |
| 16 | Add `resolve_bot_language()` function to `services/resolver.py` | Configuration, Transcription | PENDING |
| 17 | Add `image_transcription` overload and `elif` branch to `resolve_model_config` in `services/resolver.py` | Configuration, New Configuration Tier Checklist §2 | PENDING |
| 18 | Refactor `create_model_provider` in `services/model_factory.py` for unified `LLMProvider` branching | Technical Details §1 (Provider Architecture) | PENDING |
| 19 | Implement `format_processing_result()` module-level function in `media_processors/base.py` | Output Format | PENDING |
| 20 | Remove `caption` parameter from `BaseMediaProcessor.process_media` abstract signature | Output Format | PENDING |
| 21 | Update `CorruptMediaProcessor.process_media` — remove caption param, new content string, set `unprocessable_media=True` | Output Format | PENDING |
| 22 | Update `UnsupportedMediaProcessor.process_media` — remove caption param, new content string, set `unprocessable_media=True` | Output Format | PENDING |
| 23 | Update `StubSleepProcessor.process_media` — remove caption param, new content string (no brackets/Transcripted) | Output Format | PENDING |
| 24 | Update `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor` signatures (inherited from `StubSleepProcessor`) | Output Format | PENDING |
| 25 | Refactor `BaseMediaProcessor.process_job()` — caption extraction, prefix injection, `format_processing_result`, timeout `unprocessable_media` | Output Format, Processing Flow, Transcription (error handling) | PENDING |
| 26 | Refactor `BaseMediaProcessor._handle_unhandled_exception()` — `unprocessable_media=True`, unbracketed content, `format_processing_result` before persistence | Output Format | PENDING |
| 27 | Update `ImageVisionProcessor.process_media` — remove caption, add flagged-image handling, transcription call | Processing Flow, Transcription | PENDING |
| 28 | Add `"image/gif"` to `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` | Processing Flow | PENDING |
| 29 | Create migration script `scripts/migrations/migrate_pool_definitions_gif.py` | Processing Flow | PENDING |
| 30 | Update `get_configuration_schema` in `routers/bot_management.py` — dynamic tier iteration and dual `reasoning_effort` patches | Configuration, New Configuration Tier Checklist §3 | PENDING |
| 31 | Update `get_bot_defaults` in `routers/bot_management.py` to include `image_transcription` tier | Deployment Checklist §3 | PENDING |
| 32 | Create `GET /api/internal/bots/tiers` endpoint in `routers/bot_management.py` | New Configuration Tier Checklist §4 | PENDING |
| 33 | Update `EditPage.js` — add `image_transcription` uiSchema entry with `detail` field | New Configuration Tier Checklist §5 | PENDING |
| 34 | Update `EditPage.js` — fetch tiers dynamically from API and replace hardcoded tier arrays | New Configuration Tier Checklist §4 | PENDING |
| 35 | Update `scripts/migrations/initialize_quota_and_bots.py` — add `image_transcription` to `token_menu` | Deployment Checklist §5 | PENDING |
| 36 | Create `scripts/migrations/migrate_token_menu_image_transcription.py` | Deployment Checklist §6 | PENDING |
| 37 | Create `scripts/migrations/migrate_image_transcription.py` — backfill bot configs | Deployment Checklist §1 | PENDING |
| 38 | Verify `QuotaService.load_token_menu()` remains read-only (no self-healing logic) | Deployment Checklist §7 | PENDING |
| 39 | Update `test_process_media_bot_id_signature` to use dict key lookup instead of index offsets | Test Expectations | PENDING |
| 40 | Add tests: `detail` filtered from `ChatOpenAI` kwargs, only used in transcription payload | Test Expectations | PENDING |
| 41 | Add tests: callback continuity (`create_model_provider` + `transcribe_image` share same LLM reference) | Test Expectations | PENDING |
| 42 | Add tests: transcription response normalization (string, content blocks, unsupported type) | Test Expectations | PENDING |
| 43 | Add test: `moderation_result.flagged == True` returns `ProcessingResult(unprocessable_media=True, ...)` | Test Expectations | PENDING |
| 44 | Add tests: `format_processing_result` bracket wrapping and caption append/omit logic | Test Expectations | PENDING |
| 45 | Add test: caption correctly appended regardless of success/failure outcome | Test Expectations | PENDING |
| 46 | Add test: `asyncio.TimeoutError` path returns `ProcessingResult(unprocessable_media=True)` | Test Expectations | PENDING |
| 47 | Update existing tests: `process_media()` returns raw unbracketed content strings | Test Expectations | PENDING |
| 48 | Add integration tests: `process_job` end-to-end delivers fully formatted `[{MediaType} Transcription: ...]` | Test Expectations | PENDING |
| 49 | Update existing tests: renamed content strings for `UnsupportedMediaProcessor` and `CorruptMediaProcessor` | Test Expectations | PENDING |

---

## Task Details

### Task 1: Add `unprocessable_media` field to `ProcessingResult` dataclass
**File:** `infrastructure/models.py`
**Spec:** Processing Flow
**Description:** Add `unprocessable_media: bool = False` to the `ProcessingResult` dataclass. Include a docstring comment explaining the semantic: "True means the media could not be meaningfully transcribed, signaling `process_job` to skip prefix injection for the error payload."

---

### Task 2: Create `ImageTranscriptionProviderSettings` and `ImageTranscriptionProviderConfig`
**Files:** `config_models.py`
**Spec:** Configuration, Technical Details §1
**Description:** Create `ImageTranscriptionProviderSettings` inheriting from `ChatCompletionProviderSettings`, adding `detail: Literal["low", "high", "original", "auto"] = "auto"`. Create `ImageTranscriptionProviderConfig` extending `ChatCompletionProviderConfig`, redefining `provider_config: ImageTranscriptionProviderSettings`. The `LLMConfigurations.image_transcription` field type will reference this config class.

---

### Task 3: Update `ConfigTier` to include `"image_transcription"`
**File:** `config_models.py`
**Spec:** Configuration, New Configuration Tier Checklist §1
**Description:** Change `ConfigTier = Literal["high", "low", "image_moderation"]` to `ConfigTier = Literal["high", "low", "image_moderation", "image_transcription"]`. Add a comment directly above the `ConfigTier` definition and the `LLMConfigurations` model stating: "These two locations are the ONLY places in the code where the structure/keys of the tiers are defined."

---

### Task 4: Add `image_transcription` required field to `LLMConfigurations`
**File:** `config_models.py`
**Spec:** Configuration, Deployment Checklist §4
**Description:** Add `image_transcription: ImageTranscriptionProviderConfig = Field(..., title="Image Transcription Model")` as a strictly required field to the `LLMConfigurations` model, consistent with the other tiers. The migration script (Task 37) ensures backfill before code activation.

---

### Task 5: Extend `DefaultConfigurations` with image transcription defaults
**File:** `config_models.py`
**Spec:** Configuration, Deployment Checklist §2
**Description:** Add to `DefaultConfigurations`:
- `model_provider_name_image_transcription = "openAiImageTranscription"` (matching the provider module name)
- `model_image_transcription: str = os.getenv("DEFAULT_MODEL_IMAGE_TRANSCRIPTION", "gpt-5-mini")`
- `model_image_transcription_temperature: float = float(os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE", "0.05"))`
- `model_image_transcription_reasoning_effort: str = os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT", "minimal")`

All fallback values must be explicitly specified to prevent startup crashes when env vars are not set.

---

### Task 6: Delete unused `LLMProviderSettings` and `LLMProviderConfig`
**File:** `config_models.py`
**Spec:** Deployment Checklist §10
**Description:** Remove the dead code classes `LLMProviderSettings` and `LLMProviderConfig` entirely to prevent confusion with the active `ChatCompletionProviderConfig` family.

---

### Task 7: Create `LLMProvider` abstract base class
**File:** `model_providers/base.py`
**Spec:** Technical Details §1 (Provider Architecture)
**Description:** Define a new abstract base class `LLMProvider` in `model_providers/base.py` that inherits from `BaseModelProvider` and declares the abstract `get_llm() -> BaseChatModel` method. This becomes the common parent for both `ChatCompletionProvider` and `ImageTranscriptionProvider`.

---

### Task 8: Add synchronous constraint comment to `_resolve_api_key()`
**File:** `model_providers/base.py`
**Spec:** Technical Details §1 (Provider Architecture)
**Description:** Add an explicit comment inside `BaseModelProvider._resolve_api_key()` defining that it must remain strictly synchronous and perform no external I/O or background async polling, relying strictly on the pre-resolved synchronous `self.config` properties (required because `ChatOpenAI` instantiation happens inside synchronous `__init__` constructors).

---

### Task 9: Refactor `ChatCompletionProvider` to empty type-marker
**File:** `model_providers/chat_completion.py`
**Spec:** Technical Details §1 (Provider Architecture)
**Description:** Change `ChatCompletionProvider` to inherit from `LLMProvider` instead of `BaseModelProvider`. Remove the `@abstractmethod def get_llm(self)` declaration and `abc` imports. Replace the class body with `pass` so it cleanly acts as an empty type-marker class.

---

### Task 10: Create `OpenAiMixin` with shared `_build_llm_params()`
**File:** `model_providers/openAi.py` (or new file `model_providers/openai_mixin.py`)
**Spec:** Technical Details §1 (Provider Architecture)
**Description:** Extract the shared OpenAI kwargs building logic into a centralized `OpenAiMixin` class containing only `_build_llm_params()`. The logic includes: `model_dump()` → pop `api_key_source`, `record_llm_interactions` → resolve API key → filter None-valued optional fields (`reasoning_effort`, `seed`). The mixin relies on `self.config` and inherited `_resolve_api_key()` from `BaseModelProvider`. Note: `_resolve_base_url` is NOT included (error from previous specs).

---

### Task 11: Refactor `OpenAiChatProvider` to use `OpenAiMixin` with constructor-time init
**File:** `model_providers/openAi.py`
**Spec:** Technical Details §1 (Provider Architecture)
**Description:** Modify `OpenAiChatProvider` to extend both `ChatCompletionProvider` and `OpenAiMixin`. Move `ChatOpenAI` instantiation into `__init__` (call `self._build_llm_params()`, then `self._llm = ChatOpenAI(**params)`). Make `get_llm()` trivially `return self._llm`. Remove the duplicated `_build_llm_params()` from the class (now inherited from mixin).

---

### Task 12: Move `httpx` logger config to `main.py`; remove debug `print()` statements
**Files:** `model_providers/openAi.py`, `main.py`
**Spec:** Technical Details §1 (Provider Architecture)
**Description:** Extract the `httpx` logger configuration from `OpenAiChatProvider.get_llm()` and move it to the application's startup file (`main.py`). Remove all `print()` debug statements from `OpenAiChatProvider` — they are dev-only artifacts. Note: `main.py` already has `logging.getLogger("httpx").setLevel(logging.WARNING)` at module level, so verify this is sufficient or adjust as needed.

---

### Task 13: Create abstract `ImageTranscriptionProvider`
**File:** `model_providers/image_transcription.py` (new)
**Spec:** Technical Details §1 (Provider Architecture), Transcription
**Description:** Create `ImageTranscriptionProvider` extending `LLMProvider` (from `model_providers/base.py`). Declare `async def transcribe_image(self, base64_image: str, mime_type: str, language_code: str) -> str` as an `@abstractmethod`. The class inherits abstract `get_llm()` from `LLMProvider`.

---

### Task 14: Create concrete `OpenAiImageTranscriptionProvider`
**File:** `model_providers/openAiImageTranscription.py` (new)
**Spec:** Technical Details §1 (Provider Architecture), Transcription, OpenAI Vision Parameter §2
**Description:** Create `OpenAiImageTranscriptionProvider` extending `ImageTranscriptionProvider` and `OpenAiMixin`. In `__init__`:
1. Call `params = self._build_llm_params()`
2. Pop `detail` → `self._detail = params.pop("detail", "auto")`
3. Store `self._llm = ChatOpenAI(**params)`
4. `get_llm()` returns `self._llm`

Implement `transcribe_image()`:
- Construct multimodal `HumanMessage` with text prompt (hardcoded, injecting `language_code`) + `image_url` data URI + `detail` from `self._detail`
- Invoke LLM via `await self._llm.ainvoke([message])`
- Normalize response per contract: string → as-is; content blocks → join text blocks with space; otherwise → `"Unable to transcribe image content"`

Prompt text: `"Describe the contents of this image explicitly in the following language: {language_code}, and concisely in 1-3 sentences. If there is text in the image, add the text inside image to description as well."`

---

### Task 15: Add `__module__` filter to `find_provider_class`
**File:** `utils/provider_utils.py`
**Spec:** Technical Details §1 (Provider Architecture)
**Description:** Add `obj.__module__ == module.__name__` filter to the `inspect.getmembers` loop in `find_provider_class`. This ensures only the provider class defined in the specific module file is picked, ignoring imported base classes or sibling providers. Add a documentation note explaining this is a defensive measure. Preserve the existing `not inspect.isabstract(obj)` check.

---

### Task 16: Add `resolve_bot_language()` to `services/resolver.py`
**File:** `services/resolver.py`
**Spec:** Configuration, Transcription
**Description:** Create `async def resolve_bot_language(bot_id: str) -> str` that reads `config_data.configurations.user_details.language_code` from the bot configuration document via `get_global_state().configurations_collection.find_one(...)`. The entire DB fetch block must be wrapped in `try/except Exception: return "en"`. The function must **never raise an error** under any circumstances — it always falls back to `"en"`.

---

### Task 17: Add `image_transcription` overload and branch to `resolve_model_config`
**File:** `services/resolver.py`
**Spec:** Configuration, New Configuration Tier Checklist §2
**Description:** Add an `@overload` type hint: `async def resolve_model_config(bot_id: str, config_tier: Literal["image_transcription"]) -> ImageTranscriptionProviderConfig`. Add an `elif config_tier == "image_transcription"` branch in the implementation returning `ImageTranscriptionProviderConfig.model_validate(tier_data)`. Import `ImageTranscriptionProviderConfig` explicitly.

---

### Task 18: Refactor `create_model_provider` for unified `LLMProvider` branching
**File:** `services/model_factory.py`
**Spec:** Technical Details §1 (Provider Architecture)
**Description:** Refactor `create_model_provider` to:
1. Update return type annotation to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider]`
2. Update docstring to document the return contract per provider type
3. Replace `isinstance(provider, ChatCompletionProvider)` with `isinstance(provider, LLMProvider)` for the token tracking branch
4. Within the `LLMProvider` branch: `llm = provider.get_llm()`, attach `TokenTrackingCallback`, then check: if `isinstance(provider, ChatCompletionProvider)` return `llm` (raw); otherwise return `provider` (wrapper)
5. Keep `ImageModerationProvider` branch unchanged
6. Import `LLMProvider` and `ImageTranscriptionProvider`

---

### Task 19: Implement `format_processing_result()` in `media_processors/base.py`
**File:** `media_processors/base.py`
**Spec:** Output Format
**Description:** Add a module-level pure function `format_processing_result(content: str, caption: str) -> str` that:
1. Unconditionally wraps `content` in brackets: `[<content>]`
2. If `caption` is a non-empty string, appends `\n[Caption: <caption_text>]`
3. If `caption` is `None` or `""`, returns bracket-wrapped content as-is
4. Does not mutate original arguments

---

### Task 20: Remove `caption` parameter from `BaseMediaProcessor.process_media`
**File:** `media_processors/base.py`
**Spec:** Output Format
**Description:** Update the abstract method signature from `async def process_media(self, file_path: str, mime_type: str, caption: str, bot_id: str)` to `async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult`.

---

### Task 21: Update `CorruptMediaProcessor.process_media`
**File:** `media_processors/error_processors.py`
**Spec:** Output Format
**Description:** Remove `caption` parameter from the method signature. Update the return to: `ProcessingResult(content=f"Corrupted {media_type} media could not be downloaded", failed_reason=..., unprocessable_media=True)`. Preserve the `media_type = mime_type.replace("media_corrupt_", "")` derivation. No brackets, no caption handling — `format_processing_result` in `process_job` handles formatting.

---

### Task 22: Update `UnsupportedMediaProcessor.process_media`
**File:** `media_processors/error_processors.py`
**Spec:** Output Format
**Description:** Remove `caption` parameter. Return `ProcessingResult(content=f"Unsupported media type: {mime_type}", failed_reason=..., unprocessable_media=True)`. No brackets, no caption.

---

### Task 23: Update `StubSleepProcessor.process_media`
**File:** `media_processors/stub_processors.py`
**Spec:** Output Format
**Description:** Remove `caption` parameter. Change content to `f"multimedia message with guid='{os.path.basename(file_path)}'"` — no "Transcripted" prefix, no brackets. `unprocessable_media` defaults to `False` (success path). `process_job` will automatically prepend the media-type transcription prefix.

---

### Task 24: Verify `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor` signatures
**File:** `media_processors/stub_processors.py`
**Spec:** Output Format
**Description:** These classes inherit from `StubSleepProcessor` and do not override `process_media`, so their signatures are automatically updated when the parent is changed. Verify no overrides exist. If they do, update them to remove the `caption` parameter.

---

### Task 25: Refactor `BaseMediaProcessor.process_job()`
**File:** `media_processors/base.py`
**Spec:** Output Format, Processing Flow, Transcription (error handling)
**Description:** Implement the exhaustive `process_job` refactoring per the spec's code snippet:
1. Extract `caption = job.placeholder_message.content` once at the top
2. Remove `caption` from the `self.process_media(...)` call
3. Change timeout `ProcessingResult` to `content="Processing timed out"` (no brackets), add `unprocessable_media=True`
4. Add prefix injection step: if `not result.unprocessable_media and not result.failed_reason`, prepend `{MediaType} Transcription: ` using `media_type = job.mime_type.replace("media_corrupt_", "").split("/")[0].capitalize()`
5. Add formatting step: `result.content = format_processing_result(result.content, caption)` before any persistence
6. Keep persistence, archive, and delivery steps unchanged

---

### Task 26: Refactor `BaseMediaProcessor._handle_unhandled_exception()`
**File:** `media_processors/base.py`
**Spec:** Output Format
**Description:** Update to:
1. Extract `caption = job.placeholder_message.content`
2. Set `result = ProcessingResult(content="Media processing failed", failed_reason=error, unprocessable_media=True)` — no brackets in raw content
3. Apply `result.content = format_processing_result(result.content, caption)` **before** `_persist_result_first` and `_archive_to_failed`
4. Rest of the method remains the same

---

### Task 27: Update `ImageVisionProcessor.process_media` with transcription logic
**File:** `media_processors/image_vision_processor.py`
**Spec:** Processing Flow, Transcription
**Description:**
1. Remove `caption` parameter from signature
2. Keep moderation call with `feature_name="media_processing"`
3. After moderation:
   - If `moderation_result.flagged == True`: return `ProcessingResult(content="cannot process image as it violates safety guidelines", unprocessable_media=True)` with `failed_reason=None`
   - If `moderation_result.flagged == False`:
     a. Call `language_code = await resolve_bot_language(bot_id)` (inside the non-flagged branch to avoid unnecessary DB queries)
     b. Create transcription provider via `create_model_provider(bot_id, "image_transcription", "image_transcription")`
     c. Verify `isinstance(provider, ImageTranscriptionProvider)`
     d. Call `transcript = await provider.transcribe_image(base64_image, mime_type, language_code)`
     e. Return `ProcessingResult(content=transcript)`
4. No `try/except` around `transcribe_image` — exceptions propagate to `process_job`

---

### Task 28: Add `"image/gif"` to `DEFAULT_POOL_DEFINITIONS`
**File:** `services/media_processing_service.py`
**Spec:** Processing Flow
**Description:** Update the `ImageVisionProcessor` entry in `DEFAULT_POOL_DEFINITIONS` to include `"image/gif"` alongside `"image/jpeg"`, `"image/png"`, `"image/webp"`.

---

### Task 29: Create migration script `migrate_pool_definitions_gif.py`
**File:** `scripts/migrations/migrate_pool_definitions_gif.py` (new)
**Spec:** Processing Flow
**Description:** Create a migration script that completely deletes the existing `_mediaProcessorDefinitions` document from the MongoDB `configurations` collection (`COLLECTION_GLOBAL_CONFIGURATIONS`). This forces the server to recreate pool definitions from the updated Python defaults (which now include GIF) on next boot. Must use `infrastructure/db_schema.py` constants.

---

### Task 30: Update `get_configuration_schema` — dynamic tier iteration and dual `reasoning_effort` patches
**File:** `routers/bot_management.py`
**Spec:** Configuration, New Configuration Tier Checklist §3
**Description:**
1. Change the hardcoded list `['high', 'low', 'image_moderation']` in the schema surgery loop to `for prop_name in llm_configs_defs['properties'].keys():` for dynamic tier extraction
2. Duplicate the `reasoning_effort` title patches block to also target `'ImageTranscriptionProviderSettings'` (in addition to `'ChatCompletionProviderSettings'`), ensuring correct UI rendering for both settings classes

---

### Task 31: Update `get_bot_defaults` to include `image_transcription` tier
**File:** `routers/bot_management.py`
**Spec:** Deployment Checklist §3
**Description:** Add `image_transcription=ImageTranscriptionProviderConfig(...)` to the `LLMConfigurations(...)` construction in `get_bot_defaults`, using `ImageTranscriptionProviderSettings` and `DefaultConfigurations` values for the image transcription model/temperature/reasoning_effort. Import `ImageTranscriptionProviderConfig` and `ImageTranscriptionProviderSettings`.

---

### Task 32: Create `GET /api/internal/bots/tiers` endpoint
**File:** `routers/bot_management.py`
**Spec:** New Configuration Tier Checklist §4
**Description:** Add a new lightweight endpoint `GET /api/internal/bots/tiers` that returns the available LLM configuration tiers by reading `list(LLMConfigurations.model_fields.keys())` from the Python model. This aligns with the existing `/api/internal/bots` router prefix.

---

### Task 33: Add `image_transcription` uiSchema entry in `EditPage.js`
**File:** `frontend/src/pages/EditPage.js`
**Spec:** New Configuration Tier Checklist §5
**Description:** Add a fourth entry to the `llm_configs` object in `uiSchema` for `image_transcription` with:
- `"ui:title": "Image Transcription Model"`
- `"ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate`
- `provider_config` sub-object matching the `high`/`low` tiers exactly (including `FlatProviderConfigTemplate`, `api_key_source`, `reasoning_effort`, `seed` UI titles)
- Include `detail` field inside `provider_config` with `"ui:title": "Image Detail Level"`

---

### Task 34: Fetch tiers dynamically and replace hardcoded tier arrays in `EditPage.js`
**File:** `frontend/src/pages/EditPage.js`
**Spec:** New Configuration Tier Checklist §4
**Description:**
1. Add component state for dynamic tier list (e.g., `const [availableTiers, setAvailableTiers] = useState([])`)
2. In `fetchData`, fetch from the new `/api/external/bots/tiers` (or gateway-mapped equivalent) endpoint and store in state
3. Replace the hardcoded `['high', 'low', 'image_moderation']` array at ~line 135 (`api_key_source` patching) and ~line 229 (`handleFormChange` provider config iteration) with the dynamically fetched tier list

---

### Task 35: Update `initialize_quota_and_bots.py` — add `image_transcription` to `token_menu`
**File:** `scripts/migrations/initialize_quota_and_bots.py`
**Spec:** Deployment Checklist §5
**Description:** Add `"image_transcription"` tier to the `token_menu` dictionary with pricing: `input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`. Brings total to 3 tiers (`high`, `low`, `image_transcription`). Keep the "insert-if-not-exists" logic. Add a comment noting that `image_moderation` is intentionally omitted because it has no model-token cost.

---

### Task 36: Create `migrate_token_menu_image_transcription.py`
**File:** `scripts/migrations/migrate_token_menu_image_transcription.py` (new)
**Spec:** Deployment Checklist §6
**Description:** Create a migration script that completely deletes any existing `token_menu` document and re-inserts the full correct 3-tier menu (`high`, `low`, `image_transcription`) from scratch. Uses `infrastructure/db_schema.py` constants. The hard-reset strategy is acceptable since there is no production environment.

---

### Task 37: Create `migrate_image_transcription.py` — backfill bot configs
**File:** `scripts/migrations/migrate_image_transcription.py` (new)
**Spec:** Deployment Checklist §1
**Description:** Create a migration script that iterates existing bot configs in `COLLECTION_BOT_CONFIGURATIONS` and adds `config_data.configurations.llm_configs.image_transcription` where missing. Uses the default values from `DefaultConfigurations` for `openAiImageTranscription` provider, model, temperature, reasoning_effort, and default `detail="auto"`. Must use `infrastructure/db_schema.py` constants.

---

### Task 38: Verify `QuotaService.load_token_menu()` remains read-only
**File:** `services/quota_service.py`
**Spec:** Deployment Checklist §7
**Description:** Confirm that `QuotaService.load_token_menu()` remains a read-only fetch with no self-healing insert logic. If the `token_menu` document is missing, it should log an error (as it currently does). No code changes expected — this is a verification/audit task.

---

### Task 39: Update `test_process_media_bot_id_signature` test
**File:** `tests/test_image_vision_processor.py`
**Spec:** Test Expectations
**Description:** Rewrite the assertion in `test_process_media_bot_id_signature` to use a robust dictionary key lookup (e.g., `assert "bot_id" in sig.parameters`) rather than asserting on hardcoded list index offsets like `params[4]`. Also update parameter positions since `caption` is removed from the signature (bot_id moves from index 4 to index 3).

---

### Task 40: Add tests — `detail` filtered from `ChatOpenAI` kwargs
**File:** `tests/test_image_vision_processor.py` (or new test file)
**Spec:** Test Expectations
**Description:** Add tests verifying that the `detail` parameter is removed from `ChatOpenAI(...)` constructor kwargs (via `params.pop("detail", "auto")`) and is only used when constructing the multimodal image payload inside `transcribe_image()`.

---

### Task 41: Add tests — callback continuity
**File:** `tests/test_image_vision_processor.py` (or new test file)
**Spec:** Test Expectations
**Description:** Add tests verifying that the `TokenTrackingCallback` attached in `create_model_provider` and the LLM invocation in `transcribe_image()` use the exact same `ChatOpenAI` object reference (`self._llm`). This validates the constructor-time initialization pattern.

---

### Task 42: Add tests — transcription response normalization
**File:** `tests/test_image_vision_processor.py` (or new test file)
**Spec:** Test Expectations
**Description:** Add tests covering all three normalization branches:
1. `response.content` is `str` → returned as-is
2. `response.content` is content blocks → extract text blocks, concatenate with space separator, trim
3. `response.content` is unsupported type → return `"Unable to transcribe image content"`

---

### Task 43: Add test — moderation flagged returns `unprocessable_media=True`
**File:** `tests/test_image_vision_processor.py`
**Spec:** Test Expectations
**Description:** Add test that when `moderation_result.flagged == True`, `ImageVisionProcessor.process_media` returns `ProcessingResult(unprocessable_media=True, content="cannot process image as it violates safety guidelines")` with `failed_reason=None`.

---

### Task 44: Add tests — `format_processing_result` logic
**File:** `tests/test_image_vision_processor.py` (or new test file)
**Spec:** Test Expectations
**Description:** Add tests for `format_processing_result`:
1. Content is unconditionally wrapped in brackets: `"foo"` → `"[foo]"`
2. Non-empty caption is appended: `"foo"`, `"bar"` → `"[foo]\n[Caption: bar]"`
3. Empty/None caption means no suffix: `"foo"`, `""` → `"[foo]"`; `"foo"`, `None` → `"[foo]"`

---

### Task 45: Add test — caption appended regardless of success/failure
**File:** `tests/test_image_vision_processor.py` (or new test file)
**Spec:** Test Expectations
**Description:** Add test verifying that when `job.placeholder_message.content` is populated, the caption is correctly appended to the final delivered content via `format_processing_result`, regardless of whether the processing outcome was success or failure.

---

### Task 46: Add test — `asyncio.TimeoutError` returns `unprocessable_media=True`
**File:** `tests/test_image_vision_processor.py` (or new test file)
**Spec:** Test Expectations
**Description:** Add test that the `asyncio.TimeoutError` exception path in `process_job` produces a `ProcessingResult` with `unprocessable_media=True`, `content="Processing timed out"` (before formatting), and `failed_reason` set.

---

### Task 47: Update existing tests — `process_media()` returns raw unbracketed strings
**File:** `tests/test_image_vision_processor.py`
**Spec:** Test Expectations
**Description:** Update existing tests to assert that `process_media()` return values contain raw, unbracketed content strings (e.g., `"multimedia message with guid='...'"`) — verifying removal of the legacy `[...]` wrapper from individual processors.

---

### Task 48: Add integration tests — `process_job` end-to-end formatted delivery
**File:** `tests/test_image_vision_processor.py` (or new test file)
**Spec:** Test Expectations
**Description:** Add integration tests asserting that the final string delivered to the bot queue via `update_message_by_media_id` is the fully formatted form, e.g., `"[Audio Transcription: multimedia message with guid='...']"` or `"[Image Transcription: <transcript>]"` with appropriate caption appending.

---

### Task 49: Update existing tests for renamed content strings
**File:** `tests/test_image_vision_processor.py`
**Spec:** Test Expectations
**Description:** Update any existing tests that assert old content strings:
- `UnsupportedMediaProcessor`: old `"[Unsupported {mime_type} media]"` → new `f"Unsupported media type: {mime_type}"` (unbracketed; brackets added by `format_processing_result`)
- `CorruptMediaProcessor`: old `"[Corrupted {media_type} media could not be downloaded]"` → new `f"Corrupted {media_type} media could not be downloaded"` (unbracketed)
