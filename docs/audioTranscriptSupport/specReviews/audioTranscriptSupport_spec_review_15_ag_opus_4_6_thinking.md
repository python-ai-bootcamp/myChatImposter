# Spec Review: audioTranscriptSupport — Review 15_ag_opus_4_6_thinking

**Reviewer:** Opus 4.6 (Thinking)
**Date:** 2026-04-04
**Spec Version Reviewed:** Current `audioTranscriptSupport_specFile.md`

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| HIGH | R15-01 | `ImageVisionProcessor` moderation error path already sets `unprocessable_media=True` — companion fix is partially redundant | [Details](#r15-01) | READY |
| MEDIUM | R15-02 | `_handle_unhandled_exception` spec says to pass `mime_type=job.mime_type` but contradicts the new `format_processing_result` signature | [Details](#r15-02) | READY |
| MEDIUM | R15-03 | Spec snippet calls `stt.create(config=config, file_id=file.id)` but SDK `create` signature takes `CreateTranscriptionConfig` — verify `file_id` is a valid parameter for `create()` vs. being part of the config | [Details](#r15-03) | READY |
| LOW | R15-04 | `display_media_type` added to `ProcessingResult` dataclass but not listed in `infrastructure/models.py` changes | [Details](#r15-04) | READY |

---

## Detailed Findings

---

### <a id="r15-01"></a>R15-01: `ImageVisionProcessor` moderation error path already sets `unprocessable_media=True` — companion fix is partially redundant

**Priority:** HIGH

**ID:** R15-01

**Title:** `ImageVisionProcessor` moderation error path already sets `unprocessable_media=True` — companion fix is partially redundant

**Detailed Description:**

The spec's Companion Fixes section (line 37) states:

> *You must also add `unprocessable_media=True` to BOTH error-path `ProcessingResult` returns in `image_vision_processor.py` (moderation API crash and transcription API crash)*

However, examining the actual `image_vision_processor.py` code, the **moderation flagged** path (line 46-49) already **correctly** sets `unprocessable_media=True`:

```python
return ProcessingResult(
    content="Image flagged by content moderation",
    unprocessable_media=True,
)
```

The two error paths that *lack* `unprocessable_media=True` are:
1. **Moderation API crash** (line 52-55) — correctly identified, this needs the fix.
2. **Transcription API crash** (line 71-74) — correctly identified, this needs the fix.

The spec's wording of "BOTH error-path `ProcessingResult` returns" is accurate (there are indeed two `except` blocks), but could be misinterpreted by a developer who counts the `flagged` return as one of the "error paths", since moderation flagging is semantically an error/rejection scenario. This is a precision issue in the spec language — the spec says "error-path", which correctly refers to the `except` blocks, not the `flagged` path. However, a developer unfamiliar with the distinction might waste time trying to add `unprocessable_media=True` to a line that already has it.

**Recommendation:** Add a clarifying note like: *"(the existing `flagged=True` moderation return already correctly sets `unprocessable_media=True` and requires no change)"* to prevent implementer confusion.

**Status:** READY

**Required Actions:** Add a clarifying parenthetical to the spec's Companion Fixes → ImageVisionProcessor bullet: *"(Note: the existing `flagged=True` moderation return at line 46 already correctly sets `unprocessable_media=True` and requires no change; only the two `except` blocks need updating.)"*

---

### <a id="r15-02"></a>R15-02: `_handle_unhandled_exception` spec says to pass `mime_type=job.mime_type` but contradicts the new `format_processing_result` signature

**Priority:** MEDIUM

**ID:** R15-02

**Title:** `_handle_unhandled_exception` spec contradicts itself regarding `display_media_type` parameter forwarding

**Detailed Description:**

The spec introduces `display_media_type` as an optional parameter to `format_processing_result` (line 46), stating:

> *if a processor provides this, the formatter must use it directly instead of attempting to parse the `mime_type`*

The spec also states in the Companion Fixes section (line 41) for `_handle_unhandled_exception`:

> *Modify the fallback error handling in `BaseMediaProcessor._handle_unhandled_exception` to explicitly pass `unprocessable_media=True` and `mime_type=job.mime_type` to `format_processing_result`*

However, in the `_handle_unhandled_exception` method, no `ProcessingResult` with a `display_media_type` is produced (the raw `ProcessingResult` is created inline). The spec doesn't explicitly state whether `display_media_type` should also be forwarded in this path. Looking at the `process_job` call site (line 46), the spec says:

> *(1) `BaseMediaProcessor.process_job()` must pass `job.mime_type` and `result.display_media_type` to all calls to `format_processing_result`*

This means `process_job()` passes `result.display_media_type` from the processor's result. But `_handle_unhandled_exception` creates its own `ProcessingResult` internally (not from a processor result). The spec says this path should pass `unprocessable_media=True`, which means the prefix won't be injected regardless — so the `display_media_type` parameter is irrelevant here. This is **logically consistent**, but the spec doesn't explicitly connect these dots. An implementer might be confused about whether `display_media_type` needs to be handled in the unhandled exception path.

**Recommendation:** Add a brief note to the `_handle_unhandled_exception` bullet clarifying that `display_media_type` is irrelevant in this path since `unprocessable_media=True` suppresses prefix injection entirely.

**Status:** READY

**Required Actions:** Add a clarifying note to the `_handle_unhandled_exception` bullet indicating: *"(`display_media_type` does not need to be forwarded in this path since `unprocessable_media=True` suppresses prefix injection entirely.)"*

---

### <a id="r15-03"></a>R15-03: Spec snippet calls `stt.create(config=config, file_id=file.id)` but this needs SDK verification

**Priority:** MEDIUM

**ID:** R15-03

**Title:** Verify SDK `stt.create()` method accepts `file_id` as a separate keyword argument alongside `config`

**Detailed Description:**

The spec's reference snippet (line 145) uses:

```python
transcription = await self.client.stt.create(config=config, file_id=file.id)
```

This passes `file_id` as a separate keyword argument to `stt.create()`. However, if we look at the Soniox SDK documentation for async transcription, the convenience wrapper `transcribe()` is what accepts `file_id` directly. The lower-level `create()` method may expect `file_id` to be part of the configuration object itself, or it may accept it as a separate argument — the documentation doesn't explicitly show the `create()` signature with both `config` and `file_id` separately.

Looking at the SDK docs, the quickstart uses `client.stt.transcribe(model="stt-async-v4", file_id="uploaded-file-id")` as the convenience method. The spec explicitly rejects using `transcribe()` in favor of the manual 4-step pattern. The `stt.create()` method with `config=` and `file_id=` as separate arguments is plausible but not explicitly documented in the public SDK docs.

The spec does include a note (line 175): *"The `CreateTranscriptionConfig` object from the Soniox `soniox.types` package has been verified to explicitly accept the `model` parameter in its constructor"* — but this verification note only covers the `model` parameter on `CreateTranscriptionConfig`, not the `file_id` parameter on `stt.create()`.

If `stt.create()` does **not** accept `file_id` as a separate keyword, the implementation will crash at runtime with a `TypeError`.

**Recommendation:** Add an explicit verification note (similar to the existing one about `CreateTranscriptionConfig`) confirming that `stt.create(config=..., file_id=...)` is the verified call signature. If the SDK actually expects `file_id` inside the config, the snippet needs to be updated.

**Status:** READY

**Required Actions:** Add an explicit verification instruction near the snippet: *"The implementer MUST verify the `stt.create` call signature directly in the Soniox SDK source code to ensure `file_id` is accepted as a parameter in `create()` (as written in the snippet) rather than within the `CreateTranscriptionConfig` object. Adjust the exact snippet syntax during implementation if necessary."*

---

### <a id="r15-04"></a>R15-04: `display_media_type` added to `ProcessingResult` dataclass but not listed in project file changes

**Priority:** LOW

**ID:** R15-04

**Title:** `infrastructure/models.py` not listed in "Relevant Background Information" despite requiring modification

**Detailed Description:**

The spec (line 46) states:

> *Add an optional `display_media_type: str = None` attribute to the `ProcessingResult` dataclass*

The `ProcessingResult` dataclass is defined in `infrastructure/models.py` (line 22-27 of that file):

```python
@dataclass
class ProcessingResult:
    content: str
    failed_reason: Optional[str] = None
    unprocessable_media: bool = False
```

However, `infrastructure/models.py` is **not** listed in the spec's "Relevant Background Information" → "Project Files" section (lines 49-64). This is a minor documentation gap — the file will clearly need modification (adding the `display_media_type` field), but an implementer following the project files list strictly might overlook it.

**Recommendation:** Add `infrastructure/models.py` to the "Project Files" list with a note *(modify — add `display_media_type` to `ProcessingResult`)*.

**Status:** READY

**Required Actions:** Add `infrastructure/models.py` to the "Project Files" list with a parenthetical note indicating it needs modification: *(modify — add `display_media_type` to `ProcessingResult`)*.

---

## Overall Assessment

The spec is **solid and well-structured** for implementation. The level of detail in the provider architecture, cleanup patterns, companion fixes, and deployment checklist demonstrates deep understanding of the existing codebase. The items above are mostly **precision/clarity issues** rather than fundamental design flaws:

- **R15-01** (HIGH) is about preventing implementer confusion, not a correctness bug.
- **R15-02** (MEDIUM) and **R15-04** (LOW) are documentation completeness gaps.
- **R15-03** (MEDIUM) is the only item with potential runtime impact — if the `stt.create()` signature assumption is wrong, it would cause a crash. This should be verified against the actual SDK source before implementation begins.

The core architectural decisions (sibling provider pattern, background task cleanup, token estimation, prefix injection refactoring, `unprocessable_media` companion fixes) are all sound and consistent with the existing codebase patterns.
