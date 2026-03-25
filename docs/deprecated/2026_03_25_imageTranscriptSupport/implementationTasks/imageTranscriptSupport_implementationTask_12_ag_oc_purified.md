# Implementation Tasks — Image Transcription Support (Purified)

Based on the highest quality coverage of `01_ag_opus_4_6` combined with the exceptionally cohesive phase-based structure of `08_oc_mimo_v2_pro`.

---

## Task Summary Table

| #  | Phase / Task | Spec Section(s) | Status |
|----|--------------|-----------------|--------|
| **1** | **Phase 1: Configuration Models & Resolvers** | | |
| 1.1 | Delete dead code `LLMProviderSettings` & `LLMProviderConfig` | Deployment Checklist §10 | PENDING |
| 1.2 | Create `ImageTranscriptionProviderSettings` & `ImageTranscriptionProviderConfig` | Configuration; Provider Architecture §1 | PENDING |
| 1.3 | Add `image_transcription` to `ConfigTier` Literal & `LLMConfigurations` model | Configuration; New Config Tier Checklist §4.1 | PENDING |
| 1.4 | Add `DefaultConfigurations` entries for image transcription | Deployment Checklist §2 | PENDING |
| 1.5 | Add `image_transcription` overload to `resolve_model_config` | New Config Tier Checklist §4.2 | PENDING |
| 1.6 | Add `resolve_bot_language` fallback function in `services/resolver.py` | Transcription; Configuration | PENDING |
| **2** | **Phase 2: Processing Flow Infrastructure** | | |
| 2.1 | Add `unprocessable_media` field to `ProcessingResult` | Processing Flow | PENDING |
| 2.2 | Add `"image/gif"` to `DEFAULT_POOL_DEFINITIONS` in `media_processing_service.py` | Processing Flow | PENDING |
| 2.3 | Create migration `migrate_pool_definitions_gif.py` to delete `_mediaProcessorDefinitions` | Processing Flow | PENDING |
| **3** | **Phase 3: Sibling Provider Architecture Setup** | | |
| 3.1 | Add `LLMProvider` abstract class & add strict synchronous comment to `_resolve_api_key()` | Provider Architecture §1 | PENDING |
| 3.2 | Refactor `ChatCompletionProvider` into an empty type-marker inheriting `LLMProvider` | Provider Architecture §1 | PENDING |
| 3.3 | Create `OpenAiMixin` & refactor `OpenAiChatProvider` (constructor-time init) | Provider Architecture §1 | PENDING |
| 3.4 | Move `httpx` logger configuration to startup in `main.py` | Provider Architecture §1 | PENDING |
| 3.5 | Create abstract `ImageTranscriptionProvider` in `model_providers/image_transcription.py` | Provider Architecture §1 | PENDING |
| 3.6 | Create concrete `OpenAiImageTranscriptionProvider` in `model_providers/openAiImageTranscription.py` | Provider Architecture §1; Transcription | PENDING |
| 3.7 | Add `__module__` filter to `find_provider_class` in `utils/provider_utils.py` | Provider Architecture §1 | PENDING |
| 3.8 | Refactor `create_model_provider` in `services/model_factory.py` (unified `LLMProvider` branch) | Provider Architecture §1 | PENDING |
| **4** | **Phase 4: Global Output Formatting Refactoring** | | |
| 4.1 | Create `format_processing_result` pure function in `media_processors/base.py` | Output Format | PENDING |
| 4.2 | Remove `caption` parameter from `process_media` signature (base + all 7 subclasses) | Output Format | PENDING |
| 4.3 | Refactor `BaseMediaProcessor.process_job()` per exhaustive spec snippet (prefix injection & formatting) | Output Format; Processing Flow | PENDING |
| 4.4 | Update `BaseMediaProcessor._handle_unhandled_exception` (use formatting, remove brackets) | Output Format | PENDING |
| 4.5 | Update `CorruptMediaProcessor.process_media` (new content string, `unprocessable_media=True`) | Output Format | PENDING |
| 4.6 | Update `UnsupportedMediaProcessor.process_media` (new content string, `unprocessable_media=True`) | Output Format | PENDING |
| 4.7 | Update `StubSleepProcessor.process_media` (new content string, no brackets, `unprocessable_media=False`) | Output Format | PENDING |
| **5** | **Phase 5: Image Transcription Processing Pipeline** | | |
| 5.1 | Implement `ImageVisionProcessor.process_media` (moderation flow, flagged handling, transcription call) | Processing Flow; Transcription | PENDING |
| 5.2 | Update `asyncio.TimeoutError` paths to return `unprocessable_media=True` (no brackets) | Test Expectations | PENDING |
| **6** | **Phase 6: Frontend Binding & Dynamic App Schema** | | |
| 6.1 | Make schema surgery loop dynamic & patch `reasoning_effort` in `get_configuration_schema` | Configuration; New Config Tier Checklist §4.3 | PENDING |
| 6.2 | Create new `GET /api/internal/bots/tiers` endpoint in `bot_management.py` | New Config Tier Checklist §4.4 | PENDING |
| 6.3 | Fetch tiers dynamically & replace hardcoded tier arrays in `frontend/EditPage.js` | New Config Tier Checklist §4.4 | PENDING |
| 6.4 | Add `image_transcription` uiSchema entry statically with `detail` object in `frontend/EditPage.js` | New Config Tier Checklist §4.5 | PENDING |
| **7** | **Phase 7: System Deployments & DB Migrations** | | |
| 7.1 | Update `get_bot_defaults` in `routers/bot_management.py` to inject `image_transcription` tier | Deployment Checklist §3 | PENDING |
| 7.2 | Update `initialize_quota_and_bots.py` — add `image_transcription` tier token prices | Deployment Checklist §5 | PENDING |
| 7.3 | Extend `global_configurations.token_menu` with `image_transcription` (handled by migrations) | Configuration | PENDING |
| 7.4 | Create `scripts/migrations/migrate_image_transcription.py` (backfill bot configs safely) | Deployment Checklist §1 | PENDING |
| 7.5 | Create `scripts/migrations/migrate_token_menu_image_transcription.py` (hard-reset token menu) | Deployment Checklist §6 | PENDING |
| **8** | **Phase 8: Validation & Integration Tests Base** | | |
| 8.1 | Add tests: `detail` filtered from `ChatOpenAI` kwargs, used only in transcription payload | Test Expectations | PENDING |
| 8.2 | Add tests: callback continuity (same LLM object in factory & transcription) | Test Expectations | PENDING |
| 8.3 | Add tests: transcription response normalization (string, content blocks, unsupported) | Test Expectations | PENDING |
| 8.4 | Add test: `moderation_result.flagged == True` returns `ProcessingResult(unprocessable_media=True, ...)` | Test Expectations | PENDING |
| 8.5 | Add test: `format_processing_result` bracket wrapping & appended caption logic unconditionally | Test Expectations | PENDING |
| 8.6 | Add test: `asyncio.TimeoutError` returns `ProcessingResult(unprocessable_media=True)` with failed_reason | Test Expectations | PENDING |
| 8.7 | Update existing unit tests: `process_media` returns raw unbracketed content | Test Expectations | PENDING |
| 8.8 | Update existing tests: renamed content strings for `UnsupportedMediaProcessor` & `CorruptMediaProcessor` | Test Expectations | PENDING |
| 8.9 | Add integration tests: `process_job` end-to-end final formatted string delivered to queue | Test Expectations | PENDING |
| 8.10 | Update `test_process_media_bot_id_signature` to use robust dict key lookup `assert "bot_id" in sig.parameters` | Test Expectations | PENDING |

---

## Detailed Task Descriptions

### Phase 1: Configuration Models & Resolvers

**1.1 Delete dead code `LLMProviderSettings` & `LLMProviderConfig`**
Remove these unused classes entirely from `config_models.py` to prevent any confusion with the active `ChatCompletion` family.

**1.2 Create `ImageTranscriptionProviderSettings` & `ImageTranscriptionProviderConfig`**
In `config_models.py`, create `ImageTranscriptionProviderSettings(ChatCompletionProviderSettings)` adding `detail: Literal["low", "high", "original", "auto"] = "auto"`. Create `ImageTranscriptionProviderConfig(ChatCompletionProviderConfig)` redefining `provider_config: ImageTranscriptionProviderSettings`.

**1.3 Add `image_transcription` to `ConfigTier` Literal & `LLMConfigurations` model**
Update `ConfigTier = Literal["high", "low", "image_moderation", "image_transcription"]`. Add `image_transcription: ImageTranscriptionProviderConfig = Field(...)` natively to `LLMConfigurations`. Add the comment explicitly stating *"These two locations are the ONLY places in the code where the structure/keys of the tiers are defined."* above both definitions.

**1.4 Add `DefaultConfigurations` entries for image transcription**
Add to `DefaultConfigurations` inside `config_models.py`:
- `model_provider_name_image_transcription = "openAiImageTranscription"`
- `model_image_transcription = os.getenv("DEFAULT_MODEL_IMAGE_TRANSCRIPTION", "gpt-5-mini")`
- `model_image_transcription_temperature = float(os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE", "0.05"))`
- `model_image_transcription_reasoning_effort = os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT", "minimal")` (Fallbacks are strictly required to prevent crashes).

**1.5 Add `image_transcription` overload to `resolve_model_config`**
In `services/resolver.py`, add `@overload` for `Literal["image_transcription"] -> ImageTranscriptionProviderConfig`. Insert `elif config_tier == "image_transcription": return ImageTranscriptionProviderConfig.model_validate(tier_data)`. Import the config class.

**1.6 Add `resolve_bot_language` fallback function**
Create `resolve_bot_language(bot_id: str) -> str` in `services/resolver.py`. Reads `config_data.configurations.user_details.language_code` from the bot configuration document. Wrap the entire DB fetch explicitly in a bare `try/except Exception: return "en"` block so it **never** raises an error.

### Phase 2: Processing Flow Infrastructure

**2.1 Add `unprocessable_media` field to `ProcessingResult`**
In `infrastructure/models.py`, add `unprocessable_media: bool = False` to the dataclass. Include docstring: *"True means the media could not be meaningfully transcribed, signaling `process_job` to skip prefix injection for the error payload."*

**2.2 Add `"image/gif"` to `DEFAULT_POOL_DEFINITIONS`**
Update `ImageVisionProcessor` supported mime types inside `services/media_processing_service.py` to include `"image/gif"` alongside JPEG, PNG, WEBP.

**2.3 Create `migrate_pool_definitions_gif.py`**
Create a python file in `scripts/migrations/` that completely **deletes** the existing `_mediaProcessorDefinitions` document from `COLLECTION_GLOBAL_CONFIGURATIONS`, forcing a pristine recreation of the DB pools payload on the next service boot.

### Phase 3: Sibling Provider Architecture Setup

**3.1 Add `LLMProvider` abstract class**
In `model_providers/base.py`, define `LLMProvider(BaseModelProvider, ABC)` with `@abstractmethod def get_llm(self) -> BaseChatModel`. Add an explicit comment inside `_resolve_api_key()` stating it must remain inherently synchronous with no external I/O.

**3.2 Refactor `ChatCompletionProvider` into empty type-marker**
In `model_providers/chat_completion.py`, change inheritance to `LLMProvider`. Remove the abstract `get_llm` declaration, remove `abc` imports, and replace the class body exclusively with `pass`.

**3.3 Create `OpenAiMixin` & refactor `OpenAiChatProvider`**
Extract `_build_llm_params()` into a centralized `OpenAiMixin` class to share OpenAI kwargs pop/resolving logic. Refactor `OpenAiChatProvider` to use constructor-time `ChatOpenAI` initialization (`self._llm` in `__init__`, `get_llm()` simply returns `self._llm`). Remove the arbitrary `print()` debugger statements.

**3.4 Move `httpx` logger configuration**
Extract the `httpx` logger instantiation from the provider `get_llm()` logic and permanently secure it at the top level inside the application's startup script (`main.py`), preventing process state side-effects.

**3.5 Create abstract `ImageTranscriptionProvider`**
Create `model_providers/image_transcription.py` generating `ImageTranscriptionProvider(LLMProvider, ABC)` exposing `@abstractmethod async def transcribe_image(self, base64_image: str, mime_type: str, language_code: str) -> str`.

**3.6 Create concrete `OpenAiImageTranscriptionProvider`**
Create `model_providers/openAiImageTranscription.py`: Subclass `(ImageTranscriptionProvider, OpenAiMixin)`. Pop `detail` from `params = self._build_llm_params()`, initialize LLM inside constructor. Implement `transcribe_image` constructing a multimodal `HumanMessage` incorporating the `language_code` request, invoking `ainvoke`, and normalizing strings explicitly against content block typings. Apply `"Unable to transcribe image content"` fallback wrappers unconditionally.

**3.7 Add `__module__` filter to `find_provider_class`**
In `utils/provider_utils.py`, add `obj.__module__ == module.__name__` into the loop protecting reflection imports against sibling cross-contamination. Retain the `not inspect.isabstract` check.

**3.8 Refactor `create_model_provider`**
Update return typing signature to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider]`. Implement a unified `isinstance(provider, LLMProvider)` token-tracking branch applying the callback securely. Extract explicit return targets (raw `llm` for Chat completion versus wrappers otherwise).

### Phase 4: Global Output Formatting Refactoring

**4.1 Create `format_processing_result` pure function**
Implement strict module-level pure function unconditionally wrapping values into bracket blocks `[<content>]`. Read the string `caption: str` parameter independently executing suffix attachments exclusively whenever populated (`\n[Caption: <caption_text>]`).

**4.2 Remove `caption` from `process_media` signatures**
Remove the caption dependency parameter entirely from `BaseMediaProcessor.process_media` abstract declarations and apply identically against the 7 derived subclasses (`ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`).

**4.3 Refactor `BaseMediaProcessor.process_job()`**
Replace existing pipeline implementations thoroughly utilizing the precise snippet supplied within the spec document: Evaluate timeout structures locally, assert conditional `Prefix Injection`, unconditionally apply `format_processing_result(result.content, caption)` **before** persistence pipelines, preserving _failed archive operations directly.

**4.4 Update `_handle_unhandled_exception`**
Instantiate string states accurately replacing `[Media processing failed]` with unbracketed `"Media processing failed"`. Bind `unprocessable_media=True`. Apply `format_processing_result` first matching exactly the pipeline behaviors observed inside `process_job`.

**4.5 Update `CorruptMediaProcessor.process_media`**
Yield unbracketed payloads: `ProcessingResult(content=f"Corrupted {media_type} media could not be downloaded", failed_reason=..., unprocessable_media=True)`. Maintain string substitution extraction bindings securely (`"media_corrupt_"` stripped).

**4.6 Update `UnsupportedMediaProcessor.process_media`**
Yield unbracketed payloads: `ProcessingResult(content=f"Unsupported media type: {mime_type}", failed_reason=..., unprocessable_media=True)`.

**4.7 Update `StubSleepProcessor.process_media`**
Purge redundant prefix structures and legacy brackets yielding strict formatted values natively `ProcessingResult(content=f"multimedia message with guid='{...}'")` retaining `unprocessable_media=False`.

### Phase 5: Image Transcription Processing Pipeline

**5.1 Implement `ImageVisionProcessor.process_media`**
Develop explicit integrations natively handling moderation execution:
- Fetch via base64 thread loaders.
- Execute `"image_moderation"` evaluation requests.
- Upon `moderation_result.flagged == True`: return `"cannot process image as it violates safety guidelines"` with `unprocessable_media=True` intentionally passing `failed_reason=None` enabling failure log bypasses.
- Upon cleanly unflagged assets: perform database call `resolve_bot_language`, execute `transcribe_image`, returning native unhandled `transcript` strings seamlessly. No try/except bounds natively spanning the provider abstraction layer.

**5.2 Update `asyncio.TimeoutError` paths**
This was handled partially in `process_job` refactor, but specifically assert that standard timeouts natively inject decoupled `unprocessable_media=True` structures suppressing erroneous downstream bracket injections.

### Phase 6: Frontend Binding & Dynamic App Schema

**6.1 Make schema surgery dynamic**
Target `get_configuration_schema` replacing hardcoded `['high', 'low', 'image_moderation']` bounds iterating exclusively against `llm_configs_defs['properties'].keys()`. Additionally inject title mappings resolving `reasoning_effort` labels successfully for `'ImageTranscriptionProviderSettings'`.

**6.2 Create `GET /api/internal/bots/tiers`**
Develop a simple static API query dumping lists bound independently against `LLMConfigurations.model_fields.keys()`.

**6.3 Update `EditPage.js` dynamic fetch arrays**
Trigger programmatic queries polling the new endpoint directly mapped across `fetchData`, removing hardcoded arrays (around line 135 and 229) overriding dependencies with state-driven mapping iterations.

**6.4 Add `image_transcription` uiSchema statics**
Initialize the frontend template natively: bind the fourth definition explicitly carrying `"ui:title": "Image Transcription Model"`. Ensure the exact properties of `provider_config` match siblings exactly (`api_key_source`, `reasoning_effort`, `seed`), while appending the unique `detail` entry.

### Phase 7: System Deployments & DB Migrations

**7.1 Update `get_bot_defaults`**
Reassign application entry payloads ensuring configurations bind securely extending `image_transcription=ImageTranscriptionProviderConfig(...)` passing initialized `DefaultConfigurations`.

**7.2 Update `initialize_quota_and_bots.py`**
Modify setup templates securing token menu values (`input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`) reflecting 3 distinct evaluation tiers explicitly. Note that `image_moderation` must remain absent.

**7.3 Extend `global_configurations.token_menu` (Verify)**
This serves as a manual post-deployment checkpoint ensuring database migration updates apply effectively over environments natively mapping newly inserted cost arrays securely.

**7.4 Create `migrate_image_transcription.py`**
Publish `infrastructure/db_schema.py` dependent iterations targeting `COLLECTION_BOT_CONFIGURATIONS`, executing document updates backfilling the necessary image_transcription payloads where absent matching active schema rules.

**7.5 Create `migrate_token_menu_image_transcription.py`**
Institute destructive hard-reset directives safely wiping `token_menu` objects and replacing definitions mapping correct arrays uniformly over existing global configurations without self-healing `QuotaService` modifications.

### Phase 8: Validation & Integration Tests Base

**8.1 Detail kwargs removal checks**
Produce test assets instantiating explicit parameters confirming omission layers strip dependencies exclusively from OpenAI constructor calls securely injecting assignments strictly over execution blocks natively (`transcribe_image`).

**8.2 Callback continuity tracing**
Assert tracking mechanisms mapping factory creation payloads explicitly match final LLM instance tracking IDs verifying continuity across object injections securely.

**8.3 Transcription normalization assertions**
Evaluate string returns, complex block combinations tracking deterministic concatenations, and undefined parameter assertions resolving safely wrapping unhandled values.

**8.4 Moderation flagged handlers**
Mock specific safety guideline blocking flags tracing structural responses applying valid `unprocessable_media=True` behaviors correctly.

**8.5 `format_processing_result` unittests**
Target pure functional models confirming empty strings and missing captions process correctly omitting wrappers versus standard applications correctly mapping suffix elements.

**8.6 `asyncio.TimeoutError` evaluations**
Test mock exceptions firing inside processing loops asserting valid exception extraction handling mapping exact string structures safely.

**8.7 Unit payload unbracketed testing**
Validate underlying outputs natively strip legacy structures (`[...]`) ensuring output values function natively prior to the integrated formatting injections.

**8.8 Renamed error payloads**
Scan deprecated assertions matching `Corrupted` or `Unsupported` variables explicitly substituting test configurations executing cleanly.

**8.9 Integration string validation**
Assert pipeline handlers `update_message_by_media_id` natively parse cleanly injected schemas applying deterministic layouts matching `"[Audio Transcription: format...]"` flawlessly.

**8.10 Dictionary key lookups**
Ensure structural introspection checks referencing `bot_id` implement independent parameter evaluations mimicking secure `assert "bot_id" in sig.parameters` overrides securely modifying `test_image_vision_processor.py`.
