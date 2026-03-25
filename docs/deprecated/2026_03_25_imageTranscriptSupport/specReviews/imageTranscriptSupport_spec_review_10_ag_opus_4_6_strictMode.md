# Spec Review: imageTranscriptSupport
**Review ID:** `10_ag_opus_4_6_strictMode`

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|-----|-------|------|--------|
| P1 | RV-01 | `ProcessingResult` missing `unprocessable_media` field causes runtime crash | [→](#rv-01) | READY |
| P1 | RV-02 | `process_media` caption removal conflicts with `process_job` call-site still passing caption | [→](#rv-02) | READY |
| P1 | RV-03 | `LLMProvider` / `BaseLLMProvider` naming ambiguity — spec uses both names inconsistently | [→](#rv-03) | READY |
| P1 | RV-04 | `chat_completion.py` `ChatCompletionProvider` is currently concrete (abstract `get_llm`), spec reclassifies it as empty type-marker — method conflict | [→](#rv-04) | READY |
| P1 | RV-05 | `find_provider_class` module-name filter will silently break for existing `openAiModeration` if filter logic is incorrect | [→](#rv-05) | READY |
| P1 | RV-06 | `ConfigTier` Literal not updated — `create_model_provider` and `resolver.py` will reject `"image_transcription"` tier at type level | [→](#rv-06) | READY |
| P2 | RV-07 | `ImageVisionProcessor` is instantiated with no `__init__` args but `BaseMediaProcessor.__init__` requires `handled_mime_types` | [→](#rv-07) | READY |
| P2 | RV-08 | `OpenAiChatProvider` constructor-time initialization conflicts with current lazy `get_llm()` pattern — refactor scope is wide | [→](#rv-08) | READY |
| P2 | RV-09 | `update_message_by_media_id` signature mismatch: queue method takes `(guid, content)` but `process_job` calls with `(correspondent_id, guid, content)` | [→](#rv-09) | READY |
| P2 | RV-10 | `error_processors` bracket/caption removal breaks existing non-flagged normal output path — caption is still needed for non-`unprocessable_media` cases | [→](#rv-10) | READY |
| P2 | RV-11 | `initialize_quota_and_bots.py` token_menu missing `image_transcription` tier — spec needs clarification on why `image_moderation` is excluded | [→](#rv-11) | READY |
| P2 | RV-12 | `EditPage.js` hardcoded tier list at line 135 (`api_key_source` loop) not addressed by spec's helper function strategy | [→](#rv-12) | READY |
| P3 | RV-13 | Spec states `LLMConfigurations.image_transcription` uses `Field(...)` (required) but existing DB documents lack the field — migration ordering risk | [→](#rv-13) | READY |
| P3 | RV-14 | `global_configurations` referenced in spec as a project file does not exist as a standalone file | [→](#rv-14) | READY |
| P3 | RV-15 | `QuotaService.load_token_menu` self-healing logic correctly specifies "all 3 tiers" — needs explicit comment about `image_moderation` exclusion | [→](#rv-15) | READY |
| P3 | RV-16 | `migrate_token_menu_image_transcription.py` "hard reset" strategy is destructive — risk accepted for non-prod | [→](#rv-16) | READY |
| P4 | RV-17 | Spec lacks explicit test coverage for the moderation-flagged path and the `unprocessable_media` caption-appending behavior | [→](#rv-17) | READY |
| P4 | RV-18 | `detail` field value `"original"` is not a valid OpenAI Vision API value — spec accepts it deliberately but it will produce an API error | [→](#rv-18) | READY |
| P4 | RV-19 | Spec omits `media_processors/__init__.py` changes — no changes actually required for this file | [→](#rv-19) | READY |

---

## Detailed Descriptions

---

### RV-01
**Priority:** P1
**Title:** `ProcessingResult` missing `unprocessable_media` field causes runtime crash

**Detailed Description:**
The current `infrastructure/models.py` defines `ProcessingResult` as:
```python
@dataclass
class ProcessingResult:
    content: str
    failed_reason: Optional[str] = None
```
There is no `unprocessable_media` field. The spec (§ Processing Flow, § Output Format, § Error Handling) requires extensive use of `result.unprocessable_media`, both in `ImageVisionProcessor` (to return `unprocessable_media=True` for flagged images) and in `BaseMediaProcessor.process_job()` (to check `result.unprocessable_media` for formatting logic). If this field is not added, every `ProcessingResult(unprocessable_media=True)` call and every `if result.unprocessable_media:` check will fail at runtime. This is a foundational data-model change that all other processing logic depends on. The spec clearly mandates it but does not call it out explicitly as a data-model change in a checklist or deployment step.

**Status:** READY
**Required Actions:** In `infrastructure/models.py`, add `unprocessable_media: bool = False` to the `ProcessingResult` dataclass, accompanied by a docstring comment explaining the semantic: *"True means the media could not be meaningfully transcribed; `process_job` will wrap the content in brackets and append any caption."*

---

### RV-02
**Priority:** P1
**Title:** `process_media` caption removal conflicts with `process_job` call-site still passing caption

**Detailed Description:**
The spec (§ Output Format) says:
> "Remove the `caption: str` argument from the `process_media` signature in `BaseMediaProcessor` and update all subclass signatures to match."

However, `BaseMediaProcessor.process_job()` (line 29 of `base.py`) currently calls:
```python
self.process_media(file_path, job.mime_type, job.placeholder_message.content, job.bot_id)
```
If `caption` is removed from the `process_media` signature, this call site must also be updated. The spec does not mention updating the `process_job` call site at all. Additionally, the spec says caption-appending logic moves into `process_job` after the call (checking `result.unprocessable_media` AND `job.placeholder_message.content`). But `job.placeholder_message.content` is the caption — so the caption is still accessed inside `process_job`, just no longer passed down. This restructuring is implicitly required but never explicitly stated as a change to `process_job`'s internal call to `process_media`.

All existing processors (`CorruptMediaProcessor`, `UnsupportedMediaProcessor`, `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`, `ImageVisionProcessor`) currently accept `caption` in their `process_media` signatures and use it internally for formatting. Removing `caption` from the signature means all these processors must stop using caption internally (since the spec moves that responsibility to `process_job`). The spec addresses error processors explicitly but does not mention updating stub processors which also use `caption` in their responses.

**Status:** READY
**Required Actions:** 
1. Update `BaseMediaProcessor.process_job()` to remove the `caption` argument from the `self.process_media` call.
2. Update the `process_media` method signature in `BaseMediaProcessor` and **all** subclasses (including `CorruptMediaProcessor`, `UnsupportedMediaProcessor`, and all stub processors in `stub_processors.py`) to remove the `caption` parameter.

---

### RV-03
**Priority:** P1
**Title:** `LLMProvider` / `BaseLLMProvider` naming ambiguity — spec uses both names inconsistently

**Detailed Description:**
In § Provider Architecture, the spec states:
> "Define a new abstract base class `LLMProvider` (or `BaseLLMProvider`) in `model_providers/base.py`"

Then in the Mermaid diagram the class is named `LLMProvider`. Throughout the rest of the spec the name `LLMProvider` is used consistently (e.g., "unified `isinstance(provider, LLMProvider)` branch", "Refactor `create_model_provider` to use a unified `isinstance(provider, LLMProvider)` branch"). However, the parenthetical `(or BaseLLMProvider)` is ambiguous and leaves the implementer free to choose either name, which could cause import mismatches across multiple files that reference it. The spec must settle on one name. Given that the Mermaid diagram and all textual references after the first mention use `LLMProvider`, that should be the canonical name, but the spec should remove the ambiguity.

**Status:** READY
**Required Actions:** Standardize the new abstract base class name to `LLMProvider` exactly. Update all occurrences in the spec to `LLMProvider` and remove all parenthetical references to `(or BaseLLMProvider)`.

---

### RV-04
**Priority:** P1
**Title:** `ChatCompletionProvider` currently has abstract `get_llm` — spec's type-marker reclassification removes it, which is a breaking change

**Detailed Description:**
Current `model_providers/chat_completion.py`:
```python
class ChatCompletionProvider(BaseModelProvider):
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        pass
```
The spec states ChatCompletionProvider should "become an empty type-marker class" after inheriting from `LLMProvider`. The `get_llm` abstract method would then live in `LLMProvider` not in `ChatCompletionProvider`. This means:
1. `ChatCompletionProvider` goes from declaring `get_llm` to inheriting it from `LLMProvider` — the abstract method moves up the hierarchy.
2. `OpenAiChatProvider` currently implements `get_llm` directly on `ChatCompletionProvider`, which satisfies both. After refactoring, `OpenAiChatProvider` must implement `LLMProvider.get_llm()`. This works, but the spec doesn't call out that `ChatCompletionProvider`'s existing `@abstractmethod` declaration must be removed.

If an implementer simply adds `ChatCompletionProvider --> LLMProvider` without removing the existing `@abstractmethod get_llm` from `ChatCompletionProvider`, there is no conflict but the type-marker intent is muddied. The spec should explicitly state the `@abstractmethod` in `ChatCompletionProvider` is to be removed.

**Status:** READY
**Required Actions:** Explicitly instruct the implementer in the spec to remove the `@abstractmethod def get_llm(self)` declaration and `abc` imports from `model_providers/chat_completion.py`, replacing the `ChatCompletionProvider` class body with `pass` so it cleanly acts as an empty type-marker inheriting from `LLMProvider`.

---

### RV-05
**Priority:** P1
**Title:** `find_provider_class` module-name filter may use incorrect comparison and break existing providers

**Detailed Description:**
The spec prescribes:
> "`find_provider_class` in `utils/provider_utils.py` must include an `obj.__module__ == module.__name__` filter"

This is potentially incorrect. `obj.__module__` returns the **dotted module path** where the class was originally defined (e.g., `"model_providers.openAi"`), while `module.__name__` also returns the **dotted module path** of the imported module (e.g., `"model_providers.openAiImageTranscription"`). So the comparison `obj.__module__ == module.__name__` is actually valid and correct — it checks that the class's original module matches the loaded module. However, the current `find_provider_class` uses `inspect.getmembers` which returns ALL members including imported ones, sorted alphabetically. The issue is real: if `openAiImageTranscription.py` imports `OpenAiChatProvider`, `inspect.getmembers` would iterate alphabetically and `OpenAiChatProvider` (C < I) would come before `OpenAiImageTranscriptionProvider`. The fix is sound, but the spec should state clearly that this filter is comparing `obj.__module__` (dotted path of originating module) to `module.__name__` (dotted path of the loaded module), and that both are full dotted paths like `"model_providers.openAiImageTranscription"`, not short names. Without this clarification, an implementer might incorrectly use `module.__file__` or `module.__spec__.name` or check the short name only.

Also note: `inspect.isabstract(obj)` check is already in `find_provider_class` which would correctly filter out abstract classes, but the alphabetical ordering issue for concrete imported classes is not filtered by abstraction alone.

**Status:** READY
**Required Actions:** Explicitly clarify in the spec that the new filter `obj.__module__ == module.__name__` must compare the **full dotted path** of the originating module (`obj.__module__`) against the **full dotted path** of the loaded module (`module.__name__`), preventing alphabetical sorting of imported classes from picking the wrong provider.

---

### RV-06
**Priority:** P1
**Title:** `ConfigTier` Literal not updated — `create_model_provider` and `resolver.py` will reject `"image_transcription"` tier at type-check level

**Detailed Description:**
Current `config_models.py` line 5:
```python
ConfigTier = Literal["high", "low", "image_moderation"]
```
The spec (§ Configuration, § New Configuration Tier Checklist item 1) says to add `"image_transcription"` to `ConfigTier`. However, `create_model_provider` accepts `config_tier: ConfigTier` and `resolve_model_config` also uses `ConfigTier`. If `ConfigTier` is not updated, any call `create_model_provider(..., "image_transcription")` will be a type error and will fail at runtime (FastAPI/Pydantic may also validate it). The spec mentions this in the checklist but does NOT provide an explicit code snippet showing the updated Literal. While this is referenced in checklist item 1, it's easy to miss because the checklist is in section 4 and the actual type definition is in `config_models.py`. This coordinated multi-file change should be more prominent and should include the updated type definition.

**Status:** READY
**Required Actions:** Add an explicit code block to the spec for `config_models.py` showing the exact required update: `ConfigTier = Literal["high", "low", "image_moderation", "image_transcription"]`.

---

### RV-07
**Priority:** P2
**Title:** `ImageVisionProcessor` is instantiated with no `__init__` args but `BaseMediaProcessor.__init__` requires `handled_mime_types`

**Detailed Description:**
`BaseMediaProcessor.__init__` signature:
```python
def __init__(self, handled_mime_types: List[str], processing_timeout: float = 60.0):
```
`ImageVisionProcessor` currently does not override `__init__`. When `factory.py`'s `get_processor_class` returns `ImageVisionProcessor` and the caller instantiates it, the caller must pass `handled_mime_types`. Looking at `factory.py`, it returns the class itself; instantiation happens elsewhere (likely in `services/media_processing_service.py` which the spec references but was not provided for study). The spec does not address how `ImageVisionProcessor` is instantiated or whether it should provide default `handled_mime_types`. The image moderation tier uses `"image_moderation"` mime prefix detection — `ImageVisionProcessor` presumably handles `image/*` types. The spec should document what `handled_mime_types` should be set to for `ImageVisionProcessor`, or confirm its super().__init__ call is handled at the service level.

**Status:** READY
**Required Actions:** Verified: No changes needed. `MediaProcessingService` (lines 146-148) already correctly instantiates all processors (via `get_processor_class`) and passes the required `handled_mime_types` and `processing_timeout` from the pool definitions. `ImageVisionProcessor` and others can safely rely on the base class constructor.

---

### RV-08
**Priority:** P2
**Title:** `OpenAiChatProvider` constructor-time initialization conflicts with current lazy `get_llm()` pattern — refactor scope is wide

**Detailed Description:**
The spec requires:
> "Both `OpenAiChatProvider` and `OpenAiImageTranscriptionProvider` must use constructor-time initialization: create the `ChatOpenAI` instance inside `__init__` and store it as `self._llm`. Make `get_llm()` simply return `self._llm`."

Current `OpenAiChatProvider.get_llm()` creates a new `ChatOpenAI` instance on every call (lazy). Moving to constructor-time initialization means the `ChatOpenAI` instance (with its callback list) is created once in `__init__`. The factory's callback attachment (`create_model_provider`) then mutates `llm.callbacks` after `get_llm()` is called. Since `get_llm()` now returns the same stored `self._llm`, the callback gets attached to the correct object. However, the spec says `create_model_provider` calls `llm = provider.get_llm()` and then mutates `llm.callbacks`. But per the refactor, `self._llm` (the same object) is what's stored. So `llm` and `self._llm` alias each other — mutations to `llm.callbacks` are visible through `self._llm`. This works correctly for the transcription case. The concern is: the spec mentions `OpenAiChatProvider` must also be refactored to use this pattern, but does not flag any existing callers of `OpenAiChatProvider.get_llm()` beyond the factory. If any code bypasses the factory and calls `provider.get_llm()` directly multiple times, it now gets the same instance (previously got a fresh instance each call). This behavioral change is not flagged as a potential breaking change.

**Status:** READY
**Required Actions:** Verified: No changes needed. The spec explicitly requires this change to accommodate callback persistence, and the move to constructor-time initialization is intentional.

---

### RV-09
**Priority:** P2
**Title:** `update_message_by_media_id` signature mismatch — `process_job` calls with wrong argument ordering

**Detailed Description:**
In `base.py` line 54, `process_job` calls:
```python
delivered = await bot_queues.update_message_by_media_id(
    job.correspondent_id, job.guid, result.content
)
```
But in `queue_manager.py`, the `BotQueuesManager.update_message_by_media_id` signature is:
```python
async def update_message_by_media_id(self, correspondent_id: str, guid: str, content: str) -> bool:
```
These match. However, `CorrespondentQueue.update_message_by_media_id` only takes `(self, guid: str, content: str)`:
```python
async def update_message_by_media_id(self, guid: str, content: str) -> bool:
```
This is currently working (BotQueuesManager delegates to CorrespondentQueue with correct args). The spec's change to `process_job` to check `result.unprocessable_media` and format content BEFORE calling `update_message_by_media_id` seems consistent — `result.content` is already the full formatted string at that point, and `update_message_by_media_id` just sets message content. No mismatch. However, the spec's content formatting in `process_job` does NOT account for caption appending when `unprocessable_media=False`. The spec says: "if `result.unprocessable_media` is True AND a caption exists... append `\n[Caption: <caption_text>]`". But what about transcription success (normal) — the transcript itself becomes the message content with no caption? This is correct by design since the transcript replaces the image. However, the spec never explicitly states "when `unprocessable_media=False`, the result content is delivered as-is without caption". This should be stated explicitly.

**Status:** READY
**Required Actions:** Verified: No changes needed. `BotQueuesManager.update_message_by_media_id` (line 404 of `queue_manager.py`) correctly accepts all 3 arguments (`correspondent_id`, `guid`, `content`), which matches the call site in `BaseMediaProcessor.process_job`.

---

### RV-10
**Priority:** P2
**Title:** `error_processors` caption removal breaks the non-`unprocessable_media` normal output path for stub processors

**Detailed Description:**
The spec (§ Output Format) says:
> "Error Processors (`CorruptMediaProcessor`, `UnsupportedMediaProcessor`) must return a `ProcessingResult` with `unprocessable_media = True` and have their manual bracket wrapping and concatenation removed, returning only the base prefix."

Currently:
```python
# CorruptMediaProcessor
content = f"{prefix} {caption}".strip() if caption else prefix
return ProcessingResult(content=content, failed_reason=...)
```
After spec change, caption appending moves to `process_job`. Good. 

But the spec does NOT explicitly address `StubSleepProcessor` and its subclasses (`AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`). These also accept `caption` in `process_media` and return content without bracket wrapping. After `caption` is removed from `process_media`, stub processors currently don't check `unprocessable_media` (they return `ProcessingResult(content="[Transcripted ...]")` already with brackets). These stubs return what appears to be a synthetic success result — `unprocessable_media` would be `False` (default). So caption is NOT appended in `process_job` for stubs (correct behavior). However, the stub processors inline-populate `content` with literal brackets. After removing `caption` from the signature, stub processors would need to stop using `caption` as well (they currently don't use it since they don't have self.caption). Confirming: stub processors do NOT use `caption` directly in their current impl (they just use `file_path`). So stub processors only need their `process_media` signature updated to drop `caption`. The spec doesn't reference stub processors at all in this refactor — this gap should be closed.

**Status:** READY
**Required Actions:** 
1. **Standardize Processors:** Update all processor subclasses (`Corrupt`, `Unsupported`, and all `Stubs`) to return "clean" text without manual bracket wrapping or caption concatenation.
2. **Handle Formatting in `process_job`:** Update `BaseMediaProcessor.process_job` to wrap `result.content` in brackets `[]` if and only if `result.unprocessable_media` is `True`.
3. **Data Retention:** Update `BaseMediaProcessor.process_job` to *always* append the original caption (`\n[Caption: <text>]`) if present, regardless of whether the processing was a success or a failure.

---

### RV-11
**Priority:** P2
**Title:** `initialize_quota_and_bots.py` token_menu missing `image_moderation` tier and doesn't match existing production data

**Detailed Description:**
The spec (§ Deployment Checklist item 5) says:
> "Update `scripts/migrations/initialize_quota_and_bots.py` to include the `image_transcription` tier dict in `token_menu`, and change its logic from skip-if-exists to completely overwrite/upsert."

Current `initialize_quota_and_bots.py` token_menu only has:
```python
token_menu = {
    "high": {...},
    "low": {...}
}
```
There is no `image_moderation` tier in the existing menu either. The spec says to add `image_transcription` but does not mention that `image_moderation` is also missing from this script. If the script is changed to a hard upsert, and `image_moderation` pricing is not included in the upsert, the `image_moderation` tier will be missing from the token_menu document in any fresh DB initialized by this script. The spec's pricing is defined only for `image_transcription` (`input_tokens: 0.25`, `cached_input_tokens: 0.025`, `output_tokens: 2.0`). The `image_moderation` tier pricing is never defined anywhere in the spec. Since `QuotaService.calculate_cost()` uses `config_tier not in self._token_menu` as a guard, moderation costs would silently fall through with cost `0.0` — currently by accident, but future breakage is possible.

**Status:** READY
**Required Actions:** 
1. **Initial Script:** Update `scripts/migrations/initialize_quota_and_bots.py` to include the `image_transcription` tier in the `token_menu` dictionary, bringing the total to 3 tiers (`high`, `low`, `image_transcription`).
2. **Patch Script:** Ensure `scripts/migrations/migrate_token_menu_image_transcription.py` also uses this 3-tier menu.
3. **Clarification:** Add a comment in the code highlighting that `image_moderation` is intentionally omitted from the `token_menu` because it has no model-token cost calculation.

---

### RV-12
**Priority:** P2
**Title:** `EditPage.js` hardcoded tier list at line 135 conflicts — spec's dynamic helper incomplete

**Detailed Description:**
The spec (§ New Configuration Tier Checklist item 4) provides the helper:
```javascript
const getAvailableTiers = (schemaData) => Object.keys(schemaData?.properties?.configurations?.properties?.llm_configs?.properties || {});
```
And says to update **both** hardcoded loops: around line 135 (for `api_key_source`) and line 229 (for `handleFormChange`).

Looking at the actual `EditPage.js`:
- **Line 135**: `['high', 'low', 'image_moderation'].forEach(type => {` — inside `fetchData()`, this runs during data load to backfill `api_key_source`. This runs **before** `schema` is populated in state (the loop uses `originalData`, not `schemaData`). Using `getAvailableTiers(schemaData)` here is correct since `schemaData` is in scope at that point.
- **Line 229**: `['high', 'low', 'image_moderation'].forEach(type => {` — inside `handleFormChange`, `schema` is in component state. The helper must be called as `getAvailableTiers(schema)` not `getAvailableTiers(schemaData)` since `schemaData` is only in `fetchData` scope.

The spec's helper is defined as taking `schemaData` as parameter, which is ambiguous — in `handleFormChange`, the right source is component state `schema`. The spec should clarify which variable to use in each location.

Additionally, the `uiSchema` in `EditPage.js` hardcodes the `llm_configs` sub-sections statically (lines 419-458). The spec (§ New Configuration Tier Checklist item 5) says to **statically add** a 4th entry for `image_transcription` to `uiSchema`. This static addition is required regardless of the dynamic helper — these are separate concerns (schema validation vs. UI rendering). The spec correctly states this as static addition, but reviewers should note that adding `image_transcription` to `uiSchema` statically while extracting the tier list dynamically is an intentional asymmetry that should be acknowledged in the code.

**Status:** READY
**Required Actions:** Mandate a comprehensive refactor of `EditPage.js`. Every occurrence of the hardcoded tier array `["high", "low", "image_moderation"]` (specifically around line 135 for `api_key_source` and line 229 for `handleFormChange`) must be replaced with the dynamic `getAvailableTiers(schemaData)` helper function defined in the spec. The spec should also clarify that the helper should use `schemaData` in `fetchData` and component state `schema` in `handleFormChange`.

---

### RV-13
**Priority:** P3
**Title:** `LLMConfigurations.image_transcription` as required `Field(...)` creates a startup failure if migration hasn't run

**Detailed Description:**
The spec (§ Deployment Checklist item 4) says:
> "Define `LLMConfigurations.image_transcription` as a strictly required field using `Field(...)` ... Rely solely on the database migration script (`migrate_image_transcription.py`) to backfill this data for old bots."

However, `BotConfiguration.model_validate(config_data)` is called in `bot_management.py` in multiple routes (link, get, save). If the migration has not run yet and a bot config loaded from DB lacks `image_transcription`, `model_validate` will raise a Pydantic `ValidationError`, crashing those routes. The spec acknowledges this implicitly by insisting on migration-first rollout, but this dependency order is not documented in the Deployment Checklist as a sequencing requirement. The deployment checklist is ordered (1-7) but step 4 (make field required) is listed before any verification steps. Step 1 is the migration — so the sequence implies migration must run before code deploy, but this is never stated as a hard prerequisite.

**Status:** READY
**Required Actions:** Add a documentation note/line in the spec (Checklist Item 4) explicitly stating that making the field required is safe because the deployment sequence **must** ensure the migration script (`migrate_image_transcription.py`) runs successfully before the new code is activated, guaranteeing that all bot documents in the database already contain the tier.

---

### RV-14
**Priority:** P3
**Title:** `global_configurations` referenced in spec as a project file does not exist as a standalone file

**Detailed Description:**
The spec's "Project Files" section lists:
> "`global_configurations` *(token menu update for image transcription tier pricing)*"

And the description says:
> "`global_configurations.token_menu` is extended with an `"image_transcription"` pricing entry"

However, searching the project, there is no file named `global_configurations.py` or similar. `COLLECTION_GLOBAL_CONFIGURATIONS` is the MongoDB collection name (defined as `"configurations"` in `db_schema.py`). The `token_menu` is a MongoDB document in that collection, not a Python object. There is no Python module `global_configurations`. The spec appears to be conflating the MongoDB collection/document with a Python module. The actual implementation location for the token menu settings is the migration script and `QuotaService.load_token_menu()`. The spec's "Project Files" reference to `global_configurations` is misleading and may cause confusion for the implementer.

**Status:** READY
**Required Actions:** Update the spec (§ Relevant Background Information) to remove `global_configurations` from the "Project Files" list and explicitly clarify that references to `global_configurations.token_menu` refer to the MongoDB collection document, not a Python module.

---

### RV-15
**Priority:** P3
**Title:** `QuotaService.load_token_menu` self-healing logic spec says insert default with "all 3 tiers" but there are actually 4 tiers

**Detailed Description:**
The spec (§ Deployment Checklist item 5) says:
> "Update `QuotaService.load_token_menu()` ... to automatically insert a default `token_menu` document (including all 3 tiers) into the global config collection if it is missing."

But the tiers would be: `high`, `low`, `image_moderation`, `image_transcription` — that is **4 tiers**, not 3. The spec's "3 tiers" count appears to be an error that predates the inclusion of `image_moderation` as a tier, or it counts only the LLM chat tiers (`high`, `low`, `image_transcription`). This is ambiguous and will lead to an incorrectly implemented default token_menu if the implementer takes the "3 tiers" literally.

**Status:** READY
**Required Actions:** Add an explicit comment or documentation note in the spec (§ Deployment Checklist item 5) clarifying that "3 tiers" is correct because `image_moderation` does not perform model-token cost calculation and thus does not require an entry in the `token_menu` document.

---

### RV-16
**Priority:** P3
**Title:** `migrate_token_menu_image_transcription.py` "hard reset" strategy is destructive with no rollback path

**Detailed Description:**
The spec (§ Deployment Checklist item 5) specifies:
> "This script should completely delete any existing `token_menu` document and re-insert the full correct menu from scratch (including `image_transcription`), acting as a hard reset."

This is a destructive operation with no documented rollback or backup step. If the script is run with incorrect pricing data (e.g., a typo in `input_tokens`), the previous data is unrecoverable without a manual DB snapshot. The spec provides no "backup before delete" step or verification gate. For a production script modifying financial/quota data, this is a significant omission. A safer approach (delete → insert with pre-validation, or upsert) should at minimum be flagged as a deliberate risk acceptance.

**Status:** READY
**Required Actions:** Add a comment to the spec (§ Deployment Checklist item 5) explicitly stating that the "hard reset" strategy is acceptable because there is currently no actual production environment, so the risk of data loss or service disruption is zero.

---

### RV-17
**Priority:** P4
**Title:** Spec lacks explicit test coverage for moderation-flagged path and `unprocessable_media` caption-appending behavior

**Detailed Description:**
The spec's (§ Test Expectations) section defines three specific test areas:
1. `detail` filtered from `ChatOpenAI` kwargs
2. Callback continuity
3. Transcription normalization (3 branches)

Missing from the explicit test list:
- Test that `moderation_result.flagged == True` returns `ProcessingResult(unprocessable_media=True, content="cannot process image as it violates safety guidelines")`
- Test that `BaseMediaProcessor.process_job` correctly formats `unprocessable_media=True` result with bracket wrapping
- Test that caption is correctly appended when `unprocessable_media=True` AND `job.placeholder_message.content` is populated
- Test that caption is NOT appended when `unprocessable_media=False`
- Test the `asyncio.TimeoutError` path returns `unprocessable_media=True`

These are core behavioral changes and should be explicitly required by the test expectations section.

**Status:** READY
**Required Actions:** Update the spec (§ Test Expectations) to explicitly include the missing test cases: moderation flagging output format check, `BaseMediaProcessor.process_job` bracket-wrapping and caption-appending logic (for both success and failure), and `asyncio.TimeoutError` path behavior returning `unprocessable_media=True`.

---

### RV-18
**Priority:** P4
**Title:** `detail` value `"original"` is not a valid OpenAI Vision API value — though spec explicitly accepts this

**Detailed Description:**
The spec (§ OpenAI Vision Parameter) states:
> "Valid values: `\"low\"`, `\"high\"`, `\"original\"`, `\"auto\"`"

However, according to the OpenAI Vision API documentation (https://developers.openai.com/api/docs/guides/images-vision), the valid values for `detail` are `"low"`, `"high"`, and `"auto"`. The value `"original"` is not a documented, valid OpenAI detail level. The spec acknowledges this by saying:
> "The decision to omit validation for the `\"original\"` detail level against the configured model is an **accepted, deliberate design choice**"

However, the issue is not just about model compatibility — `"original"` itself is not a valid `detail` value at all on the current OpenAI API. Including it in the `Literal` type (`Literal["low", "high", "original", "auto"]`) means the Pydantic schema will accept this value, and it will only fail at runtime when the API rejects it. The spec should at minimum note that `"original"` may not work with ANY model, not just some models, and that this is an accepted silent-failure point by design. This is flagged P4 because the spec explicitly documents the design choice.

**Status:** READY
**Required Actions:** None. The spec (§ 2) already explicitly states that the decision to omit validation for the `"original"` detail level is an **accepted, deliberate design choice**. No further action is required as the risk is already documented and accepted.

---

### RV-19
**Priority:** P4
**Title:** Spec omits `media_processors/__init__.py` changes — new processor files may need registration

**Detailed Description:**
The spec's "Project Files" section lists `media_processors/__init__.py` as a relevant file, suggesting it may need changes. The spec text, however, never describes what changes to make to this file. If `__init__.py` re-exports modules or sets up the processor registry, new provider files (`model_providers/image_transcription.py`, `model_providers/openAiImageTranscription.py`) may need to be registered there. Review of the actual `__init__.py` file was not possible (not shown), but its listing in the "Project Files" section is either:
1. A placeholder that was never followed up in the spec body, or
2. An intentional no-op (the file doesn't need changes, was just listed for context)

The spec should either explicitly state "no changes needed to `__init__.py`" or describe what changes are required.

**Status:** READY
**Required Actions:** None. Investigative check on `media_processors/factory.py` and `__init__.py` confirms that the factory imports processor classes directly and `__init__.py` is currently empty. Since no new processor files are being added (only the existing `ImageVisionProcessor` is being modified), no registration changes are required in `__init__.py`.
