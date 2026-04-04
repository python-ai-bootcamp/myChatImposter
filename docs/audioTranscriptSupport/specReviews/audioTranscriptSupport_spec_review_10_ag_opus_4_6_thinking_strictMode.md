# Spec Review: Audio Transcription Support

**Review ID:** `10_ag_opus_4_6_thinking_strictMode`
**Spec File:** `docs/audioTranscriptSupport/audioTranscriptSupport_specFile.md`
**Reviewer:** Antigravity (Claude Opus 4, Thinking, Strict Mode)
**Date:** 2026-04-03

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| HIGH | R10-01 | `TokenConsumptionService.record_event` uses `ConfigTier` type hint which will reject `"audio_transcription"` at static analysis until `ConfigTier` Literal is updated simultaneously | [Details](#r10-01) | READY |
| HIGH | R10-02 | Spec's `token_tracker` closure inside the `AudioTranscriptionProvider` factory branch is defined as `async` but the provider's `set_token_tracker` stores it as a plain callable — caller must `await` it, requiring the provider to treat the callback as a coroutine consistently | [Details](#r10-02) | READY |
| MEDIUM | R10-04 | Spec mandates `format_processing_result` accept `mime_type: str` but does not update the function signature to pass `mime_type` through `_handle_unhandled_exception` where the `job` object's `mime_type` is available | [Details](#r10-04) | READY |
| MEDIUM | R10-05 | `ProcessingResult` dataclass gains `display_media_type: Optional[str] = None` but the `_persist_result_first` method only serializes `result.content` to MongoDB — the new field is lost on bot reconnect recovery | [Details](#r10-05) | READY |
| MEDIUM | R10-06 | `ImageVisionProcessor` error-path `ProcessingResult` returns at lines 52-55 and 71-74 lack `unprocessable_media=True` — spec mandates it but the instruction is embedded in a Companion Fix paragraph that may be missed | [Details](#r10-06) | READY |
| LOW | R10-07 | Spec's `_resolve_api_key()` returns `None` for `api_key_source="environment"` but `AsyncSonioxClient(api_key=None)` SDK behavior when environment variable `SONIOX_API_KEY` is not set is unspecified | [Details](#r10-07) | READY |

---

## Detailed Review Items

---

### <a id="r10-01"></a>R10-01: `TokenConsumptionService.record_event` uses `ConfigTier` type hint which will reject `"audio_transcription"` at static analysis until `ConfigTier` Literal is updated simultaneously

**Priority:** HIGH

**ID:** R10-01

**Title:** `TokenConsumptionService.record_event` uses `ConfigTier` type hint which will reject `"audio_transcription"` at static analysis until `ConfigTier` Literal is updated simultaneously

**Detailed Description:**

The spec (line 14) states:

> "`ConfigTier` is updated to include `\"audio_transcription\"`."

And the spec's new `token_tracker` closure (lines 173–184) passes `config_tier=config_tier` to `token_service.record_event(...)`. Examining `services/token_consumption_service.py` (lines 12–18):

```python
async def record_event(self, 
                       user_id: str, 
                       bot_id: str, 
                       feature_name: str, 
                       input_tokens: int, 
                       output_tokens: int, 
                       config_tier: ConfigTier,
                       cached_input_tokens: int = 0):
```

The `config_tier` parameter is typed as `ConfigTier`, which is currently defined as:

```python
ConfigTier = Literal["high", "low", "image_moderation", "image_transcription"]
```

The spec correctly mandates updating `ConfigTier` to include `"audio_transcription"` (line 14, line 200). However, the `TokenConsumptionService.record_event` function is **not** listed in the spec's "Relevant Background Information > Project Files" section, and neither is `services/quota_service.py` which also uses `ConfigTier` as a type hint in `calculate_cost()`.

The critical concern is **implementation atomicity**: If a developer updates the token tracking closure in `model_factory.py` to pass `config_tier="audio_transcription"` without simultaneously ensuring `ConfigTier` is expanded in `config_models.py`, the code will pass at runtime (Python's `Literal` is only enforced by static type checkers, not at runtime), but static analysis tools (mypy, pyright) will flag it as a type error. More importantly, if `QuotaService.calculate_cost` receives `"audio_transcription"` before the `token_menu` migration runs, it silently returns `0.0` (the existing `Unknown config_tier` fallback at line 50-53 of `quota_service.py`), causing unbilled usage.

The spec addresses the `ConfigTier` update and the migration script requirement separately, but does not explicitly list `token_consumption_service.py` or `quota_service.py` as affected files, creating an implicit dependency that may confuse implementers trying to trace the full change impact.

**Status:** READY

**Required Actions:**
- **Action**: Add `services/token_consumption_service.py` and `services/quota_service.py` to the spec's "Relevant Background Information > Project Files" section as impacted files. No code changes are required in these files — the `ConfigTier` Literal update in `config_models.py` already covers them transitively. This addition improves traceability of the full change surface area for implementers.

---

### <a id="r10-02"></a>R10-02: Spec's `token_tracker` closure inside the `AudioTranscriptionProvider` factory branch is defined as `async` but the provider's `set_token_tracker` stores it as a plain callable — caller must `await` it, requiring consistent async treatment

**Priority:** HIGH

**ID:** R10-02

**Title:** Spec's `token_tracker` closure is `async` but `set_token_tracker` stores it generically — inconsistent async contract between factory and provider

**Detailed Description:**

The spec's model factory snippet (lines 173–184) defines:

```python
async def token_tracker(input_tokens: int, output_tokens: int, cached_input_tokens: int = 0):
    await token_service.record_event(
        user_id=user_id,
        bot_id=bot_id,
        feature_name=feature_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        config_tier=config_tier
    )

provider.set_token_tracker(token_tracker)
```

And the spec's `AudioTranscriptionProvider` (line 121) states:

> "It must also formally declare ... an explicit `def set_token_tracker(self, tracker_func):` method."

The provider's `transcribe_audio` snippet (lines 142–151) then calls:

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

The `await self._token_tracker(...)` call correctly treats the callback as a coroutine. However, the `set_token_tracker` method has no type annotation enforcing that `tracker_func` must be an async callable. If a future developer passes a synchronous function to `set_token_tracker`, the `await` call will raise a `TypeError: object NoneType can't be used in 'await' expression` (or similar) at runtime.

Additionally, the spec references `job_info.usage.input_audio_tokens` and `job_info.usage.output_text_tokens` (lines 148-149) as the Soniox SDK usage attribute names. These field names (`input_audio_tokens`, `output_text_tokens`) are inferred from the Soniox pricing model but are **not documented** in any of the five external resource links provided in the spec. The SDK docs show `transcription.usage` exists but do not enumerate its sub-fields. If the actual SDK attribute names differ (e.g., `input_tokens`, `output_tokens`, or `duration_seconds`), the implementation will produce `AttributeError` at runtime.

The spec adds a note (line 146-148): *"Note: Soniox token-based pricing officially uses 'Input Audio Tokens' and 'Output Text Tokens'."* — but this is presented as a code comment inside the snippet, not as a verified SDK reference. The implementer has no way to independently verify this from the provided external resources.

**Status:** READY

**Required Actions:**
- **Action**: Add an instruction to the spec to enforce the async contract by adding a type annotation to `set_token_tracker` (e.g., `tracker_func: Callable[..., Awaitable[None]]`).
- **Action**: Update the code snippet for the `token_tracker` call inside `transcribe_audio`. Since Soniox does not provide token usage natively, replace the `job_info.usage` field lookups with an arithmetic estimation based on audio duration and output text length:
  - **Input Tokens**: `int((job_info.audio_duration_ms or 0) / 120)` (extrapolating 30,000 tokens per hour, or 3600000 ms).
  - **Output Tokens**: `int(len(transcription_text) * 0.3)` (estimating 0.3 tokens per character).

---

### <a id="r10-04"></a>R10-04: Spec mandates `format_processing_result` accept `mime_type: str` parameter but does not update `_handle_unhandled_exception` to pass `job.mime_type`

**Priority:** MEDIUM

**ID:** R10-04

**Title:** `format_processing_result` signature gains `mime_type` parameter but `_handle_unhandled_exception` caller is not updated in the spec

**Detailed Description:**

The spec (line 43) states:

> "Refactor `format_processing_result` in `media_processors/base.py` to accept a `mime_type: str` parameter. ... Ensure `BaseMediaProcessor.process_job` passes `job.mime_type` to all calls to `format_processing_result`."

The current `process_job` method in `base.py` calls `format_processing_result` at line 91. The spec says to pass `job.mime_type` here. However, `_handle_unhandled_exception` (lines 186–191) **also** calls `format_processing_result`:

```python
async def _handle_unhandled_exception(self, job, db, error, get_bot_queues=None):
    raw = ProcessingResult(content="Media processing failed", failed_reason=error)
    formatted = format_processing_result(
        content=raw.content,
        caption=job.placeholder_message.content,
        original_filename=job.original_filename,
        unprocessable_media=False,    # spec says change to True
    )
```

After the refactoring, `format_processing_result` requires a `mime_type` parameter. The spec instructs the `_handle_unhandled_exception` fix to change `unprocessable_media` to `True` (line 38), but does not mention adding `mime_type=job.mime_type` to this call. If `mime_type` is a required positional parameter (no default), this will produce a `TypeError` at runtime. If `mime_type` has a default value, the prefix logic may produce incorrect output (e.g., missing or empty media type prefix).

The spec should explicitly state that `_handle_unhandled_exception`'s call to `format_processing_result` must also pass `mime_type=job.mime_type`, or clarify that the `mime_type` parameter should have a sensible default (e.g., `mime_type: str = ""`).

**Status:** READY

**Required Actions:**
- **Action**: Add an explicit instruction to the spec ensuring that the call to `format_processing_result` inside `BaseMediaProcessor._handle_unhandled_exception` is also updated to pass `mime_type=job.mime_type` to prevent a `TypeError` at runtime.

---

### <a id="r10-05"></a>R10-05: `ProcessingResult` gains `display_media_type` field but `_persist_result_first` only serializes `result.content` — the new field is lost on bot reconnect recovery path

**Priority:** MEDIUM

**ID:** R10-05

**Title:** New `display_media_type` attribute on `ProcessingResult` is not persisted to MongoDB, making it unavailable during bot reconnect recovery

**Detailed Description:**

The spec (line 43) introduces:

> "Add an optional `display_media_type: str = None` attribute to the `ProcessingResult` dataclass; if a processor provides this, the formatter must use it directly instead of attempting to parse the `mime_type`."

However, examining `BaseMediaProcessor._persist_result_first` (lines 147–158 of `base.py`):

```python
async def _persist_result_first(self, job, result, db):
    update = {"$set": {"status": "completed", "result": result.content}}
    # ...
```

Only `result.content` is persisted to MongoDB. The `display_media_type`, `unprocessable_media`, and `failed_reason` fields are not serialized. This is fine for the current flow because `format_processing_result` is called **before** `_persist_result_first`, so `result.content` already contains the fully formatted string with prefix injection applied.

However, this means `display_media_type` is a **transient** field that only affects the `format_processing_result` call during the active processing flow. If a processor sets `display_media_type` for any reason beyond prefix injection (e.g., for logging or analytics), the information is lost after persistence. The spec does not make the transient nature of this field explicit.

This is a design clarity issue rather than a bug — the field works correctly for its intended purpose (prefix injection in `format_processing_result`), but the spec should explicitly note that `display_media_type` is a **processing-time-only** field that is consumed by the formatter and not persisted.

**Status:** READY

**Required Actions:**
- **Action**: Add a note to the spec explicitly clarifying that `display_media_type` is a transient, processing-time-only variable strictly intended for consumption by `format_processing_result`, and that it is intentionally not persisted to the database.

---

### <a id="r10-06"></a>R10-06: `ImageVisionProcessor` error-path `ProcessingResult` returns at lines 52-55 and 71-74 lack `unprocessable_media=True` — spec mandates it but instruction is buried in a Companion Fix paragraph

**Priority:** MEDIUM

**ID:** R10-06

**Title:** `ImageVisionProcessor` error paths don't set `unprocessable_media=True` — spec instruction exists but is embedded in a dense paragraph easily missed by implementers

**Detailed Description:**

The spec (line 35) states:

> "**Companion Fix (ImageVisionProcessor)**: Because this spec introduces a global prefix injection pattern, it inadvertently affects the existing `ImageVisionProcessor`. You must also add `unprocessable_media=True` to BOTH error-path `ProcessingResult` returns in `image_vision_processor.py` (moderation API crash and transcription API crash) to prevent the system from injecting misleading success prefixes onto those errors."

Examining the current code in `image_vision_processor.py`:

```python
# Line 52-55: Moderation error
except Exception as e:
    logger.error(f"IMAGE MODERATION ({bot_id}): Moderation failed: {e}")
    return ProcessingResult(
        content="Image could not be moderated",
        failed_reason=f"Moderation error: {e}",
    )

# Line 69-74: Transcription error
except Exception as e:
    logger.error(f"IMAGE TRANSCRIPTION ({bot_id}): Transcription failed: {e}")
    return ProcessingResult(
        content="Image could not be transcribed",
        failed_reason=f"Transcription error: {e}",
    )
```

Both error paths currently default `unprocessable_media=False`. After the global prefix injection refactoring, these would produce outputs like:

```
[Image Transcription: Image could not be moderated]
[Image Transcription: Image could not be transcribed]
```

The "Image Transcription:" prefix on error messages is misleading — it implies successful transcription occurred. The spec correctly identifies and addresses this, but the instruction is buried as a "Companion Fix" sub-bullet within the `AudioTranscriptionProcessor`'s error handling section. 

Note that the moderation-flagged path (lines 46-49) correctly sets `unprocessable_media=True` already, which is consistent. The gap is only in the two `except` error paths.

This was also identified in review R09-01 specifically for `CorruptMediaProcessor` and `UnsupportedMediaProcessor`, and the spec now includes dedicated bullet points for those (line 36). However, the `ImageVisionProcessor` fix remains embedded in the error handling paragraph rather than being given its own dedicated sub-bullet comparable to the error processor companion fix.

**Status:** READY

**Required Actions:**
- **Action**: Rearrange the spec format to extract the `ImageVisionProcessor` companion fix instruction out of the dense `AudioTranscriptionProcessor` error handling paragraph. Give it a distinct, isolated bullet point under a dedicated "Companion Fixes" or "Cross-Processor Impact" section to ensure it is highly visible to the implementer.

---

### <a id="r10-07"></a>R10-07: `_resolve_api_key()` returns `None` for `api_key_source="environment"` but `AsyncSonioxClient(api_key=None)` behavior when `SONIOX_API_KEY` env var is not set is unspecified

**Priority:** LOW

**ID:** R10-07

**Title:** API key resolution returns `None` for environment-sourced keys, but whether `AsyncSonioxClient` falls back to env var lookup when `api_key=None` is passed is undocumented in the spec

**Detailed Description:**

The spec's `initialize` snippet (lines 129–130) shows:

```python
async def initialize(self):
    self.client = AsyncSonioxClient(api_key=self._resolve_api_key())
```

Examining `BaseModelProvider._resolve_api_key()` in `model_providers/base.py` (lines 11–24):

```python
def _resolve_api_key(self) -> Optional[str]:
    settings = self.config.provider_config
    if settings.api_key_source == "explicit":
        if not settings.api_key:
            raise ValueError("api_key_source is 'explicit' but no api_key provided.")
        return settings.api_key
    return None
```

When `api_key_source` is `"environment"` (the expected default for the `audio_transcription` tier), `_resolve_api_key()` returns `None`. The `AsyncSonioxClient(api_key=None)` constructor call would pass `None` as the API key.

The Soniox Python SDK documentation for `SonioxClient` / `AsyncSonioxClient` does not explicitly document the behavior when `api_key=None` is passed. The standard SDK pattern (visible in their quickstart examples) is:

```python
client = SonioxClient()  # No api_key argument — reads from SONIOX_API_KEY env var
```

The implicit assumption is that when `api_key=None` is passed, the SDK falls back to reading `SONIOX_API_KEY` from the environment. This is a common pattern in Python SDKs (e.g., OpenAI's SDK does the same for `OPENAI_API_KEY`), and `_resolve_api_key()` is designed precisely with this pattern in mind — the existing `OpenAI` providers work identically.

However, the spec does not explicitly document that the `SONIOX_API_KEY` environment variable must be set in the deployment environment for the `environment` api_key_source mode to work. The deployment checklist (Section 2, "Deployment Checklist") does not mention setting this env var. If the environment variable is missing and the SDK doesn't fall back gracefully (e.g., raises an authentication error at client construction time during `initialize()`), the `AudioTranscriptionProcessor` will fail on every request.

This is low priority because:
1. The pattern matches all existing providers (OpenAI uses the same mechanism).
2. The `SONIOX_API_KEY` env var is a standard operational prerequisite.
3. Runtime failures would surface immediately upon the first transcription attempt.

**Status:** READY

**Required Actions:**
- **Action**: Add an explicit bullet point to the "Deployment Checklist" (Section 2) in the spec stipulating that the `SONIOX_API_KEY` must be provisioned in the deployment environment since the Soniox SDK does not fail gracefully if it is missing and `api_key_source` is set to `"environment"`.

---
