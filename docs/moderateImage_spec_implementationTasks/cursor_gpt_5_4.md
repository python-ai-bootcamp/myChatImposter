# Implementation Tasks: Media Processor Image Moderation

All tasks below are `PENDING` because this document is for implementation planning only.

Out of scope per the spec overview: moderation policy enforcement, image understanding/generation, and rollout-safety or migration work for missing/invalid `image_moderation` bot config.

## Summary Table

| ID | Task | Spec Root(s) | Status |
|---|---|---|---|
| 1 | Lock down default `image_moderation` config values for new/default bot configurations | Requirements, Relevant Background Information | PENDING |
| 2 | Extract `ImageVisionProcessor` into its own canonical module and remove it from stub processors | Technical Details §1 | PENDING |
| 3 | Rewire processor factory resolution to the new `ImageVisionProcessor` module | Technical Details §1, §8 | PENDING |
| 4 | Migrate the media-processor contract from `quota_exceeded` to `bot_id` | Technical Details §2, §8 | PENDING |
| 5 | Implement event-loop-safe image byte loading and base64 encoding in `ImageVisionProcessor` | Requirements, Technical Details §3, §8 | PENDING |
| 6 | Update the image moderation provider interface to accept `(base64_image, mime_type)` | Technical Details §4, §8 | PENDING |
| 7 | Update `OpenAiModerationProvider` to build the data URI, call the async SDK, normalize results, and log raw output | Requirements, Technical Details §4, §6, §8 | PENDING |
| 8 | Resolve the moderation provider inside `ImageVisionProcessor`, validate its type, call moderation, log normalized output, and return the stub `ProcessingResult` | Requirements, Technical Details §4, §5, §6, §7 | PENDING |
| 9 | Preserve centralized failure handling by letting moderation/config/provider exceptions bubble to `BaseMediaProcessor` | Technical Details §5 | PENDING |
| 10 | Add verification for default config seeding of `openAiModeration` + `omni-moderation-latest` | Requirements | PENDING |
| 11 | Add verification that factory resolution points to `media_processors.image_vision_processor` | Technical Details §1, §8 | PENDING |
| 12 | Add verification that every processor uses the new `process_media(..., bot_id)` contract | Technical Details §2, §8 | PENDING |
| 13 | Add verification that moderation provider signatures use `(base64_image, mime_type)` | Technical Details §4, §8 | PENDING |
| 14 | Add verification that image loading/base64 work is offloaded via `asyncio.to_thread(...)` | Technical Details §3, §8 | PENDING |
| 15 | Add verification that the OpenAI moderation payload matches the required `image_url` data-URI shape | Technical Details §4, §8 | PENDING |

## Implementation Tasks

1. **[PENDING] Enforce default bot-level `image_moderation` configuration sources and values.**  
   Rooted in the Requirements section that makes bot-specific `image_moderation` config authoritative and requires new/default bot configs to default to `openAiModeration` with `omni-moderation-latest`. Review and correct the default configuration surfaces in `config_models.py`, `routers/bot_management.py`, and `routers/bot_ui.py` so newly created bots and default templates consistently seed the moderation tier with those exact values and do not rely on a processor-side fallback.

2. **[PENDING] Create `media_processors/image_vision_processor.py` as the only canonical source of `ImageVisionProcessor`.**  
   Rooted in Technical Details §1. Extract `ImageVisionProcessor` from `media_processors/stub_processors.py` into a new `media_processors/image_vision_processor.py` module, and make the extracted class inherit directly from `BaseMediaProcessor` rather than `StubSleepProcessor`.

3. **[PENDING] Remove `ImageVisionProcessor` completely from `media_processors/stub_processors.py` without bridge imports.**  
   Rooted in Technical Details §1 hygiene rules 2 and 3. Leave `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, and `DocumentProcessor` in place, but remove the image processor class and avoid any alias or re-export that would leave `stub_processors.py` acting as an alternate source of truth.

4. **[PENDING] Update processor factory wiring to resolve the extracted image processor from its new module.**  
   Rooted in Technical Details §1 rule 4 and the Verification Checklist. Update `media_processors/factory.py` so its import path and `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` both point at `media_processors.image_vision_processor.ImageVisionProcessor`.

5. **[PENDING] Change the shared media-processing contract from `process_media(..., quota_exceeded)` to `process_media(..., bot_id)`.**  
   Rooted in Technical Details §2. Update `BaseMediaProcessor.process_job()` in `media_processors/base.py` to pass `job.bot_id`, update the abstract method signature in `BaseMediaProcessor`, and update all concrete processor implementations that currently follow the old signature: `StubSleepProcessor` and its subclasses, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, and the extracted `ImageVisionProcessor`. Keep `caption` support intact for the error processors.

6. **[PENDING] Implement event-loop-safe image byte loading and raw base64 preparation inside `ImageVisionProcessor.process_media()`.**  
   Rooted in the Requirements section and Technical Details §3. Read the actual bytes from `file_path`, convert them into a raw base64 string, and offload both the file read and the encoding work through `asyncio.to_thread(...)` so the processor does not block the event loop.

7. **[PENDING] Update the moderation provider contract to receive raw base64 image data plus MIME type.**  
   Rooted in Technical Details §4. Change `ImageModerationProvider.moderate_image()` in `model_providers/image_moderation.py` from `moderate_image(image_url: str)` to `moderate_image(base64_image: str, mime_type: str)`, while preserving `ModerationResult` as the normalized return type carrying `flagged`, `categories`, and `category_scores`.

8. **[PENDING] Refactor `OpenAiModerationProvider` to build the required data URI internally and call the async OpenAI moderation API with the exact payload shape.**  
   Rooted in Requirements plus Technical Details §4. In `model_providers/openAiModeration.py`, update `moderate_image()` to accept `(base64_image, mime_type)`, construct `data_uri = f"data:{mime_type};base64,{base64_image}"`, call the async `openai` SDK directly (without LangChain), and send the exact moderation input shape `[{"type": "image_url", "image_url": {"url": data_uri}}]`.

9. **[PENDING] Normalize the OpenAI moderation response and log the raw SDK output at `INFO` level.**  
   Rooted in Technical Details §4 return handling and §6 logging requirements. In `OpenAiModerationProvider.moderate_image()`, log `response.model_dump()` via Python logging, then map the first moderation result into `ModerationResult(flagged, categories, category_scores)` while intentionally omitting `category_applied_input_types` from the normalized model for this phase.

10. **[PENDING] Implement runtime provider resolution in `ImageVisionProcessor` using the bot's own `image_moderation` tier, then log the normalized moderation result and return the stub processing output.**  
   Rooted in the Requirements section plus Technical Details §4, §6, and §7. Inside `ImageVisionProcessor.process_media()`, call `await create_model_provider(bot_id, "media_processing", "image_moderation")`, validate that the resolved object implements `ImageModerationProvider`, invoke `moderate_image(base64_image, mime_type)`, log `moderation_result.model_dump()` at `INFO`, and return `ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")` without embedding moderation data in the user-facing message.

11. **[PENDING] Preserve the centralized failure path by not adding local moderation fallback handling inside `ImageVisionProcessor`.**  
   Rooted in Technical Details §5. Keep moderation/provider/config-resolution failures uncaught inside `ImageVisionProcessor.process_media()` so they bubble into `BaseMediaProcessor.process_job()` and continue using the existing `_handle_unhandled_exception` safety net.

12. **[PENDING] Add verification that new/default bot configuration flows seed `image_moderation` with `openAiModeration` and `omni-moderation-latest`.**  
   Rooted in the Requirements section. Add or extend tests around configuration defaults and bot creation/template flows so the moderation tier is proven to come from bot config with the required default provider/model values.

13. **[PENDING] Add verification that `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` resolves to the new module.**  
   Rooted in Technical Details §1 rule 5 and Verification Checklist item 1. Add a targeted test or assertion proving that factory resolution points to `media_processors.image_vision_processor` and not to `media_processors.stub_processors`.

14. **[PENDING] Add verification that the `process_media(..., bot_id)` contract is applied to the base class and all concrete processors.**  
   Rooted in Technical Details §2 and Verification Checklist item 2. Add a test or equivalent proof that `BaseMediaProcessor`, `StubSleepProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, and `ImageVisionProcessor` all expose the updated signature with `bot_id` as the fourth argument.

15. **[PENDING] Add verification that the moderation provider interfaces use `(base64_image, mime_type)` and that the OpenAI payload shape is correct.**  
   Rooted in Technical Details §4 and Verification Checklist items 3 and 5. Add tests or assertions that prove both `ImageModerationProvider.moderate_image()` and `OpenAiModerationProvider.moderate_image()` accept `(base64_image, mime_type)`, and that the actual SDK input sent by the OpenAI moderation provider matches `[{"type": "image_url", "image_url": {"url": data_uri}}]`.

16. **[PENDING] Add verification that `ImageVisionProcessor` uses `asyncio.to_thread(...)` for image loading/base64 work.**  
   Rooted in Technical Details §3 and Verification Checklist item 4. Add a test or equivalent proof that the image-read and base64-encode path is explicitly offloaded from the event loop through `asyncio.to_thread(...)`.
