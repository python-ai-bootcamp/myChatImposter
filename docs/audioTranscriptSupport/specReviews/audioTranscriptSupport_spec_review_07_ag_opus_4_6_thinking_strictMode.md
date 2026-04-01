# Spec Review: Audio Transcription Support

**Review ID:** `07_ag_opus_4_6_thinking_strictMode`
**Spec File:** `docs/audioTranscriptSupport/audioTranscriptSupport_specFile.md`
**Reviewer:** Antigravity (Claude Opus 4, Thinking, Strict Mode)
**Date:** 2026-03-31

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| HIGH | R07-01 | Spec enumerates a 4-step async pattern but step numbering lists 4 steps while spec line says "3-step" | [Details](#r07-01) | READY |
| HIGH | R07-02 | `_handle_unhandled_exception` passes `unprocessable_media=False` contradicting explicit spec requirement | [Details](#r07-02) | READY |
| HIGH | R07-03 | `TimeoutError` handler in `process_job` does not set `unprocessable_media=True` as spec requires | [Details](#r07-03) | READY |
| MEDIUM | R07-04 | Soniox SDK `destroy()` method could replace manual two-step cleanup of transcription + file | [Details](#r07-04) | READY |
| MEDIUM | R07-05 | `DEFAULT_POOL_DEFINITIONS` expansion is incomplete — spec omits `audio/aiff`, `audio/m4a`, and `audio/asf` despite Soniox support | [Details](#r07-05) | READY |
| MEDIUM | R07-06 | `resolver.py` refactor to dictionary-based registry will silently return `ChatCompletionProviderConfig` for unknown tiers | [Details](#r07-06) | READY |
| LOW | R07-07 | `AudioTranscriptionProviderSettings` inherits from `BaseModelProviderSettings` but spec doesn't address `record_llm_interactions` field leakage | [Details](#r07-07) | READY |

---

## Detailed Review Items

---

### <a id="r07-01"></a>R07-01: Spec enumerates a 4-step async pattern but describes it as "3-step"

**Priority:** HIGH

**Detailed Description:**

The spec (line 29) states:

> "Start transcription using the explicit **3-step** async pattern: (1) `file = await client.files.upload(file_path)`, (2) `transcription = await client.stt.create(config=..., file_id=file.id)`, (3) `await client.stt.wait(transcription.id)`, (4) `transcript = await client.stt.get_transcript(transcription.id)`."

This sentence labels the pattern as "3-step" but then proceeds to enumerate **4 distinct steps** (upload → create → wait → get_transcript). The mismatch between the label and the enumeration is a clear contradiction that could confuse the implementer about whether one of these steps is intended to be omitted or combined.

Furthermore, the Soniox SDK documentation reveals that `client.stt.create` is the correct method name for creating an async transcription job (as opposed to `client.stt.transcribe` which is the convenience wrapper the spec explicitly prohibits). The spec's code snippet on lines 133–135 correctly uses `client.stt.create`, but the textual description's "3-step" label creates ambiguity as to whether `wait` + `get_transcript` should be considered a single conceptual step or whether `upload` is being excluded from the count.

**Status:** READY

**Required Actions:**
- **Action:** Update the specification language on line 29 from "Start transcription using the explicit 3-step async pattern" to "Start transcription using the explicit **4-step** async pattern". This explicitly resolves the contradiction.

---

### <a id="r07-02"></a>R07-02: `_handle_unhandled_exception` passes `unprocessable_media=False` contradicting spec requirement

**Priority:** HIGH

**Detailed Description:**

The spec (line 40, final sentence of the Output Format section) explicitly states:

> "Furthermore, modify the fallback error handling in `BaseMediaProcessor._handle_unhandled_exception` to explicitly set `unprocessable_media=True` (it currently defaults to False) so that unhandled system errors are correctly flagged as unprocessable media and safely bypass the prefix injection logic."

Examining the current codebase in `media_processors/base.py` at line 190, the `_handle_unhandled_exception` method explicitly passes `unprocessable_media=False`:

```python
formatted = format_processing_result(
    content=raw.content,
    caption=job.placeholder_message.content,
    original_filename=job.original_filename,
    unprocessable_media=False,   # <-- contradicts spec requirement
)
```

This is a real bug that the spec correctly identifies must be fixed. However, the broader concern is the **interaction between this fix and the new prefix injection logic**. When `_handle_unhandled_exception` fires, the current code produces output like `[Media processing failed]\n<caption>`. After the spec's prefix injection refactoring, if `unprocessable_media` remains `False` here, the output would become `[Audio Transcription: Media processing failed]\n<caption>` — prepending a success-like "Audio Transcription:" prefix to an error message, which is semantically nonsensical and would confuse both operators reading logs and bots parsing the message content.

The spec correctly identifies this must be `True`, but this is a critical fix that must not be overlooked during implementation, as the consequences are user-visible (corrupt message formatting).

**Status:** READY

**Required Actions:**
- **Action:** Add a new explicit requirement to the "Testing / Deployment Checklist" section to include a unit test that verifies `BaseMediaProcessor._handle_unhandled_exception` correctly sets `unprocessable_media=True` and produces the expected output formatting (i.e., no prefix is incorrectly prepended to the system error message).

---

### <a id="r07-03"></a>R07-03: `TimeoutError` handler in `process_job` does not set `unprocessable_media=True`

**Priority:** HIGH

**Detailed Description:**

The spec (line 35) states:

> "**Base Processor Global Update**: Update `BaseMediaProcessor.process_job()`'s existing `asyncio.TimeoutError` exception block to explicitly include `unprocessable_media=True` when returning its `ProcessingResult`. This enforces the timeout expectation system-wide."

Looking at the current code in `media_processors/base.py` lines 84–88:

```python
except asyncio.TimeoutError:
    result = ProcessingResult(
        content="Processing timed out",
        failed_reason=f"TIMEOUT: processing exceeded {self.processing_timeout}s",
    )
```

The `ProcessingResult` dataclass defaults `unprocessable_media=False` (verified in `infrastructure/models.py` line 26). This means the current timeout handler will, after the prefix injection refactoring, produce messages like `[Audio Transcription: Processing timed out]` — which misleadingly implies a successful transcription occurred when the processing actually timed out.

The same logic applies system-wide: image timeouts would produce `[Image Transcription: Processing timed out]`, which is semantically incorrect.

This change is critical because it is a **global behavioral change** affecting all media processors (audio, image, video, document), not just the new audio transcription processor. The spec correctly identifies this but it must be coordinated carefully to avoid regression.

**Status:** READY

**Required Actions:**
- **Action:** Add a new explicit requirement to the "Testing / Deployment Checklist" section to include a unit test that verifies `BaseMediaProcessor.process_job` correctly handles `asyncio.TimeoutError` by setting `unprocessable_media=True`, thereby suppressing prefix injection across all processor types.

---

### <a id="r07-04"></a>R07-04: Soniox SDK `destroy()` method could replace manual two-step cleanup

**Priority:** MEDIUM

**Detailed Description:**

The spec (line 31) prescribes a manual two-step cleanup in the `finally` block:

```python
async def _cleanup():
    if transcription:
        try: await self.client.stt.delete(transcription.id)
        except Exception: pass
    if file:
        try: await self.client.files.delete(file.id)
        except Exception: pass
asyncio.create_task(_cleanup())
```

However, the Soniox Python SDK documentation (confirmed from the "Delete or destroy transcription" section) exposes a `client.stt.destroy(transcription_id)` convenience method that:

> "Delete transcription **and its file** if it was uploaded."

This single call `await self.client.stt.destroy(transcription.id)` would atomically delete both the transcription job and its associated uploaded file, reducing the cleanup from two network calls to one and eliminating the window where the transcription is deleted but the file remains (or vice versa).

The spec's two-step approach works correctly, but the `destroy()` method is more robust and reduces the probability of quota leak under partial failure scenarios. However, there is a subtlety: if the transcription job creation itself failed (step 2) but the file upload succeeded (step 1), `destroy()` cannot be called because there's no `transcription.id`. In that case, only `client.files.delete(file.id)` would be needed. So the cleanup logic should be:

1. If `transcription` exists → call `destroy(transcription.id)` (handles both transcription + file)
2. If only `file` exists (transcription creation failed) → call `files.delete(file.id)`

This is a design simplification opportunity, not a correctness bug.

**Status:** READY

**Required Actions:**
- **Action:** Add an explicit architectural note to the spec explaining that while the Soniox SDK offers a convenience `destroy()` method that deletes both the transcription and its file, this is intentionally **rejected** in favor of the manual 2-step `finally` block. The spec must clarify that because the explicit 4-step upload pattern is used, a failure during job creation (Step 2) leaves an uploaded `file` but no `transcription.id`, rendering `destroy()` useless and leaking the file. The explicit 2-step cleanup is required for correctness.

---

### <a id="r07-05"></a>R07-05: `DEFAULT_POOL_DEFINITIONS` MIME type expansion is incomplete

**Priority:** MEDIUM

**Detailed Description:**

The spec (line 22) states:

> "Ensure `DEFAULT_POOL_DEFINITIONS` in `services/media_processing_service.py` is expanded to route additional Soniox-supported audio MIME types (including `audio/ogg`, `audio/mpeg`, `audio/wav`, `audio/webm`, `audio/mp4`, `audio/aac`, `audio/flac`, and `audio/amr`) to the `AudioTranscriptionProcessor`."

The Soniox documentation (confirmed from the "Audio formats" section) lists the following supported formats:

> `aac, aiff, amr, asf, flac, mp3, ogg, wav, webm, m4a, mp4`

Comparing the spec's MIME type list against Soniox's supported formats:

| Soniox Format | Spec MIME Type | Status |
|---------------|---------------|--------|
| `aac` | `audio/aac` | ✅ Included |
| `aiff` | `audio/aiff` | ❌ **Missing** |
| `amr` | `audio/amr` | ✅ Included |
| `asf` | `audio/x-ms-asf` or `video/x-ms-asf` | ❌ **Missing** |
| `flac` | `audio/flac` | ✅ Included |
| `mp3` | `audio/mpeg` | ✅ Included |
| `ogg` | `audio/ogg` | ✅ Included |
| `wav` | `audio/wav` | ✅ Included |
| `webm` | `audio/webm` | ✅ Included |
| `m4a` | `audio/mp4` or `audio/x-m4a` | ⚠️ Partially (via `audio/mp4`) |
| `mp4` | `audio/mp4` | ✅ Included |

Three formats supported by Soniox are not addressed:
1. **`audio/aiff`** — Common on Apple platforms; legitimate audio format
2. **`audio/x-ms-asf`** (or `video/x-ms-asf`) — Windows Media format; rarely sent via WhatsApp but supported by Soniox
3. **`audio/x-m4a`** — Some systems report `.m4a` files with this MIME type instead of `audio/mp4`

The practical impact is low for WhatsApp-based audio (which primarily uses `audio/ogg` Opus codec), but for completeness and future-proofing, `audio/aiff` at minimum should be considered. The `asf` format is niche enough to potentially defer.

**Status:** READY

**Required Actions:**
- **Action:** Update the specification (line 22) to explicitly include `audio/aiff`, `audio/x-m4a`, and `audio/x-ms-asf` in the list of MIME types that must be routed to the `AudioTranscriptionProcessor` within `DEFAULT_POOL_DEFINITIONS`.

---

### <a id="r07-06"></a>R07-06: Dictionary-based registry refactor for `resolve_model_config` silently falls back to `ChatCompletionProviderConfig`

**Priority:** MEDIUM

**Detailed Description:**

The spec (Section 3, item 2, line 194) states:

> "`services/resolver.py`: Add the overloaded type `Literal["audio_transcription"]` to `resolve_model_config`, and refactor the functional python body away from hardcoded if/elif statements, instead using a dynamic dictionary-based registry mapping `ConfigTier` to Pydantic Models with `.get(config_tier, ChatCompletionProviderConfig)`."

The proposed `.get(config_tier, ChatCompletionProviderConfig)` pattern uses `ChatCompletionProviderConfig` as the **fallback default** for unknown tiers. This means that if a new tier is added to `ConfigTier` in the future but someone forgets to update the dictionary in `resolver.py`, the resolver will silently parse that tier's config as `ChatCompletionProviderConfig` instead of raising an error.

Compare this with the current implementation which has an explicit `else` branch that falls through to `ChatCompletionProviderConfig`:

```python
if config_tier == "image_moderation":
    return BaseModelProviderConfig.model_validate(tier_data)
elif config_tier == "image_transcription":
    return ImageTranscriptionProviderConfig.model_validate(tier_data)
else:
    return ChatCompletionProviderConfig.model_validate(tier_data)
```

While the current code also defaults to `ChatCompletionProviderConfig`, the dictionary-based approach makes this silent fallback even less visible. A safer alternative would be to raise a `ValueError` for unknown tiers:

```python
config_class = tier_registry.get(config_tier)
if config_class is None:
    raise ValueError(f"Unknown config tier: {config_tier}")
return config_class.model_validate(tier_data)
```

This is a design suggestion, not a bug — the spec's approach will work correctly for the four known tiers. But the silent fallback is a maintenance trap.

**Status:** READY

**Required Actions:**
- **Action:** Update the literal spec snippet for `resolver.py` to remove the `.get(config_tier, ChatCompletionProviderConfig)` fallback. Instead, mandate an explicit `if config_class is None:` check that raises a `ValueError(f"Unknown config tier: {config_tier}")` to enforce safe failure on unregistered tiers.

---

### <a id="r07-07"></a>R07-07: `AudioTranscriptionProviderSettings` inherits from `BaseModelProviderSettings` but doesn't address field absence concerns

**Priority:** LOW

**Detailed Description:**

The spec (line 12) states:

> "Create a new `AudioTranscriptionProviderSettings` class inheriting from `BaseModelProviderSettings` (because audio transcription lacks chat parameters like explicit reasoning effort flags), adding the `temperature: float = 0.0` field."

This correctly bypasses `ChatCompletionProviderSettings` (which adds `temperature`, `reasoning_effort`, `seed`, `record_llm_interactions`) and inherits directly from `BaseModelProviderSettings` (which has `api_key_source`, `api_key`, `model`).

However, `BaseModelProviderSettings` does **not** have a `temperature` field. By adding `temperature: float = 0.0` to `AudioTranscriptionProviderSettings`, the spec creates a field that will be present in the Pydantic JSON schema. The spec also notes this temperature is a "dummy variable specifically ignored by the Soniox provider implementation, kept strictly to ensure future-proofing."

This is architecturally fine but creates a minor inconsistency: the frontend UI (via `get_configuration_schema`) will expose a `temperature` input for the audio transcription tier that has no functional effect. The spec handles the frontend section (line 196) by noting that the `ui:title` should omit `reasoning_effort` and `seed`, but it doesn't explicitly mention whether `temperature` should be visible in the UI or hidden. Since the field is a dummy, exposing it could mislead operators.

This is a minor UI clarity concern, not a functional bug.

**Status:** READY

**Required Actions:**
- **Action:** Add an explicit note to the frontend spec section (line 196) clarifying that the `temperature: float = 0.0` defined in the backend model will intentionally materialize as a visible dummy field in the EditPage UI. State explicitly that this is a known, desired behavior for future-proofing and requires no UI hiding logic.

---

