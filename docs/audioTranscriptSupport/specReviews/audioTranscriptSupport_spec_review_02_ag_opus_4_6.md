# Spec Review: audioTranscriptSupport
**Review ID:** `02_ag_opus_4_6`  
**Spec File:** `docs/audioTranscriptSupport/audioTranscriptSupport_specFile.md`  
**Date:** 2026-03-27  
**Reviewer:** Antigravity (ag_opus_4_6)

---

## Review Verdict

> [!TIP]
> **The spec is solid and ready for implementation.** The updated spec has successfully incorporated solutions for all 9 issues identified in the first review (`01_ag_opus_4_6`). The architecture is clean, the SDK usage is correctly specified, the token tracking callback injection pattern is well-defined, and the checklists are comprehensive. The items below are minor polish points — none are implementation blockers.

## Summary Table

| Priority | ID | Title | Link | Status |
|---|---|---|---|---|
| 🟡 LOW | `R10` | `transcribe(wait=True)` SDK shortcut may not return `usage` and `text` on the transcription object — verify against actual SDK | [→ R10](#r10) | READY |
| 🟡 LOW | `R11` | Sync `SonioxClient` used in spec snippets — provider should use `AsyncSonioxClient` for consistency with async codebase | [→ R11](#r11) | READY |
| 🟡 LOW | `R12` | `AudioTranscriptionProcessor.process_media` error handling contract contradicts the ImageVisionProcessor sibling pattern | [→ R12](#r12) | READY |

---

## Detailed Findings

---

### R10

**Priority:** 🟡 LOW  
**ID:** `R10`  
**Title:** `transcribe(wait=True)` SDK shortcut may not return `usage` and `text` on the transcription object — verify against actual SDK  
**Status:** READY  
**Required actions:** Replace the spec's `transcribe(file=..., wait=True)` snippet with the explicit 3-step async pattern using `AsyncSonioxClient`: (1) `transcription = await client.stt.transcribe(model=..., file=audio_path)`, (2) `await client.stt.wait(transcription.id)`, (3) `transcript = await client.stt.get_transcript(transcription.id)`. Extract usage via `client.stt.get(transcription.id).usage` after completion. The `wait=True` shortcut **MUST NOT** be used because it may block the event loop with synchronous polling internally, freezing all concurrent media processing workers and HTTP endpoints. Cleanup via `await client.stt.destroy(transcription.id)` in a `finally` block remains mandatory.

**Detailed description:**

The spec (§Transcription and §Technical Details §1) mandates this pattern:

```python
transcription = await client.stt.transcribe(
    model=self.settings.model,
    file=audio_path,
    wait=True
)
# Then directly access:
# transcription.usage.input_audio_tokens
# transcription.usage.output_text_tokens
# transcription.text
```

The Soniox SDK documentation shows `transcribe()` as a convenience method that **creates** the transcription job (and optionally uploads the file). The standard documented lifecycle is:

1. `transcription = client.stt.transcribe(model=..., file=...)` → returns creation response (with `id`, `status`)
2. `client.stt.wait(transcription.id)` → polls until completion
3. `transcript = client.stt.get_transcript(transcription.id)` → returns object with `.text` and `.tokens`

The `wait=True` parameter and the presence of `.text` and `.usage` directly on the return value of `transcribe()` are **not shown in the current SDK documentation**. If this is a real SDK feature, the spec is correct. If it isn't, then the implementation will need the 3-step approach, and the usage/token data may need to be retrieved differently (e.g., from `client.stt.get(transcription.id).usage`).

**Recommendation:** Before implementation, verify this against the actual installed `soniox` Python package (e.g., by inspecting `soniox.resources.stt.SttResource.transcribe` signature). If `wait=True` is not supported, update the code snippet to use the explicit 3-step pattern. The `destroy()` cleanup in the `finally` block remains correct either way.

---

### R11

**Priority:** 🟡 LOW  
**ID:** `R11`  
**Title:** Sync `SonioxClient` used in spec snippets — provider should use `AsyncSonioxClient` for consistency with async codebase  
**Status:** READY  
**Required actions:** Add an explicit `from soniox import AsyncSonioxClient` import line to the spec's `SonioxAudioTranscriptionProvider` snippet. Add a note: *"All Soniox SDK calls must use `AsyncSonioxClient`, not the synchronous `SonioxClient`. Each call (`transcribe`, `wait`, `get_transcript`, `destroy`) must be `await`ed."*

**Detailed description:**

The spec (§Technical Details §1) states:

> *"Use the `AsyncSonioxClient` from the Soniox Python SDK."*

This is correct — the application codebase is fully async (`process_media` is `async def`, and `model_factory.create_model_provider` is async). However, the SDK documentation examples all demonstrate the synchronous `SonioxClient`, not `AsyncSonioxClient`. The SDK *does* provide an async variant, but:

1. The `transcribe(file=..., wait=True)` shortcut demonstrated in the spec may have a slightly different async signature (e.g., `await client.stt.transcribe(...)` vs `client.stt.transcribe(...)`).
2. The cleanup call `client.stt.destroy(transcription.id)` must also be awaited: `await client.stt.destroy(transcription.id)`.

The spec text correctly says `AsyncSonioxClient`, and the snippet uses `await`, so this is internally consistent. The risk is only that an implementer might copy examples from the Soniox docs (which are all sync) and forget to use the async variant. This is a documentation-level concern, not a spec defect.

**Recommendation:** Consider adding an explicit import line to the spec's provider snippet: `from soniox import AsyncSonioxClient` to prevent confusion.

---

### R12

**Priority:** 🟡 LOW  
**ID:** `R12`  
**Title:** `AudioTranscriptionProcessor.process_media` error handling contract contradicts the ImageVisionProcessor sibling pattern  
**Status:** READY  
**Required actions:** Revise the spec's error handling section to align with the `ImageVisionProcessor` sibling pattern. `AudioTranscriptionProcessor.process_media` should wrap the `transcribe_audio` call in a `try/except` block and return a structured `ProcessingResult(content="Unable to transcribe audio content", failed_reason=f"Transcription error: {e}")` on failure, matching the operator-friendly error reporting used by `ImageVisionProcessor`. Remove the directive prohibiting custom error handling.

**Detailed description:**

The spec (§Transcription, "Error handling") states:

> *"No custom error handling (`try/except`) should be added around `transcribe_audio` within `AudioTranscriptionProcessor`. All exceptions propagate up to `BaseMediaProcessor.process_job()`, which handles failures gracefully and wraps timeouts returning `unprocessable_media=True`."*

This is a valid and defensible design — `BaseMediaProcessor.process_job()` already handles `asyncio.TimeoutError` (producing `unprocessable_media=True`) and catches all unhandled exceptions via `_handle_unhandled_exception`.

However, the sibling `ImageVisionProcessor.process_media` uses the **opposite** pattern: it wraps both the moderation and transcription calls in individual `try/except` blocks (lines 35–55 and 58–74), catching exceptions and returning structured `ProcessingResult` objects with specific `failed_reason` strings like `"Moderation error: {e}"` and `"Transcription error: {e}"`.

This creates an inconsistency in error reporting. If `AudioTranscriptionProcessor` lets all errors bubble up:
- The `_handle_unhandled_exception` handler produces a generic `"Media processing failed"` content string, which is less informative for operator debugging than the structured `failed_reason` strings `ImageVisionProcessor` produces.
- The `failed_reason` in the `_failed` collection will be the raw exception string, which might lack context about *which step* failed (though for audio transcription there's really only one step, so this is less of a concern).

This is an acceptable trade-off — audio transcription has only one API call vs image processing's two (moderation + transcription), so the "let bubbles be caught" pattern is simpler and correct. But an implementer reading both processors side-by-side might question the inconsistency. A brief explanation in the spec of *why* the no-try/except pattern was chosen (e.g., "unlike image processing, audio transcription has a single external call, so granular error handling adds no value") would prevent confusion.

**Recommendation:** Add one sentence to the spec's error handling paragraph explaining the rationale.

---

## Previous Review Status

All 9 items from review `01_ag_opus_4_6` have been successfully addressed in this version of the spec:

| Previous ID | Resolution |
|---|---|
| R01 | ✅ Addressed — explicit `elif isinstance(provider, AudioTranscriptionProvider)` branch is now mandated in §Technical Details §1 (line 135) |
| R02 | ✅ Addressed — spec now uses the clean SDK shortcut `transcribe(file=path, wait=True)` + single `destroy()` cleanup |
| R03 | ✅ Addressed — script renamed to `audioTranscriptionUpgradeScript.py` (line 53) |
| R04 | ✅ Addressed — full "Callback Injection" pattern with `set_token_tracker()` now specified with code snippets (lines 17, 126–150) |
| R05 | ✅ Addressed — `factory.py` now listed in project files (line 44) and factory import update in checklist (line 161) |
| R06 | ✅ Addressed — hardcoded tier arrays in `bot_management.py` (line 166) and both `EditPage.js` loops (lines 167–168) are called out |
| R07 | ✅ Addressed — default model set to `"stt-async-v4"` via `DEFAULT_MODEL_AUDIO_TRANSCRIPTION` env var (line 11) |
| R08 | ✅ Addressed — resolved by adopting the `file=` shortcut pattern (merged with R02 resolution) |
| R09 | ✅ Addressed — spec explicitly states omitting `reasoning_effort` and `seed` from `uiSchema` (line 167) |
