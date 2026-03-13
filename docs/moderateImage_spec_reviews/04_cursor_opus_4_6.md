# Spec Review: Media Processor Image Moderation

**Spec File:** `docs/moderateImage_spec.md`  
**Reviewer:** Cursor Opus 4.6 (high-thinking)  
**Date:** 2026-03-13  

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| P3 | OP-001 | Extracted `ImageVisionProcessor` parent class not explicitly stated | [Details](#op-001) | DONE |

---

## Overall Assessment

**The spec is solid and implementation-ready.** After thorough cross-referencing of the spec against all relevant source files, the OpenAI Moderation API documentation, and the three prior review rounds, no P1 or P2 issues remain.

The spec has been iteratively hardened through three prior review rounds (01, 02, 03). All previously identified issues — including the `process_media()` signature cascade (01-F-001), the `moderate_image()` return type contract (01-F-002), the provider signature mismatch (01-F-003), the nonexistent `ConfigurationMissingError` (01-F-004), class/file naming errors (01-F-005/F-006), config resolution path (02-MIMG-001), factory wiring steps (02-MIMG-002), event-loop safety (02-MIMG-003), and the base class call site explicitness (03-CC-001) — have been resolved in the current spec.

### What was verified and found correct

- **`process_media()` contract change**: Keeps `caption` (used by `CorruptMediaProcessor` and `UnsupportedMediaProcessor` in `error_processors.py`), drops `quota_exceeded` (unused by any processor's conversion logic; still preserved on `MediaProcessingJob` and archived by `_archive_to_failed`), adds `bot_id`. The call site code snippets in the spec match the actual code in `base.py` lines 28–31 and 79–82 exactly.
- **Factory wiring**: The 5-step hygiene checklist in Section 1 covers all necessary changes. `factory.py` currently imports `ImageVisionProcessor` from `stub_processors` (line 3–6) and maps it in `PROCESSOR_CLASS_MAP` (line 13). The spec mandates updating both.
- **Provider resolution**: `create_model_provider(bot_id, "media_processing", "image_moderation")` correctly maps to `ConfigTier = "image_moderation"`, which `resolve_model_config` handles by returning `BaseModelProviderConfig` from `config_data.configurations.llm_configs.image_moderation`. The `LLMConfigurations` model in `config_models.py` (line 101) confirms `image_moderation: BaseModelProviderConfig` exists. Dynamic import of `model_providers.openAiModeration` via `find_provider_class` finds `OpenAiModerationProvider`, which passes the `isinstance(provider, ImageModerationProvider)` check in `model_factory.py` (line 76).
- **`moderate_image()` contract update**: Changing `(self, image_url: str)` to `(self, base64_image: str, mime_type: str)` in both `ImageModerationProvider` (abstract) and `OpenAiModerationProvider` (concrete) is explicitly specified. Data URI construction inside the provider matches the OpenAI API's expected input format for `omni-moderation-latest`.
- **OpenAI API format**: The payload shape `[{"type": "image_url", "image_url": {"url": data_uri}}]` with `data_uri = f"data:{mime_type};base64,{base64_image}"` matches the OpenAI Moderation API documentation for image inputs via the `omni-moderation-latest` model.
- **`ModerationResult` model**: `Dict[str, bool]` for categories and `Dict[str, float]` for category_scores correctly accommodate the API's slash-delimited keys (e.g., `sexual/minors`, `self-harm/intent`).
- **Two-level logging**: Raw SDK response at debug in the provider; normalized `ModerationResult.model_dump()` at info in the processor. Clean separation of concerns.
- **Error handling**: Bubbling to `BaseMediaProcessor.process_job` leverages the existing `_handle_unhandled_exception` path (line 72–74 of `base.py`), which persists an error result, archives to `_failed`, and attempts best-effort delivery.
- **Event-loop safety**: `asyncio.to_thread(...)` for file I/O and base64 encoding prevents blocking the event loop during image processing.
- **Processing result**: The stub format `f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']"` matches the existing convention in `StubSleepProcessor` (line 18 of `stub_processors.py`).
- **Affected subclasses list**: Complete. `StubSleepProcessor` signature change propagates to `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor` via inheritance. `CorruptMediaProcessor` and `UnsupportedMediaProcessor` are listed separately. `ImageVisionProcessor` gets its own complete implementation in the new module.
- **Worker instantiation**: `MediaProcessingService._worker_loop` creates processors via `processor_class(pool_definition["mimeTypes"], pool_definition.get("processingTimeoutSeconds", 60))`, which maps to `BaseMediaProcessor.__init__(handled_mime_types, processing_timeout)`. The extracted `ImageVisionProcessor` needs no custom `__init__` — the base class constructor is sufficient.
- **File references**: All filenames in the spec's "Relevant Background Information" section match the actual filesystem (including camelCase `openAi.py` and `openAiModeration.py`).

---

## Detailed Findings

---

### OP-001

**Priority:** P3  
**Title:** Extracted `ImageVisionProcessor` parent class not explicitly stated  

**Description:**

`ImageVisionProcessor` currently inherits from `StubSleepProcessor` (`stub_processors.py` line 21–23):

```python
class ImageVisionProcessor(StubSleepProcessor):
    sleep_seconds = 5
    media_label = "image"
```

After extraction to `media_processors/image_vision_processor.py`, the new class will have a completely new `process_media()` implementation (sections 3–7 describe the full logic: file I/O, base64 encoding, provider resolution, moderation call, logging, result). It should therefore inherit directly from `BaseMediaProcessor`, not `StubSleepProcessor` — the stub's `sleep_seconds` and `media_label` attributes become meaningless, and keeping the inheritance would be misleading.

This is strongly implied by the spec's overall context (extracting away from `stub_processors.py`, providing a real implementation), and any competent implementer will get it right. However, the spec never explicitly states which class `ImageVisionProcessor` should inherit from after extraction.

**Suggested Action:**

Optional clarity improvement: add a one-line note to Section 1, e.g., "The extracted `ImageVisionProcessor` inherits directly from `BaseMediaProcessor`." Not blocking — the change is unambiguously implied by the described implementation.

---

## Conclusion

The spec is implementation-ready. The single P3 observation above is informational and not a gate to starting work. All architectural decisions, contract changes, integration points, error handling, and logging requirements are coherent, internally consistent, and correctly aligned with the codebase and the OpenAI Moderation API.
