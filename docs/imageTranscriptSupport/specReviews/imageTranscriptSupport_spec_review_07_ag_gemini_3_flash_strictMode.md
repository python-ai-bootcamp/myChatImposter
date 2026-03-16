# Spec Review: Image Transcript Support (07_ag_gemini_3_flash_strictMode)

## Summary Table

| Priority | ID | Title | Link | Status |
| :--- | :--- | :--- | :--- | :--- |
| P1 | ISSUE_02 | Missing Schema Surgery for `llm_configs` in `bot_management.py` | [#issue_02](#issue_02) | READY |
| P2 | GAP_01 | `ImageVisionProcessor` Return Content Consistency | [#gap_01](#gap_01) | READY |
| P3 | LINT_01 | Resolver Overload Return Type Precision | [#lint_01](#lint_01) | READY |

---

## Detailed Findings


<a id="issue_02"></a>
### [P1] ISSUE_02: Missing Schema Surgery for `llm_configs` in `bot_management.py`
**Title:** Missing Schema Surgery for `llm_configs` in `bot_management.py`
**Detailed Description:**
`routers/bot_management.py` (line 364) currently iterates over a hardcoded list: `for prop_name in ['high', 'low', 'image_moderation']:`. The spec (Section 1.17 and 4.3) requires this to be dynamic using `LLMConfigurations.model_fields.keys()`. Failing to update this will result in the `image_transcription` tier appearing with an unwanted `anyOf` dropdown (including a `null` option) in the UI, breaking the "Premium Design" requirement.
**Status:** READY
**Required Actions:**
1. Create a centralized list of configuration tiers in a shared location (e.g., `config_models.py` or a new constants file).
2. Refactor `routers/bot_management.py` to iterate over this shared list during schema surgery.
3. Ensure `LLMConfigurations` and `ConfigTier` also reference this shared source of truth where possible.

<a id="gap_01"></a>
### [P2] GAP_01: `ImageVisionProcessor` Return Content Consistency
**Title:** `ImageVisionProcessor` Return Content Consistency
**Detailed Description:**
The current `ImageVisionProcessor.process_media` returns a hardcoded placeholder (line 30). The spec requires a specific format (Section 34-47) involving attachments and captions. While the spec mentions using the "base media processor existing mechanism", `base.py` doesn't explicitly handle the caption-appending logic (only `resolve_media_path` and result persistence). This logic must be explicitly added to `ImageVisionProcessor` or a shared utility.
**Status:** READY
**Required Actions:**
1. Refactor `BaseMediaProcessor.process_job` to perform caption concatenation on the `result.content` before it is persisted and delivered.
2. Update `BaseMediaProcessor._handle_unhandled_exception` to similarly concatenate the original caption with the standard `[Media processing failed]` placeholder.
3. Ensure the formatting follows the specification: `[Attached image description: <transcription>]\n[Image caption: <caption>]` for success, and `[Media processing failed]\n[Image caption: <caption>]` for failure scenarios.


<a id="lint_01"></a>
### [P3] LINT_01: Resolver Overload Return Type Precision
**Title:** Resolver Overload Return Type Precision
**Detailed Description:**
The spec (Section 4.2) suggests adding an `@overload` for `resolve_model_config`. Currently, `resolver.py` (lines 17-19) returns `ChatCompletionProviderConfig` for `high`/`low` and `BaseModelProviderConfig` for `image_moderation`. The new overload should return `ImageTranscriptionProviderConfig` specifically, ensuring type safety for callers who expect the `detail` field.
**Status:** READY
**Required Actions:**
1. Add an `@overload` decoration to `resolve_model_config` in `services/resolver.py` that specifically handles the `"image_transcription"` literal.
2. Ensure the overload return type is imported as `ImageTranscriptionProviderConfig` to provide precise autocompletion and type checking for the `detail` parameter.
