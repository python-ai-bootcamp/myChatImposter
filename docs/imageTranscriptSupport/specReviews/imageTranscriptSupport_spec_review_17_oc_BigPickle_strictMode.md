# Spec Review: imageTranscriptSupport

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|-----|-------|------|--------|
| HIGH | 1 | Transcription normalization returns bracketed string contradicting spec design | [#1](#1-transcription-normalization-returns-bracketed-string) | READY |

---

## Detailed Issue Descriptions

### 1. Transcription normalization returns bracketed string

**Priority:** HIGH
**Status:** READY

**Location:** Spec line 38

**Description:** The transcription response normalization contract specifies:
- Line 36: "If `response.content` is `str`: return it as-is."
- Line 37: "If `response.content` is content blocks: extract text-bearing blocks..."
- Line 38: "If `response.content` is neither string nor content blocks: return `"[Unable to transcribe image content]"`."

The spec's own design principle (line 47) states: *"caption formatting is centralized"* and *"brackets are handled exclusively by `format_processing_result`"* - wrapping content in brackets `[<content>]` if and only if `result.unprocessable_media` is `True`.

By returning `"[Unable to transcribe image content]"` with brackets already included, line 38 violates this core design principle. If this error case sets `unprocessable_media=True` (which would be the expected behavior), `format_processing_result` would double-wrap it, producing `"[[Unable to transcribe image content]]"`.

**Required Actions:**
Change the spec on line 38 to explicitly state that it should return `"Unable to transcribe image content"` (no brackets). This ensures `format_processing_result` will handle the bracket wrapping cleanly without causing a double-bracketed string.

---

## Status

All other items in the spec are either:
- Implementation tasks (files to create, code to write)
- Well-defined requirements
- Deliberate design decisions

The spec is **ready for implementation** with the above fix applied.

**Items marked PENDING to be addressed:**
1. Fix line 38 to return unbracketed string
