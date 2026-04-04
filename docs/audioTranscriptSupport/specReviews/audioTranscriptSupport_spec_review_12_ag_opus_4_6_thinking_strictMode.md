# Spec Review: audioTranscriptSupport — Review 12

**Review ID:** `12_ag_opus_4_6_thinking_strictMode`  
**Spec File:** `docs/audioTranscriptSupport/audioTranscriptSupport_specFile.md`  
**Date:** 2026-04-04  

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| HIGH | R12-01 | `AsyncSonioxClient` lifecycle: no `close()`/`aclose()` in provider teardown | [Details](#r12-01) | READY |
| HIGH | R12-02 | `format_processing_result` new required `mime_type` parameter breaks callers if not defaulted | [Details](#r12-02) | READY |
| MEDIUM | R12-03 | Fire-and-forget cleanup task not awaited — risk of silent swallowing on event loop shutdown | [Details](#r12-03) | READY |
| MEDIUM | R12-05 | Spec omits `image_moderation` pricing tier from migration `token_menu` without explicit justification | [Details](#r12-05) | READY |

---

## Detailed Descriptions

---

### <a id="r12-01"></a>R12-01 — `AsyncSonioxClient` lifecycle: no `close()`/`aclose()` in provider teardown

**Priority:** HIGH  
**Status:** READY  
**Required Actions:** Accept as known technical debt. The `AsyncSonioxClient` lifecycle leak is a known issue that will be resolved in a future phase by introducing a provider caching layer inside the model factory. No spec changes required for this phase.

#### Description

The spec (Section 1, Provider Architecture) instructs the developer to create the `AsyncSonioxClient` inside `initialize()` and store it as `self.client`. The spec also explicitly acknowledges (line 175): *"The provider instances intentionally omit a teardown/close call as a known leaky capability..."*

However, the `AsyncSonioxClient` (like most async HTTP client wrappers) likely manages an internal `httpx.AsyncClient` or `aiohttp.ClientSession`. Without an explicit `close()` or `aclose()` call:

1. **Resource leak**: Each `create_model_provider` call that instantiates a new `SonioxAudioTranscriptionProvider` creates a new HTTP connection pool that is never cleaned up. Since the spec states a future "provider caching layer inside the factory will effectively cap the maximum active connections," this leak is bounded — but the caching layer does not yet exist.

2. **Python warnings**: Many async HTTP libraries emit `ResourceWarning` or `Unclosed client session` warnings at GC time, which pollute production logs.

The spec's justification ("later a provider caching layer inside the factory will effectively cap the maximum active connections to the active bot volume") is a forward-looking architectural deferral, but the current implementation creates a **new provider instance per `create_model_provider` call** with no caching or reuse. This means every audio transcription invocation leaks one `AsyncSonioxClient` session.

**Contrast with existing pattern:** The `ImageModerationProvider` and `ImageTranscriptionProvider` subtypes create their provider-specific clients dynamically inside their methods (e.g., `moderate_image`, `transcribe_image`), scoping the lifecycle to a single call. The Soniox provider instead persists the client on `self`, making the leak structural.

#### Suggested Analysis

Verify the Soniox Python SDK to determine whether `AsyncSonioxClient` implements `__aenter__`/`__aexit__` or a public `close()` method. If so, the spec should either:
- (a) Instruct the `transcribe_audio` method to create and close the client within its own scope (like the image providers do), or
- (b) Document the leak magnitude and explicitly accept it with a ticket reference for the caching layer.

---

### <a id="r12-02"></a>R12-02 — `format_processing_result` new required `mime_type` parameter breaks callers if not defaulted

**Priority:** HIGH  
**Status:** READY  
**Required Actions:** Update the spec to declare `mime_type: str` as a required parameter in `format_processing_result`. Add an explicit checklist of all call sites that must be updated atomically: (1) `BaseMediaProcessor.process_job()` — pass `job.mime_type`, (2) `BaseMediaProcessor._handle_unhandled_exception()` — pass `job.mime_type`.

#### Description

The spec (Output Format section, line 46) instructs:

> *"Refactor `format_processing_result` in `media_processors/base.py` to accept a `mime_type: str` parameter..."*

The current signature of `format_processing_result` is:

```python
def format_processing_result(
    content: str,
    caption: str,
    original_filename: Optional[str] = None,
    unprocessable_media: bool = False,
) -> ProcessingResult:
```

Adding `mime_type: str` as a **required** parameter (no default) would break all existing callers unless they are simultaneously updated. The spec does cover updating `process_job` (line 46: "Ensure `BaseMediaProcessor.process_job` passes `job.mime_type`...") and `_handle_unhandled_exception` (line 41).

**The issue:** The spec does not explicitly state whether `mime_type` should be a required or optional parameter in the function signature. If it's added as a **required positional or keyword parameter**, the implementation must be **atomic** — every caller must be updated in the same commit. If any caller is missed, the application will crash at runtime.

Given that `format_processing_result` is a module-level utility called from:
1. `BaseMediaProcessor.process_job()` (line 91 of `base.py`)
2. `BaseMediaProcessor._handle_unhandled_exception()` (line 186 of `base.py`)

Both are in the same file, so the atomicity risk is low. However, the spec should **explicitly** state that `mime_type` must be inserted **after** the existing positional parameters to maintain backward compatibility during development, or alternatively specify it as `mime_type: Optional[str] = None` with a sensible fallback for callers that don't yet provide it.

#### Suggested Analysis

Add explicit specification of the parameter default value or ordering to prevent ambiguity during implementation.

---

### <a id="r12-03"></a>R12-03 — Fire-and-forget cleanup task not awaited — risk of silent swallowing on event loop shutdown

**Priority:** MEDIUM  
**Status:** READY  
**Required Actions:** Accept as known technical debt. Document in the spec that fire-and-forget cleanup tasks may not complete during application shutdown, and that leaked Soniox resources are bounded by the transcription pool size (2 concurrent workers). No code changes required.

#### Description

The spec (Transcription section, line 31) prescribes:

> *"Wrap the network cleanup commands inside an asynchronous closure, and execute it using `asyncio.create_task(...)` within the `finally` block of the `transcribe_audio` method."*

This fire-and-forget pattern (shown in the code snippet at line 169: `asyncio.create_task(_cleanup())`) is architecturally sound for preventing `CancelledError` from blocking cleanup. However, the spec does not address what happens when the **event loop itself is shutting down** (e.g., during application graceful shutdown via `MediaProcessingService.stop()`).

During shutdown:
1. `MediaProcessingService.stop()` cancels all worker tasks (line 63-69 of `media_processing_service.py`).
2. Worker tasks propagate `CancelledError` into the processor's `process_job` method.
3. The `transcribe_audio` `finally` block fires and creates a background cleanup task via `asyncio.create_task()`.
4. If the event loop finishes processing remaining tasks before the cleanup HTTP calls complete, the Soniox file/transcription resources are **leaked on the remote server**.

The existing worker shutdown flow does `task.cancel()` → `await task` → catches `CancelledError`. But the fire-and-forget cleanup tasks spawned inside `transcribe_audio` are not tracked by anyone — they're "attached natively to the event loop" as the spec states, but nothing guarantees they'll finish before the process exits.

#### Suggested Analysis

Evaluate whether this risk is acceptable given that:
- Production deployments typically have graceful shutdown periods
- Soniox has a 2,000 transcription / file quota, so leaked resources accumulate but don't immediately cause failures
- The migration script or a periodic maintenance task could batch-delete stale Soniox resources

If the risk is accepted, the spec should document it explicitly as known technical debt. Otherwise, consider recommending a registry of background cleanup tasks that the shutdown path can `asyncio.gather()` with a timeout.

---

### <a id="r12-05"></a>R12-05 — Spec omits `image_moderation` pricing tier from migration `token_menu` without explicit justification

**Priority:** MEDIUM  
**Status:** READY  
**Required Actions:** Add a comment in the spec's migration section explicitly noting that `image_moderation` is intentionally excluded from the `token_menu` because moderation providers currently bypass the token tracking pipeline.

#### Description

The spec (Deployment Checklist, line 195) states:

> *"Replaces the existing `token_menu` (which contains only 3 tiers) with a new one containing ALL 4: `high`, `low`, `image_transcription`, `audio_transcription`."*

The existing `ConfigTier` is `Literal["high", "low", "image_moderation", "image_transcription"]`, meaning there are currently **4 config tiers**, but the spec claims the existing `token_menu` contains only **3 tiers**. After the migration, the new `token_menu` also has **4 tiers** but notably **drops `image_moderation`** entirely.

Analyzing the code: In `model_factory.py` (line 87-88), the `ImageModerationProvider` branch returns the provider directly without attaching any token tracking. This means `image_moderation` never generates token consumption events, so it logically does not need a `token_menu` pricing entry.

However, looking at `QuotaService.calculate_cost()` (line 51-53 of `quota_service.py`), if a `config_tier` not in `_token_menu` is passed, it logs a warning and returns `0.0`:

```python
if config_tier not in self._token_menu:
    logger.warning(f"Unknown config_tier: {config_tier}")
    return 0.0
```

If a future developer adds token tracking to the moderation branch (or if the companion fix's `feature_name="image_moderation"` somehow reaches the cost calculation path), the silent `0.0` return would cause **unbilled usage** and a warning log flood.

The spec should explicitly call out that `image_moderation` is intentionally excluded from the `token_menu` because moderation providers bypass the token tracking pipeline, and that this assumption should be validated whenever the moderation provider architecture changes.

#### Suggested Analysis

Add an explicit note in the migration script and/or the deployment checklist explaining why `image_moderation` is omitted from the `token_menu`.

---

*End of review.*
