# Spec Review: Audio Transcription Support

**Review ID:** `08_ag_opus_4_6_thinking_strictMode`
**Spec File:** `docs/audioTranscriptSupport/audioTranscriptSupport_specFile.md`
**Reviewer:** Antigravity (Claude Opus 4, Thinking, Strict Mode)
**Date:** 2026-04-01

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| HIGH | R08-01 | `create_model_provider` refactoring extracts `TokenConsumptionService` universally but silently breaks if `token_consumption_collection` is `None` for non-LLM branches | [Details](#r08-01) | READY |
| HIGH | R08-02 | Spec's `transcribe_audio` error-path `ProcessingResult` omits `unprocessable_media=True` producing semantically incorrect prefix injection on transcription exceptions | [Details](#r08-02) | READY |
| HIGH | R08-03 | Soniox SDK exposes `delete_if_exists` convenience methods but spec's cleanup code uses bare `delete` which will throw `SonioxNotFoundError` on already-deleted resources | [Details](#r08-03) | READY |
| MEDIUM | R08-04 | `format_processing_result` refactoring to accept `mime_type` has no explicit fallback for `None` or empty mime_type values from legacy/stub processors | [Details](#r08-04) | READY |
| MEDIUM | R08-05 | `AudioTranscriptionProcessor.process_media` catches generic `Exception` but `asyncio.CancelledError` in Python 3.9+ is a `BaseException`, silently leaking it through to `process_job`'s outer handler | [Details](#r08-05) | READY |
| LOW | R08-06 | Spec code snippet accesses `job_info.usage.input_audio_tokens` and `output_text_tokens` but Soniox SDK docs do not document these exact attribute names | [Details](#r08-06) | READY |
---

## Detailed Review Items

---

### <a id="r08-01"></a>R08-01: `create_model_provider` refactoring extracts `TokenConsumptionService` universally but silently breaks if `token_consumption_collection` is `None` for non-LLM branches

**Priority:** HIGH

**Detailed Description:**

The spec (line 162) states:

> "**Refactor Initialization**: Extract the instantiation of `TokenConsumptionService` and its required `get_global_state()` dictionary fetch out of the `if isinstance(provider, LLMProvider):` tracking block. It must be initialized universally *before* the type checks so that it is accessible to all provider branches."

Looking at the current code in `services/model_factory.py` (lines 55–63), the `TokenConsumptionService` instantiation is currently **guarded** by a `None` check:

```python
if isinstance(provider, LLMProvider):
    llm = provider.get_llm()
    state = get_global_state()
    token_consumption_collection = state.token_consumption_collection
    if token_consumption_collection is not None:   # <-- guard
        token_service = TokenConsumptionService(token_consumption_collection)
        # ... attach callback
    else:
        logger.warning("... Token tracking DISABLED.")
```

After the refactoring, the `TokenConsumptionService` instantiation moves **before** the type checks and becomes universally executed. The spec's code snippet (lines 167–178) shows:

```python
async def token_tracker(input_tokens, output_tokens, cached_input_tokens=0):
    await token_service.record_event(...)
provider.set_token_tracker(token_tracker)
```

But if `token_consumption_collection` is `None` (the existing fallback scenario), then `token_service` will be constructed with `None`, and `token_service.record_event()` will silently fail with the internal `logger.error("TokenConsumptionService: No collection configured.")` message — this is correct and survivable. **However**, the `QuotaService.update_user_usage()` call inside `record_event` will also be skipped, meaning audio transcription token usage will be invisible to both the billing pipeline and quota enforcement.

The critical issue is that the spec does not address what happens in the `elif isinstance(provider, AudioTranscriptionProvider)` branch when `token_consumption_collection is None`. The current `LLMProvider` branch has an explicit `else: logger.warning(...)` path. The new `AudioTranscriptionProvider` branch must also handle this gracefully — either by conditionally skipping `set_token_tracker()` entirely (to avoid injecting a no-op tracker that silently drops usage data) or by logging an explicit warning.

Without this guard, a deployment where `token_consumption_collection` is `None` (e.g., a test environment) will create an `AudioTranscriptionProvider` with a token tracker that silently swallows all usage events — no warning, no error, just invisible data loss in the billing pipeline.

**Status:** READY

**Required Actions:**
- **Action:** Add an explicit note to the spec's `model_factory.py` refactoring section (line 162) reminding the implementer that the existing `if token_consumption_collection is not None:` guard and its `else: logger.warning(...)` fallback must be preserved when extracting `TokenConsumptionService` initialization to the universal scope. The new `AudioTranscriptionProvider` branch must replicate this same guard pattern before calling `set_token_tracker()`, ensuring that test environments or incomplete DB initialization produce a visible warning rather than silently dropping token usage events.

---

### <a id="r08-02"></a>R08-02: Spec's `transcribe_audio` error-path `ProcessingResult` omits `unprocessable_media=True` producing semantically incorrect prefix injection on transcription exceptions

**Priority:** HIGH

**Detailed Description:**

The spec (line 34) states:

> "To align with the `ImageVisionProcessor` sibling pattern, `AudioTranscriptionProcessor.process_media` should wrap the `transcribe_audio` call in a `try/except` block. If an exception occurs, catch it and return a structured `ProcessingResult(content="Unable to transcribe audio content", failed_reason=f"Transcription error: {e}")`."

This `ProcessingResult` defaults `unprocessable_media=False` (verified in `infrastructure/models.py` line 26). After the spec's prefix injection refactoring (line 40), the `format_processing_result` function will prepend `"Audio Transcription: "` to content **unless** `unprocessable_media=True`.

This means when the Soniox API throws an exception (network failure, quota exceeded, auth error), the resulting message will be:

```
[Audio Transcription: Unable to transcribe audio content]
<caption>
```

The "Audio Transcription:" prefix on an error message is semantically misleading — it implies a transcription was produced when one was not. This directly contradicts the spec's own design principle for the `unprocessable_media` flag (line 33):

> "`unprocessable_media=True` prevents the `"Audio Transcription: "` text injection"

The spec correctly applies `unprocessable_media=True` for the empty/unexpected-format case (line 32): `ProcessingResult(content="Unable to transcribe audio content", failed_reason="Unexpected format from Soniox API", unprocessable_media=True)`. But the general exception case (line 34) is missing this flag.

The same issue exists in the current `ImageVisionProcessor.process_media` (lines 71-74), which returns `ProcessingResult(content="Image could not be transcribed", failed_reason=...)` without `unprocessable_media=True`. After the prefix injection refactoring, this will produce `[Image Transcription: Image could not be transcribed]` — equally misleading. However, fixing `ImageVisionProcessor` is outside the scope of this spec's direct requirements; it is noted here because the spec instructs audio transcription to mirror this sibling pattern, thereby propagating the same design flaw.

**Status:** READY

**Required Actions:**
- **Action (Audio):** Update the spec's error handling section (line 34) to explicitly include `unprocessable_media=True` in the exception-handling `ProcessingResult`: `ProcessingResult(content="Unable to transcribe audio content", failed_reason=f"Transcription error: {e}", unprocessable_media=True)`. This ensures error messages bypass the prefix injection and produce `[Unable to transcribe audio content]` rather than `[Audio Transcription: Unable to transcribe audio content]`.
- **Action (Image — companion fix):** Add an explicit requirement to the spec mandating that `ImageVisionProcessor.process_media`'s two error-path `ProcessingResult` returns (moderation API crash on line 54-58 and transcription API crash on line 71-74 of `image_vision_processor.py`) must also include `unprocessable_media=True`. This is a necessary companion fix because the prefix injection refactoring introduced by this spec is a global change that would otherwise produce semantically incorrect output (`[Image Transcription: Image could not be moderated]`) on the existing sibling processor.

---

### <a id="r08-03"></a>R08-03: Soniox SDK exposes `delete_if_exists` convenience methods but spec's cleanup code uses bare `delete` which will throw `SonioxNotFoundError` on already-deleted resources

**Priority:** HIGH

**Detailed Description:**

The spec's cleanup code snippet (lines 152–158) uses bare `delete` calls wrapped in `try/except Exception: pass`:

```python
async def _cleanup():
    if transcription:
        try: await self.client.stt.delete(transcription.id)
        except Exception: pass
    if file:
        try: await self.client.files.delete(file.id)
        except Exception: pass
```

The Soniox Python SDK documentation (confirmed from the "Delete file" and "Delete or destroy transcription" sections) explicitly states:

- `client.files.delete("file-id")` — "throws `SonioxNotFoundError` if file does not exist"
- `client.stt.delete("transcription-id")` — throws error if not found

The SDK provides safer alternatives:

- `client.files.delete_if_exists("file-id")` — silently succeeds if already deleted
- `client.stt.delete_if_exists("transcription-id")` — silently succeeds if already deleted

While the spec's `try/except Exception: pass` blocks will catch `SonioxNotFoundError` (since it inherits from `Exception`), this pattern is problematic for several reasons:

1. **Overly broad exception swallowing**: The `except Exception: pass` will also swallow legitimate network errors, auth failures, and rate limiting responses during cleanup — silently leaving resources undeleted on the Soniox servers. This directly undermines the spec's stated goal of "avoiding quota exhaustion" (line 31).

2. **API semantics mismatch**: The `delete_if_exists` methods are idempotent by design — they handle the race condition where the Soniox server auto-expires or another process deletes the resource between creation and cleanup. The bare `delete` + catch-all is a brittle reimplementation of this behavior.

3. **Fire-and-forget context**: Since this cleanup runs inside an `asyncio.create_task(_cleanup())` fire-and-forget task (to bypass `CancelledError`), there is no caller to observe failures. Using `delete_if_exists` would reduce the probability of unobserved failures while preserving the same cleanup semantics.

The spec should use `delete_if_exists` for both the transcription and file cleanup, and **selectively** log non-`SonioxNotFoundError` exceptions rather than blindly swallowing them.

**Status:** READY

**Required Actions:**
- **Action:** Update the cleanup code snippet in the spec (lines 154 and 157) to use the `delete_if_exists` SDK methods: `await self.client.stt.delete_if_exists(transcription.id)` and `await self.client.files.delete_if_exists(file.id)`. Change both broad `except Exception: pass` blocks to `except Exception as e: logger.error(f"Failed to cleanup Soniox resources: {e}")` to ensure legitimate network/auth errors are logged instead of swallowed.

---

### <a id="r08-04"></a>R08-04: `format_processing_result` refactoring to accept `mime_type` has no explicit fallback for `None` or empty mime_type values from legacy/stub processors

**Priority:** MEDIUM

**Detailed Description:**

The spec (line 40) states:

> "Refactor `format_processing_result` in `media_processors/base.py` to accept a `mime_type: str` parameter. Inside the formatter, add logic to dynamically capitalize the media type from the mime type (e.g., `"audio"`) and conditionally prepend `"{MediaType} Transcription: "` to the content."

And:

> "Ensure `BaseMediaProcessor.process_job` passes `job.mime_type` to all calls to `format_processing_result`."

Examining the current `process_job` method in `base.py` (lines 90–96 and 186–191), `format_processing_result` is called in two places:

1. **Normal processing path** (line 91): `format_processing_result(content=result.content, caption=..., ...)` — `job.mime_type` will be available here.
2. **`_handle_unhandled_exception`** (line 186): `format_processing_result(content=raw.content, caption=..., ...)` — `job.mime_type` is available since `job` is passed as a parameter.

However, the spec's description says to "dynamically capitalize the media type from the mime type (e.g., `'audio'`)". The extraction logic would be something like `mime_type.split('/')[0].capitalize()`. But consider:

1. **Stub processors** (`VideoDescriptionProcessor`, `DocumentProcessor`): These stubs return `ProcessingResult` without `unprocessable_media=True`. After refactoring, they will receive prefixes like `"Video Transcription: "` and `"Application Transcription: "` (from `application/pdf`). The "Application Transcription:" prefix for PDF documents is semantically awkward. The spec acknowledges this is "intentionally global" (line 40 note) but does not address the `application/pdf` → `"Application Transcription:"` case specifically.

2. **CorruptMediaProcessor** and **UnsupportedMediaProcessor**: These error processors need to be verified — do they set `unprocessable_media=True`? If not, corrupt media will get prefixed with `"Media_corrupt_image Transcription: "` (from the synthetic MIME types `media_corrupt_image`, `media_corrupt_audio`, etc.), which is nonsensical. The spec does not address this.

3. **Edge case**: What if `mime_type` is `None` or empty? The `MediaProcessingJob` dataclass in `infrastructure/models.py` defines `mime_type: str` (required, no default), so `None` should not occur in production. But defensive coding would still want a fallback.

The spec should explicitly address what the `format_processing_result` implementation does when `mime_type` doesn't follow the standard `type/subtype` format (as with the synthetic corrupt MIME types).

**Status:** READY

**Required Actions:**
- **Action:** Update the `ProcessingResult` dataclass to include an optional `display_media_type: str = None` attribute. Modify `BaseMediaProcessor.process_job` and `format_processing_result` so that if a processor explicitly provides this string (e.g., `"Audio"` or `"Image"`), the formatter uses it directly for prefix injection instead of attempting to parse the `mime_type`.
- **Action Note:** Corrupt media types do not need explicit parsing fallback because their processors correctly set `unprocessable_media=True` (preventing the prefix entirely). Sub-optimal prefixing for stub processors (like `DocumentProcessor` producing `"Application Transcription"`) is acceptable temporary technical debt until those processors are replaced.

### <a id="r08-05"></a>R08-05: `AudioTranscriptionProcessor.process_media` catches generic `Exception` but `asyncio.CancelledError` in Python 3.9+ is a `BaseException`, silently leaking it through to `process_job`'s outer handler

**Priority:** MEDIUM

**Detailed Description:**

The spec (line 34) states:

> "To align with the `ImageVisionProcessor` sibling pattern, `AudioTranscriptionProcessor.process_media` should wrap the `transcribe_audio` call in a `try/except` block."

The sibling `ImageVisionProcessor.process_media` uses `except Exception as e:` (lines 53, 70). Since Python 3.9, `asyncio.CancelledError` inherits from `BaseException`, not `Exception`. This means a task cancellation (triggered by `process_job`'s `asyncio.wait_for` timeout wrapper) will **propagate through** the `except Exception` block unhandled.

This is actually the **correct behavior** for the timeout case — `asyncio.wait_for` raises `asyncio.TimeoutError` (which IS an `Exception` subclass and IS caught by `process_job`'s inner `except asyncio.TimeoutError` on line 84). But there's a subtlety: if the service is shutting down and the worker task is cancelled externally (via `task.cancel()` in `MediaProcessingService.stop()`, line 64), the `CancelledError` will propagate through `process_media`, through the inner `try` block, and be caught by the outer `except Exception as e:` in `process_job` (line 129) — which calls `_handle_unhandled_exception`.

Wait — `CancelledError` is a `BaseException` in Python 3.9+, so it will NOT be caught by `except Exception` on line 129 either. It will propagate further to the `_worker_loop` which has `except asyncio.CancelledError: break` (line 176-177). So the behavior is actually correct.

**However**, the spec's cleanup pattern uses `asyncio.create_task(_cleanup())` in the `finally` block of `transcribe_audio` specifically to handle `CancelledError` bypassing cleanup. The concern is: if the `process_media` `try/except Exception` wraps the `transcribe_audio` call, a `CancelledError` during transcription will:

1. Trigger the `finally` block in `transcribe_audio` → fire-and-forget cleanup task spawned ✓
2. Propagate through `process_media`'s `except Exception` unhandled (since `CancelledError` isn't `Exception`) ✓
3. Propagate through `process_job`'s `except Exception` unhandled ✓
4. Hit `process_job`'s `finally` → `delete_media_file(job.guid)` — local file cleaned up ✓
5. Reach `_worker_loop`'s `except asyncio.CancelledError: break` — worker stops ✓

This flow is actually correct, but the spec doesn't document this cancellation propagation path. The concern is that an implementer reading the spec's "wrap in try/except" instruction might use `except BaseException` (to be "safe"), which would incorrectly catch `CancelledError` and return a `ProcessingResult` instead of letting the cancellation propagate — breaking the graceful shutdown path.

The spec should add an explicit note clarifying that `process_media`'s `except` block must use `except Exception` (not `except BaseException`) to allow `asyncio.CancelledError` to propagate correctly during service shutdown.

**Status:** READY

**Required Actions:**
- **Action:** Add an explicit instruction/warning to the `AudioTranscriptionProcessor.process_media` spec section (around line 34) stating that the exception handler MUST be written as `except Exception as e:` rather than `except BaseException as e:`. Include a brief explanation that `asyncio.CancelledError` inherits from `BaseException` in Python 3.9+, and catching it would break the graceful worker shutdown flow by converting the cancellation into a normal media processing error rather than allowing it to propagate to the worker loop.

---

### <a id="r08-06"></a>R08-06: Spec code snippet accesses `job_info.usage.input_audio_tokens` and `output_text_tokens` but Soniox SDK docs do not document these exact attribute names

**Priority:** LOW

**Detailed Description:**

The spec's code snippet (lines 140–146) accesses usage metrics as:

```python
if self._token_tracker:
    job_info = await self.client.stt.get(transcription.id)
    if job_info and job_info.usage:
        await self._token_tracker(
            input_tokens=job_info.usage.input_audio_tokens,
            output_tokens=job_info.usage.output_text_tokens,
            cached_input_tokens=0
        )
```

The Soniox Python SDK documentation for `client.stt.get()` shows:

```python
transcription = client.stt.get("transcription-id")
print(transcription.id, transcription.status)
```

However, the documentation does **not** explicitly document the `usage` attribute or its sub-fields (`input_audio_tokens`, `output_text_tokens`). The return type structure is inferred from the API reference but not confirmed in the SDK-specific docs reviewed. The field names `input_audio_tokens` and `output_text_tokens` may be correct (they follow Soniox's naming convention), but they could equally be named `input_tokens`, `audio_seconds`, or something else entirely.

If these attribute names are incorrect, the `transcribe_audio` method will not crash (due to the `if job_info and job_info.usage:` guard), but token tracking will be silently skipped — meaning all audio transcription usage will be invisible to the billing and quota systems.

This is a minor risk because the attribute names are plausible and the spec author likely verified them against undocumented API responses. However, the implementer should be instructed to verify the exact `usage` object structure against the SDK's type stubs or a live API response before implementation.

**Status:** READY

**Required Actions:**
- **Action:** Update the code snippet in the spec (lines 140–146) to include an inline comment explaining why those specific attribute names are used, to prevent future reviewers from flagging them as undocumented. For example: `# Note: Soniox token-based pricing officially uses 'Input Audio Tokens' and 'Output Text Tokens'. These attributes map directly to their live API structure despite being omitted from basic SDK guides.`

---
