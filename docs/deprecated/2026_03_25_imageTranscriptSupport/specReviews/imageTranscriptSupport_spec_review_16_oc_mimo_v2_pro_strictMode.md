# Spec Review: Image Transcription Support
## Review ID: 16_oc_mimo_v2_pro_strictMode

**Reviewer:** opencode (mimo-v2-pro-free)
**Date:** 2026-03-21
**Spec File:** [imageTranscriptSupport_specFile.md](../imageTranscriptSupport_specFile.md)

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|-----|-------|------|--------|
| CRITICAL | R01 | `_handle_unhandled_exception` formatting bypass after caption removal — `format_processing_result` call ordering must be explicitly guaranteed | [→ R01](#r01) | READY |
| CRITICAL | R02 | `ImageVisionProcessor` feature_name for transcription call must be `"image_transcription"` per spec but current code passes `"media_processing"` to moderation — transcription call path is entirely new | [→ R02](#r02) | READY |
| HIGH | R03 | Existing test `test_process_media_bot_id_signature` asserts `caption` parameter at position 4 — will break after spec removes `caption` from abstract signature | [→ R03](#r03) | READY |
| MEDIUM | R06 | `format_processing_result` module placement unspecified — spec references it but does not define where it should be implemented | [→ R06](#r06) | READY |
| MEDIUM | R07 | Frontend `EditPage.js` `uiSchema` template for `image_transcription` tier not explicitly provided — spec says "match other tiers exactly" but implementers need the exact template block | [→ R07](#r07) | READY |
| LOW | R08 | OpenAI `"original"` detail level only supported on `gpt-5.4+` — default model `gpt-5-mini` will error at runtime if misconfigured | [→ R08](#r08) | READY |

---

## Detailed Descriptions

<a id="r01"></a>
### R01: `_handle_unhandled_exception` formatting bypass after caption removal

**Priority:** CRITICAL
**Status:** READY

**Detailed Description:**
The spec states on line 48: *"The `result.content = format_processing_result(result, caption)` reassignment **must be executed first**, before calling `_persist_result_first`, `_archive_to_failed`, and the best-effort queue injection via `update_message_by_media_id`."*

This ordering constraint is correct and well-reasoned. However, the current `_handle_unhandled_exception` implementation (`base.py:121-140`) has three downstream consumers of `result.content`:

```python
result = ProcessingResult(content="[Media processing failed]", failed_reason=error)  # step 1
persisted = await self._persist_result_first(job, result, db)                        # step 2
if persisted:
    await self._archive_to_failed(job, result, db)                                   # step 3
# ...
delivered = await bot_queues.update_message_by_media_id(..., result.content)          # step 4
```

After the spec's changes, `result` will be `ProcessingResult(content="Media processing failed", failed_reason=error, unprocessable_media=True)`. The spec requires `format_processing_result(result, caption)` to be called before step 2, so steps 2, 3, and 4 all read the formatted `result.content`.

The spec correctly identifies this on line 48. However, the caption source inside `_handle_unhandled_exception` is `job.placeholder_message.content` — the spec mentions this on line 48 but does not explicitly show the code pattern. Implementers need to see that:
1. `caption = job.placeholder_message.content`
2. `result.content = format_processing_result(result, caption)` must come BEFORE `_persist_result_first`

If this ordering is not implemented correctly, the `_failed` archive collection will store unformatted content (missing brackets and captions), and the queue delivery will also show raw unformatted content to the user.

**Required Actions:**
Add an explicit code example to the spec showing the exact pattern and ordering for `_handle_unhandled_exception` without the redundant `or ""` check:
```python
async def _handle_unhandled_exception(self, job, db, error, get_bot_queues=None):
    caption = job.placeholder_message.content
    result = ProcessingResult(content="Media processing failed", failed_reason=error, unprocessable_media=True)
    result.content = format_processing_result(result, caption)  # MUST be first, before persistence
    persisted = await self._persist_result_first(job, result, db)
    ...
```

---

<a id="r02"></a>
### R02: `ImageVisionProcessor` feature_name for transcription — dual provider creation pattern

**Priority:** CRITICAL
**Status:** READY

**Detailed Description:**
The spec on line 32 states: *"The `feature_name` passed to `create_model_provider` for this transcription call must be `"image_transcription"` (the second argument) to enable fine-grained token tracking. The moderation call should continue passing `"media_processing"` as its `feature_name`."*

The current `ImageVisionProcessor.process_media` (`image_vision_processor.py:20-27`) only makes ONE `create_model_provider` call for moderation. After the spec's changes, `process_media` will make TWO calls:
1. `create_model_provider(bot_id, "media_processing", "image_moderation")` — for moderation (existing)
2. `create_model_provider(bot_id, "image_transcription", "image_transcription")` — for transcription (new)

The spec correctly describes this, but does not explicitly state that TWO separate provider instances are created. This is an important architectural detail because:
- Each call instantiates a NEW provider with a NEW `TokenTrackingCallback`
- The moderation provider uses `AsyncOpenAI` directly (raw SDK)
- The transcription provider uses `ChatOpenAI` via LangChain
- They share no state or instances

This is a deliberate, correct design (no shared state between moderation and transcription). However, implementers should be aware that this means two separate API clients are created per image processed.

**Required Actions:**
Add an explicit clarification note to the `Processing Flow` or `Transcription` section of the spec, stating: *"Note: This architecture intentionally instantiates two separate provider instances per image processed (one for moderation using `AsyncOpenAI`, one for transcription using `ChatOpenAI`), ensuring a clear separation of concerns and exact token tracking per feature. Also note that image moderation doesn't even really do token tracking behind the scenes."*

---

<a id="r03"></a>
### R03: Existing test `test_process_media_bot_id_signature` will break

**Priority:** HIGH

**Detailed Description:**
The existing test in `tests/test_image_vision_processor.py:20-26` checks:
```python
params = list(inspect.signature(cls.process_media).parameters.values())
fourth = params[4]  # self=0, file_path=1, mime_type=2, caption=3, bot_id=4
assert fourth.name == "bot_id"
```

The spec requires removing the `caption` parameter from `process_media` in `BaseMediaProcessor` and ALL subclasses. After this change, the signature becomes `process_media(self, file_path, mime_type, bot_id)` — `bot_id` moves from position 4 to position 3. The test hardcodes `params[4]` and will crash with an `IndexError`.

Additionally, the spec on line 300 mentions: *"Update all existing automated tests covering `StubSleepProcessor`, along with other stubs and success-path implementations, to assert that successfully processed media returns plain, unbracketed strings."* This is the correct direction but does not explicitly mention THIS specific test.

**Required Actions:**
Add an explicit bullet point to the "Test Expectations" section of the spec detailing that `test_process_media_bot_id_signature` must precisely be updated: change the hardcoded index from `params[4]` to `params[3]` and verify the updated assertion correctly checks for `"bot_id"` due to the removal of the `caption` parameter.

---

<a id="r06"></a>
### R06: `format_processing_result` module placement unspecified

**Priority:** MEDIUM
**Status:** READY

**Detailed Description:**
The spec references `format_processing_result(result: ProcessingResult, caption: str) -> str` on lines 39, 47, and 48. It defines the function as:
- A **pure function** (returns string without mutating `result`)
- Wraps content in brackets `[<content>]` if `result.unprocessable_media is True`
- Always appends `\n[Caption: <caption_text>]` if caption exists

However, the spec does not specify WHERE this function should be implemented. Options:
1. As a method on `BaseMediaProcessor` in `media_processors/base.py` — closest to where it's used
2. As a module-level function in `media_processors/base.py` — pure function style
3. In a new utility module — separated concern
4. In `infrastructure/models.py` alongside `ProcessingResult` — co-located with the data model

The most natural placement is either `media_processors/base.py` (module-level function, since it's pure) or `infrastructure/models.py` (co-located with `ProcessingResult`). Either works, but the spec should be explicit to prevent inconsistency.

**Required Actions:**
Add an explicit instruction to the spec defining that `format_processing_result(result: ProcessingResult, caption: str) -> str` must be implemented as a module-level function inside `media_processors/base.py`.

---

<a id="r07"></a>
### R07: Frontend `uiSchema` template for `image_transcription` not explicitly shown

**Priority:** MEDIUM
**Status:** READY

**Detailed Description:**
The spec on line 286 states: *"Statically add a fourth entry to the `llm_configs` object in `uiSchema` for `image_transcription`. The `ui:title` should be `"Image Transcription Model"`, and the rest of the template configuration should match the other tiers exactly."*

The current `EditPage.js` `uiSchema` (`frontend/src/pages/EditPage.js:392-493`) has three tier entries with identical structure:
```javascript
high: {
    "ui:title": "High Model",
    "ui:ObjectFieldTemplate": NestedCollapsibleObjectFieldTemplate,
    provider_config: {
        "ui:ObjectFieldTemplate": FlatProviderConfigTemplate,
        api_key_source: { ... },
        reasoning_effort: { ... },
        seed: { ... },
    }
},
low: { /* same structure */ },
image_moderation: { /* same structure */ },
```

The spec does not provide the explicit `image_transcription` entry. While "match other tiers exactly" is clear for experienced developers, the `image_transcription` tier has an ADDITIONAL field (`detail`) that the other tiers don't have. The spec should clarify:
1. Does `detail` get its own UI widget in the `uiSchema`?
2. What should `detail`'s `ui:title` be?
3. Should it use `FlatProviderConfigTemplate` or a different template?

**Required Actions:**
Update the spec to include a textual rule clarifying the `detail` property: *"Include the `detail` field inside `provider_config` with a `ui:title` of `"Image Detail Level"`, while matching the structure of the other fields exactly."*

---

<a id="r08"></a>
### R08: OpenAI `"original"` detail level model compatibility

**Priority:** LOW

**Detailed Description:**
The spec on line 255 states: *"Valid values: `\"low\"`, `\"high\"`, `\"original\"`, `\"auto\"`."* It also states: *"The decision to omit validation for the `\"original\"` detail level against the configured model is an **accepted, deliberate design choice**."*

Per the OpenAI vision documentation:
- `"original"` detail level is only supported on `gpt-5.4` and future models
- Models like `gpt-5-mini`, `gpt-5.4-mini`, `o4-mini`, etc. only support `low`, `high`, and `auto`
- The default model for image transcription is `gpt-5-mini` (line 12)

If a user configures `detail: "original"` on a bot using `gpt-5-mini`, the OpenAI API will return an error. The spec correctly accepts this as a deliberate design choice — the error propagates through the standard error handling path.

However, this should be documented in the configuration UI (the `detail` field description/tooltip) to inform users which detail levels are model-dependent.

**Required Actions:**
No functional changes are needed because the lack of validation is an accepted design choice. Update the spec to add an explicit comment confirming that *"this runtime error behavior for mismatched detail levels and models is a known and acceptable behavior that was already approved in this specification."*

---

