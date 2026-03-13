# Spec Review: Media Processor Image Moderation (Permissive Report)

**Spec File:** `docs/moderateImage_spec.md`  
**Reviewer:** Cursor Opus 4.6 (high-thinking, permissive)  
**Date:** 2026-03-13  

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| P3 | PR-001 | `ModerationResult` omits `category_applied_input_types` from OpenAI API response | [Details](#pr-001) | DONE |
| P3 | PR-002 | Serialization format for raw SDK response logging is unspecified | [Details](#pr-002) | DONE |
| P4 | PR-003 | `feature_name` parameter in `create_model_provider` call is unused for moderation path | [Details](#pr-003) | DONE |
| P4 | PR-004 | Inconsistent path separator style in project file references | [Details](#pr-004) | DONE |

---

## Overall Assessment

**The spec is well-hardened and implementation-ready.** After thorough cross-referencing against all 18 referenced project files, the OpenAI Moderation API documentation, and the five prior review rounds, no P1 or P2 issues remain.

The spec has been iteratively strengthened through five prior reviews. All previously identified issues have been resolved in the current text:

- **Round 01 (F-001 through F-006):** `process_media()` signature cascade, `moderate_image()` return type contract, provider signature mismatch, nonexistent `ConfigurationMissingError`, class naming, file naming — all resolved.
- **Round 02 (MIMG-001 through MIMG-003):** Config resolution path, factory wiring steps, event-loop safety — all resolved.
- **Round 03 (CC-001):** Base class call site explicitness — resolved (code snippets now included).
- **Round 04 (OP-001):** Parent class for extracted `ImageVisionProcessor` — resolved (explicit "inherits directly from `BaseMediaProcessor`" statement added).
- **Round 05 (MIMG-501 through MIMG-504):** Rollout safety acknowledgment, default model wording, logging policy, verification scope — all resolved.

### What was verified and found correct

- **`process_media()` contract change:** Keeps `caption` (used by `CorruptMediaProcessor` and `UnsupportedMediaProcessor`), drops `quota_exceeded` (unused by any processor's conversion logic; preserved on `MediaProcessingJob` and archived by `_archive_to_failed`), adds `bot_id`. The "Current" / "Should be" code snippets match the actual code in `base.py` lines 28–31 and 79–82.
- **Affected subclass enumeration:** Complete. `StubSleepProcessor` propagates to `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor` via inheritance. `CorruptMediaProcessor` and `UnsupportedMediaProcessor` listed separately. `ImageVisionProcessor` gets its own implementation in the new module.
- **Factory wiring:** The 5-step hygiene checklist covers all necessary changes. `factory.py` currently imports `ImageVisionProcessor` from `stub_processors` (lines 2–6) and maps it in `PROCESSOR_CLASS_MAP` (line 13). The spec mandates updating both.
- **Provider resolution chain:** `create_model_provider(bot_id, "media_processing", "image_moderation")` → `resolve_model_config(bot_id, "image_moderation")` → returns `BaseModelProviderConfig` from `config_data.configurations.llm_configs.image_moderation`. Dynamic import of `model_providers.openAiModeration` via `find_provider_class` finds `OpenAiModerationProvider`, which passes the `isinstance(provider, ImageModerationProvider)` check in `model_factory.py` line 76. `LLMConfigurations` in `config_models.py` (line 101) confirms `image_moderation: BaseModelProviderConfig` exists.
- **`moderate_image()` signature change safety:** Grep confirms no production callers of `moderate_image()` outside `model_providers/openAiModeration.py` and `model_providers/image_moderation.py`. The signature change from `(self, image_url: str)` to `(self, base64_image: str, mime_type: str)` is safe.
- **OpenAI API payload format:** `[{"type": "image_url", "image_url": {"url": data_uri}}]` with `data_uri = f"data:{mime_type};base64,{base64_image}"` matches the OpenAI Moderation API documentation for `omni-moderation-latest` image inputs.
- **`ModerationResult` model:** `Dict[str, bool]` for categories and `Dict[str, float]` for category_scores correctly accommodate the API's slash-delimited keys (e.g., `sexual/minors`, `self-harm/intent`).
- **Error handling:** Bubbling to `BaseMediaProcessor.process_job` leverages the existing `_handle_unhandled_exception` path (`base.py` lines 72–74), which persists an error result, archives to `_failed`, and attempts best-effort delivery.
- **Event-loop safety:** `asyncio.to_thread(...)` for file I/O and base64 encoding prevents blocking.
- **Processing result format:** The stub string `f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']"` matches the existing convention in `StubSleepProcessor` (`stub_processors.py` line 18).
- **Worker instantiation:** `MediaProcessingService._worker_loop` creates processors via `processor_class(pool_definition["mimeTypes"], pool_definition.get("processingTimeoutSeconds", 60))`, which maps to `BaseMediaProcessor.__init__(handled_mime_types, processing_timeout)`. The extracted `ImageVisionProcessor` needs no custom `__init__`.
- **Default configuration alignment:** `DefaultConfigurations` in `config_models.py` (lines 172–175) already sets `model_provider_name_moderation = "openAiModeration"` and `model_image_moderation = "omni-moderation-latest"`, matching the spec's requirements.
- **Verification checklist:** Covers factory resolution, contract migration, provider interface, event-loop safety, and moderation payload shape — the five highest-risk behavioral changes.
- **Rollout safety:** Explicitly acknowledged as out of scope with a clear rationale (all bots already upgraded, residual probability accepted).

---

## Detailed Findings

---

### PR-001

**Priority:** P3  
**ID:** PR-001  
**Title:** `ModerationResult` omits `category_applied_input_types` from OpenAI API response  
**Status:** DONE

**Description:**

The OpenAI `omni-moderation-latest` model returns a `category_applied_input_types` field in its response, which maps each moderation category to the input types (e.g., `["image"]`, `["text"]`, `[]`) that were evaluated for that category. This is visible in the API documentation:

```json
"category_applied_input_types": {
    "sexual": ["image"],
    "sexual/minors": [],
    "harassment": [],
    "violence": ["image"],
    "violence/graphic": ["image"]
}
```

The current `ModerationResult` model (`model_providers/image_moderation.py`) captures only `flagged`, `categories`, and `category_scores`. The `category_applied_input_types` field is discarded during normalization in `OpenAiModerationProvider`.

The spec's own requirements state: "Log moderation outputs for auditing/debugging." The `category_applied_input_types` field is useful audit data — it tells operators which categories were actually evaluated against the image input vs. left unevaluated (score 0 by default). This distinction matters when interpreting why certain category scores are zero.

**Impact:** Low. The three captured fields (`flagged`, `categories`, `category_scores`) provide sufficient information for the preparation phase. Enforcement is out of scope, so the missing field does not affect runtime behavior.

**Selected mitigation:** **(B) Explicitly document the omission in the spec.** Add a note that `category_applied_input_types` is intentionally omitted from `ModerationResult` in this preparation phase, to be revisited when enforcement logic is introduced. The raw SDK response log (Section 6) already captures the full API response including this field, so audit coverage is not lost.

---

### PR-002

**Priority:** P3  
**ID:** PR-002  
**Title:** Serialization format for raw SDK response logging is unspecified  
**Status:** DONE

**Description:**

Section 6 of the spec requires:

> "In `OpenAiModerationProvider.moderate_image()`: log raw SDK response via `logger.info(...)`."

The OpenAI Python SDK returns a Pydantic-based response object from `client.moderations.create(...)`. The spec does not specify how this object should be serialized for logging. Common options include:

- `str(response)` — produces a repr-style string
- `response.model_dump()` — produces a dict (logged as Python dict repr)
- `response.model_dump_json()` — produces a JSON string

Each produces a different log format with different readability and parseability characteristics. The spec is explicit about the processor-side logging format (`moderation_result.model_dump()`), but leaves the provider-side format to implementer discretion.

**Impact:** Low. The intent is clear (log the raw response for debugging). Any reasonable serialization achieves the goal. The ambiguity only matters if downstream log-parsing tools expect a specific format.

**Selected mitigation:** **(A) Specify `.model_dump()` for consistency.** Update the spec's Section 6 provider-side logging to read: "log raw SDK response via `logger.info(response.model_dump())`". This matches the processor-side convention (`moderation_result.model_dump()`) and ensures both logging points use the same serialization approach.

---

### PR-003

**Priority:** P4  
**ID:** PR-003  
**Title:** `feature_name` parameter in `create_model_provider` call is unused for moderation path  
**Status:** DONE

**Description:**

The spec mandates calling `create_model_provider(bot_id, "media_processing", "image_moderation")`. The `feature_name` parameter (`"media_processing"`) is accepted by the factory function but has no effect in the `ImageModerationProvider` code path.

In `services/model_factory.py`, `feature_name` is only consumed when constructing a `TokenTrackingCallback` for `ChatCompletionProvider` instances (lines 55–61). For `ImageModerationProvider`, the function returns the provider directly (line 77) without using `feature_name`.

This means `"media_processing"` is a dead parameter in this call — it's accepted but discarded.

**Impact:** None at runtime. The factory API requires the parameter, so it must be supplied. The value is semantically reasonable and would become meaningful if token tracking were later extended to moderation providers.

**Selected mitigation:** **Explicitly acknowledge in the spec.** Add a note stating that the `feature_name` parameter (`"media_processing"`) is currently unused in the `ImageModerationProvider` code path, and that this is known and accepted. Token/cost tracking for moderation providers will be needed in the future, at which point this parameter will become meaningful.

---

### PR-004

**Priority:** P4  
**ID:** PR-004  
**Title:** Inconsistent path separator style in project file references  
**Status:** DONE

**Description:**

The "Relevant Background Information → Project Files" section uses mixed path separators:

- Backslashes: `media_processors\base.py`, `model_providers\openAi.py`, `services\media_processing_service.py`
- Forward slashes: `media_processors/error_processors.py`, `media_processors/__init__.py`, `model_providers/chat_completion.py`, `utils/provider_utils.py`

While both work on Windows, this is a cosmetic inconsistency. The project runs in Docker (Linux-based containers) where only forward slashes are valid filesystem paths.

**Impact:** None. These are documentation references, not executable paths. All listed files exist and are correctly named.

**Selected mitigation:** **(A) Normalize to forward slashes.** Update the spec's "Relevant Background Information → Project Files" section to use forward slashes consistently across all file references. The project runs in Docker (Linux containers) where forward slashes are the native separator.

---

## Conclusion

The spec is implementation-ready. It has been iteratively hardened through five prior review rounds covering signature cascades, provider contracts, error handling, factory wiring, parent class inheritance, rollout safety, logging policy, and verification scope. All prior P1 and P2 findings have been addressed.

The four items above are P3/P4 observations — minor informational gaps and cosmetic inconsistencies that do not affect the correctness or implementability of the spec. None are blocking.
