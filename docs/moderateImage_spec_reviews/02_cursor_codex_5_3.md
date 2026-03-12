# Review: `docs/moderateImage_spec.md`

The spec direction is strong and implementation-ready in most areas (API payload shape, async SDK use, error bubbling strategy, and normalized logging contract are all aligned with the current codebase and OpenAI docs).  
The items below are the only substantial gaps that should be resolved before coding starts.

## Summary Table

| priority | id | title | link | status |
| --- | --- | --- | --- | --- |
| P1 | MIMG-001 | Per-bot moderation config resolution path is not specified | [Jump](#mimg-001) | DONE |
| P1 | MIMG-002 | `ImageVisionProcessor` extraction is missing mandatory factory wiring steps | [Jump](#mimg-002) | DONE |
| P2 | MIMG-003 | Event-loop safety gap for image file read and base64 encoding | [Jump](#mimg-003) | DONE |

---

## MIMG-001

- **priority:** P1
- **id:** MIMG-001
- **title:** Per-bot moderation config resolution path is not specified
- **status:** DONE
- **detailed description:**  
  The spec requires using the bot's `image_moderation` settings, but the implementation path to obtain that config is not defined.  
  In this codebase, `OpenAiModerationProvider` requires a `BaseModelProviderConfig`, and the centralized/consistent way to resolve bot-scoped provider config is `create_model_provider(...)` (or at least `resolve_model_config(...)`).  
  The current spec says "`ImageVisionProcessor` will use `OpenAiModerationProvider`", but does not say how `bot_id -> config` resolution is performed inside media processing. Without an explicit decision, implementers can easily hardcode defaults/env settings and silently violate the core requirement ("use bot settings").  
  **Selected mitigation (Option A):** explicitly mandate factory-based provider resolution via `await create_model_provider(bot_id, "media_processing", "image_moderation")`, assert the result implements `ImageModerationProvider`, and allow resolution/creation failures to bubble to `BaseMediaProcessor.process_job` unhandled-exception flow.

---

## MIMG-002

- **priority:** P1
- **id:** MIMG-002
- **title:** `ImageVisionProcessor` extraction is missing mandatory factory wiring steps
- **status:** DONE
- **detailed description:**  
  The spec says `ImageVisionProcessor` is moved from `media_processors/stub_processors.py` into `media_processors/image_vision_processor.py`, but does not explicitly include the required registration/wiring changes that make workers instantiate the new class.  
  In the current architecture, `MediaProcessingService` resolves processors via `media_processors/factory.py` (`PROCESSOR_CLASS_MAP`). If imports/map entries are not updated exactly, the worker pool will continue using the old stub class and moderation will never execute, while appearing healthy at runtime.  
  **Selected mitigation (Option A):** add an explicit mandatory wiring checklist in the spec: (1) create `media_processors/image_vision_processor.py`, (2) remove `ImageVisionProcessor` from `media_processors/stub_processors.py` completely (no alias bridge), and (3) update `media_processors/factory.py` import and `PROCESSOR_CLASS_MAP` entry to point to the new module.

---

## MIMG-003

- **priority:** P2
- **id:** MIMG-003
- **title:** Event-loop safety gap for image file read and base64 encoding
- **status:** DONE
- **detailed description:**  
  The spec correctly requires async SDK calls, but it does not specify how file I/O and base64 conversion should be handled inside async `process_media()`.  
  Reading potentially large image files and base64-encoding them synchronously in the event loop can stall other coroutines in the worker process, which conflicts with the stated non-blocking intent.  
  **Selected mitigation (Option A):** explicitly require offloading both image file read and base64 encoding from the event loop using `asyncio.to_thread(...)`, keeping the moderation SDK call async as already specified.
