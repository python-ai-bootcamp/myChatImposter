# Implementation Tasks: Media Processor Image Moderation

## Scope Boundaries

Per the spec overview, the following are **out of scope** for this phase:
- Moderation policy enforcement
- Image understanding / generation
- Rollout-safety checks and data migrations for bots with missing or invalid `image_moderation` config

## Summary Table

| # | Phase | Task | File(s) | Spec Section(s) | Status |
|---|-------|------|---------|-----------------|--------|
| 1 | A — Contracts | Update `BaseMediaProcessor.process_media()` abstract signature: `quota_exceeded` → `bot_id` | `media_processors/base.py` | §2 | DONE |
| 2 | A — Contracts | Update `BaseMediaProcessor.process_job()` call site to pass `job.bot_id` | `media_processors/base.py` | §2 | DONE |
| 3 | A — Contracts | Update `StubSleepProcessor.process_media()` signature: `quota_exceeded` → `bot_id` | `media_processors/stub_processors.py` | §2 | DONE |
| 4 | A — Contracts | Update `CorruptMediaProcessor.process_media()` signature: `quota_exceeded` → `bot_id` | `media_processors/error_processors.py` | §2 | DONE |
| 5 | A — Contracts | Update `UnsupportedMediaProcessor.process_media()` signature: `quota_exceeded` → `bot_id` | `media_processors/error_processors.py` | §2 | DONE |
| 6 | A — Contracts | Update `ImageModerationProvider.moderate_image()` abstract signature to `(base64_image, mime_type)` | `model_providers/image_moderation.py` | §4 | DONE |
| 7 | A — Contracts | Update `OpenAiModerationProvider.moderate_image()`: signature, data URI, SDK payload, raw response logging | `model_providers/openAiModeration.py` | §4, §6 | DONE |
| 8 | B — Processor | Create `media_processors/image_vision_processor.py` with `ImageVisionProcessor` inheriting from `BaseMediaProcessor` | `media_processors/image_vision_processor.py` (**new**) | §1 | DONE |
| 9 | B — Processor | Implement event-loop-safe image byte reading and base64 encoding via `asyncio.to_thread` | `media_processors/image_vision_processor.py` | §3 | DONE |
| 10 | B — Processor | Implement factory-based provider resolution with `ImageModerationProvider` type validation and moderation call | `media_processors/image_vision_processor.py` | §4 | DONE |
| 11 | B — Processor | Ensure centralized error handling — no local catch in `ImageVisionProcessor.process_media()` | `media_processors/image_vision_processor.py` | §5 | DONE |
| 12 | B — Processor | Add normalized `ModerationResult` logging at INFO level | `media_processors/image_vision_processor.py` | §6 | DONE |
| 13 | B — Processor | Return stub-style `ProcessingResult` without moderation payload in content | `media_processors/image_vision_processor.py` | §7 | DONE |
| 14 | C — Hygiene | Update `media_processors/factory.py` import to new module | `media_processors/factory.py` | §1 rule 4 | DONE |
| 15 | C — Hygiene | Remove `ImageVisionProcessor` from `stub_processors.py` — no aliases or re-exports | `media_processors/stub_processors.py` | §1 rules 2–3 | DONE |
| 16 | D — Defaults | Verify default bot config seeds `openAiModeration` + `omni-moderation-latest` | `config_models.py`, bot creation paths | Requirements | DONE |
| 17 | E — Verification | Verify: `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` resolves to `media_processors.image_vision_processor` | test file | §1 rule 5, §8 item 1 | DONE |
| 18 | E — Verification | Verify: `process_media(..., bot_id: str)` signature on base class and all concrete processors | test file | §8 item 2 | DONE |
| 19 | E — Verification | Verify: `moderate_image(base64_image, mime_type)` signatures on both provider classes | test file | §8 item 3 | DONE |
| 20 | E — Verification | Verify: image bytes read and base64-encoded via `asyncio.to_thread(...)` | test file | §8 item 4 | DONE |
| 21 | E — Verification | Verify: moderation SDK input matches `[{"type": "image_url", "image_url": {"url": data_uri}}]` | test file | §8 item 5 | DONE |

---

## Phase A — Interface Contract Updates (§2, §4, §6)

Update all shared interface signatures first so downstream implementation targets the correct contracts.

---

### Task 1 — Update `BaseMediaProcessor.process_media()` abstract signature
**Status:** DONE
**Spec Section:** §2 `process_media()` Contract Update (abstract method)
**File:** `media_processors/base.py`

Change the `process_media` abstract method signature from:
```python
@abstractmethod
async def process_media(self, file_path: str, mime_type: str, caption: str, quota_exceeded: Optional[bool]) -> ProcessingResult:
    """Subclass implements ONLY this: actual AI/conversion logic."""
    ...
```
To:
```python
@abstractmethod
async def process_media(self, file_path: str, mime_type: str, caption: str, bot_id: str) -> ProcessingResult:
    """Subclass implements ONLY this: actual AI/conversion logic."""
    ...
```

Remove `Optional` from the `typing` import if it is no longer referenced anywhere else in `base.py`.

This task defines the contract that all concrete processors and the `process_job` call site must conform to — complete it before the other §2 tasks.

---

### Task 2 — Update `BaseMediaProcessor.process_job()` call site
**Status:** DONE
**Spec Section:** §2 `process_media()` Contract Update (base class call site)
**File:** `media_processors/base.py`
**Depends on:** Task 1

Inside `BaseMediaProcessor.process_job()`, change the fourth argument passed to `self.process_media(...)` from `job.quota_exceeded` to `job.bot_id`:

Current:
```python
result = await asyncio.wait_for(
    self.process_media(file_path, job.mime_type, job.placeholder_message.content, job.quota_exceeded),
    timeout=self.processing_timeout,
)
```
Should be:
```python
result = await asyncio.wait_for(
    self.process_media(file_path, job.mime_type, job.placeholder_message.content, job.bot_id),
    timeout=self.processing_timeout,
)
```

---

### Task 3 — Update `StubSleepProcessor.process_media()` signature
**Status:** DONE
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)
**File:** `media_processors/stub_processors.py`
**Depends on:** Task 1

Change `StubSleepProcessor.process_media()` parameter from `quota_exceeded: Optional[bool]` to `bot_id: str`. The method body is unchanged — `bot_id` is accepted but ignored. Subclasses `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, and `DocumentProcessor` inherit this signature automatically and require no separate change.

Remove the `Optional` import from `typing` if no longer needed in `stub_processors.py`.

---

### Task 4 — Update `CorruptMediaProcessor.process_media()` signature
**Status:** DONE
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)
**File:** `media_processors/error_processors.py`
**Depends on:** Task 1

Change `CorruptMediaProcessor.process_media()` parameter from `quota_exceeded: Optional[bool]` to `bot_id: str`. The method body is unchanged — `bot_id` is accepted but ignored. Keep existing `caption`-based content composition intact.

---

### Task 5 — Update `UnsupportedMediaProcessor.process_media()` signature
**Status:** DONE
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)
**File:** `media_processors/error_processors.py`
**Depends on:** Task 1

Change `UnsupportedMediaProcessor.process_media()` parameter from `quota_exceeded: Optional[bool]` to `bot_id: str`. The method body is unchanged — `bot_id` is accepted but ignored. Keep existing `caption`-based content composition intact.

Remove the `Optional` import from `typing` in `error_processors.py` if no longer needed.

---

### Task 6 — Update `ImageModerationProvider.moderate_image()` abstract signature
**Status:** DONE
**Spec Section:** §4 Provider Resolution and Moderation Call (provider contract update)
**File:** `model_providers/image_moderation.py`

Change the `ImageModerationProvider.moderate_image()` abstract method signature from:
```python
async def moderate_image(self, image_url: str) -> ModerationResult:
```
To:
```python
async def moderate_image(self, base64_image: str, mime_type: str) -> ModerationResult:
```

The caller (`ImageVisionProcessor`) will supply raw base64-encoded image bytes and the MIME type. Construction of the `data:` URI is delegated to the concrete provider implementation, not the caller.

`ModerationResult` continues to capture `flagged`, `categories`, and `category_scores`. The `category_applied_input_types` field from the OpenAI API response is intentionally omitted from `ModerationResult` in this preparation phase; the raw SDK response log (Task 7) preserves full audit coverage.

---

### Task 7 — Update `OpenAiModerationProvider.moderate_image()`: signature, data URI, SDK payload, and raw response logging
**Status:** DONE
**Spec Section:** §4 Provider Resolution and Moderation Call (provider contract update, input payload shape), §6 Logging Requirements
**File:** `model_providers/openAiModeration.py`
**Depends on:** Task 6

Four changes in this file:

1. **Signature**: Change method signature from `(self, image_url: str)` to `(self, base64_image: str, mime_type: str)`.

2. **Data URI construction**: Inside the method body, construct the data URI as:
   ```python
   data_uri = f"data:{mime_type};base64,{base64_image}"
   ```

3. **SDK payload**: Use the data URI in the moderation input exactly as:
   ```python
   input=[{"type": "image_url", "image_url": {"url": data_uri}}]
   ```
   The async `openai` SDK is used directly (no LangChain wrapper). The SDK call must stay async.

4. **Logging**: After the SDK call completes, log the raw response before constructing `ModerationResult`:
   ```python
   logger.info(response.model_dump())
   ```
   Add a module-level `logger = logging.getLogger(__name__)` and `import logging`.

The normalized `ModerationResult` return (`flagged`, `categories`, `category_scores`) stays as-is. The `provider_name` used for dynamic loading by `model_factory.py` is `"openAiModeration"`, which already matches the existing filename convention.

---

## Phase B — Processor Extraction and Implementation (§1, §3, §4, §5, §6, §7)

Create the new `ImageVisionProcessor` in its canonical module and implement the full `process_media()` body. Tasks 9–13 collectively build the method body; the file is not functionally complete until all five are applied.

---

### Task 8 — Create `media_processors/image_vision_processor.py`
**Status:** DONE
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene
**File:** `media_processors/image_vision_processor.py` (**new file**)
**Depends on:** Tasks 1–2 (contract must be defined before implementing)

Create `media_processors/image_vision_processor.py` containing the `ImageVisionProcessor` class. Key requirements:
- Inherits directly from `BaseMediaProcessor` (**not** from `StubSleepProcessor`).
- This file is the only canonical source for `ImageVisionProcessor` — no other file may define or re-export it.
- Define `process_media(self, file_path: str, mime_type: str, caption: str, bot_id: str) -> ProcessingResult` (method body is filled by Tasks 9–13).
- Add module-level `logger = logging.getLogger(__name__)`.

---

### Task 9 — Implement event-loop-safe image loading
**Status:** DONE
**Spec Section:** §3 Image Data Loading (Event-Loop Safe)
**File:** `media_processors/image_vision_processor.py`
**Depends on:** Task 8

Inside `ImageVisionProcessor.process_media()`, read image bytes from `file_path` and base64-encode them. Both the synchronous file I/O and the base64 encoding must be offloaded from the event loop using `asyncio.to_thread(...)`:

```python
import base64

def _load_image_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

base64_image = await asyncio.to_thread(_load_image_base64, file_path)
```

The helper function (or equivalent inline callable) must perform both the read and the encode within the same `to_thread` call — a single thread dispatch for a single logical operation.

---

### Task 10 — Implement factory-based provider resolution and moderation call
**Status:** DONE
**Spec Section:** §4 Provider Resolution and Moderation Call
**File:** `media_processors/image_vision_processor.py`
**Depends on:** Tasks 6–7 (provider contract must be updated), Task 9 (base64_image must be available)

After obtaining `base64_image` (Task 9), resolve the moderation provider and call it:

```python
from services.model_factory import create_model_provider
from model_providers.image_moderation import ImageModerationProvider

provider = await create_model_provider(bot_id, "media_processing", "image_moderation")
if not isinstance(provider, ImageModerationProvider):
    raise TypeError(f"Expected ImageModerationProvider, got {type(provider)}")
moderation_result = await provider.moderate_image(base64_image, mime_type)
```

Rules:
- Do not hardcode model name, provider name, or API key in the processor.
- The `feature_name` parameter (`"media_processing"`) is currently unused in the `ImageModerationProvider` code path — it is only consumed for `ChatCompletionProvider` token tracking. This is known and accepted per the spec.

---

### Task 11 — Ensure centralized error handling — no local catch
**Status:** DONE
**Spec Section:** §5 Error Handling Strategy
**File:** `media_processors/image_vision_processor.py`
**Depends on:** Task 10

This is a design constraint, not additive code. If moderation, provider resolution, or config resolution throws:
- Do **not** wrap the moderation/provider block in a `try/except` for manual fallback content inside `ImageVisionProcessor.process_media()`.
- Let exceptions propagate uncaught out of `process_media()` so that `BaseMediaProcessor.process_job()`'s existing `_handle_unhandled_exception` mechanism handles them centrally.

This must be actively verified during implementation — ensure no defensive `try/except` creeps in around Tasks 9–10 logic.

---

### Task 12 — Add normalized `ModerationResult` logging
**Status:** DONE
**Spec Section:** §6 Logging Requirements
**File:** `media_processors/image_vision_processor.py`
**Depends on:** Task 10

After a successful moderation call, log the normalized result at `INFO` level:

```python
logger.info(moderation_result.model_dump())
```

This captures `flagged`, `categories`, and `category_scores`. It is separate from the raw SDK response log in `OpenAiModerationProvider` (Task 7) — both log lines serve different audit purposes (normalized vs. raw).

---

### Task 13 — Return stub-style `ProcessingResult`
**Status:** DONE
**Spec Section:** §7 Processing Result for This Phase
**File:** `media_processors/image_vision_processor.py`
**Depends on:** Task 12

After logging (Task 12), return the preparation-phase stub result:

```python
import os
from infrastructure.models import ProcessingResult

return ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")
```

The moderation payload must **not** be embedded in the message content at this phase. This maintains the existing message format for downstream consumers.

The `process_media()` method body is now complete after Tasks 9–13.

---

## Phase C — Module Hygiene Migration (§1)

Rewire the factory and remove the old definition. Task 14 must be completed before Task 15 to avoid a broken import window.

---

### Task 14 — Update `media_processors/factory.py` import to new module
**Status:** DONE
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene (rule 4)
**File:** `media_processors/factory.py`
**Depends on:** Task 8 (new module must exist)

Change the import of `ImageVisionProcessor` from `media_processors.stub_processors` to `media_processors.image_vision_processor`:

Current:
```python
from media_processors.stub_processors import (
    AudioTranscriptionProcessor,
    DocumentProcessor,
    ImageVisionProcessor,
    VideoDescriptionProcessor,
)
```
Should be:
```python
from media_processors.stub_processors import (
    AudioTranscriptionProcessor,
    DocumentProcessor,
    VideoDescriptionProcessor,
)
from media_processors.image_vision_processor import ImageVisionProcessor
```

The `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` entry remains unchanged — it still maps the string key to the `ImageVisionProcessor` class, which now comes from the new module.

---

### Task 15 — Remove `ImageVisionProcessor` from `stub_processors.py`
**Status:** DONE
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene (rules 2–3)
**File:** `media_processors/stub_processors.py`
**Depends on:** Task 8 (new module created), Task 14 (factory rewired)

Delete the `ImageVisionProcessor` class definition entirely from `stub_processors.py`. Strict hygiene rules:
- Do **not** leave an alias (e.g., `ImageVisionProcessor = image_vision_processor.ImageVisionProcessor`).
- Do **not** add a bridge import or re-export of any kind.
- The remaining classes — `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor` — stay in `stub_processors.py` unchanged (except for the signature update from Task 3).

---

## Phase D — Default Configuration Alignment (Requirements)

---

### Task 16 — Verify default bot config seeds `openAiModeration` + `omni-moderation-latest`
**Status:** DONE
**Spec Section:** Requirements
**File:** `config_models.py`, `routers/bot_management.py`, `routers/bot_ui.py`

The spec requires that new/default bot configurations default to `openAiModeration` provider with `omni-moderation-latest` model. Verify that all configuration surfaces that seed new bots consistently use these values:

1. **`config_models.py`** — `DefaultConfigurations` already defines `model_provider_name_moderation = "openAiModeration"` and `model_image_moderation = "omni-moderation-latest"`. Confirm these are correct and unchanged.

2. **`routers/bot_management.py`** — The admin bot creation path constructs a default `BotConfiguration` with `LLMConfigurations(image_moderation=BaseModelProviderConfig(provider_name=DefaultConfigurations.model_provider_name_moderation, ...))`. Confirm the `image_moderation` tier is populated from `DefaultConfigurations` values (not hardcoded alternatives).

3. **`routers/bot_ui.py`** — The regular-user bot creation/patch path similarly constructs `LLMConfigurations` with an `image_moderation` tier sourced from `DefaultConfigurations`. Confirm this path also uses `DefaultConfigurations.model_provider_name_moderation` and `DefaultConfigurations.model_image_moderation`.

This is a verification/alignment task, not new feature work. If defaults are already correct, document that finding and move on.

---

## Phase E — Verification (§8)

Each verification task maps 1:1 to a checklist item from §8. The proof method is flexible: unit test, integration test, assertion, or equivalent. Suggested test file: `tests/test_image_vision_processor.py`.

---

### Task 17 — Verification: Factory resolution points to `media_processors.image_vision_processor`
**Status:** DONE
**Spec Section:** §1 Hygiene Rule 5, §8 Verification Checklist item 1
**File:** `tests/test_image_vision_processor.py`
**Depends on:** Task 14

Write a test proving that `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` is defined in the `media_processors.image_vision_processor` module:

```python
from media_processors.factory import PROCESSOR_CLASS_MAP

def test_image_vision_processor_factory_resolution():
    cls = PROCESSOR_CLASS_MAP["ImageVisionProcessor"]
    assert cls.__module__ == "media_processors.image_vision_processor"
```

---

### Task 18 — Verification: `process_media(..., bot_id: str)` signature on all processors
**Status:** DONE
**Spec Section:** §8 Verification Checklist item 2
**File:** `tests/test_image_vision_processor.py`
**Depends on:** Tasks 1, 3–5, 8

Write a test verifying the fourth parameter of `process_media` is named `bot_id` with type annotation `str` across all affected classes:
- `BaseMediaProcessor` (abstract)
- `StubSleepProcessor` (and inherited subclasses `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`)
- `CorruptMediaProcessor`
- `UnsupportedMediaProcessor`
- `ImageVisionProcessor`

```python
import inspect

def test_process_media_bot_id_signature():
    for cls in [BaseMediaProcessor, StubSleepProcessor, CorruptMediaProcessor,
                UnsupportedMediaProcessor, ImageVisionProcessor]:
        params = list(inspect.signature(cls.process_media).parameters.values())
        fourth = params[4]  # self=0, file_path=1, mime_type=2, caption=3, bot_id=4
        assert fourth.name == "bot_id"
        assert fourth.annotation is str
```

---

### Task 19 — Verification: `moderate_image(base64_image, mime_type)` signatures on both provider classes
**Status:** DONE
**Spec Section:** §8 Verification Checklist item 3
**File:** `tests/test_image_vision_processor.py`
**Depends on:** Tasks 6–7

Write a test verifying that both `ImageModerationProvider.moderate_image` and `OpenAiModerationProvider.moderate_image` accept `base64_image: str` and `mime_type: str` as their parameters (in that order, after `self`):

```python
import inspect

def test_moderate_image_signature():
    for cls in [ImageModerationProvider, OpenAiModerationProvider]:
        params = list(inspect.signature(cls.moderate_image).parameters.values())
        assert params[1].name == "base64_image" and params[1].annotation is str
        assert params[2].name == "mime_type" and params[2].annotation is str
```

---

### Task 20 — Verification: Event-loop safety — image loading via `asyncio.to_thread`
**Status:** DONE
**Spec Section:** §8 Verification Checklist item 4
**File:** `tests/test_image_vision_processor.py`
**Depends on:** Task 9

Write a test confirming `ImageVisionProcessor.process_media()` offloads file reading and base64 encoding to a thread via `asyncio.to_thread`. The test should mock `asyncio.to_thread` and verify it is called with a callable that performs both operations within a single thread dispatch, ensuring the event loop is not blocked by synchronous I/O.

---

### Task 21 — Verification: Moderation SDK payload shape
**Status:** DONE
**Spec Section:** §8 Verification Checklist item 5
**File:** `tests/test_image_vision_processor.py`
**Depends on:** Task 7

Write a test verifying the exact input structure sent to `client.moderations.create()` inside `OpenAiModerationProvider.moderate_image()`. The test should mock the OpenAI `AsyncOpenAI` client, invoke `moderate_image(base64_image, mime_type)`, and capture the `input` argument to confirm it matches:

```python
[{"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}]
```

This proves the data URI is constructed internally by the provider and the SDK receives the exact payload shape specified in §4.
