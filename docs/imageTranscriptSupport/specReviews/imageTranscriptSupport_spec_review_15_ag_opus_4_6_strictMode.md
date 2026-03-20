# Spec Review: imageTranscriptSupport
**Review ID:** `15_ag_opus_4_6_strictMode`
**Spec File:** `docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`
**Date:** 2026-03-20

---

## Summary Table

| Priority | ID | Title | Link | Status |
|---|---|---|---|---|
| CRITICAL | R01 | `UnsupportedMediaProcessor` content string in spec does not match `error_processors.py` logic — spec uses `f"Unsupported media type: {mime_type}"` but current code uses `f"Unsupported {mime_type} media"` | [→ R01](#r01) | PENDING |
| CRITICAL | R02 | `EditPage.js` hardcoded tier array in `fetchData` scope (line 135) is still `['high', 'low', 'image_moderation']` after the spec's dynamic helper is applied only to `handleFormChange` — incomplete fix | [→ R02](#r02) | PENDING |
| HIGH | R03 | `initialize_quota_and_bots.py` migration changes are underspecified — spec says "change from skip-if-exists to completely overwrite/upsert" but the migration file only has 2 tiers and a skip-if-exists guard; the spec's 3-tier overwrite requirement is logistically unclear | [→ R03](#r03) | PENDING |
| HIGH | R04 | `CorruptMediaProcessor` content string is inconsistent with current `error_processors.py` — spec says `f"Corrupted {media_type} media could not be downloaded"` but current code derives `media_type` from stripping `"media_corrupt_"` prefix, which may not apply once `caption` is removed | [→ R04](#r04) | PENDING |
| HIGH | R05 | `format_processing_result` placement interaction with `_handle_unhandled_exception` delivery path — after `result.content = format_processing_result(...)`, the best-effort `update_message_by_media_id` inside `_handle_unhandled_exception` correctly reads `result.content`, but the spec does not explicitly confirm this path is also correct after the reassignment | [→ R05](#r05) | PENDING |
| HIGH | R06 | `ImageVisionProcessor` currently has no `__init__` and relies on `BaseMediaProcessor`'s default — with the new transcription call needing `resolve_bot_language`, spec doesn't clarify whether `ImageVisionProcessor` needs to call `resolve_bot_language` before or after moderation, or handle the case where it raises | [→ R06](#r06) | PENDING |
| MEDIUM | R07 | `create_model_provider` unified `LLMProvider` branch: spec says attach `TokenTrackingCallback` for all `LLMProvider` subtypes (including `ImageTranscriptionProvider`), but `_llm` is stored in `self._llm` at `__init__` time — the callback attachment via `llm.callbacks` after factory construction mutates the same `_llm` object, which is correct, but the spec doesn't guard against calling `get_llm()` twice (factory calls it, then the spec says `get_llm()` returns `self._llm`) | [→ R07](#r07) | PENDING |
| MEDIUM | R08 | `DefaultConfigurations` class uses `os.getenv(...)` at class definition time (module load), yet spec adds new `os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE")` and `os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT")` — but does not specify default fallback values for these new env vars, unlike existing vars that all have explicit fallbacks | [→ R08](#r08) | PENDING |
| MEDIUM | R09 | Spec requires `image_transcription` in `uiSchema` of `EditPage.js` to be statically added, but the `handleFormChange` `forEach` loop must also be updated for `image_transcription` to correctly handle `api_key_source` and `reasoning_effort` normalization — the spec's dynamic helper only fixes the loop iteration, not the explicit fourth entry requirement in `handleFormChange` | [→ R09](#r09) | PENDING |
| MEDIUM | R10 | `media_processing_service.py` `DEFAULT_POOL_DEFINITIONS` contains the `ImageVisionProcessor` mime types pool without `image/gif` — spec requires adding `image/gif`, but the spec only mentions `ImageVisionProcessor` requirements; it omits explicitly naming `media_processing_service.py` `DEFAULT_POOL_DEFINITIONS` as the file to update | [→ R10](#r10) | PENDING |
| LOW | R11 | `QuotaService.load_token_menu` self-healing insert spec says "insert the following default document" but does not specify what happens if the insert itself fails (e.g., duplicate key race condition on startup) — no error handling contract defined | [→ R11](#r11) | PENDING |
| LOW | R12 | Spec's `LLMConfigurations.image_transcription` field defined as `Field(...)` (required) will cause Pydantic `ValidationError` on any existing API call to `GET /{bot_id}` that loads `BotConfiguration.model_validate(config_data)` for bots lacking the new tier until migration runs — spec acknowledges this indirectly but does not spell out the deployment sequencing risk for `GET` endpoints | [→ R12](#r12) | PENDING |

---

## Detailed Descriptions

---

### R01
**Priority:** CRITICAL
**Title:** `UnsupportedMediaProcessor` content string in spec does not match `error_processors.py` logic

**Detailed Description:**

The spec (Output Format section) defines the clean content for `UnsupportedMediaProcessor` as:
> `ProcessingResult(content=f"Unsupported media type: {mime_type}", failed_reason=..., unprocessable_media=True)`

However, examining `media_processors/error_processors.py` lines 13–17, the current implementation generates:
```python
prefix = f"[Unsupported {mime_type} media]"
```

So the current human-readable form is `"Unsupported {mime_type} media"` (without brackets, after the spec removes them). But the spec defines the new clean content as `"Unsupported media type: {mime_type}"` — a different phrasing. This is a **content string discrepancy** that could cause test failures if existing tests assert the current wording.

Similarly for `CorruptMediaProcessor` (see R04), the phrasing change is a deliberate spec decision, but it is important that both the spec and tests agree on the exact new strings post-refactor. The spec must be the single source of truth and it currently defines a different string than what exists, without acknowledging the breaking change in user-visible output.

**Status:** PENDING
**Required Actions:** Confirm that the spec's new content strings for `UnsupportedMediaProcessor` (`"Unsupported media type: {mime_type}"`) and `CorruptMediaProcessor` (`"Corrupted {media_type} media could not be downloaded"`) are intentional changes to user-visible output. Then update the test expectations checklist (Section 5) to include tests asserting the exact new content strings for both processors, so implementers know what strings to target.

---

### R02
**Priority:** CRITICAL
**Title:** `EditPage.js` hardcoded tier array in `fetchData` scope (line 135) is only partially fixed by the dynamic helper

**Detailed Description:**

The spec (Section 4, item 4) says:
> "Every occurrence of the hardcoded tier array `["high", "low", "image_moderation"]` (specifically around line 135 for `api_key_source` and line 229 for `handleFormChange`) must be replaced with the dynamic helper function."

Examining `frontend/src/pages/EditPage.js`:
- **Line 135** (`fetchData` scope): `['high', 'low', 'image_moderation'].forEach(type => {` — this processes existing form data when loading a non-new bot. The helper `getAvailableTiers(schemaData)` is available in `fetchData` scope since `schemaData` is fetched just above it in the same function. However, the spec says the helper uses `schemaData` in the `fetchData` scope — **this is correct** and implementable.
- **Line 229** (`handleFormChange`): `['high', 'low', 'image_moderation'].forEach(type => {` — the spec says use `schema` (component state) here.

**The bug in the spec:** The spec defines the helper as:
```javascript
const getAvailableTiers = (schemaData) => Object.keys(schemaData?.properties?.configurations?.properties?.llm_configs?.properties || {});
```

This nested path `properties.configurations.properties.llm_configs.properties` assumes the `llm_configs` definition is **inlined** directly in the schema root. However, in practice, Pydantic-generated schemas use `$refs` extensively. The API schema served at `/api/external/bots/schema` uses `$defs` for component definitions. Looking at `get_configuration_schema` in `bot_management.py`, the `LLMConfigurations` properties are accessed through `schema[defs_key][ref_name]` (a looked-up `$ref`). The schema's top-level `properties.configurations.properties.llm_configs` will likely contain a `$ref`, not inline `properties`. Therefore, `schemaData?.properties?.configurations?.properties?.llm_configs?.properties` will return `undefined`, and `Object.keys(undefined || {})` returns an empty array — causing the forEach loop to silently never execute, completely breaking the API key source normalization for all tiers.

**Status:** PENDING
**Required Actions:** The spec must verify the actual structure of the API schema returned by `GET /api/external/bots/schema` to confirm whether `llm_configs.properties` is inlined or `$ref`-ed. If the schema uses `$refs`, the helper function must resolve the ref appropriately, for example by checking `$ref` and looking up the corresponding definition in `schemaData.$defs`. Alternatively, the spec should confirm that `llm_configs_defs['properties']` in the backend schema surgery already flattens/inlines the tier properties so the frontend path is valid.

---

### R03
**Priority:** HIGH
**Title:** `initialize_quota_and_bots.py` overwrite/upsert requirement is logistically unclear and potentially destructive

**Detailed Description:**

The spec (Section 3, item 5) states:
> "Update `scripts/migrations/initialize_quota_and_bots.py` to include the `image_transcription` tier in the `token_menu` dictionary, bringing the total to 3 tiers (`high`, `low`, `image_transcription`), and change its logic from skip-if-exists to completely overwrite/upsert."

Examining the current `initialize_quota_and_bots.py` (lines 48–69): it currently does a `find_one` then `insert_one` if missing (skip-if-exists pattern).

The concern: this script's name `initialize_quota_and_bots.py` suggests it is a one-time initialization script. The spec says to change it to "completely overwrite/upsert" — but the script also handles unrelated operations (updating user quotas, deactivating bots). Changing the token_menu section to overwrite would mean **every re-run of this initialization script would reset the token menu**, even if it was legitimately modified. 

Furthermore, the spec also says in item 6 to create a separate migration `migrate_token_menu_image_transcription.py` to "completely delete any existing `token_menu` document and re-insert the full correct menu from scratch." Having *two* places that do a hard-reset of the token menu (one changes from skip-if-exists to overwrite, one does a hard delete+reinsert) is redundant and the spec does not clarify the intended use-case difference between the two.

**Status:** PENDING
**Required Actions:** Clarify whether `initialize_quota_and_bots.py` should use a true upsert (replace the document atomically with `replace_one(..., upsert=True)`) or a conditional overwrite. Also clarify the operational distinction between this script and `migrate_token_menu_image_transcription.py` — is `initialize_quota_and_bots.py` now meant to always reset the token menu, or only when deploying fresh environments? Add an explicit comment in the spec about this to avoid confusion for the implementer.

---

### R04
**Priority:** HIGH
**Title:** `CorruptMediaProcessor` derives `media_type` from mime type prefix stripping — spec does not clarify whether this derivation logic is preserved

**Detailed Description:**

The spec (Output Format section) defines:
> `CorruptMediaProcessor`: return `ProcessingResult(content=f"Corrupted {media_type} media could not be downloaded", failed_reason=..., unprocessable_media=True)`

Examining `media_processors/error_processors.py` lines 5–10:
```python
class CorruptMediaProcessor(BaseMediaProcessor):
    async def process_media(self, file_path: str, mime_type: str, caption: str, bot_id: str) -> ProcessingResult:
        media_type = mime_type.replace("media_corrupt_", "")
        prefix = f"[Corrupted {media_type} media could not be downloaded]"
        content = f"{prefix} {caption}".strip() if caption else prefix
        return ProcessingResult(content=content, failed_reason=f"download failed - {media_type} corrupted")
```

The derivation of `media_type` from `mime_type.replace("media_corrupt_", "")` is the existing correct behavior — the `mime_type` for corrupt media jobs is stored as `"media_corrupt_image"`, `"media_corrupt_audio"`, etc. (see `DEFAULT_POOL_DEFINITIONS` in `media_processing_service.py` line 20). After the refactor removes `caption` from `process_media`, the spec's new content string `f"Corrupted {media_type} media could not be downloaded"` (without brackets) is correct in form, but the spec says nothing about whether the existing `mime_type.replace("media_corrupt_", "")` derivation must be retained. An implementer replacing the method body might inadvertently drop this stripping logic.

**Status:** PENDING
**Required Actions:** Add a note to the spec's `CorruptMediaProcessor` content definition explicitly stating that `media_type` is derived from `mime_type.replace("media_corrupt_", "")` (the existing logic), i.e.: *"`media_type` is derived from `mime_type.replace("media_corrupt_", "")` — this existing derivation must be preserved."*

---

### R05
**Priority:** HIGH
**Title:** `_handle_unhandled_exception` best-effort delivery path is not explicitly confirmed to correctly receive the formatted string after the reassignment

**Detailed Description:**

The spec (Output Format section) states:
> "Update `BaseMediaProcessor._handle_unhandled_exception` to ensure its `ProcessingResult` correctly sets `unprocessable_media=True` and change its hardcoded content from `\"[Media processing failed]\"` to `\"Media processing failed\"` to avoid double-wrapping."

And:
> "After `result.content = format_processing_result(result, caption)`, both `_persist_result_first` and `update_message_by_media_id` will automatically receive the formatted string via `result.content` — no further action is needed at those call sites."

Examining `_handle_unhandled_exception` in `media_processors/base.py` (lines 121–140), the method:
1. Creates `ProcessingResult(content="[Media processing failed]", ...)` 
2. Calls `_persist_result_first(job, result, db)`
3. Calls `_archive_to_failed(job, result, db)`
4. In the best-effort delivery block, calls `bot_queues.update_message_by_media_id(..., result.content)`

If `result.content = format_processing_result(result, caption)` is called **between steps 1 and 2**, then steps 2, 3, and 4 all use the formatted `result.content`. This is correct. **However**, the spec's clarifying note says "`_persist_result_first` and `update_message_by_media_id` will automatically receive the formatted string" — but this note appears to be written in the context of `process_job`. The spec does not explicitly confirm that the same guarantee applies to the `_archive_to_failed` call inside `_handle_unhandled_exception`, which also reads `result.content` (via `doc["result"]` using `result.content` at line 109–110). `_archive_to_failed` stores `result.content` in the `_failed` collection, so it will correctly receive the formatted string too — but the spec is silent about this.

**Status:** PENDING
**Required Actions:** Add an explicit note that in `_handle_unhandled_exception`, the `result.content = format_processing_result(result, caption)` reassignment must occur **before** `_persist_result_first`, `_archive_to_failed`, and the best-effort delivery all read `result.content`. The spec should confirm that `_archive_to_failed` inherits the formatted string correctly through `result.content` with no further changes needed.

---

### R06
**Priority:** HIGH
**Title:** `ImageVisionProcessor.process_media` must call `resolve_bot_language` but the spec does not address error propagation or call ordering relative to moderation

**Detailed Description:**

The spec (Transcription section) states:
> "`ImageVisionProcessor` will explicitly retrieve the bot's configured language by calling `resolve_bot_language(bot_id)`. It will then use the bot's `image_transcription` tier…"

And (Processing Flow section):
> "After `moderation_result` is obtained: If `moderation_result.flagged == false`: proceed to transcribe the image."

Examining `media_processors/image_vision_processor.py`, the current `process_media` method:
1. Loads image base64
2. Creates moderation provider
3. Gets `moderation_result`
4. Returns a stub result

The spec says `resolve_bot_language` is called in `process_media`. The question is: **when** is it called? Options:
- Before moderation (wastes a DB roundtrip if the image ends up flagged)
- After moderation check passes (only when transcription will actually happen — more efficient)

The spec says "retrieve the bot's configured language" in the transcription flow, suggesting it should happen when transcription is determined to proceed. But the spec also says "No custom error handling (`try/except`) should be added around `transcribe_image`" and errors propagate to `BaseMediaProcessor.process_job`. This same error propagation philosophy should apply to `resolve_bot_language`, but unlike `transcribe_image`, if `resolve_bot_language` raises (e.g., bot config not found), it will also propagate — this is correct behavior per the spec's implicit design, but:

A subtle issue: `resolve_bot_language` queries the DB, same collection as `resolve_model_config`. The spec says it falls back to `"en"` if the document or field is missing. But `resolve_model_config` raises `ValueError` if no config is found. `resolve_bot_language` must NOT raise if config is missing — it must return `"en"`. The spec states this fallback but does not cross-reference the comparison with `resolve_model_config`'s raise behavior, which could confuse an implementer into incorrectly mirroring `resolve_model_config`'s error-raising pattern.

**Status:** PENDING
**Required Actions:** Add a note to the spec clarifying (1) `resolve_bot_language` should be called **inside the** `if moderation_result.flagged == False` branch, just before the transcription call, to avoid unnecessary DB queries for flagged images. (2) Explicitly contrast its fallback-to-`"en"` behavior against `resolve_model_config`'s raise behavior: *"`resolve_bot_language` must fall back to `"en"` on any missing document or field — it must never raise. This contrasts with `resolve_model_config`, which raises `ValueError` for missing configurations."*

---

### R07
**Priority:** MEDIUM
**Title:** `create_model_provider` calling `provider.get_llm()` in the factory potentially creates a second `ChatOpenAI` instance if `__init__` already stored `self._llm`

**Detailed Description:**

The spec (Section 1) mandates constructor-time initialization: both `OpenAiChatProvider` and `OpenAiImageTranscriptionProvider` create `self._llm` in `__init__`, and `get_llm()` returns `self._llm`. The factory (`create_model_provider`) calls:
```python
llm = provider.get_llm()
```
to get the `llm` object for callback attachment.

Under the new design, `get_llm()` does NOT create a new instance — it simply returns `self._llm`. So calling `provider.get_llm()` in the factory is safe (no double construction). **However**, the spec says:
> "Both `OpenAiChatProvider` and `OpenAiImageTranscriptionProvider` must use constructor-time initialization: create the `ChatOpenAI` instance inside `__init__` and store it as `self._llm`. Make `get_llm()` simply return `self._llm`."

And the factory logic text says:
```
YES → llm = provider.get_llm()
      attach TokenTrackingCallback(llm)
```

The callback attachment mutates `llm.callbacks`. Since `llm is provider._llm` (same object), mutating `llm.callbacks` also updates `provider._llm.callbacks`. When `transcribe_image()` later calls `self._llm.ainvoke(...)`, the same callback is present. This is the desired behavior.

But what if the factory is called twice for the same provider (not expected, but not guarded against)? Each call to `provider.get_llm()` returns the same `self._llm`, so the callback would be appended twice if `create_model_provider` is somehow called twice for the same provider instance. The spec doesn't guard against this. However, since `create_model_provider` creates a new `ProviderClass(config=config)` each time it is called (line 44: `provider = ProviderClass(config=config)`), each factory call produces a fresh provider instance with a fresh `self._llm` — so double-callback-attachment is not a risk in practice.

The actual gap: the spec does not confirm that `create_model_provider` always creates a fresh `ProviderClass` instance (which it does via `ProviderClass(config=config)`), versus caching providers. This implicit assumption should be documented.

**Status:** PENDING
**Required Actions:** Add a brief note to the spec confirming that `create_model_provider` always constructs a fresh provider instance (`ProviderClass(config=config)`) and does not cache or reuse provider instances. This closes the implicit assumption and ensures the callback-continuity guarantee remains valid across multiple calls to `create_model_provider`.

---

### R08
**Priority:** MEDIUM
**Title:** New `os.getenv` calls for `DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE` and `DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT` have no specified fallback defaults

**Detailed Description:**

The spec (Configuration section) states:
> "the configuration should use new dedicated environment variables: `os.getenv(\"DEFAULT_MODEL_IMAGE_TRANSCRIPTION\", \"gpt-5-mini\")`, `os.getenv(\"DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE\")`, and `os.getenv(\"DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT\")`"

And (Section 3, item 2):
> "Extend `DefaultConfigurations` in `config_models.py` with `model_provider_name_image_transcription = \"openAiImageTranscription\"` and defaults for the image transcription model/settings using `os.getenv(\"DEFAULT_MODEL_IMAGE_TRANSCRIPTION\", \"gpt-5-mini\")`, as well as introducing new dedicated environment variables `DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE` and `DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT`…"

Examining `config_models.py` (`DefaultConfigurations` class, lines 169–179), every existing `os.getenv` call includes a **fallback default value**:
- `os.getenv("DEFAULT_CHAT_PROVIDER", "whatsAppBaileys")`
- `os.getenv("DEFAULT_MODEL_HIGH", "gpt-5")`
- `os.getenv("DEFAULT_MODEL_TEMPERATURE", "0.05")`
- `os.getenv("DEFAULT_MODEL_REASONING_EFFORT", "minimal")`

However, the spec's new `os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE")` and `os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT")` have **no fallback defaults specified**. If these env vars are not set, `os.getenv()` returns `None`. Since `DefaultConfigurations.model_temperature` is typed as `float`, assigning `None` to a `float` field would cause a `TypeError` at class definition time when constructing `ImageTranscriptionProviderConfig` via `get_bot_defaults`.

Even if the fields are `Optional`, the spec is inconsistent with its own pattern of always providing fallbacks. The spec should explicitly specify: should these fall back to the `low` tier defaults (`model_temperature = 0.05`, `model_reasoning_effort = "minimal"`)? Or should they have different fallbacks?

**Status:** PENDING
**Required Actions:** Specify explicit fallback values for the new env vars in `DefaultConfigurations`:
- `DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE`: recommend `float(os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE", "0.05"))` (matches `low` tier)
- `DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT`: recommend `os.getenv("DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT", "minimal")` (matches `low` tier)
Both are consistent with the spec's statement that `image_transcription` defaults match the `low` tier settings.

---

### R09
**Priority:** MEDIUM
**Title:** `EditPage.js` `handleFormChange` forEach loop for `image_transcription` tier requires static addition, not just the dynamic helper, for `reasoning_effort` normalization

**Detailed Description:**

The spec (Section 4, items 4 and 5) says:
1. Replace the hardcoded `["high", "low", "image_moderation"]` array in `handleFormChange` with the dynamic helper `getAvailableTiers(schema)`.
2. Statically add a fourth entry to the `llm_configs` object in `uiSchema` for `image_transcription`.

Item 1 correctly addresses the **general loop** for `api_key_source` handling. However, the `handleFormChange` function (lines 229–244) also performs `reasoning_effort` normalization logic inside the same loop. The spec's dynamic helper will automatically include `image_transcription` in the loop iteration once it's a tier in the schema — **this is correct**.

However, there is a subtlety: `image_transcription` uses `ImageTranscriptionProviderConfig`, which inherits `ChatCompletionProviderSettings` and thus has `reasoning_effort`. The normalization logic inside the loop (lines 239–242) guards with `const newReasoningEffort = providerConfig.reasoning_effort`. For the `image_moderation` tier, `BaseModelProviderConfig` does NOT have a `reasoning_effort` field, so `providerConfig.reasoning_effort` would be `undefined` — the guard works by accident. When `image_transcription` is added dynamically to the loop, it DOES have `reasoning_effort`, so the normalization will apply correctly. 

The real gap: the spec requires `uiSchema` to have a static `image_transcription` entry specifying `"ui:title": "Image Transcription Model"` and `NestedCollapsibleObjectFieldTemplate`. But unlike the other tiers (`high`, `low`), the spec does not specify whether the `provider_config` sub-entry for `image_transcription` in `uiSchema` should also include `reasoning_effort`, `seed`, and `api_key_source` UI titles — it only says "the rest of the template configuration should match the other tiers exactly." An implementer needs explicit confirmation that this means copying the `provider_config` sub-section verbatim from `high`/`low`.

**Status:** PENDING
**Required Actions:** The spec should explicitly state: *"The `image_transcription` uiSchema entry's `provider_config` sub-object should be identical to the `high` and `low` tiers' `provider_config` entries, including `api_key_source`, `reasoning_effort`, and `seed` UI title properties and `FlatProviderConfigTemplate`."* This prevents a minimal copy that omits the `provider_config` sub-entry entirely.

---

### R10
**Priority:** MEDIUM
**Title:** Spec requires adding `image/gif` to `ImageVisionProcessor` pool, but does not name `media_processing_service.py` `DEFAULT_POOL_DEFINITIONS` as the file to update

**Detailed Description:**

The spec (Processing Flow section) states:
> "`ImageVisionProcessor` requirements must officially add `\"image/gif\"` to the media processing pool definitions alongside JPEG, PNG, and WEBP, strictly passing it to OpenAI to leverage their native non-animated GIF support."

Examining `services/media_processing_service.py` line 18:
```python
{"mimeTypes": ["image/jpeg", "image/png", "image/webp"], "processorClass": "ImageVisionProcessor", ...}
```

And `_ensure_configuration_templates` (lines 108–135) inserts `DEFAULT_POOL_DEFINITIONS` into MongoDB on first run. The pool definitions are configurable — they are stored in the `configurations` collection under `_mediaProcessorDefinitions`. On subsequent runs, the DB version takes precedence over `DEFAULT_POOL_DEFINITIONS` (see `_load_pool_definitions` lines 95–106).

This means: just updating `DEFAULT_POOL_DEFINITIONS` in `media_processing_service.py` to add `image/gif` will NOT update existing environments where the pool definitions were already initialized in MongoDB. The spec does not address this deployment concern — existing environments will continue routing GIFs to `UnsupportedMediaProcessor` unless the MongoDB document is also updated. This likely requires either a migration script or the `initialize_quota_and_bots.py` script to force-update the pool definitions.

**Status:** PENDING
**Required Actions:** (1) Add `services/media_processing_service.py` explicitly to the list of files to update in the spec (add `"image/gif"` to `DEFAULT_POOL_DEFINITIONS`). (2) Address the deployment concern for existing environments by either: adding a migration script for the `_mediaProcessorDefinitions` document in MongoDB, or noting that admins must manually delete the existing configuration document to force re-initialization with the new defaults.

---

### R11
**Priority:** LOW
**Title:** `QuotaService.load_token_menu` self-healing insert has no error handling contract for insert failures

**Detailed Description:**

The spec (Section 3, item 7) states:
> "Update `QuotaService.load_token_menu()` to automatically insert a default `token_menu` document into the global config collection if it is missing."

The current `load_token_menu` simply logs an error if the document is missing. The spec's new behavior inserts a new document. However, in a multi-instance deployment, two backend instances may both read "no token_menu" simultaneously and both attempt to insert the same document with `_id: "token_menu"`, causing a `DuplicateKeyError` on the second insert.

The spec does not specify how to handle insert failures. Options include: (a) use `replace_one(..., upsert=True)` instead of `insert_one`, (b) catch `DuplicateKeyError` and re-fetch the now-existing document, or (c) use `find_one_and_update` with upsert. The spec is silent on this.

**Status:** PENDING
**Required Actions:** Specify that the self-healing insert should use `insert_one` wrapped in a try/except for `DuplicateKeyError` (or similar pymongo exception), re-fetching the document if the insert fails due to concurrent insertion. Alternatively, use `update_one({"_id": "token_menu"}, {"$setOnInsert": default_doc}, upsert=True)` to make the operation atomic and idempotent.

---

### R12
**Priority:** LOW
**Title:** Required `image_transcription` field in `LLMConfigurations` will break existing `GET /{bot_id}` endpoint for non-migrated bots before migration runs

**Detailed Description:**

The spec (Section 3, item 4) states:
> "Define `LLMConfigurations.image_transcription` as a strictly required field using `Field(...)` inside `LLMConfigurations` to keep it consistent with the other tiers."

And:
> "Note: Making the field required is safe because the deployment sequence **must** ensure the migration script runs successfully before the new code is activated."

This assumption is correct for new bot creation (defaults include the field) and for fully-migrated environments. However, `bot_management.py` line 457 calls `BotConfiguration.model_validate(config_data)` inside the `GET /{bot_id}` endpoint for role-based config validation. If the migration has NOT yet run for a specific bot, this `model_validate` call will raise a Pydantic `ValidationError` for the missing required field, causing a `500 Internal Server Error` for the `GET` endpoint before migration.

This is a brief but real deployment window risk: if the new code is deployed and any request to read an un-migrated bot's config arrives before the migration completes, the GET endpoint fails. The spec mentions this risk for the "deployment sequence" but does not prescribe a resolution for API consumers during the migration window.

**Status:** PENDING
**Required Actions:** Add a note to the deployment checklist explicitly acknowledging: *"During the migration window, `GET /{bot_id}` calls for un-migrated bots will return a 500 error. To minimize this, the migration script should be run and verified before the new code version receives any production traffic. If a zero-downtime migration is required, consider temporarily making `image_transcription` an `Optional` field with a default until migration completes."*

---

*Review generated: 2026-03-20 | Reviewer: ag_opus_4_6 | Strict Mode*
