# Spec Review: audioTranscriptSupport
**Review ID:** `01_ag_opus_4_6`  
**Spec File:** `docs/audioTranscriptSupport/audioTranscriptSupport_specFile.md`  
**Date:** 2026-03-26  
**Reviewer:** Antigravity (ag_opus_4_6)

---

## Summary Table

| Priority | ID | Title | Link | Status |
|---|---|---|---|---|
| 🔴 HIGH | `R01` | `model_factory.py` will crash for `AudioTranscriptionProvider` — missing branch in polymorphic dispatch | [→ R01](#r01) | READY |
| 🔴 HIGH | `R02` | Spec flow steps 1–3 contradict the simpler SDK shortcut (`client.stt.transcribe`) and specify a more complex multi-step manual flow without explaining why | [→ R02](#r02) | READY |
| 🔴 HIGH | `R03` | Migration script filename is wrong: spec says `audioTranslationUpgradeScript.py` (translation, not transcription) | [→ R03](#r03) | READY |
| 🟠 MEDIUM | `R04` | Token tracking for `AudioTranscriptionProvider` is completely unspecified — no mechanism is described, yet the spec mentions `feature_name` tracking | [→ R04](#r04) | READY |
| 🟠 MEDIUM | `R05` | `factory.py` update is omitted from all checklists — import must be migrated from `stub_processors` to `audio_transcription_processor` | [→ R05](#r05) | READY |
| 🟠 MEDIUM | `R06` | `bot_management.py` schema surgery hardcodes tier names — `audio_transcription` will render broken in the UI without two additional manual fixes | [→ R06](#r06) | READY |
| 🟡 LOW | `R07` | `AudioTranscriptionProviderSettings` inherits `model` field from `BaseModelProviderSettings` but Soniox model selection may need explicit spec guidance | [→ R07](#r07) | READY |
| 🟡 LOW | `R08` | Spec incorrectly states `client.files.upload` + `client.stt.transcribe(file_id=...)` is required; the SDK `transcribe(file=path)` does this in one call | [→ R08](#r08) | READY |
| 🟡 LOW | `R09` | `ImageTranscriptionProviderSettings` inherits `ChatCompletionProviderSettings` (adds `reasoning_effort`, `seed`, `record_llm_interactions`) — spec does not address whether `AudioTranscriptionProviderSettings` must deliberately exclude these | [→ R09](#r09) | READY |

---

## Detailed Findings

---

### R01

**Priority:** 🔴 HIGH  
**Title:** `model_factory.py` will crash for `AudioTranscriptionProvider` — missing branch in polymorphic dispatch  
**Status:** READY  
**Required actions:** Mandate adding an explicit `elif isinstance(provider, AudioTranscriptionProvider): return provider` branch to `create_model_provider` in `services/model_factory.py` to correctly return the provider and bypass LangChain mechanisms without throwing a `TypeError`.

**Detailed description:**

`services/model_factory.py` (`create_model_provider`) currently handles three provider types with explicit branches:

```python
if isinstance(provider, LLMProvider):
    ...   # ChatCompletionProvider + ImageTranscriptionProvider
elif isinstance(provider, ImageModerationProvider):
    return provider
else:
    raise TypeError(f"Unknown provider type: {type(provider)}")
```

The new `AudioTranscriptionProvider` inherits from `BaseModelProvider` directly (explicitly *not* from `LLMProvider`), and is not `ImageModerationProvider`. Therefore, calling `create_model_provider(..., "audio_transcription")` will **always hit the `raise TypeError` branch** and crash at runtime.

The spec mentions this issue only briefly in a parenthetical note inside §Technical Details §1:

> *"Add check for `isinstance(provider, AudioTranscriptionProvider)` if any custom duration tracking must be hooked."*

This phrasing is vague and leaves it to the implementer to infer the critical fix. There is no corresponding checklist item. The factory will be broken the moment `AudioTranscriptionProcessor` calls `create_model_provider`. This is a **deployment blocker**.

The required change is a new explicit branch:

```python
elif isinstance(provider, AudioTranscriptionProvider):
    return provider
```

The spec needs to state this unambiguously as a **required step** (not an optional tracking consideration) in both the provider architecture section and the deployment checklist.

---

### R02

**Priority:** 🔴 HIGH  
**Title:** Spec flow steps 1–3 contradict the simpler SDK shortcut and specify a more complex multi-step manual flow without explaining why  
**Status:** READY  
**Required actions:** Modify spec to mandate the cleaner SDK `transcribe(file=path)` pattern and use the single `client.stt.destroy(transcription.id)` call for cleanup in the `finally` block, eliminating the partial-upload edge case and `NameError` risk completely.

**Detailed description:**

The spec mandates (§Transcription, "Transcription response normalization contract") the following explicit multi-step flow:

> 1. Upload the file using `client.files.upload` (or async equivalent).  
> 2. Start transcription using `client.stt.transcribe(..., file_id=file.id)`.  
> 3. Wait for completion natively (`client.stt.wait`) and fetch the transcript (`client.stt.get_transcript`).

However, the Soniox Python SDK `client.stt.transcribe` method **already accepts a local file path directly** (via the `file=` parameter) and handles the upload + job creation internally in a single call:

```python
transcription = client.stt.transcribe(model="stt-async-v4", file="audio.mp3")
```

The spec chooses the two-step approach (explicit upload + separate transcribe-by-`file_id`) without documenting *why*. This is important because:

1. It means a `file` object is created in step 1, and `file.id` must be stored to pass into step 2. If a timeout or exception occurs between steps 1 and 2 but before the `try/finally` cleanup is fully set up, the uploaded file could leak.
2. The `finally` block in step 4 correctly calls `client.files.delete_if_exists(file.id)` — but only if `file` was successfully assigned in step 1. If step 1 throws (e.g. upload quota exceeded), `file` is never set, and `delete_if_exists` cannot be called (would `NameError`/`AttributeError`). The cleanup block structure must account for this (e.g. `file = None` pre-assignment + conditional delete).
3. If using `client.stt.transcribe(file=path)` instead, the SDK handles file upload and the `destroy(transcription.id)` call is sufficient to clean up both the transcription job and its file, simplifying the cleanup.

The spec should either: (a) clearly justify why the explicit two-step upload is preferred over the single `file=` approach, or (b) adopt `file=` + `destroy()` as the cleaner pattern. The current text mixes both paradigms (it mentions `client.files.upload` explicitly in step 1 but also lists `client.stt.destroy(transcription.id)` as an alternative to both deletes in step 4), creating ambiguity about which pattern to actually implement.

---

### R03

**Priority:** 🔴 HIGH  
**Title:** Migration script filename is wrong — spec says `audioTranslationUpgradeScript.py` ("translation", not "transcription")  
**Status:** READY  
**Required actions:** Fix the typo in the spec by renaming the script from `audioTranslationUpgradeScript.py` to `audioTranscriptionUpgradeScript.py` in all checklists and references, keeping it in the `scripts/` directory.

**Detailed description:**

In §Relevant Background Information (project files list) and §Deployment Checklist step 1, the spec names the migration script:

> `scripts/audioTranslationUpgradeScript.py`

This is a typo: **"Translation"** instead of **"Transcription"**. The feature being implemented is *audio transcription*. All existing historical migration scripts in `scripts/deprecated/migrations/` use consistent naming matching the feature they target (e.g. `add_image_transcription_tier.py`, `migrate_image_moderation.py`).

Using the wrong filename will cause confusion when the script is actually created. The correct name should be `audioTranscriptionUpgradeScript.py` (or following the snake_case convention of existing migrations: `add_audio_transcription_tier.py`).

---

### R04

**Priority:** 🟠 MEDIUM  
**Title:** Token tracking for `AudioTranscriptionProvider` is completely unspecified — no mechanism is described despite `feature_name` tracking being called out  
**Status:** READY  
**Required actions:** Mandate a "Callback Injection" pattern where `create_model_provider` creates an async tracking closure (accepting `input_tokens`, `output_tokens`, and `cached_input_tokens=0`) and injects it into the provider via `set_token_tracker()`. The provider then directly extracts the exact token usage from the Soniox SDK's `usage` object (`usage.input_audio_tokens` and `usage.output_text_tokens`) and invokes this callback internally after transcription to decouple it from MongoDB logic. 

Snippet  that should be added into spec:

**Snippet for `model_factory.py`):**
```python
async def token_tracker(input_tokens: int, output_tokens: int, cached_input_tokens: int = 0):
    await token_service.record_event(
        user_id=user_id,
        bot_id=bot_id,
        feature_name="audio_transcription",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        config_tier=config_tier
    )

provider.set_token_tracker(token_tracker)
```

**Snippet for `SonioxAudioTranscriptionProvider`:**
```python
transcription = await client.stt.transcribe(
    model=self.settings.model,
    file=audio_path,
    wait=True
)

if self._token_tracker and transcription.usage:
    await self._token_tracker(
        input_tokens=transcription.usage.input_audio_tokens,
        output_tokens=transcription.usage.output_text_tokens,
        cached_input_tokens=0
    )
    
return transcription.text
```

**Detailed description:**

The spec (§Transcription) states:

> *"The `feature_name` passed to `create_model_provider` for this transcription call must be `\"audio_transcription\"` (to enable token/duration tracking)."*

It also states in §Configuration:

> *"`global_configurations.token_menu` is extended with an `\"audio_transcription\"` pricing entry … because their prices are now token based, not time based."*

However, `create_model_provider` only attaches token tracking via `TokenTrackingCallback` for providers that are instances of `LLMProvider` (which uses LangChain's callback infrastructure). `AudioTranscriptionProvider` explicitly does **not** inherit from `LLMProvider` — it is a raw async API wrapper bypassing LangChain entirely.

This creates a gap: `feature_name="audio_transcription"` is passed in, but there is no mechanism specified or described for **how** token/usage data gets recorded when the provider runs. The `token_menu` entry and `feature_name` are only meaningful if something actually writes to the token consumption collection.

The spec needs to specify one of the following approaches:
1. **Manual tracking:** `SonioxAudioTranscriptionProvider.transcribe_audio()` must call `TokenConsumptionService` directly with audio duration/token metrics after a successful transcription.
2. **Factory-level hook:** The new `elif isinstance(provider, AudioTranscriptionProvider)` branch in `model_factory.py` wraps the provider and attaches a tracking hook (but the async lifecycle makes this harder — Soniox doesn't stream tokens the way LangChain does).
3. **No tracking yet:** Explicitly acknowledge that token tracking is deferred/stub and the `token_menu` entry is a placeholder.

Without clarification, an implementer will pass `feature_name` into `create_model_provider`, notice that nothing is tracked, and either skip implementing tracking or implement it inconsistently.

---

### R05

**Priority:** 🟠 MEDIUM  
**Title:** `factory.py` update is omitted from all checklists — import must be migrated from `stub_processors` to `audio_transcription_processor`  
**Status:** READY  
**Required actions:** Add an explicit step to the Deployment Checklist to "Update the import of `AudioTranscriptionProcessor` in `media_processors/factory.py` to point to `media_processors.audio_transcription_processor` instead of `stub_processors`."

**Detailed description:**

`media_processors/factory.py` currently imports `AudioTranscriptionProcessor` from `stub_processors`:

```python
from media_processors.stub_processors import (
    AudioTranscriptionProcessor,
    ...
)
```

The spec correctly states that `AudioTranscriptionProcessor` must be moved to `media_processors/audio_transcription_processor.py` and deleted from `stub_processors.py`. However, **neither the Relevant Background Information section nor any deployment/configuration checklist mentions updating `factory.py`**. The file is not listed in the "Project Files" section of the spec.

If `factory.py` is not updated after the move, the application will fail to import at startup with an `ImportError`. This is a straightforward but critical omission.

`media_processors/factory.py` must be added to the spec's "Relevant Background Information / Project Files" list, and the import update must be listed as an explicit implementation step.

---

### R06

**Priority:** 🟠 MEDIUM  
**Title:** `bot_management.py` schema surgery hardcodes tier names — `audio_transcription` will render broken in UI without two additional manual fixes  
**Status:** PENDING  
**Required actions:** *(to be filled)*

**Detailed description:**

The spec notes (§New Configuration Tier Checklist, step 3):

> *"Dynamic tier extraction covers this if implemented using `.keys()`."*

This is accurate for `get_configuration_schema()`, but the spec overlooks two additional places in `bot_management.py` where tier names are **hardcoded** and must be manually updated:

**1. Schema surgery loop (line ~365):**
```python
for prop_name in ['high', 'low', 'image_moderation', 'image_transcription']:
```
This list does not use `.keys()` — it is a static hardcoded list. `audio_transcription` must be added here or the `anyOf`-null cleanup will not run for it, causing the UI to show a redundant `anyOf` dropdown for the new tier.

**2. `handleFormChange` in `EditPage.js` (line ~229):**
```javascript
['high', 'low', 'image_moderation', 'image_transcription'].forEach(type => {
```
And the `api_key_source` backfill loop (line ~135):
```javascript
['high', 'low', 'image_moderation', 'image_transcription'].forEach(type => {
```
Both loops in `EditPage.js` iterate over a static tier list. If `audio_transcription` is not added here, the frontend will not apply the `api_key_source` coercion or the reasoning effort guard for the new tier, potentially sending malformed data.

The spec's §New Configuration Tier Checklist step 4 says to add a `uiSchema` entry for `audio_transcription` in `EditPage.js`, but it does not call out updating these two static `forEach` loops. These are straightforward but non-obvious and will cause silent bugs.

---

### R07

**Priority:** 🟡 LOW  
**Title:** `AudioTranscriptionProviderSettings` inherits `model` field from `BaseModelProviderSettings` but Soniox model selection may need explicit spec guidance  
**Status:** READY  
**Required actions:** Update the configuration section of the spec to set the default value of the `DEFAULT_MODEL_AUDIO_TRANSCRIPTION` environment variable to a valid Soniox async model string (e.g., `"stt-async-v4"`) instead of `"soniox"`.

**Detailed description:**

`BaseModelProviderSettings` defines `model: str` as a required field (no default). `AudioTranscriptionProviderSettings` inherits from it. The spec correctly describes adding `model_provider_name_audio_transcription = "sonioxAudioTranscription"` to `DefaultConfigurations` and specifies `DEFAULT_MODEL_AUDIO_TRANSCRIPTION` env var defaulting to `"soniox"` in `LLMConfigurations`.

However, the default **model name** string that `SonioxAudioTranscriptionProvider` will actually pass to the Soniox API (e.g. `"stt-async-v4"`) is not specified. The Soniox docs show `model="stt-async-v4"` as the model identifier in all code examples. The spec should either:
- Define the default value for `DEFAULT_MODEL_AUDIO_TRANSCRIPTION` to be a concrete Soniox model name like `"stt-async-v4"` (not the vague `"soniox"` string which appears to conflate provider name and model name), or
- Clarify that the `model` field is passed directly to `client.stt.transcribe(model=...)` and document which Soniox model string to use as default.

Currently `os.getenv("DEFAULT_MODEL_AUDIO_TRANSCRIPTION", "soniox")` would pass `model="soniox"` to the Soniox API, which is likely an invalid model name that would return a 400/422 error from the API.

---

### R08

**Priority:** 🟡 LOW  
**Title:** Spec mandates an explicit `client.files.upload` step but the SDK's `transcribe(file=path)` shortcut avoids it — the spec should pick one pattern consistently  
**Status:** READY  
**Required actions:** Resolved inherently by the fix for R02. Remove the conflicting explicit upload phrasing from the spec entirely.

**Detailed description:**

This is a narrower elaboration of R02. The SDK docs clearly show two equivalent patterns for local files:

**Pattern A (explicit upload):**
```python
file = client.files.upload("audio.mp3")
transcription = client.stt.transcribe(model="...", file_id=file.id)
```

**Pattern B (shortcut):**
```python
transcription = client.stt.transcribe(model="...", file="audio.mp3")
# SDK handles upload internally; destroy() cleans both file and job
```

The spec mandates Pattern A verbatim in the numbered steps (step 1 is `client.files.upload`, step 2 is `client.stt.transcribe(..., file_id=file.id)`). However step 4 mentions `client.stt.destroy(transcription.id)` as an alternative — which is the cleanup for Pattern B (destroy cleans both the transcription job *and* its associated file).

The two patterns are not interchangeable in the `finally` cleanup: Pattern A needs `client.files.delete_if_exists(file.id)` + `client.stt.delete_if_exists(transcription.id)` as separate calls; Pattern B only needs `client.stt.destroy(transcription.id)`. Mixing them creates a logical inconsistency.

This is lower priority than R02 because the spec's primary pattern (A) is technically correct and functional — but it should be self-consistent.

---

### R09

**Priority:** 🟡 LOW  
**Title:** Spec does not address whether `AudioTranscriptionProviderSettings` must explicitly exclude `reasoning_effort`, `seed`, and `record_llm_interactions` inherited from parent classes  
**Status:** READY  
**Required actions:** Add a sentence to step 4 of the "New Configuration Tier Checklist" stating: "Ensure the `uiSchema` configuration for `audio_transcription` deliberately omits the `reasoning_effort` and `seed` sub-entries, as this provider is not a Chat Completion provider."

**Detailed description:**

Looking at the existing inheritance chain:

- `BaseModelProviderSettings`: `api_key_source`, `api_key`, `model`
- `ChatCompletionProviderSettings(BaseModelProviderSettings)`: adds `temperature`, `reasoning_effort`, `seed`, `record_llm_interactions`
- `ImageTranscriptionProviderSettings(ChatCompletionProviderSettings)`: adds `detail`

The spec mandates a **different** inheritance: `AudioTranscriptionProviderSettings(BaseModelProviderSettings)` — bypassing `ChatCompletionProviderSettings`. This is the correct design since Soniox is not a chat model.

The spec explicitly states: *"because audio transcription lacks chat parameters like explicit reasoning effort flags"* — which is good reasoning.

However, the spec does not note a subtle implication: the Pydantic schema for `AudioTranscriptionProviderSettings` will **not** include `reasoning_effort`, `seed`, or `record_llm_interactions`, which means:
1. The `get_configuration_schema` schema surgery in `bot_management.py` that patches `reasoning_effort` titles in `ChatCompletionProviderSettings` will not affect `AudioTranscriptionProviderSettings` — this is fine.
2. `EditPage.js`'s `handleFormChange` guards `reasoning_effort` for all tier types — since `audio_transcription` config won't have this field, iterating over it in the forEach loop (R06) will silently skip it — also fine.
3. But the `uiSchema` entry for `audio_transcription` in `EditPage.js` mentioned in step 4 of §New Configuration Tier Checklist should **not** include `reasoning_effort` or `seed` sub-entries, unlike the other tiers. The spec does not call this out explicitly; implementers may cargo-cult the existing `image_transcription` uiSchema entry (which has `reasoning_effort`, `seed`, `detail`) and inadvertently include irrelevant fields.

This is a low-risk spec gap — the result would merely be non-functional UI fields, not a runtime error — but it should be documented.
