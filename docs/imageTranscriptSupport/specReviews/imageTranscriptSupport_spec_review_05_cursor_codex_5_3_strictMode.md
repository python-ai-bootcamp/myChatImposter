# Spec Review: imageTranscriptSupport

**Review ID:** 05_cursor_codex_5_3_strictMode  
**Spec File:** `/docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`  
**Date:** 2026-03-15

## Overall Assessment

The spec is directionally solid and close to implementation-ready, but several high-impact contract gaps remain between the proposed design and the current code architecture. Most importantly, the new `detail` setting can conflict with the current shared OpenAI provider initialization path, and response-shape handling is underspecified in a way that can break queue processing.

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| HIGH | ITS-23 | `detail` config integration is underspecified and can break `ChatOpenAI` initialization | [Details](#its-23-detail-config-integration-is-underspecified-and-can-break-chatopenai-initialization) | READY |
| HIGH | ITS-24 | Transcription output contract assumes string content but does not define normalization | [Details](#its-24-transcription-output-contract-assumes-string-content-but-does-not-define-normalization) | READY |
| MEDIUM | ITS-25 | Provider inheritance remains optional while callback-critical LLM instance reuse is mandatory | [Details](#its-25-provider-inheritance-remains-optional-while-callback-critical-llm-instance-reuse-is-mandatory) | READY |
| MEDIUM | ITS-26 | Migration target collection naming is ambiguous across code paths | [Details](#its-26-migration-target-collection-naming-is-ambiguous-across-code-paths) | READY |

---

## Detailed Findings

### ITS-23: `detail` config integration is underspecified and can break `ChatOpenAI` initialization

- **Priority:** HIGH
- **ID:** ITS-23
- **Title:** `detail` config integration is underspecified and can break `ChatOpenAI` initialization
- **Detailed Description:**  
  The spec introduces `detail` as part of the new image transcription config and encourages optional inheritance through `OpenAiChatProvider`. In the current code, `OpenAiChatProvider._build_llm_params()` serializes `provider_config` and forwards almost all keys directly into `ChatOpenAI(...)`, only removing a small known subset.

  If `detail` is implemented inside provider settings (`provider_config`), it is likely to be forwarded as an unknown constructor argument to `ChatOpenAI`, causing runtime failure before any transcription call. The spec does not define whether `detail` lives outside provider settings, or (if inside settings) where/how it is stripped before LLM construction.

  Since this is a startup/runtime correctness concern for every image transcription invocation, this should be specified explicitly.
- **Status:** READY
- **Required Actions:**  
  Introduce a shared OpenAI helper layer (mixin/base) used by both `OpenAiChatProvider` and `OpenAiImageTranscriptionProvider` to centralize API-key resolution, safe OpenAI LLM kwargs filtering, and cached `get_llm()` instance reuse. Keep `OpenAiImageTranscriptionProvider` as the concrete `ImageTranscriptionProvider` implementation (no sibling inheritance coupling), ensure transcription-only `detail` is never forwarded into `ChatOpenAI(...)` constructor kwargs and is used only when building the image payload in `transcribe_image(...)`, and add tests that verify `detail` filtering plus callback continuity on the same cached LLM instance.

### ITS-24: Transcription output contract assumes string content but does not define normalization

- **Priority:** HIGH
- **ID:** ITS-24
- **Title:** Transcription output contract assumes string content but does not define normalization
- **Detailed Description:**  
  The spec states that `transcribe_image` returns `response.content` and that the transcript is passed into normal queue flow as text. In the current architecture, queue messages (`Message.content`) are treated as plain strings and string size accounting/retention relies on this assumption.

  For multimodal responses, model SDK/LangChain content can be non-string or structured (e.g., content blocks). The spec does not define normalization rules (e.g., prefer plain text extraction, fallback behavior when content is non-text, or error strategy). Without this contract, implementers may pass non-string content into queue processing, causing subtle runtime/type issues.

  The spec should explicitly define a deterministic string-extraction policy for transcription responses before formatting placeholders.
- **Status:** READY
- **Required Actions:**  
  Define an explicit normalization contract in the spec: if `response.content` is a string, return it as-is; if it is content blocks, extract text-bearing blocks in original order and concatenate into a single deterministic string (e.g., single-space separator, trim outer whitespace); if it is neither string nor content blocks, return the hardcoded fallback `[Unable to transcribe image content]`. Also require a small test case that covers all three branches and verifies queue formatting always receives a plain string.

### ITS-25: Provider inheritance remains optional while callback-critical LLM instance reuse is mandatory

- **Priority:** MEDIUM
- **ID:** ITS-25
- **Title:** Provider inheritance remains optional while callback-critical LLM instance reuse is mandatory
- **Detailed Description:**  
  The spec still allows `OpenAiImageTranscriptionProvider` to extend `ImageTranscriptionProvider` "optionally via `OpenAiChatProvider`", while token tracking correctness depends on using the same cached LLM instance that receives callback attachment in `create_model_provider`.

  If an implementer does not inherit (or otherwise replicate) the exact cached-LLM behavior, the factory can attach callbacks to one LLM instance while `transcribe_image` invokes another, silently dropping token accounting. This is a repeatable contract hazard because the spec makes inheritance optional but makes the behavior mandatory.

  The spec should either require inheritance from a shared cached implementation or require an explicit normative contract that `get_llm()` must be idempotent and return the same in-memory instance for callback integrity.
- **Status:** READY
- **Required Actions:**  
  Make callback continuity an explicit normative contract in the spec: for image transcription providers, `get_llm()` must be idempotent and return the same cached in-memory LLM instance for the provider lifetime; the `TokenTrackingCallback` attached by `create_model_provider` must target that exact instance used later by `transcribe_image(...)`. Add a dedicated test that asserts callback attachment and transcription invocation use the same LLM object reference.

### ITS-26: Migration target collection naming is ambiguous across code paths

- **Priority:** MEDIUM
- **ID:** ITS-26
- **Title:** Migration target collection naming is ambiguous across code paths
- **Detailed Description:**  
  The spec asks for new migration scripts but does not explicitly pin collection names. In the current codebase, bot configs are read from `bot_configurations`, while global token menu lives in `configurations` (`COLLECTION_GLOBAL_CONFIGURATIONS`). Historical scripts in the repository also reference legacy names directly.

  Because this feature requires both bot-level config migration (`llm_configs.image_transcription`) and global token-menu patching, unclear collection targeting can lead to partially migrated environments (e.g., defaults patched but runtime still missing per-bot field, or token menu patched in the wrong collection).

  The spec should explicitly require using `infrastructure/db_schema.py` constants for all migrations and should enumerate which collection each migration must touch.
- **Status:** READY
- **Required Actions:**  
  Add an explicit spec-level collection contract for migrations: all migration scripts must import and use `infrastructure/db_schema.py` constants (no hardcoded collection names). Explicitly define that per-bot `image_transcription` tier migration targets `COLLECTION_BOT_CONFIGURATIONS`, while token menu tier migration targets `COLLECTION_GLOBAL_CONFIGURATIONS`. Include a short verification checklist in deployment steps (before/after counts and sample validation queries) to confirm both migrations applied successfully.

---
