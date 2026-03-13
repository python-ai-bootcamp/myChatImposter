# Image Moderation Spec - Implementation Tasks

| # | Task | Spec Section(s) | Status |
|---|---|---|---|
| 1 | Extract `ImageVisionProcessor` into dedicated module inheriting from `BaseMediaProcessor` | Technical Details §1 | PENDING |
| 2 | Remove `ImageVisionProcessor` from `stub_processors.py` with no bridge alias/re-export | Technical Details §1 | PENDING |
| 3 | Rewire factory imports/map to resolve `ImageVisionProcessor` from new module | Technical Details §1 | PENDING |
| 4 | Migrate base `process_media()` abstract contract to `(file_path, mime_type, caption, bot_id)` | Technical Details §2 | PENDING |
| 5 | Update `BaseMediaProcessor.process_job()` to pass `job.bot_id` instead of `job.quota_exceeded` | Technical Details §2 | PENDING |
| 6 | Update `StubSleepProcessor` contract signature (propagates to audio/video/document stubs) | Technical Details §2 | PENDING |
| 7 | Update `CorruptMediaProcessor` and `UnsupportedMediaProcessor` signatures while preserving caption behavior | Technical Details §2 | PENDING |
| 8 | Implement new `ImageVisionProcessor.process_media(..., bot_id)` signature | Technical Details §2, §1 | PENDING |
| 9 | Implement event-loop-safe image file read + base64 conversion via `asyncio.to_thread(...)` | Technical Details §3 | PENDING |
| 10 | Resolve moderation provider via `create_model_provider(bot_id, "media_processing", "image_moderation")` and type-check provider | Technical Details §4 | PENDING |
| 11 | Update `ImageModerationProvider` method contract to `moderate_image(base64_image, mime_type)` | Technical Details §4 | PENDING |
| 12 | Update `OpenAiModerationProvider` method contract to `moderate_image(base64_image, mime_type)` | Technical Details §4 | PENDING |
| 13 | Build data URI in provider and send exact SDK payload shape for image moderation | Technical Details §4, External Resource | PENDING |
| 14 | Keep provider response normalization to `ModerationResult(flagged, categories, category_scores)` | Technical Details §4 | PENDING |
| 15 | Preserve error bubbling from `ImageVisionProcessor` to centralized base handler (no local fallback catch) | Technical Details §5 | PENDING |
| 16 | Add INFO log for raw moderation SDK response in `OpenAiModerationProvider` | Technical Details §6 | PENDING |
| 17 | Add INFO log for normalized moderation result in `ImageVisionProcessor` | Technical Details §6 | PENDING |
| 18 | Return required stub-style `ProcessingResult` message from `ImageVisionProcessor` | Technical Details §7 | PENDING |
| 19 | Verify/ensure defaults for new bot configs use `openAiModeration` + `omni-moderation-latest` across default builders | Requirements, `config_models.py` alignment | PENDING |
| 20 | Add verification evidence for all checklist items (factory wiring, signature migration, provider interface, to-thread usage, payload shape) | Technical Details §8 | PENDING |

1. **[PENDING] Extract `ImageVisionProcessor` into `media_processors/image_vision_processor.py`.**  
   Rooted in Technical Details §1. Create the canonical `ImageVisionProcessor` implementation in its own module and ensure it inherits directly from `BaseMediaProcessor`.

2. **[PENDING] Remove `ImageVisionProcessor` from `media_processors/stub_processors.py`.**  
   Rooted in Technical Details §1 (strict hygiene rules 2-3). Fully delete the class from `stub_processors.py` and do not leave compatibility alias imports or re-exports.

3. **[PENDING] Update `media_processors/factory.py` to import/map from the new module.**  
   Rooted in Technical Details §1 (strict hygiene rule 4). Update `PROCESSOR_CLASS_MAP["ImageVisionProcessor"]` to point to class from `media_processors.image_vision_processor`.

4. **[PENDING] Update `BaseMediaProcessor` abstract contract to use `bot_id` instead of `quota_exceeded`.**  
   Rooted in Technical Details §2. Change abstract method signature to `process_media(file_path, mime_type, caption, bot_id)` and remove `quota_exceeded` from the processing contract.

5. **[PENDING] Update `BaseMediaProcessor.process_job()` call site to pass `job.bot_id`.**  
   Rooted in Technical Details §2 base call-site requirement. Replace fourth argument in call to `self.process_media(...)` from `job.quota_exceeded` to `job.bot_id`.

6. **[PENDING] Update `StubSleepProcessor` signature to match new contract.**  
   Rooted in Technical Details §2 affected subclasses. Change `StubSleepProcessor.process_media(...)` signature to receive `bot_id: str`; inherited stubs (`AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`) follow automatically.

7. **[PENDING] Update error processor signatures while preserving caption behavior.**  
   Rooted in Technical Details §2 and contract rule to keep caption support. Change `CorruptMediaProcessor` and `UnsupportedMediaProcessor` signatures to `(..., bot_id: str)` without altering existing caption-based content composition.

8. **[PENDING] Implement `ImageVisionProcessor.process_media(..., bot_id)` with new contract.**  
   Rooted in Technical Details §1 and §2. Define method in extracted processor module and wire full moderation flow around the new signature.

9. **[PENDING] Add event-loop-safe image byte loading and base64 conversion.**  
   Rooted in Technical Details §3 and Requirements (moderate actual image bytes). Read bytes from `file_path` and encode to raw base64 string using `asyncio.to_thread(...)` so file I/O and encoding are offloaded from the event loop.

10. **[PENDING] Resolve moderation provider through model factory using bot config.**  
    Rooted in Technical Details §4 and Requirements (bot-specific authoritative config; no hardcoding). Call `await create_model_provider(bot_id, "media_processing", "image_moderation")`, validate result is `ImageModerationProvider`, and avoid hardcoded provider/model/api-key logic in processor.

11. **[PENDING] Update `ImageModerationProvider` interface to `(base64_image, mime_type)`.**  
    Rooted in Technical Details §4 provider contract update. Change abstract method signature to `moderate_image(base64_image: str, mime_type: str) -> ModerationResult`.

12. **[PENDING] Update `OpenAiModerationProvider` interface to `(base64_image, mime_type)`.**  
    Rooted in Technical Details §4 provider contract update. Change concrete method signature to match interface while keeping async SDK usage.

13. **[PENDING] Build provider-side data URI and enforce exact moderation payload shape.**  
    Rooted in Technical Details §4 plus OpenAI moderation docs. Construct `data_uri = f"data:{mime_type};base64,{base64_image}"` and pass exact input payload `[{"type": "image_url", "image_url": {"url": data_uri}}]` to `client.moderations.create(...)`.

14. **[PENDING] Preserve normalized `ModerationResult` fields for this preparation phase.**  
    Rooted in Technical Details §4 return handling. Ensure provider returns normalized `ModerationResult` containing `flagged`, `categories`, and `category_scores` (without adding policy enforcement payload usage in this phase).

15. **[PENDING] Keep error handling centralized by letting processor exceptions bubble up.**  
    Rooted in Technical Details §5. Do not catch moderation/provider/config resolution failures inside `ImageVisionProcessor.process_media()` for manual fallback; allow `BaseMediaProcessor.process_job` centralized fallback path to handle them.

16. **[PENDING] Log raw moderation SDK response at INFO in `OpenAiModerationProvider`.**  
    Rooted in Technical Details §6. Add `logger.info(response.model_dump())` after moderation API call for audit/debug visibility.

17. **[PENDING] Log normalized moderation result at INFO in `ImageVisionProcessor`.**  
    Rooted in Technical Details §6. Log `logger.info(moderation_result.model_dump())` on successful moderation.

18. **[PENDING] Return required stub-style `ProcessingResult` for image processing output.**  
    Rooted in Technical Details §7 and Overview scope. Return `ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")` without embedding moderation payload in user-facing content.

19. **[PENDING] Verify/align default config paths for moderation provider/model.**  
    Rooted in Requirements (default bot configuration requirement). Confirm and adjust if needed so new/default bot config generation paths use `openAiModeration` and `omni-moderation-latest` via `config_models.py` defaults and bot default builders.

20. **[PENDING] Add explicit verification evidence for all checklist items.**  
    Rooted in Technical Details §8. Add tests/assertions (or equivalent proofs) for: factory points to new module, full contract migration to `bot_id`, provider interface signatures updated, `asyncio.to_thread(...)` usage, and exact SDK payload structure.
