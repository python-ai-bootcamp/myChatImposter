# Implementation Tasks: Media Processor Image Moderation

## Summary Table

| # | Task | Spec Section(s) | Status |
|---|------|-----------------|--------|
| 1 | Create `media_processors/image_vision_processor.py` with `ImageVisionProcessor` inheriting from `BaseMediaProcessor` | §1 Extraction and Strict Module Hygiene | PENDING |
| 2 | Remove `ImageVisionProcessor` from `media_processors/stub_processors.py` | §1 Extraction and Strict Module Hygiene | PENDING |
| 3 | Update `media_processors/factory.py` to import `ImageVisionProcessor` from new module | §1 Extraction and Strict Module Hygiene | PENDING |
| 4 | Update `BaseMediaProcessor.process_media()` abstract signature: `quota_exceeded` → `bot_id` | §2 `process_media()` Contract Update | PENDING |
| 5 | Update `BaseMediaProcessor.process_job()` call site to pass `job.bot_id` instead of `job.quota_exceeded` | §2 `process_media()` Contract Update | PENDING |
| 6 | Update `StubSleepProcessor.process_media()` signature: `quota_exceeded` → `bot_id` | §2 `process_media()` Contract Update | PENDING |
| 7 | Update `CorruptMediaProcessor.process_media()` signature: `quota_exceeded` → `bot_id` | §2 `process_media()` Contract Update | PENDING |
| 8 | Update `UnsupportedMediaProcessor.process_media()` signature: `quota_exceeded` → `bot_id` | §2 `process_media()` Contract Update | PENDING |
| 9 | Implement event-loop-safe image loading in `ImageVisionProcessor.process_media()` via `asyncio.to_thread` | §3 Image Data Loading (Event-Loop Safe) | PENDING |
| 10 | Update `ImageModerationProvider.moderate_image()` abstract signature to accept `(base64_image, mime_type)` | §4 Provider Resolution and Moderation Call | PENDING |
| 11 | Update `OpenAiModerationProvider.moderate_image()` signature to accept `(base64_image, mime_type)` | §4 Provider Resolution and Moderation Call | PENDING |
| 12 | Implement data URI construction inside `OpenAiModerationProvider.moderate_image()` | §4 Provider Resolution and Moderation Call | PENDING |
| 13 | Implement provider resolution in `ImageVisionProcessor` via `create_model_provider` with `ImageModerationProvider` type check | §4 Provider Resolution and Moderation Call | PENDING |
| 14 | Add raw SDK response logging in `OpenAiModerationProvider.moderate_image()` | §6 Logging Requirements | PENDING |
| 15 | Add normalized `ModerationResult` logging in `ImageVisionProcessor.process_media()` | §6 Logging Requirements | PENDING |
| 16 | Return stub-style `ProcessingResult` from `ImageVisionProcessor.process_media()` | §7 Processing Result for This Phase | PENDING |
| 17 | Verify: factory resolution points to `media_processors.image_vision_processor` module | §1 Hygiene Rule 5, §8 Verification Checklist | PENDING |
| 18 | Verify: `process_media(..., bot_id)` signature applied to base class and all concrete processors | §8 Verification Checklist | PENDING |
| 19 | Verify: `moderate_image(base64_image, mime_type)` signatures on both provider classes | §8 Verification Checklist | PENDING |
| 20 | Verify: image bytes read and base64-encoded via `asyncio.to_thread(...)` | §8 Verification Checklist | PENDING |
| 21 | Verify: moderation payload shape matches `[{"type": "image_url", "image_url": {"url": data_uri}}]` | §8 Verification Checklist | PENDING |

---

## Task Details

### Task 1 — Create `media_processors/image_vision_processor.py`
**Status:** PENDING
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene

Create a new file `media_processors/image_vision_processor.py` containing the `ImageVisionProcessor` class. The class must inherit directly from `BaseMediaProcessor` (not from `StubSleepProcessor`). This is the only canonical source for `ImageVisionProcessor` going forward. The class will implement `process_media()` with the new contract signature (see Tasks 9, 13, 15, 16 for the method body).

---

### Task 2 — Remove `ImageVisionProcessor` from `stub_processors.py`
**Status:** PENDING
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene (rules 2, 3)

Delete the `ImageVisionProcessor` class definition from `media_processors/stub_processors.py`. Do not leave any alias, re-export, or bridge import for `ImageVisionProcessor` in that file. The remaining stub classes (`StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`) stay untouched structurally.

---

### Task 3 — Update `factory.py` import to new module
**Status:** PENDING
**Spec Section:** §1 `ImageVisionProcessor` Extraction and Strict Module Hygiene (rule 4)

In `media_processors/factory.py`, change the `ImageVisionProcessor` import from `media_processors.stub_processors` to `media_processors.image_vision_processor`. The `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` entry must reference the class from the new module.

---

### Task 4 — Update `BaseMediaProcessor.process_media()` abstract signature
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (abstract method)

In `media_processors/base.py`, change the `process_media` abstract method signature from `(self, file_path: str, mime_type: str, caption: str, quota_exceeded: Optional[bool])` to `(self, file_path: str, mime_type: str, caption: str, bot_id: str)`. Remove the `Optional` import if no longer needed.

---

### Task 5 — Update `process_job()` call site in `BaseMediaProcessor`
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (base class call site)

In `media_processors/base.py`, within `BaseMediaProcessor.process_job()`, change the fourth argument in the `self.process_media(...)` call from `job.quota_exceeded` to `job.bot_id`.

---

### Task 6 — Update `StubSleepProcessor.process_media()` signature
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)

In `media_processors/stub_processors.py`, change `StubSleepProcessor.process_media()` parameter from `quota_exceeded: Optional[bool]` to `bot_id: str`. The method body remains unchanged — `bot_id` is ignored by this processor. Its subclasses (`AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`) inherit the updated signature automatically.

---

### Task 7 — Update `CorruptMediaProcessor.process_media()` signature
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)

In `media_processors/error_processors.py`, change `CorruptMediaProcessor.process_media()` parameter from `quota_exceeded: Optional[bool]` to `bot_id: str`. The method body remains unchanged — `bot_id` is ignored.

---

### Task 8 — Update `UnsupportedMediaProcessor.process_media()` signature
**Status:** PENDING
**Spec Section:** §2 `process_media()` Contract Update (affected subclasses)

In `media_processors/error_processors.py`, change `UnsupportedMediaProcessor.process_media()` parameter from `quota_exceeded: Optional[bool]` to `bot_id: str`. The method body remains unchanged — `bot_id` is ignored.

---

### Task 9 — Implement event-loop-safe image loading
**Status:** PENDING
**Spec Section:** §3 Image Data Loading (Event-Loop Safe)

Inside `ImageVisionProcessor.process_media()`, read image bytes from `file_path` and base64-encode them. Both the file I/O and the base64 encoding must be offloaded from the event loop using `asyncio.to_thread(...)` to avoid blocking.

---

### Task 10 — Update `ImageModerationProvider.moderate_image()` abstract signature
**Status:** PENDING
**Spec Section:** §4 Provider Resolution and Moderation Call (provider contract update)

In `model_providers/image_moderation.py`, change the `ImageModerationProvider.moderate_image()` abstract method signature from `(self, image_url: str)` to `(self, base64_image: str, mime_type: str)`. The caller will pass raw base64 image data and the MIME type; the provider is responsible for constructing the data URI internally.

---

### Task 11 — Update `OpenAiModerationProvider.moderate_image()` signature and data URI construction
**Status:** PENDING
**Spec Section:** §4 Provider Resolution and Moderation Call (provider contract update, input payload shape)

In `model_providers/openAiModeration.py`, update the `moderate_image()` method signature from `(self, image_url: str)` to `(self, base64_image: str, mime_type: str)`. Inside the method, construct the data URI as `f"data:{mime_type};base64,{base64_image}"` and use it in the moderation API input structure.

---

### Task 12 — Ensure moderation input payload shape
**Status:** PENDING
**Spec Section:** §4 Provider Resolution and Moderation Call (input payload shape)

In `OpenAiModerationProvider.moderate_image()`, ensure the input sent to the OpenAI SDK `client.moderations.create()` is exactly: `[{"type": "image_url", "image_url": {"url": data_uri}}]`, where `data_uri` is the internally constructed data URI from Task 11. This is already the current structure but must be verified/maintained after the signature change.

---

### Task 13 — Implement provider resolution in `ImageVisionProcessor`
**Status:** PENDING
**Spec Section:** §4 Provider Resolution and Moderation Call (factory-based resolution, validation)

In `ImageVisionProcessor.process_media()`, resolve the moderation provider via `await create_model_provider(bot_id, "media_processing", "image_moderation")`. Validate that the returned provider is an instance of `ImageModerationProvider`. Call `provider.moderate_image(base64_image, mime_type)` and capture the `ModerationResult`. Do not hardcode provider name, model, or API key in the processor.

---

### Task 14 — Add raw SDK response logging in `OpenAiModerationProvider`
**Status:** PENDING
**Spec Section:** §6 Logging Requirements

In `OpenAiModerationProvider.moderate_image()`, after the SDK call completes, log the raw response via `logger.info(response.model_dump())` at `INFO` level. This provides full audit coverage of the unfiltered API response (including `category_applied_input_types` which is not captured in `ModerationResult`).

---

### Task 15 — Add normalized `ModerationResult` logging in `ImageVisionProcessor`
**Status:** PENDING
**Spec Section:** §6 Logging Requirements

In `ImageVisionProcessor.process_media()`, after a successful moderation call, log the normalized result via `logger.info(moderation_result.model_dump())` at `INFO` level.

---

### Task 16 — Return stub-style `ProcessingResult`
**Status:** PENDING
**Spec Section:** §7 Processing Result for This Phase

At the end of `ImageVisionProcessor.process_media()`, return `ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")`. Do not embed moderation payload in the message content. This maintains backward-compatible message format for this preparation phase.

---

### Task 17 — Verification: Factory resolution points to new module
**Status:** PENDING
**Spec Section:** §1 Hygiene Rule 5, §8 Verification Checklist item 1

Write a test or assertion that proves `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` resolves to a class defined in the `media_processors.image_vision_processor` module (not `stub_processors`). This enforces the extraction hygiene guarantee.

---

### Task 18 — Verification: `process_media(..., bot_id)` contract applied everywhere
**Status:** PENDING
**Spec Section:** §8 Verification Checklist item 2

Write a test or assertion verifying that `BaseMediaProcessor.process_media` and all concrete subclasses (`StubSleepProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `ImageVisionProcessor`) have the updated `(file_path, mime_type, caption, bot_id)` signature with `bot_id: str` as the fourth parameter.

---

### Task 19 — Verification: Provider `moderate_image` signatures updated
**Status:** PENDING
**Spec Section:** §8 Verification Checklist item 3

Write a test or assertion verifying that both `ImageModerationProvider.moderate_image` and `OpenAiModerationProvider.moderate_image` accept `(base64_image: str, mime_type: str)` parameters.

---

### Task 20 — Verification: Event-loop safety of image loading
**Status:** PENDING
**Spec Section:** §8 Verification Checklist item 4

Write a test or assertion verifying that `ImageVisionProcessor.process_media()` offloads file reading and base64 encoding to a thread via `asyncio.to_thread(...)`, ensuring the event loop is not blocked by synchronous I/O.

---

### Task 21 — Verification: Moderation payload shape
**Status:** PENDING
**Spec Section:** §8 Verification Checklist item 5

Write a test or assertion verifying that the input sent to the OpenAI moderation SDK call matches the exact structure `[{"type": "image_url", "image_url": {"url": data_uri}}]` where `data_uri` follows the `data:{mime_type};base64,{base64_image}` format.
