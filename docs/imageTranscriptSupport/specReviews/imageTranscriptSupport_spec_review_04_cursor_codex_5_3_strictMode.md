# Spec Review: imageTranscriptSupport

**Review ID:** 04_cursor_codex_5_3_strictMode  
**Spec File:** `/docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`  
**Date:** 2026-03-15

## Overall Assessment

The spec is in strong shape and is generally solid enough to start implementation. It incorporates the major findings from prior reviews and aligns well with current project architecture (`ImageVisionProcessor`, provider factory flow, resolver usage, quota tracking, and migration patterns).

One substantial ambiguity remains in the provider inheritance/caching contract. It is important to resolve this before implementation to avoid silent token-tracking regressions for image transcription calls.

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| MEDIUM | ITS-22 | Provider inheritance is optional while callback-critical caching is specified only on `OpenAiChatProvider` | [Details](#its-22-provider-inheritance-is-optional-while-callback-critical-caching-is-specified-only-on-openaichatprovider) | PENDING |

---

## Detailed Findings

### ITS-22: Provider inheritance is optional while callback-critical caching is specified only on `OpenAiChatProvider`

- **Priority:** MEDIUM
- **ID:** ITS-22
- **Title:** Provider inheritance is optional while callback-critical caching is specified only on `OpenAiChatProvider`
- **Detailed Description:**  
  The spec's Technical Details section allows `OpenAiImageTranscriptionProvider` to extend `ImageTranscriptionProvider` "optionally via `OpenAiChatProvider`", while the token-tracking correctness guarantee relies on `get_llm()` caching behavior being present on the concrete provider instance used by `transcribe_image`.

  In the same section, caching is mandated specifically by changing `OpenAiChatProvider.get_llm()` to cache and reuse `self._llm`. This is correct **only if** the transcription provider inherits that implementation (directly or indirectly).  

  Because inheritance via `OpenAiChatProvider` is currently optional, an implementer may choose to implement `OpenAiImageTranscriptionProvider` directly from `ImageTranscriptionProvider` and return a fresh `ChatOpenAI` instance per `get_llm()` call. In that implementation, the callback attached by `create_model_provider` can still be lost before `transcribe_image()` invocation, recreating the same silent token-tracking failure this spec intends to prevent.
- **Status:** PENDING
- **Required Actions:** 

---
