# Implementation Tasks — Image Transcription Support
**Author:** ag_sonnet_4_6  
**Spec:** `docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`

---

## Task Summary Table

| #  | Task | Spec Section(s) | Status |
|----|------|-----------------|--------|
| 1  | Add `unprocessable_media` field to `ProcessingResult` dataclass | Processing Flow | PENDING |
| 2  | Delete dead code `LLMProviderSettings` & `LLMProviderConfig` from `config_models.py` | Deployment Checklist §10 | PENDING |
| 3  | Create `ImageTranscriptionProviderSettings` in `config_models.py` | Configuration; Provider Architecture §1 | PENDING |
| 4  | Create `ImageTranscriptionProviderConfig` in `config_models.py` | Configuration; Provider Architecture §1 | PENDING |
| 5  | Update `ConfigTier` Literal to include `"image_transcription"` | Configuration; New Config Tier Checklist §4.1 | PENDING |
| 6  | Add `image_transcription` required field to `LLMConfigurations` + add tier-definition comment | Configuration; New Config Tier Checklist §4.1 | PENDING |
| 7  | Extend `DefaultConfigurations` with image-transcription entries | Deployment Checklist §2 | PENDING |
| 8  | Define `LLMProvider` abstract class in `model_providers/base.py` | Provider Architecture §1 | PENDING |
| 9  | Add synchronous-only comment to `BaseModelProvider._resolve_api_key()` | Provider Architecture §1 | PENDING |
| 10 | Refactor `ChatCompletionProvider` to inherit from `LLMProvider`, make it an empty type-marker | Provider Architecture §1 | PENDING |
| 11 | Define `OpenAiMixin` with `_build_llm_params()` | Provider Architecture §1 | PENDING |
| 12 | Refactor `OpenAiChatProvider` to use `OpenAiMixin`, constructor-time `ChatOpenAI` init, remove `print()` debug statements | Provider Architecture §1 | PENDING |
| 13 | Move `httpx` logger configuration from `OpenAiChatProvider` to `main.py` | Provider Architecture §1 | PENDING |
| 14 | Create abstract `ImageTranscriptionProvider` in `model_providers/image_transcription.py` | Provider Architecture §1 | PENDING |
| 15 | Create concrete `OpenAiImageTranscriptionProvider` in `model_providers/openAiImageTranscription.py` | Provider Architecture §1; Transcription; OpenAI Vision Parameter §2 | PENDING |
| 16 | Add `__module__` filter to `find_provider_class` in `utils/provider_utils.py` | Provider Architecture §1 | PENDING |
| 17 | Refactor `create_model_provider` in `services/model_factory.py` (unified `LLMProvider` branch, updated return type & docstring) | Provider Architecture §1 | PENDING |
| 18 | Add `resolve_bot_language` function to `services/resolver.py` | Configuration; Transcription | PENDING |
| 19 | Add `image_transcription` overload + `elif` branch to `resolve_model_config` in `services/resolver.py` | New Config Tier Checklist §4.2 | PENDING |
| 20 | Add `image/gif` to `ImageVisionProcessor` mime types in `DEFAULT_POOL_DEFINITIONS` | Processing Flow | PENDING |
| 21 | Create `format_processing_result` module-level pure function in `media_processors/base.py` | Output Format | PENDING |
| 22 | Remove `caption` parameter from `process_media` in `BaseMediaProcessor` abstract method (+ all 7 subclass signatures) | Output Format | PENDING |
| 23 | Refactor `BaseMediaProcessor.process_job()` per full spec snippet (caption extraction, prefix injection step, format step, `TimeoutError` with `unprocessable_media=True`) | Output Format; Processing Flow | PENDING |
| 24 | Update `BaseMediaProcessor._handle_unhandled_exception` (`unprocessable_media=True`, remove brackets, call `format_processing_result` first) | Output Format | PENDING |
| 25 | Update `CorruptMediaProcessor.process_media` (new content string, `unprocessable_media=True`, no caption, no brackets) | Output Format | PENDING |
| 26 | Update `UnsupportedMediaProcessor.process_media` (new content string, `unprocessable_media=True`, no caption, no brackets) | Output Format | PENDING |
| 27 | Update `StubSleepProcessor.process_media` (new content string without "Transcripted" prefix or brackets, `unprocessable_media` defaults `False`) | Output Format | PENDING |
| 28 | Implement full `ImageVisionProcessor.process_media` (moderation → flagged path → transcription path) | Processing Flow; Transcription | PENDING |
| 29 | Update `get_bot_defaults` in `routers/bot_management.py` to include `image_transcription` tier | Deployment Checklist §3 | PENDING |
| 30 | Make schema surgery loop dynamic + add `ImageTranscriptionProviderSettings` `reasoning_effort` patch in `get_configuration_schema` | Configuration; New Config Tier Checklist §4.3 | PENDING |
| 31 | Create `GET /api/internal/bots/tiers` endpoint in `routers/bot_management.py` | New Config Tier Checklist §4.4 | PENDING |
| 32 | Update `frontend/src/pages/EditPage.js` — statically add `image_transcription` uiSchema entry (with `detail` field) | New Config Tier Checklist §4.5 | PENDING |
| 33 | Update `frontend/src/pages/EditPage.js` — fetch tiers dynamically, replace all hardcoded tier arrays | New Config Tier Checklist §4.4 | PENDING |
| 34 | Update `scripts/migrations/initialize_quota_and_bots.py` — add `image_transcription` tier to `token_menu` (3-tier total, `image_moderation` intentionally omitted) | Deployment Checklist §5 | PENDING |
| 35 | Create `scripts/migrations/migrate_image_transcription.py` (backfill `image_transcription` tier into all existing bot configs) | Deployment Checklist §1; Migration Contract §8 | PENDING |
| 36 | Create `scripts/migrations/migrate_token_menu_image_transcription.py` (hard-reset `token_menu` in MongoDB) | Deployment Checklist §6; Migration Contract §8 | PENDING |
| 37 | Create `scripts/migrations/migrate_pool_definitions_gif.py` (delete `_mediaProcessorDefinitions` to force GIF pool recreation on next boot) | Processing Flow; Migration Contract §8 | PENDING |
| 38 | Add tests: `detail` popped from `ChatOpenAI` kwargs, used only in transcription payload | Test Expectations | PENDING |
| 39 | Add tests: callback continuity — same `self._llm` object used in factory and in `transcribe_image` | Test Expectations | PENDING |
| 40 | Add tests: transcription response normalization (string, content blocks, unsupported type branches) | Test Expectations | PENDING |
| 41 | Add test: `moderation_result.flagged == True` returns correct `ProcessingResult(unprocessable_media=True, ...)` | Test Expectations | PENDING |
| 42 | Add test: `format_processing_result` — unconditional bracket wrapping, caption appended/omitted correctly | Test Expectations | PENDING |
| 43 | Add test: caption correctly appended to final content regardless of success or failure path | Test Expectations | PENDING |
| 44 | Add test: `asyncio.TimeoutError` path returns `ProcessingResult(unprocessable_media=True)` | Test Expectations | PENDING |
| 45 | Update existing unit tests: `process_media()` returns raw unbracketed content strings | Test Expectations | PENDING |
| 46 | Add integration tests: `process_job` end-to-end final string delivered to queue is `"[{MediaType} Transcription: {content}]"` | Test Expectations | PENDING |
| 47 | Update existing tests: renamed content strings for `UnsupportedMediaProcessor` and `CorruptMediaProcessor` | Test Expectations | PENDING |
| 48 | Update `test_process_media_bot_id_signature` to use dictionary key lookup instead of hardcoded index offsets | Test Expectations | PENDING |

---

## Detailed Task Descriptions

### Task 1 — Add `unprocessable_media` to `ProcessingResult`
**Spec:** Processing Flow — *"Update `infrastructure/models.py` by adding `unprocessable_media: bool = False`"*

In `infrastructure/models.py`, add `unprocessable_media: bool = False` to the `ProcessingResult` dataclass. The current dataclass only has `content: str` and `failed_reason: Optional[str]`. Add the new field with a docstring comment explaining: *"True means the media could not be meaningfully transcribed, signaling `process_job` to skip prefix injection for the error payload."*

**File:** `infrastructure/models.py`

---

### Task 2 — Delete dead code `LLMProviderSettings` & `LLMProviderConfig`
**Spec:** Deployment Checklist §10 — *"Delete the unused dead code `LLMProviderSettings` and `LLMProviderConfig` entirely from `config_models.py`"*

Remove both the `LLMProviderSettings` class (currently lines 63–92) and `LLMProviderConfig` class (currently lines 94–96) from `config_models.py`. These are unused duplicates of the `ChatCompletion*` family that exist purely as dead code and create confusion.

**File:** `config_models.py`

---

### Task 3 — Create `ImageTranscriptionProviderSettings` in `config_models.py`
**Spec:** Configuration — *"Create a new `ImageTranscriptionProviderSettings` class inheriting from `ChatCompletionProviderSettings`, adding the `detail: Literal[\"low\", \"high\", \"original\", \"auto\"] = \"auto\"` field."*

Add `ImageTranscriptionProviderSettings(ChatCompletionProviderSettings)` class to `config_models.py` with the single additional field:
```python
detail: Literal["low", "high", "original", "auto"] = "auto"
```

**File:** `config_models.py`

---

### Task 4 — Create `ImageTranscriptionProviderConfig` in `config_models.py`
**Spec:** Configuration — *"Modify `ImageTranscriptionProviderConfig` to extend `ChatCompletionProviderConfig` and redefine `provider_config: ImageTranscriptionProviderSettings`."*

Add `ImageTranscriptionProviderConfig(ChatCompletionProviderConfig)` class that redefines `provider_config: ImageTranscriptionProviderSettings`. This correctly narrows the type.

**File:** `config_models.py`

---

### Task 5 — Update `ConfigTier` Literal
**Spec:** Configuration — *"`ConfigTier` is updated to include `\"image_transcription\""`*; New Config Tier Checklist §4.1

Update:
```python
ConfigTier = Literal["high", "low", "image_moderation", "image_transcription"]
```
Add a comment directly above this line stating: *"These two locations are the ONLY places in the code where the structure/keys of the tiers are defined."* (the companion comment location being `LLMConfigurations` — see Task 6).

**File:** `config_models.py`

---

### Task 6 — Add `image_transcription` field to `LLMConfigurations` + comment
**Spec:** Configuration — *"The `LLMConfigurations.image_transcription` field type is `ImageTranscriptionProviderConfig`"*; Deployment Checklist §4 — *"Define `LLMConfigurations.image_transcription` as a strictly required field using `Field(...)`"*; New Config Tier Checklist §4.1

Add `image_transcription: ImageTranscriptionProviderConfig = Field(...)` as a **required** field to `LLMConfigurations`. Add the corresponding comment above the `LLMConfigurations` class (matching the comment added above `ConfigTier` in Task 5): *"These two locations are the ONLY places in the code where the structure/keys of the tiers are defined."*

**File:** `config_models.py`

---

### Task 7 — Extend `DefaultConfigurations` with image-transcription entries
**Spec:** Deployment Checklist §2 — *"Extend `DefaultConfigurations` in `config_models.py` with `model_provider_name_image_transcription`"*

Add the following class-level attributes to `DefaultConfigurations`:
```python
model_provider_name_image_transcription: str = "openAiImageTranscription"
model_image_transcription: str = os.getenv("DEFAULT_MODEL_IMAGE_TRANSCRIPTION", "gpt-5-mini")
model_image_transcription_temperature: float = float(os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE", "0.05"))
model_image_transcription_reasoning_effort: str = os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT", "minimal")
```
The explicit fallback values `"0.05"` and `"minimal"` match existing `low` tier defaults and are required to prevent startup crashes when env vars are absent.

**File:** `config_models.py`

---

### Task 8 — Define `LLMProvider` abstract class in `model_providers/base.py`
**Spec:** Provider Architecture §1 — *"Define a new abstract base class `LLMProvider` in `model_providers/base.py` that inherits from `BaseModelProvider` and declares the abstract `get_llm() -> BaseChatModel` method."*

In `model_providers/base.py`, add:
```python
class LLMProvider(BaseModelProvider, ABC):
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        ...
```
Import `BaseChatModel` from `langchain_core.language_models.chat_models` and `abstractmethod` from `abc`.

**File:** `model_providers/base.py`

---

### Task 9 — Add synchronous-only comment to `BaseModelProvider._resolve_api_key()`
**Spec:** Provider Architecture §1 — *"Add an explicit comment inside `BaseModelProvider._resolve_api_key()` defining that it must remain strictly synchronous and perform no external I/O or background async polling"*

Add a comment inside the `_resolve_api_key` method body explaining this constraint (required because `ChatOpenAI` instantiation happens inside synchronous `__init__` constructors).

**File:** `model_providers/base.py`

---

### Task 10 — Refactor `ChatCompletionProvider` to inherit from `LLMProvider`, become empty type-marker
**Spec:** Provider Architecture §1 — *"Modify `ChatCompletionProvider` to inherit from `LLMProvider` instead of `BaseModelProvider` and become an empty type-marker class. Explicitly remove the `@abstractmethod def get_llm(self)` declaration and `abc` imports"*

In `model_providers/chat_completion.py`:
- Change inheritance from `BaseModelProvider` to `LLMProvider`.
- Remove the `@abstractmethod def get_llm` declaration.
- Remove `from abc import abstractmethod` import.
- Replace the class body with `pass`.

**File:** `model_providers/chat_completion.py`

---

### Task 11 — Define `OpenAiMixin` with `_build_llm_params()`
**Spec:** Provider Architecture §1 — *"Define a centralized `OpenAiMixin` containing only `_build_llm_params()` — the shared OpenAI kwargs building logic."*

Create `OpenAiMixin` (can live in `model_providers/openAi.py` or a new `model_providers/openai_mixin.py`). The mixin must:
- Call `self.config.provider_config.model_dump()` to get initial params.
- Pop custom fields not accepted by `ChatOpenAI`: `api_key_source`, `record_llm_interactions`.
- Resolve API key via `self._resolve_api_key()`.
- Filter `None`-valued optional fields (`reasoning_effort`, `seed`).
- Return the final dict.

The mixin relies on `self.config` and inherited `_resolve_api_key()` from `BaseModelProvider`. It is designed strictly to be mixed into subclasses of `BaseModelProvider`.

**File:** `model_providers/openAi.py` (or new `model_providers/openai_mixin.py`)

---

### Task 12 — Refactor `OpenAiChatProvider` to use `OpenAiMixin`, constructor-time init, remove `print()` statements
**Spec:** Provider Architecture §1 — *"Both concrete classes call `self._build_llm_params()` in their `__init__` to create and store the `ChatOpenAI` instance."*

Refactor `OpenAiChatProvider`:
- Inherit from both `ChatCompletionProvider` and `OpenAiMixin`.
- In `__init__`: call `params = self._build_llm_params()`, create `self._llm = ChatOpenAI(**params)`.
- `get_llm()` simply returns `self._llm`.
- Remove all `print()` debug statements.
- Remove the `httpx` logger configuration (moved to `main.py` in Task 13).

**File:** `model_providers/openAi.py`

---

### Task 13 — Move `httpx` logger configuration to `main.py`
**Spec:** Provider Architecture §1 — *"Extract the `httpx` logger configuration from `OpenAiChatProvider.get_llm()` and move it entirely out of the model providers and into the application's startup file (e.g., `main.py`)"*

Move the following block to the application startup (`main.py`):
```python
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.INFO)
if not httpx_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('DEBUG:httpx: %(message)s'))
    httpx_logger.addHandler(handler)
```
This removes process-state side-effects from a parameter-builder method.

**File:** `main.py`

---

### Task 14 — Create abstract `ImageTranscriptionProvider`
**Spec:** Provider Architecture §1 — *"`ImageTranscriptionProvider` (in `model_providers/image_transcription.py`) extends `LLMProvider` and declares `async def transcribe_image(base64_image: str, mime_type: str, language_code: str) -> str` as an abstract method."*

Create `model_providers/image_transcription.py` with:
```python
from abc import ABC, abstractmethod
from .base import LLMProvider

class ImageTranscriptionProvider(LLMProvider, ABC):
    # Inherits abstract get_llm() -> BaseChatModel from LLMProvider
    @abstractmethod
    async def transcribe_image(self, base64_image: str, mime_type: str, language_code: str) -> str:
        ...
```

**File:** `model_providers/image_transcription.py` *(new)*

---

### Task 15 — Create concrete `OpenAiImageTranscriptionProvider`
**Spec:** Provider Architecture §1; Transcription; OpenAI Vision Parameter §2

Create `model_providers/openAiImageTranscription.py` with `OpenAiImageTranscriptionProvider(ImageTranscriptionProvider, OpenAiMixin)`:

- **`__init__`**: Call `params = self._build_llm_params()`, pop `detail` → `self._detail = params.pop("detail", "auto")`, create `self._llm = ChatOpenAI(**params)`.
- **`get_llm()`**: Return `self._llm`.
- **`transcribe_image`**: Construct a `HumanMessage` with:
  - Text part: `f"Describe the contents of this image explicitly in the following language: {language_code}, and concisely in 1-3 sentences. If there is text in the image, add the text inside image to description as well."`
  - Image part: data URI `f"data:{mime_type};base64,{base64_image}"` with `detail=self._detail`.
  - Invoke via `response = await self._llm.ainvoke([message])`.
  - Apply normalization contract:
    - `str` content → return as-is.
    - Content blocks → extract text blocks in order, concatenate with single space, strip whitespace.
    - Anything else → return `"Unable to transcribe image content"`.

**File:** `model_providers/openAiImageTranscription.py` *(new)*

---

### Task 16 — Add `__module__` filter to `find_provider_class`
**Spec:** Provider Architecture §1 — *"`find_provider_class` in `utils/provider_utils.py` must include an `obj.__module__ == module.__name__` filter"*

In `utils/provider_utils.py`, update the `inspect.getmembers` loop condition to also check `obj.__module__ == module.__name__`. Add a documentation note explaining this is a defensive measure against edge-case concrete sibling imports. Keep the existing `not inspect.isabstract(obj)` check.

**File:** `utils/provider_utils.py`

---

### Task 17 — Refactor `create_model_provider` in `services/model_factory.py`
**Spec:** Provider Architecture §1 — *"Refactor `create_model_provider` to use a unified `isinstance(provider, LLMProvider)` branch for token tracking."*

Changes:
- Update return type annotation to `Union[BaseChatModel, ImageModerationProvider, ImageTranscriptionProvider]`.
- Import `LLMProvider` and `ImageTranscriptionProvider`.
- Replace the `isinstance(provider, ChatCompletionProvider)` branch with a unified `isinstance(provider, LLMProvider)` block:
  - Get `llm = provider.get_llm()`.
  - Attach `TokenTrackingCallback` to `llm`.
  - If `isinstance(provider, ChatCompletionProvider)` → return `llm` (raw).
  - Else (i.e., `ImageTranscriptionProvider`) → return `provider` (wrapper, so the callback-attached `self._llm` is carried through).
- `ImageModerationProvider` branch stays as-is (no token tracking).
- Update docstring to document the return contract for each provider type.

**File:** `services/model_factory.py`

---

### Task 18 — Add `resolve_bot_language` to `services/resolver.py`
**Spec:** Configuration — *"Create a new resolving function `resolve_bot_language(bot_id: str) -> str`"*; Transcription — *"must **never raise an error** under any circumstances"*

Add:
```python
async def resolve_bot_language(bot_id: str) -> str:
    try:
        state = get_global_state()
        config_doc = await state.configurations_collection.find_one(
            {"config_data.bot_id": bot_id},
            {"config_data.configurations.user_details.language_code": 1}
        )
        return (
            config_doc
            .get("config_data", {})
            .get("configurations", {})
            .get("user_details", {})
            .get("language_code", "en")
        ) or "en"
    except Exception:
        return "en"
```
The entire DB fetch block is wrapped in a bare `try/except Exception: return "en"`. This function must never raise under any circumstances, unlike `resolve_model_config`.

**File:** `services/resolver.py`

---

### Task 19 — Add `image_transcription` overload to `resolve_model_config`
**Spec:** New Config Tier Checklist §4.2 — *"Add the `@overload` … AND the implementation `elif` branch returning `ImageTranscriptionProviderConfig.model_validate(tier_data)`"*

In `services/resolver.py`:
- Add `from config_models import ImageTranscriptionProviderConfig` to imports.
- Add the overload:
  ```python
  @overload
  async def resolve_model_config(bot_id: str, config_tier: Literal["image_transcription"]) -> ImageTranscriptionProviderConfig: ...
  ```
- Add `elif config_tier == "image_transcription": return ImageTranscriptionProviderConfig.model_validate(tier_data)` in the implementation body.

**File:** `services/resolver.py`

---

### Task 20 — Add `image/gif` to `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py`
**Spec:** Processing Flow — *"Update `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` to include `\"image/gif\"` in the `ImageVisionProcessor` mime types list."*

Change the `ImageVisionProcessor` entry from:
```python
{"mimeTypes": ["image/jpeg", "image/png", "image/webp"], ...}
```
to:
```python
{"mimeTypes": ["image/jpeg", "image/png", "image/webp", "image/gif"], ...}
```

**File:** `services/media_processing_service.py`

---

### Task 21 — Create `format_processing_result` in `media_processors/base.py`
**Spec:** Output Format — *"`format_processing_result(content: str, caption: str) -> str` **must be implemented as a module-level function inside `media_processors/base.py`**"*

Implement as a pure function **above** the `BaseMediaProcessor` class:
```python
def format_processing_result(content: str, caption: str) -> str:
    """Pure helper: wraps content in brackets and appends caption if non-empty."""
    result = f"[{content}]"
    if caption:
        result += f"\n[Caption: {caption}]"
    return result
```
This function must **never** mutate the arguments and must **unconditionally** wrap content in brackets regardless of success or failure.

**File:** `media_processors/base.py`

---

### Task 22 — Remove `caption` parameter from `process_media` in base + all 7 subclasses
**Spec:** Output Format — *"Update `BaseMediaProcessor.process_job()` to remove the `caption` argument from the `self.process_media` call. Also, update the `process_media` method signature in `BaseMediaProcessor` and explicitly all 7 affected subclasses"*

Update method signature everywhere to:
```python
async def process_media(self, file_path: str, mime_type: str, bot_id: str) -> ProcessingResult:
```
The 7 subclasses to update: `ImageVisionProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`.

Also remove `caption` from the `self.process_media(...)` call inside `process_job`.

**Files:** `media_processors/base.py`, `media_processors/image_vision_processor.py`, `media_processors/error_processors.py`, `media_processors/stub_processors.py`

---

### Task 23 — Refactor `BaseMediaProcessor.process_job()` per full spec snippet
**Spec:** Output Format — *"Replace the partial instructions with the following exhaustive snippet"*

Replace the entire `process_job` body with the exact spec-provided snippet. Key changes vs. current code:
1. Extract `caption = job.placeholder_message.content` at the top (before the try block).
2. Remove `caption` from the `process_media` call.
3. `asyncio.TimeoutError` now produces `ProcessingResult(content="Processing timed out", failed_reason=f"TIMEOUT: processing exceeded {self.processing_timeout}s", unprocessable_media=True)` — no brackets in the raw string.
4. **New step 2 (prefix injection):** Only when `not result.unprocessable_media and not result.failed_reason`, prepend `"{MediaType} Transcription: "` prefix using `media_type = job.mime_type.replace("media_corrupt_", "").split("/")[0].capitalize()`.
5. **New step 3 (format):** Unconditionally call `result.content = format_processing_result(result.content, caption)` before any persistence.
6. All downstream persistence/delivery operations remain unchanged (and automatically inherit the formatted string).

**File:** `media_processors/base.py`

---

### Task 24 — Update `_handle_unhandled_exception`
**Spec:** Output Format — *"Update `BaseMediaProcessor._handle_unhandled_exception` to ensure its `ProcessingResult` correctly sets `unprocessable_media=True` and change its hardcoded content from `\"[Media processing failed]\"` to `\"Media processing failed\"`"*

Changes:
- Source `caption = job.placeholder_message.content` at the top.
- Create `ProcessingResult(content="Media processing failed", failed_reason=error, unprocessable_media=True)`.
- Call `result.content = format_processing_result(result.content, caption)` **first** before `_persist_result_first`, `_archive_to_failed`, and queue delivery.

**File:** `media_processors/base.py`

---

### Task 25 — Update `CorruptMediaProcessor.process_media`
**Spec:** Output Format — *"`CorruptMediaProcessor`: return `ProcessingResult(content=f\"Corrupted {media_type} media could not be downloaded\", failed_reason=..., unprocessable_media=True)` — no caption, no brackets."*

Change the return to:
```python
media_type = mime_type.replace("media_corrupt_", "")
return ProcessingResult(
    content=f"Corrupted {media_type} media could not be downloaded",
    failed_reason=f"download failed - {media_type} corrupted",
    unprocessable_media=True
)
```
The `media_type = mime_type.replace("media_corrupt_", "")` derivation must be preserved. No caption handling; no bracket wrapping.

**File:** `media_processors/error_processors.py`

---

### Task 26 — Update `UnsupportedMediaProcessor.process_media`
**Spec:** Output Format — *"`UnsupportedMediaProcessor`: return `ProcessingResult(content=f\"Unsupported media type: {mime_type}\", failed_reason=..., unprocessable_media=True)` — no caption, no brackets."*

Change the return to:
```python
return ProcessingResult(
    content=f"Unsupported media type: {mime_type}",
    failed_reason=f"unsupported mime type: {mime_type}",
    unprocessable_media=True
)
```

**File:** `media_processors/error_processors.py`

---

### Task 27 — Update `StubSleepProcessor.process_media`
**Spec:** Output Format — *"`StubSleepProcessor` (and any inheriting stub processors): return `ProcessingResult(content=f\"multimedia message with guid='{...}'\")` — no redundant \"Transcripted\" phrasing, no brackets, `unprocessable_media` defaults to `False`"*

Change the return to:
```python
return ProcessingResult(content=f"multimedia message with guid='{os.path.basename(file_path)}'")
```
No `"Transcripted"` prefix. No brackets. `unprocessable_media` defaults to `False` (success path — `process_job` will apply the prefix and format it).

**File:** `media_processors/stub_processors.py`

---

### Task 28 — Implement full `ImageVisionProcessor.process_media`
**Spec:** Processing Flow; Transcription

Replace the stub implementation with the full flow:

1. Load image as base64 via `asyncio.to_thread(_load_image_base64, file_path)`.
2. Get moderation provider: `provider = await create_model_provider(bot_id, "media_processing", "image_moderation")`.
3. Get `moderation_result = await provider.moderate_image(base64_image, mime_type)`.
4. **Flagged path** (`moderation_result.flagged == True`):
   - Return `ProcessingResult(content="cannot process image as it violates safety guidelines", failed_reason=None, unprocessable_media=True)`.
5. **Clean path** (`moderation_result.flagged == False`):
   - `language_code = await resolve_bot_language(bot_id)`.
   - `transcription_provider = await create_model_provider(bot_id, "image_transcription", "image_transcription")`.
   - `transcript = await transcription_provider.transcribe_image(base64_image, mime_type, language_code)`.
   - Return `ProcessingResult(content=transcript)`.
6. No `try/except` around `transcribe_image` — exceptions propagate to `process_job`.

Import `resolve_bot_language` from `services.resolver`, `ImageTranscriptionProvider` from `model_providers.image_transcription`.

**File:** `media_processors/image_vision_processor.py`

---

### Task 29 — Update `get_bot_defaults` to include `image_transcription`
**Spec:** Deployment Checklist §3 — *"Update `get_bot_defaults` in `routers/bot_management.py` to include `image_transcription` in `LLMConfigurations` using `ImageTranscriptionProviderConfig` and `DefaultConfigurations`."*

Add `image_transcription=ImageTranscriptionProviderConfig(...)` to the `LLMConfigurations(...)` call inside `get_bot_defaults`, using `DefaultConfigurations.model_provider_name_image_transcription`, `DefaultConfigurations.model_image_transcription`, etc. Import `ImageTranscriptionProviderConfig` and `ImageTranscriptionProviderSettings`.

**File:** `routers/bot_management.py`

---

### Task 30 — Make schema surgery loop dynamic + patch `ImageTranscriptionProviderSettings`
**Spec:** Configuration; New Config Tier Checklist §4.3

In `get_configuration_schema` in `routers/bot_management.py`:
1. Replace:
   ```python
   for prop_name in ['high', 'low', 'image_moderation']:
   ```
   with:
   ```python
   for prop_name in llm_configs_defs['properties'].keys():
   ```
2. Extend the `reasoning_effort` title patch (currently only for `'ChatCompletionProviderSettings'`) to also process `'ImageTranscriptionProviderSettings'`.

**File:** `routers/bot_management.py`

---

### Task 31 — Create `GET /api/internal/bots/tiers` endpoint
**Spec:** New Config Tier Checklist §4.4 — *"Create a new lightweight API endpoint `GET /api/internal/bots/tiers` in `bot_management.py` that directly returns the available tiers by reading `LLMConfigurations.model_fields.keys()`"*

Add a new route:
```python
@router.get("/tiers")
async def get_llm_tiers():
    return {"tiers": list(LLMConfigurations.model_fields.keys())}
```
This must align with the existing `/api/internal/bots` router prefix, making the full path `/api/internal/bots/tiers`.

**File:** `routers/bot_management.py`

---

### Task 32 — Add `image_transcription` uiSchema entry in `EditPage.js` (static)
**Spec:** New Config Tier Checklist §4.5 — *"Statically add a fourth entry to the `llm_configs` object in `uiSchema` for `image_transcription`"*

Add a fourth static `image_transcription` entry to the `llm_configs` uiSchema object:
```js
image_transcription: {
  "ui:title": "Image Transcription Model",
  "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
  provider_config: {
    api_key_source: { "ui:title": "API Key Source" },
    reasoning_effort: { "ui:title": "Reasoning Effort" },
    seed: { "ui:title": "Seed" },
    detail: { "ui:title": "Image Detail Level" },
    "ui:ObjectFieldTemplate": FlatProviderConfigTemplate,
  }
}
```
The `provider_config` sub-object must be identical to `high`/`low` tier entries, plus the additional `detail` field.

**File:** `frontend/src/pages/EditPage.js`

---

### Task 33 — Fetch tiers dynamically, replace hardcoded arrays in `EditPage.js`
**Spec:** New Config Tier Checklist §4.4 — *"Update `EditPage.js` to fetch from this new endpoint … during `fetchData` and store the result in component state."*

1. In `fetchData`, add a call to `GET /api/internal/bots/tiers` (or via the proxy/gateway mapping).
2. Store the result in component state (e.g., `availableTiers`).
3. Replace every occurrence of the hardcoded `["high", "low", "image_moderation"]` array (around line 135 for `api_key_source` and line 229 for `handleFormChange`) with `availableTiers`.

**File:** `frontend/src/pages/EditPage.js`

---

### Task 34 — Update `initialize_quota_and_bots.py` with `image_transcription` tier
**Spec:** Deployment Checklist §5 — *"Update `scripts/migrations/initialize_quota_and_bots.py` to include the `image_transcription` tier in the `token_menu` dictionary, bringing the total to 3 tiers"*

Add the `"image_transcription"` entry to the `token_menu` dictionary with pricing:
```python
"image_transcription": {
    "input_tokens": 0.25,
    "cached_input_tokens": 0.025,
    "output_tokens": 2.0
}
```
Keep existing insert-if-not-exists safety logic. Add a comment noting `image_moderation` is intentionally omitted because it has no model-token cost calculation.

**File:** `scripts/migrations/initialize_quota_and_bots.py`

---

### Task 35 — Create `scripts/migrations/migrate_image_transcription.py`
**Spec:** Deployment Checklist §1; Migration Contract §8

Create a migration script that:
- Iterates all bot configs in `COLLECTION_BOT_CONFIGURATIONS` (using `infrastructure/db_schema.py` constants — no hardcoded collection names).
- Adds `config_data.configurations.llm_configs.image_transcription` where missing.
- Uses the same default values as `DefaultConfigurations` for the new tier.
- Follows existing migration patterns (e.g., captures pre/post document counts).

**File:** `scripts/migrations/migrate_image_transcription.py` *(new)*

---

### Task 36 — Create `scripts/migrations/migrate_token_menu_image_transcription.py`
**Spec:** Deployment Checklist §6; Migration Contract §8

Create a script that:
- Completely deletes any existing `token_menu` document from `COLLECTION_GLOBAL_CONFIGURATIONS`.
- Re-inserts the full correct 3-tier menu from scratch (hard reset strategy).
- Pricing: `high`, `low` (existing rates), and `image_transcription` (`input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`).
- Uses `infrastructure/db_schema.py` constants (no hardcoded collection names).

**File:** `scripts/migrations/migrate_token_menu_image_transcription.py` *(new)*

---

### Task 37 — Create `scripts/migrations/migrate_pool_definitions_gif.py`
**Spec:** Processing Flow — *"Create a migration script … that completely **deletes** the existing `_mediaProcessorDefinitions` document from the MongoDB `configurations` collection."*; Migration Contract §8

Create a script that:
- Deletes the `_mediaProcessorDefinitions` document from the configurations collection.
- After deletion, on next server boot `MediaProcessingService._ensure_configuration_templates()` will recreate the document from `DEFAULT_POOL_DEFINITIONS` (which now includes `image/gif`).
- Uses `infrastructure/db_schema.py` constants.

**File:** `scripts/migrations/migrate_pool_definitions_gif.py` *(new)*

---

### Task 38 — Test: `detail` filtered from `ChatOpenAI` kwargs
**Spec:** Test Expectations — *"Add tests that verify `detail` is filtered from `ChatOpenAI(...)` constructor kwargs and only used in transcription payload construction."*

- Instantiate `OpenAiImageTranscriptionProvider` with a config that includes a `detail` value.
- Assert that `self._llm` was constructed without `detail` in kwargs (i.e., `ChatOpenAI` was not called with `detail`).
- Assert that `self._detail` holds the expected value.
- Assert `detail` is correctly included in the `image_url` content block when `transcribe_image` is called.

**Files:** tests directory (e.g., `tests/test_openai_image_transcription_provider.py`)

---

### Task 39 — Test: callback continuity (same `self._llm` object)
**Spec:** Test Expectations — *"Add tests that verify callback continuity: callback attachment in `create_model_provider` and transcription invocation in `transcribe_image(...)` use the same LLM object reference."*

- Mock `create_model_provider` or directly instantiate `OpenAiImageTranscriptionProvider`.
- Attach a mock `TokenTrackingCallback` via `get_llm()`.
- Call `transcribe_image(...)` and assert that the internally used LLM object (i.e., `self._llm`) is the same object that has the callback attached.

**Files:** tests directory

---

### Task 40 — Test: transcription response normalization (all branches)
**Spec:** Test Expectations — *"Add tests for transcription normalization covering all branches."*

Three test cases:
1. `response.content` is `str` → returned as-is.
2. `response.content` is a list of content blocks (text-bearing) → concatenated with single space, outer whitespace trimmed.
3. `response.content` is neither string nor content blocks → returns `"Unable to transcribe image content"`.

**Files:** tests directory

---

### Task 41 — Test: `moderation_result.flagged == True` returns correct `ProcessingResult`
**Spec:** Test Expectations — *"Add test that `moderation_result.flagged == True` returns `ProcessingResult(unprocessable_media=True, content=\"cannot process image as it violates safety guidelines\")`."*

Mock the moderation provider to return `ModerationResult(flagged=True, ...)` and assert the exact `ProcessingResult` returned by `ImageVisionProcessor.process_media`.

**Files:** `tests/test_image_vision_processor.py`

---

### Task 42 — Test: `format_processing_result` formatting logic
**Spec:** Test Expectations — *"Add test that `format_processing_result` formats strings with unconditional bracket wrapping, and correctly omits or adds captions"*

Test cases:
- `format_processing_result("some content", "")` → `"[some content]"`.
- `format_processing_result("some content", None)` → `"[some content]"`.
- `format_processing_result("some content", "Hello caption")` → `"[some content]\n[Caption: Hello caption]"`.

**Files:** tests directory

---

### Task 43 — Test: caption correctly appended in both success and failure paths
**Spec:** Test Expectations — *"Add test that caption is correctly appended when `job.placeholder_message.content` is populated, regardless of whether processing succeeded or failed."*

Test both the success path (through `process_job`) and failure path (via `_handle_unhandled_exception`) and assert caption from `job.placeholder_message.content` appears in the final delivered content.

**Files:** tests directory

---

### Task 44 — Test: `asyncio.TimeoutError` returns `ProcessingResult(unprocessable_media=True)`
**Spec:** Test Expectations — *"Add test that the `asyncio.TimeoutError` path returns `ProcessingResult` with `unprocessable_media=True`."*

Mock `process_media` to never complete (or set very short timeout), trigger the timeout, and assert the returned `ProcessingResult` has `unprocessable_media=True` and `content="Processing timed out"` (before formatting).

**Files:** tests directory

---

### Task 45 — Update existing unit tests: `process_media()` returns raw unbracketed strings
**Spec:** Test Expectations — *"Update existing tests to assert that `process_media()` returns raw, unbracketed content strings"*

Find all existing tests that assert `process_media()` returns a string containing `[...]` brackets (e.g., `"[Transcripted audio multimedia message...]"`). Update them to assert the raw unbracketed version (e.g., `"multimedia message with guid='...'"` for stubs). Verifies removal of legacy bracket wrapping from `process_media`.

**Files:** existing test files (e.g., `tests/test_stub_processors.py`, `tests/test_audio_transcription_processor.py`, etc.)

---

### Task 46 — Add integration tests: `process_job` end-to-end final formatted string
**Spec:** Test Expectations — *"Add new tests that assert the final string delivered to the bot queue (via `update_message_by_media_id`) is the fully formatted `\"[{MediaType} Transcription: {content}]\"` form"*

Integration tests that mock `process_media` to return a raw result, run `process_job`, and assert that the string passed to `update_message_by_media_id` is in the format `"[Audio Transcription: multimedia message with guid='...']"` (for example).

**Files:** tests directory (e.g., `tests/test_base_media_processor.py`)

---

### Task 47 — Update existing tests: renamed content strings for `UnsupportedMediaProcessor` and `CorruptMediaProcessor`
**Spec:** Test Expectations — *"Update existing tests … for renamed content strings."*

Update any existing tests that assert:
- Old `UnsupportedMediaProcessor` string `"Unsupported {mime_type} media"` → new `f"Unsupported media type: {mime_type}"`.
- Old `CorruptMediaProcessor` string with bracket wrapping → new unbracketed `f"Corrupted {media_type} media could not be downloaded"`.

**Files:** existing test files (e.g., `tests/test_error_processors.py`)

---

### Task 48 — Update `test_process_media_bot_id_signature`
**Spec:** Test Expectations — *"The `test_process_media_bot_id_signature` test in `tests/test_image_vision_processor.py` must precisely be updated: rewrite the test assertion entirely to use a robust dictionary key lookup"*

Change the assertion from a hardcoded parameter index lookup (e.g., `params[3]`) to:
```python
assert "bot_id" in sig.parameters
```

**File:** `tests/test_image_vision_processor.py`
