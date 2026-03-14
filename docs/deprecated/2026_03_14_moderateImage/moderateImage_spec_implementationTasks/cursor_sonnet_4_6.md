# Implementation Tasks: Media Processor Image Moderation

## Summary Table

| # | Task | Spec Section(s) | Status |
|---|------|-----------------|--------|
| 1 | Update `BaseMediaProcessor.process_media()` abstract signature: `quota_exceeded: Optional[bool]` → `bot_id: str` | §2 `process_media()` Contract Update | PENDING |
| 2 | Update `BaseMediaProcessor.process_job()` call site: pass `job.bot_id` instead of `job.quota_exceeded` | §2 `process_media()` Contract Update | PENDING |
| 3 | Update `StubSleepProcessor.process_media()` signature: `quota_exceeded: Optional[bool]` → `bot_id: str` | §2 `process_media()` Contract Update | PENDING |
| 4 | Update `CorruptMediaProcessor.process_media()` signature: `quota_exceeded: Optional[bool]` → `bot_id: str` | §2 `process_media()` Contract Update | PENDING |
| 5 | Update `UnsupportedMediaProcessor.process_media()` signature: `quota_exceeded: Optional[bool]` → `bot_id: str` | §2 `process_media()` Contract Update | PENDING |
| 6 | Update `ImageModerationProvider.moderate_image()` abstract signature to `(base64_image: str, mime_type: str)` | §4 Provider Resolution and Moderation Call | PENDING |
| 7 | Update `OpenAiModerationProvider.moderate_image()`: new signature + internal data URI construction + raw SDK response logging | §4 Provider Resolution and Moderation Call, §6 Logging Requirements | PENDING |
| 8 | Create `media_processors/image_vision_processor.py` containing `ImageVisionProcessor` inheriting from `BaseMediaProcessor` | §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene | PENDING |
| 9 | Implement event-loop-safe image byte reading and base64 encoding via `asyncio.to_thread` inside `ImageVisionProcessor.process_media()` | §3 Image Data Loading (Event-Loop Safe) | PENDING |
| 10 | Implement factory-based provider resolution in `ImageVisionProcessor.process_media()` with `ImageModerationProvider` type validation and moderation call | §4 Provider Resolution and Moderation Call, §5 Error Handling Strategy | PENDING |
| 11 | Add normalized `ModerationResult` logging in `ImageVisionProcessor.process_media()` | §6 Logging Requirements | PENDING |
| 12 | Return stub-style `ProcessingResult` from `ImageVisionProcessor.process_media()` | §7 Processing Result for This Phase | PENDING |
| 13 | Remove `ImageVisionProcessor` from `media_processors/stub_processors.py` (no aliases or re-exports) | §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene | PENDING |
| 14 | Update `media_processors/factory.py` to import `ImageVisionProcessor` from `media_processors.image_vision_processor` | §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene | PENDING |
| 15 | Write verification: `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` resolves to class from `media_processors.image_vision_processor` module | §1 Hygiene Rule 5, §8 Verification Checklist | PENDING |
| 16 | Write verification: `process_media(..., bot_id: str)` signature is applied to `BaseMediaProcessor` and all concrete processors | §2, §8 Verification Checklist | PENDING |
| 17 | Write verification: `moderate_image(base64_image: str, mime_type: str)` signature on both `ImageModerationProvider` and `OpenAiModerationProvider` | §4, §8 Verification Checklist | PENDING |
| 18 | Write verification: `ImageVisionProcessor.process_media()` offloads file read and base64 encoding to `asyncio.to_thread` | §3, §8 Verification Checklist | PENDING |
| 19 | Write verification: moderation SDK input matches `[{"type": "image_url", "image_url": {"url": "data:{mime_type};base64,{base64_image}"}}]` | §4, §8 Verification Checklist | PENDING |

---

## Task Details

### Task 1 — Update `BaseMediaProcessor.process_media()` abstract signature
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (abstract method)
**File:** `media_processors/base.py`

Change the `process_media` abstract method signature from:
```python
async def process_media(self, file_path: str, mime_type: str, caption: str, quota_exceeded: Optional[bool]) -> ProcessingResult:
```
To:
```python
async def process_media(self, file_path: str, mime_type: str, caption: str, bot_id: str) -> ProcessingResult:
```
Remove the `Optional` import from `typing` if it is no longer referenced anywhere else in `base.py`.

This task must be completed first, as it defines the contract all concrete processors and the call site in `process_job` must conform to.

---

### Task 2 — Update `BaseMediaProcessor.process_job()` call site
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (base class call site)
**File:** `media_processors/base.py`

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
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)
**File:** `media_processors/stub_processors.py`

Change `StubSleepProcessor.process_media()` parameter from `quota_exceeded: Optional[bool]` to `bot_id: str`. The method body is unchanged — `bot_id` is accepted but ignored. Subclasses `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, and `DocumentProcessor` inherit this signature automatically and require no separate change.

Remove the `Optional` import from `typing` if no longer needed in `stub_processors.py`.

---

### Task 4 — Update `CorruptMediaProcessor.process_media()` signature
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)
**File:** `media_processors/error_processors.py`

Change `CorruptMediaProcessor.process_media()` parameter from `quota_exceeded: Optional[bool]` to `bot_id: str`. The method body is unchanged — `bot_id` is accepted but ignored in this processor.

---

### Task 5 — Update `UnsupportedMediaProcessor.process_media()` signature
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)
**File:** `media_processors/error_processors.py`

Change `UnsupportedMediaProcessor.process_media()` parameter from `quota_exceeded: Optional[bool]` to `bot_id: str`. The method body is unchanged — `bot_id` is accepted but ignored. Remove the `Optional` import from `typing` in `error_processors.py` if no longer needed.

---

### Task 6 — Update `ImageModerationProvider.moderate_image()` abstract signature
**Status:** PENDING
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

The caller (`ImageVisionProcessor`) will supply raw base64-encoded image bytes and the MIME type. Construction of the `data:` URI is delegated to the concrete provider implementation, not the caller. The `category_applied_input_types` field is intentionally omitted from `ModerationResult` in this phase.

---

### Task 7 — Update `OpenAiModerationProvider.moderate_image()`: signature, data URI, SDK payload, and raw response logging
**Status:** PENDING
**Spec Section:** §4 Provider Resolution and Moderation Call (provider contract update, input payload shape), §6 Logging Requirements
**File:** `model_providers/openAiModeration.py`

1. **Signature**: Change method signature from `(self, image_url: str)` to `(self, base64_image: str, mime_type: str)`.
2. **Data URI construction**: Inside the method body, construct the data URI as:
   ```python
   data_uri = f"data:{mime_type};base64,{base64_image}"
   ```
3. **SDK payload**: Use the data URI in the moderation input exactly as:
   ```python
   [{"type": "image_url", "image_url": {"url": data_uri}}]
   ```
4. **Logging**: After the SDK call completes, log the raw response before constructing `ModerationResult`:
   ```python
   logger.info(response.model_dump())
   ```
   Add a module-level `logger = logging.getLogger(__name__)` and import `logging`.

The `provider_name` used for dynamic loading by `model_factory.py` is `"openAiModeration"`, which already matches the existing filename convention.

---

### Task 8 — Create `media_processors/image_vision_processor.py`
**Status:** PENDING
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene
**File:** `media_processors/image_vision_processor.py` (new file)

Create `media_processors/image_vision_processor.py` containing the `ImageVisionProcessor` class. Key requirements:
- Inherits directly from `BaseMediaProcessor` (not from `StubSleepProcessor`).
- This file is the only canonical source for `ImageVisionProcessor` — no other file may define or re-export it.
- Implement the `process_media(self, file_path: str, mime_type: str, caption: str, bot_id: str) -> ProcessingResult` method (body is filled in Tasks 9–12).
- Add module-level `logger = logging.getLogger(__name__)`.

Tasks 9–12 fill in the method body. Tasks 13 and 14 complete the hygiene migration.

---

### Task 9 — Implement event-loop-safe image loading in `ImageVisionProcessor.process_media()`
**Status:** PENDING
**Spec Section:** §3 Image Data Loading (Event-Loop Safe)
**File:** `media_processors/image_vision_processor.py`

Inside `ImageVisionProcessor.process_media()`, read image bytes from `file_path` and base64-encode them. Both the synchronous file I/O and the base64 encoding must be offloaded from the event loop using `asyncio.to_thread(...)`:

```python
import base64

def _load_image_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

base64_image = await asyncio.to_thread(_load_image_base64, file_path)
```

The helper function (or equivalent inline callable) must perform both the read and the encode within the same `to_thread` call to avoid two separate thread dispatches for a single logical operation.

---

### Task 10 — Implement factory-based provider resolution and moderation call in `ImageVisionProcessor.process_media()`
**Status:** PENDING
**Spec Section:** §4 Provider Resolution and Moderation Call, §5 Error Handling Strategy
**File:** `media_processors/image_vision_processor.py`

After obtaining `base64_image` (Task 9), resolve the moderation provider and call it:

```python
from services.model_factory import create_model_provider
from model_providers.image_moderation import ImageModerationProvider

provider = await create_model_provider(bot_id, "media_processing", "image_moderation")
if not isinstance(provider, ImageModerationProvider):
    raise TypeError(f"Expected ImageModerationProvider, got {type(provider)}")
moderation_result = await provider.moderate_image(base64_image, mime_type)
```

Error handling rules (§5):
- Do **not** wrap this block in a `try/except` for fallback content. Any exception from provider resolution or the moderation call must propagate uncaught out of `process_media()` so that `BaseMediaProcessor.process_job()`'s existing `_handle_unhandled_exception` mechanism handles it centrally.
- Do not hardcode model name, provider name, or API key in the processor.

---

### Task 11 — Add normalized `ModerationResult` logging in `ImageVisionProcessor.process_media()`
**Status:** PENDING
**Spec Section:** §6 Logging Requirements
**File:** `media_processors/image_vision_processor.py`

After the successful moderation call (Task 10), log the normalized result at `INFO` level:

```python
logger.info(moderation_result.model_dump())
```

This log captures `flagged`, `categories`, and `category_scores`. It is separate from the raw SDK response log in `OpenAiModerationProvider` (Task 7).

---

### Task 12 — Return stub-style `ProcessingResult` from `ImageVisionProcessor.process_media()`
**Status:** PENDING
**Spec Section:** §7 Processing Result for This Phase
**File:** `media_processors/image_vision_processor.py`

After logging (Task 11), return the preparation-phase stub result:

```python
import os
from infrastructure.models import ProcessingResult

return ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")
```

The moderation payload must **not** be embedded in the message content at this phase. The method body is now complete after Tasks 9–12.

---

### Task 13 — Remove `ImageVisionProcessor` from `media_processors/stub_processors.py`
**Status:** PENDING
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene (rules 2–3)
**File:** `media_processors/stub_processors.py`

Delete the `ImageVisionProcessor` class definition entirely from `stub_processors.py`. Rules:
- Do **not** leave an alias (e.g., `ImageVisionProcessor = image_vision_processor.ImageVisionProcessor`).
- Do **not** add a bridge import or re-export of any kind.
- The remaining classes — `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor` — remain in `stub_processors.py` unchanged (except for the signature update from Task 3).

This task must be performed after Task 8 (new module created) and Task 14 (factory updated) to avoid a broken import window.

---

### Task 14 — Update `media_processors/factory.py` import for `ImageVisionProcessor`
**Status:** PENDING
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene (rules 4)
**File:** `media_processors/factory.py`

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

### Task 15 — Verification: Factory resolution points to `media_processors.image_vision_processor`
**Status:** PENDING
**Spec Section:** §1 Hygiene Rule 5, §8 Verification Checklist item 1
**File:** `tests/test_image_vision_processor.py` (new test file, or added to an existing relevant test file)

Write a test or assertion proving that `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` is defined in the `media_processors.image_vision_processor` module (not `stub_processors`):

```python
from media_processors.factory import PROCESSOR_CLASS_MAP

def test_image_vision_processor_factory_resolution():
    cls = PROCESSOR_CLASS_MAP["ImageVisionProcessor"]
    assert cls.__module__ == "media_processors.image_vision_processor"
```

---

### Task 16 — Verification: `process_media(..., bot_id: str)` signature applied to all processors
**Status:** PENDING
**Spec Section:** §2, §8 Verification Checklist item 2
**File:** `tests/test_image_vision_processor.py` (or same test file as Task 15)

Write a test or assertion verifying the fourth parameter of `process_media` is named `bot_id` with type annotation `str` across all concrete processors and the base class. Affected classes:
- `BaseMediaProcessor` (abstract)
- `StubSleepProcessor` (and inherited subclasses `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`)
- `CorruptMediaProcessor`
- `UnsupportedMediaProcessor`
- `ImageVisionProcessor`

---

### Task 17 — Verification: `moderate_image(base64_image, mime_type)` signature on both provider classes
**Status:** PENDING
**Spec Section:** §4, §8 Verification Checklist item 3
**File:** `tests/test_image_vision_processor.py` (or same test file)

Write a test or assertion verifying that both `ImageModerationProvider.moderate_image` and `OpenAiModerationProvider.moderate_image` accept `base64_image: str` and `mime_type: str` as their parameters (in that order, after `self`).

---

### Task 18 — Verification: Event-loop safety — image loading via `asyncio.to_thread`
**Status:** PENDING
**Spec Section:** §3, §8 Verification Checklist item 4
**File:** `tests/test_image_vision_processor.py`

Write a test that confirms `ImageVisionProcessor.process_media()` offloads file reading and base64 encoding to a thread via `asyncio.to_thread`. The test should mock `asyncio.to_thread` and verify it is called with a callable that performs both operations (i.e., a single thread dispatch handles both read and encode), ensuring the event loop is not blocked by synchronous I/O.

---

### Task 19 — Verification: Moderation SDK payload shape
**Status:** PENDING
**Spec Section:** §4, §8 Verification Checklist item 5
**File:** `tests/test_image_vision_processor.py`

Write a test that verifies the exact input structure sent to `client.moderations.create()` inside `OpenAiModerationProvider.moderate_image()`. The test should mock the OpenAI `AsyncOpenAI` client and capture the `input` argument to confirm it matches:

```python
[{"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}]
```

This proves the data URI is constructed correctly and the SDK receives the exact payload shape specified in §4.
