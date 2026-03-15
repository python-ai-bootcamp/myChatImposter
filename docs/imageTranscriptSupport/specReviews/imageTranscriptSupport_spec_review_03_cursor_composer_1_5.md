# Spec Review: imageTranscriptSupport

**Review ID:** 03_cursor_composer_1_5  
**Spec File:** `/docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`  
**Date:** 2026-03-15

## Overall Assessment

The spec is in strong shape and ready for implementation. It incorporates the findings from prior reviews (01 and 02): flagged-image behavior, `detail` parameter with `"original"` support, transcription prompt, provider architecture extending `ChatCompletionProvider`, caption handling, and deployment checklist. The design aligns well with the existing codebase patterns (`ImageModerationProvider`, `resolve_model_config`, `create_model_provider`, migration scripts).

Three items were identified that should be addressed before or during implementation. None are blocking; the spec is solid enough to proceed.

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| MEDIUM | ITS-12 | token_menu update missing from Deployment Checklist | [Details](#its-12-token_menu-update-missing-from-deployment-checklist) | PENDING |
| MEDIUM | ITS-13 | Schema surgery for image_transcription in get_configuration_schema | [Details](#its-13-schema-surgery-for-image_transcription-in-get_configuration_schema) | PENDING |
| LOW | ITS-14 | transcribe_image async signature not explicit | [Details](#its-14-transcribe_image-async-signature-not-explicit) | PENDING |

---

## Detailed Findings

### ITS-12: token_menu update missing from Deployment Checklist

- **Priority:** MEDIUM
- **ID:** ITS-12
- **Title:** token_menu update missing from Deployment Checklist
- **Detailed Description:**  
  The Requirements section states: *"global_configurations.token_menu is extended with an 'image_transcription' pricing entry so vision usage is tracked and priced under the correct tier."*

  The Deployment Checklist (§3) lists four items: migration script, `DefaultConfigurations`, `get_bot_defaults`, and Pydantic `default_factory`. It does **not** include a step to add the `"image_transcription"` entry to the `token_menu` document in the global configurations collection.

  Without this, `QuotaService.calculate_cost(config_tier="image_transcription", ...)` will hit the fallback branch (`config_tier not in self._token_menu`) and return `0.0`, so vision tokens will not be priced or counted toward user quotas. The `TokenTrackingCallback` will still record events with `config_tier="image_transcription"`, but cost calculation will be zero.

  The `token_menu` is stored in the `configurations` collection (per `COLLECTION_GLOBAL_CONFIGURATIONS`) with `_id: "token_menu"`. The structure is `{ high: {...}, low: {...} }` where each tier has `input_tokens`, `output_tokens`, `cached_input_tokens` (per 1M tokens). The `initialize_quota_and_bots.py` script creates this document but does not include `image_moderation` or `image_transcription`. A migration or initialization step is needed to add the `image_transcription` entry.
- **Status:** PENDING
- **Required Actions:** Add a fifth item to the Deployment Checklist: update the `token_menu` document in the global configurations collection to include an `"image_transcription"` entry with appropriate pricing (input_tokens, output_tokens, cached_input_tokens per 1M tokens). This can be done via a migration script (e.g., `scripts/migrate_image_transcription.py` or a separate `migrate_token_menu_image_transcription.py`) or by extending `initialize_quota_and_bots.py` to add the entry when creating/updating the token_menu. Vision pricing differs from text; refer to OpenAI's vision pricing documentation for values.

---

### ITS-13: Schema surgery for image_transcription in get_configuration_schema

- **Priority:** MEDIUM
- **ID:** ITS-13
- **Title:** Schema surgery for image_transcription in get_configuration_schema
- **Detailed Description:**  
  In `routers/bot_management.py`, the `get_configuration_schema` endpoint applies schema patching to ensure `LLMConfigurations` properties are not optional in the generated JSON Schema. The relevant loop at line 364 is:

  ```python
  for prop_name in ['high', 'low', 'image_moderation']:
  ```

  This iterates over the LLM config tier names to fix `anyOf`/`null` patterns so the UI does not show a redundant optional dropdown. When `image_transcription` is added to `LLMConfigurations`, this list must be extended to include `'image_transcription'`. Otherwise, the schema for the new tier may render with confusing optional semantics in the frontend form.
- **Status:** PENDING
- **Required Actions:** Add `'image_transcription'` to the `prop_name` list in the schema surgery loop within `get_configuration_schema` (around line 364 in `routers/bot_management.py`).

---

### ITS-14: transcribe_image async signature not explicit

- **Priority:** LOW
- **ID:** ITS-14
- **Title:** transcribe_image async signature not explicit
- **Detailed Description:**  
  The spec states that `ImageTranscriptionProvider` declares `transcribe_image(base64_image, mime_type) -> str` as an abstract method. The implementation will invoke the LLM via LangChain's `ainvoke`, which is asynchronous. Therefore, the method must be `async def transcribe_image(...) -> str`, and callers (e.g., `ImageVisionProcessor.process_media`) must `await` it.

  The spec does not explicitly show the `async` keyword. The existing `ImageModerationProvider.moderate_image` is `async`, so the pattern is established. Making the async nature explicit in the spec avoids implementer ambiguity.
- **Status:** PENDING
- **Required Actions:** In the Technical Details §1 (Provider Architecture), explicitly specify `async def transcribe_image(base64_image: str, mime_type: str) -> str` for the abstract method signature.

---
