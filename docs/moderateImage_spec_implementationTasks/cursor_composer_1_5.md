# Implementation Tasks: Media Processor Image Moderation

## Summary Table

| # | Task | Spec Section(s) | Status |
|---|------|-----------------|--------|
| 1 | Create `media_processors/image_vision_processor.py` with `ImageVisionProcessor` inheriting from `BaseMediaProcessor` | §1 Extraction and Strict Module Hygiene | PENDING |
| 2 | Remove `ImageVisionProcessor` from `media_processors/stub_processors.py` completely (no alias/re-export) | §1 Extraction and Strict Module Hygiene | PENDING |
| 3 | Update `media_processors/factory.py` import and `PROCESSOR_CLASS_MAP` to new module | §1 Extraction and Strict Module Hygiene | PENDING |
| 4 | Update `BaseMediaProcessor.process_media()` abstract signature: `quota_exceeded` → `bot_id` | §2 `process_media()` Contract Update | PENDING |
| 5 | Update `BaseMediaProcessor.process_job()` call site to pass `job.bot_id` instead of `job.quota_exceeded` | §2 `process_media()` Contract Update | PENDING |
| 6 | Update `StubSleepProcessor` and all subclasses: `process_media()` signature `quota_exceeded` → `bot_id` | §2 `process_media()` Contract Update | PENDING |
| 7 | Update `CorruptMediaProcessor` and `UnsupportedMediaProcessor`: `process_media()` signature `quota_exceeded` → `bot_id` | §2 `process_media()` Contract Update | PENDING |
| 8 | Implement event-loop-safe image loading in `ImageVisionProcessor.process_media()` via `asyncio.to_thread(...)` | §3 Image Data Loading (Event-Loop Safe) | PENDING |
| 9 | Update `ImageModerationProvider.moderate_image()` abstract signature to `(base64_image: str, mime_type: str)` | §4 Provider Resolution and Moderation Call | PENDING |
| 10 | Update `OpenAiModerationProvider.moderate_image()`: signature `(base64_image, mime_type)`, construct data URI internally, send `[{"type": "image_url", "image_url": {"url": data_uri}}]` | §4 Provider Resolution and Moderation Call | PENDING |
| 11 | Implement provider resolution in `ImageVisionProcessor` via `create_model_provider(bot_id, "media_processing", "image_moderation")` with `ImageModerationProvider` type check | §4 Provider Resolution and Moderation Call | PENDING |
| 12 | Ensure no exception catching in `ImageVisionProcessor.process_media()` for moderation/provider failures — let bubble to `BaseMediaProcessor.process_job` | §5 Error Handling Strategy | PENDING |
| 13 | Add raw SDK response logging via `logger.info(response.model_dump())` in `OpenAiModerationProvider.moderate_image()` | §6 Logging Requirements | PENDING |
| 14 | Add normalized `ModerationResult` logging via `logger.info(moderation_result.model_dump())` in `ImageVisionProcessor.process_media()` | §6 Logging Requirements | PENDING |
| 15 | Return stub-style `ProcessingResult(content=f"[Transcripted image multimedia message with guid='{...}']")` from `ImageVisionProcessor.process_media()` | §7 Processing Result for This Phase | PENDING |
| 16 | Verification: `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` points to `media_processors.image_vision_processor` module | §1 Rule 5, §8 Verification Checklist | PENDING |
| 17 | Verification: `process_media(..., bot_id)` signature applied to base and all concrete processors | §8 Verification Checklist | PENDING |
| 18 | Verification: `moderate_image(base64_image, mime_type)` signatures on both provider classes | §8 Verification Checklist | PENDING |
| 19 | Verification: image bytes read and base64-encoded via `asyncio.to_thread(...)` | §8 Verification Checklist | PENDING |
| 20 | Verification: moderation payload shape matches `[{"type": "image_url", "image_url": {"url": data_uri}}]` | §8 Verification Checklist | PENDING |

---

## Task Details

### Task 1 — Create `media_processors/image_vision_processor.py`
**Status:** PENDING  
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene

Create `media_processors/image_vision_processor.py` as the canonical source for `ImageVisionProcessor`. The class must inherit directly from `BaseMediaProcessor` (not `StubSleepProcessor`). Implement `process_media()` with the new contract and moderation flow (Tasks 8, 11, 14, 15).

---

### Task 2 — Remove `ImageVisionProcessor` from `stub_processors.py`
**Status:** PENDING  
**Spec Section:** §1 Extraction and Strict Module Hygiene (rules 2, 3)

Delete the `ImageVisionProcessor` class from `media_processors/stub_processors.py`. Do not add any alias, re-export, or bridge import. Leave `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, and `DocumentProcessor` unchanged.

---

### Task 3 — Update `factory.py` import and map
**Status:** PENDING  
**Spec Section:** §1 Extraction and Strict Module Hygiene (rule 4)

In `media_processors/factory.py`, import `ImageVisionProcessor` from `media_processors.image_vision_processor` instead of `media_processors.stub_processors`. Ensure `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` references the class from the new module.

---

### Task 4 — Update `BaseMediaProcessor.process_media()` abstract signature
**Status:** PENDING  
**Spec Section:** §2 `process_media()` Contract Update (abstract method)

In `media_processors/base.py`, change the abstract `process_media` signature from `(file_path, mime_type, caption, quota_exceeded: Optional[bool])` to `(file_path, mime_type, caption, bot_id: str)`. Adjust `Optional` import if no longer needed.

---

### Task 5 — Update `BaseMediaProcessor.process_job()` call site
**Status:** PENDING  
**Spec Section:** §2 `process_media()` Contract Update (base class call site)

In `media_processors/base.py`, in `BaseMediaProcessor.process_job`, replace the fourth argument in the `self.process_media(...)` call from `job.quota_exceeded` with `job.bot_id`.

---

### Task 6 — Update `StubSleepProcessor` and subclasses
**Status:** PENDING  
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)

In `media_processors/stub_processors.py`, change `StubSleepProcessor.process_media()` from `quota_exceeded: Optional[bool]` to `bot_id: str`. Subclasses `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor` inherit the new signature. Keep logic unchanged; `bot_id` is ignored.

---

### Task 7 — Update `CorruptMediaProcessor` and `UnsupportedMediaProcessor`
**Status:** PENDING  
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)

In `media_processors/error_processors.py`, change both `CorruptMediaProcessor.process_media()` and `UnsupportedMediaProcessor.process_media()` from `quota_exceeded: Optional[bool]` to `bot_id: str`. Keep `caption` handling. `bot_id` is ignored.

---

### Task 8 — Event-loop-safe image loading
**Status:** PENDING  
**Spec Section:** §3 Image Data Loading (Event-Loop Safe)

In `ImageVisionProcessor.process_media()`, read image bytes from `file_path`, base64-encode them, and offload both operations using `asyncio.to_thread(...)` so the event loop is not blocked.

---

### Task 9 — Update `ImageModerationProvider.moderate_image()` abstract signature
**Status:** PENDING  
**Spec Section:** §4 Provider Resolution and Moderation Call (provider contract)

In `model_providers/image_moderation.py`, change `ImageModerationProvider.moderate_image()` from `(self, image_url: str)` to `(self, base64_image: str, mime_type: str)`. Callers pass raw base64 and MIME type; the provider builds the data URI internally.

---

### Task 10 — Update `OpenAiModerationProvider.moderate_image()`
**Status:** PENDING  
**Spec Section:** §4 Provider Resolution and Moderation Call (provider contract, input payload shape)

In `model_providers/openAiModeration.py`, update `moderate_image()` to accept `(base64_image: str, mime_type: str)`. Construct `data_uri = f"data:{mime_type};base64,{base64_image}"` and send `[{"type": "image_url", "image_url": {"url": data_uri}}]` to the SDK. Preserve normalized `ModerationResult` with `flagged`, `categories`, and `category_scores` (omit `category_applied_input_types`).

---

### Task 11 — Provider resolution in `ImageVisionProcessor`
**Status:** PENDING  
**Spec Section:** §4 Provider Resolution and Moderation Call, Requirements (bot-specific config)

In `ImageVisionProcessor.process_media()`, resolve the provider with `await create_model_provider(bot_id, "media_processing", "image_moderation")`. Check that the result implements `ImageModerationProvider`. Call `provider.moderate_image(base64_image, mime_type)` and capture `ModerationResult`. Do not hardcode provider, model, or API key.

---

### Task 12 — Error handling: no local catch in `ImageVisionProcessor`
**Status:** PENDING  
**Spec Section:** §5 Error Handling Strategy

Do not wrap moderation or provider resolution in try/except inside `ImageVisionProcessor.process_media()`. Let exceptions propagate to `BaseMediaProcessor.process_job`, which uses `_handle_unhandled_exception` for fallback behavior.

---

### Task 13 — Raw SDK response logging
**Status:** PENDING  
**Spec Section:** §6 Logging Requirements

In `OpenAiModerationProvider.moderate_image()`, after the SDK call, log the raw response at INFO via `logger.info(response.model_dump())`.

---

### Task 14 — Normalized moderation result logging
**Status:** PENDING  
**Spec Section:** §6 Logging Requirements

In `ImageVisionProcessor.process_media()`, after a successful moderation call, log the result at INFO via `logger.info(moderation_result.model_dump())`.

---

### Task 15 — Stub-style `ProcessingResult`
**Status:** PENDING  
**Spec Section:** §7 Processing Result for This Phase

In `ImageVisionProcessor.process_media()`, return `ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")`. Do not add moderation data to the message content.

---

### Task 16 — Verification: Factory resolution
**Status:** PENDING  
**Spec Section:** §1 Rule 5, §8 Verification Checklist item 1

Add a test or assertion that `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` resolves to a class defined in `media_processors.image_vision_processor` (not `stub_processors`).

---

### Task 17 — Verification: `process_media(..., bot_id)` contract
**Status:** PENDING  
**Spec Section:** §8 Verification Checklist item 2

Add a test or assertion that `BaseMediaProcessor.process_media` and all concrete processors (`StubSleepProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `ImageVisionProcessor`) use the new `(file_path, mime_type, caption, bot_id)` signature with `bot_id: str` as the fourth parameter.

---

### Task 18 — Verification: Provider `moderate_image` signatures
**Status:** PENDING  
**Spec Section:** §8 Verification Checklist item 3

Add a test or assertion that `ImageModerationProvider.moderate_image` and `OpenAiModerationProvider.moderate_image` both accept `(base64_image: str, mime_type: str)`.

---

### Task 19 — Verification: Event-loop safety
**Status:** PENDING  
**Spec Section:** §8 Verification Checklist item 4

Add a test or assertion that `ImageVisionProcessor.process_media()` uses `asyncio.to_thread(...)` for file read and base64 encoding, so the event loop is not blocked by synchronous I/O.

---

### Task 20 — Verification: Moderation payload shape
**Status:** PENDING  
**Spec Section:** §8 Verification Checklist item 5

Add a test or assertion that the input passed to the OpenAI moderation SDK has the form `[{"type": "image_url", "image_url": {"url": data_uri}}]` with `data_uri = f"data:{mime_type};base64,{base64_image}"`.
