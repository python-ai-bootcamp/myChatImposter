# Spec Review: Media Processor Image Moderation

**Spec File:** `docs/moderateImage_spec.md`  
**Reviewer:** Sir Gravitush, Master of Tech  
**Date:** 2026-03-12  

---

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| 🔴 P1 | F-001 | `process_media()` signature change breaks all existing processors and the base class contract | [Details](#f-001) | PENDING |
| 🔴 P1 | F-002 | `moderate_image()` return type contradiction — spec says `.model_dump()` on raw SDK response, but existing provider already returns a `ModerationResult` Pydantic model | [Details](#f-002) | PENDING |
| 🟠 P2 | F-003 | `moderate_image()` method signature mismatch — spec wants `(base64_image, mime_type)`, existing code takes `(image_url)` | [Details](#f-003) | PENDING |
| 🟠 P2 | F-004 | Spec references a nonexistent `ConfigurationMissingError` exception class | [Details](#f-004) | PENDING |
| 🟡 P3 | F-005 | Spec refers to "OpenAiLlmProvider" — the actual class is `OpenAiModerationProvider` | [Details](#f-005) | PENDING |
| 🟡 P3 | F-006 | Spec file lists wrong filenames for project references (`openai.py`, `openai_moderation.py` vs actual `openAi.py`, `openAiModeration.py`) | [Details](#f-006) | PENDING |
| 🟡 P3 | F-007 | No mention of how `ImageVisionProcessor` obtains `bot_id` to resolve the moderation config inside `process_media` | [Details](#f-007) | PENDING |

---

## Detailed Findings

---

### F-001

**Priority:** 🔴 P1  
**Title:** `process_media()` signature change breaks all existing processors and the base class contract  

**Description:**

Section 4.2 of the spec states:

> *"current process_media() signature will be updated to `self.process_media(file_path, job.mime_type, job.bot_id)` since these are all the arguments any media processor needs to run (old stub processors signature will be updated as well as the new ImageVisionProcessor for receiving them correctly)"*

The current abstract method signature defined in `media_processors/base.py` line 80 is:

```python
async def process_media(self, file_path: str, mime_type: str, caption: str, quota_exceeded: Optional[bool]) -> ProcessingResult:
```

And the call site in `base.py` line 29 passes:

```python
result = await asyncio.wait_for(
    self.process_media(file_path, job.mime_type, job.placeholder_message.content, job.quota_exceeded),
    ...
)
```

**Issues with the proposed change:**

1. **Drops `caption`**: Both `CorruptMediaProcessor` and `UnsupportedMediaProcessor` (in `error_processors.py`) actively use the `caption` parameter to construct their error messages (e.g. `f"{prefix} {caption}".strip() if caption else prefix`). Removing `caption` from the signature **breaks these processors** and removes functionality.

2. **Drops `quota_exceeded`**: This field is currently part of the signature. While no current processor acts on it beyond passing it through, it is available for future use. The spec does not acknowledge or address this removal.

3. **Adds `bot_id`**: Only `ImageVisionProcessor` needs `bot_id` (to resolve the moderation config). Pushing it into every processor's signature pollutes the base contract with a concern specific to one subclass.

4. **All existing subclasses break**: `StubSleepProcessor`, `AudioTranscriptionProcessor`, `VideoDescriptionProcessor`, `DocumentProcessor`, `CorruptMediaProcessor`, `UnsupportedMediaProcessor` all need to be updated.

**The spec must explicitly decide:** either keep the base signature as-is and have `ImageVisionProcessor` receive `bot_id` through an alternative mechanism (e.g., constructor injection, or by accessing it from the `job` object at a higher level), or explicitly document the full migration of all affected processors and the removal of the `caption`/`quota_exceeded` parameters with replacement logic for `CorruptMediaProcessor` and `UnsupportedMediaProcessor`.

---

### F-002

**Priority:** 🔴 P1  
**Title:** `moderate_image()` return type contradiction — spec says `.model_dump()` on raw SDK response, but existing provider already returns a `ModerationResult` Pydantic model  

**Description:**

Section 4.4 of the spec states:

> *"**Return Type Conversion**: Call `.model_dump()` on the returned Pydantic `ModerationCreateResponse` object."*

This implies that `process_media` (the caller in `ImageVisionProcessor`) should receive a raw `dict` from the moderation call.

However, the existing `OpenAiModerationProvider.moderate_image()` (in `model_providers/openAiModeration.py`) does NOT return the raw SDK response. It already:
1. Extracts `response.results[0]` 
2. Constructs and returns a `ModerationResult(flagged=..., categories=..., category_scores=...)` Pydantic model

So calling `.model_dump()` on the return of `moderate_image()` would dump a `ModerationResult` dict, **not** the full `ModerationCreateResponse`.

**The spec must clarify the contract:**
- **Option A:** If the spec intends the full raw response to be logged, then `moderate_image()` should be changed to return the raw `ModerationCreateResponse` (or its `.model_dump()` output) directly, and the `ModerationResult` model becomes unused.
- **Option B:** If `ModerationResult` is the intended abstraction boundary, then the spec should say to call `.model_dump()` on the `ModerationResult`, and the logged dict will only contain `{flagged, categories, category_scores}`, not the full API response.

This also affects Spec Section 4.6: *"log the full moderation result dictionary returned by the wrapper"*. What constitutes "full" depends on which option is chosen.

---

### F-003

**Priority:** 🟠 P2  
**Title:** `moderate_image()` method signature mismatch — spec wants `(base64_image, mime_type)`, existing code takes `(image_url)`  

**Description:**

Section 4.4 of the spec states:

> *"The `OpenAiLlmProvider` must take the raw `base64_image` and `mime_type` passed to its `moderate_image` method and construct the data-URI `f"data:{mime_type};base64,{base64_image}"` internally."*

This means the spec expects `moderate_image` to accept two parameters: `base64_image` and `mime_type`.

However, the current `ImageModerationProvider` abstract method in `model_providers/image_moderation.py` line 15 has:

```python
async def moderate_image(self, image_url: str) -> ModerationResult:
```

And the concrete `OpenAiModerationProvider.moderate_image()` in `openAiModeration.py` line 9 takes:

```python
async def moderate_image(self, image_url: str) -> ModerationResult:
```

The spec wants the data-URI to be built **inside** the provider from raw base64 + mime_type, but the current code expects a pre-built `image_url` string.

**The spec should explicitly state** that the `ImageModerationProvider` abstract method signature and the `OpenAiModerationProvider` concrete implementation both need to be updated from `(self, image_url: str)` to `(self, base64_image: str, mime_type: str)`.

---

### F-004

**Priority:** 🟠 P2  
**Title:** Spec references a nonexistent `ConfigurationMissingError` exception class  

**Description:**

Section 4.5 of the spec states:

> *"If the wrapper throws an exception (e.g., `ConfigurationMissingError`, or if the SDK fails after all internal retries)..."*

A search of the entire codebase finds **zero** references to `ConfigurationMissingError`. This class does not exist. The existing configuration resolution code in `services/resolver.py` raises a standard `ValueError` when configuration is not found:

```python
raise ValueError(f"No configuration found for bot_id: {bot_id}")
raise ValueError(f"Tier '{config_tier}' not found in configuration for bot_id: {bot_id}")
```

And `services/model_factory.py` uses generic `Exception` catching.

This is a minor documentation accuracy issue — the spec should reference `ValueError` or simply say "configuration resolution errors" generically, rather than citing a non-existent exception class.

---

### F-005

**Priority:** 🟡 P3  
**Title:** Spec refers to "OpenAiLlmProvider" — the actual class is `OpenAiModerationProvider`  

**Description:**

Section 4.4 states:

> *"The `OpenAiLlmProvider` must take the raw `base64_image` and `mime_type`..."*

There is no class named `OpenAiLlmProvider` in the codebase. The relevant classes are:
- `OpenAiChatProvider` (in `model_providers/openAi.py`) — for chat completions
- `OpenAiModerationProvider` (in `model_providers/openAiModeration.py`) — for image moderation

The spec should reference `OpenAiModerationProvider` instead.

---

### F-006

**Priority:** 🟡 P3  
**Title:** Spec file lists wrong filenames for project references  

**Description:**

The spec's "Relevant Background Information → Project Files" section lists:
- `model_providers\openai.py` — actual file is `model_providers\openAi.py` (camelCase)
- `model_providers\openai_moderation.py` — actual file is `model_providers\openAiModeration.py` (camelCase)

These are case-sensitive on Linux-based systems (relevant since the project uses Docker). The filenames in the spec should match the actual filesystem.

---

### F-007

**Priority:** 🟡 P3  
**Title:** No mention of how `ImageVisionProcessor` obtains `bot_id` to resolve the moderation config inside `process_media`  

**Description:**

The new `ImageVisionProcessor.process_media()` needs `bot_id` to call `create_model_provider(bot_id, feature_name, config_tier)` or equivalent to resolve the moderation provider.

The spec says (Section 4.2):
> *"process_media() signature will be updated to `self.process_media(file_path, job.mime_type, job.bot_id)`"*

However, as discussed in F-001, changing the base signature is problematic. Even setting that aside, the spec **doesn't describe the actual wiring** of how `bot_id` flows into the moderation provider creation. The spec should specify:
1. Will `ImageVisionProcessor` call `create_model_provider()` from `services/model_factory.py`?
2. Or will it directly use `resolve_model_config()` + manual provider instantiation?
3. Or will the provider be injected at construction time?

This is a design gap — the mechanism for provider resolution within `process_media` needs to be specified.

---

## Overall Assessment

The spec captures the **intent** well — extracting `ImageVisionProcessor` into its own module, adding moderation API integration, and keeping the rest as a stub. The broad architecture is sound and aligns with the existing project patterns (`BaseMediaProcessor` lifecycle, `model_factory`, `resolver`).

However, **F-001 and F-002 are genuine P1 issues** that need resolution before implementation begins. The `process_media()` signature change cascades across the entire processor hierarchy and the error about return types will cause implementers to make inconsistent choices. The P2/P3 items are naming/documentation inaccuracies that should be corrected but won't block a careful implementer.

**Recommendation:** Address F-001 and F-002 explicitly in the spec before starting implementation. The remaining items are fixable inline during implementation.
