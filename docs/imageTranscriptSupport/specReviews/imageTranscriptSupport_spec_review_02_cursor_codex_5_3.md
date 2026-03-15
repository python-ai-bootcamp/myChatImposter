# Spec Review: imageTranscriptSupport

**Review ID:** 02_cursor_codex_5_3  
**Spec File:** `/docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`  
**Date:** 2026-03-14

## Overall Assessment

The spec is in strong shape. All seven findings from review 01 have been addressed and incorporated — the flagged-image behavior, `detail` parameter naming, transcription prompt, LangChain invocation pattern, config type hierarchy, and caption handling are all clearly specified. The provider architecture (abstract `ImageTranscriptionProvider` + concrete `OpenAiImageTranscriptionProvider`) is well-defined and follows the existing `ImageModerationProvider` pattern closely.

Three remaining gaps were identified, all relating to deployment mechanics and operational concerns rather than core feature design. **The spec is solid enough to begin implementation**, with these items addressed either during implementation or as documented follow-ups.

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| MEDIUM | ITS-09 | Recommended design improvement: extend `ChatCompletionProvider` instead of parallel hierarchy | [Details](#its-09-recommended-design-improvement-extend-chatcompletionprovider-instead-of-creating-a-parallel-provider-hierarchy) | READY |
| MEDIUM | ITS-10 | Incomplete default propagation and migration strategy | [Details](#its-10-incomplete-default-propagation-and-migration-strategy) | READY |
| LOW | ITS-11 | `detail` Literal excludes `"original"` value from OpenAI spec | [Details](#its-11-detail-literal-excludes-original-value-from-openai-spec) | READY |

---

## Detailed Findings

### ITS-09: Token tracking and quota enforcement gap for image transcription

- **Priority:** MEDIUM
- **ID:** ITS-09
- **Title:** Recommended design improvement: extend `ChatCompletionProvider` instead of creating a parallel provider hierarchy
- **Detailed Description:**  
  The spec proposes a new `ImageTranscriptionProvider` abstract class (mirroring the `ImageModerationProvider` pattern) where the provider internally builds a `ChatOpenAI`, invokes it, and returns the result. This creates a third branch in `create_model_provider` that is separate from the existing `ChatCompletionProvider` path.

  However, unlike `ImageModerationProvider` (which uses OpenAI's free moderation endpoint via `AsyncOpenAI` — a fundamentally different API), `ImageTranscriptionProvider` uses the same `ChatOpenAI` LLM as `ChatCompletionProvider`. The only difference is *how the message is constructed* (multimodal `HumanMessage` with vision content blocks vs plain text).

  Under the spec's proposed design, the factory cannot attach `TokenTrackingCallback` via the existing `ChatCompletionProvider` path because the provider is a separate type. This means vision tokens (which are billed per-token and can be significant) would bypass token tracking and quota enforcement entirely.

  A cleaner approach: `OpenAiImageTranscriptionProvider` **extends `ChatCompletionProvider`** (not a parallel abstract class). It implements `get_llm()` to return a `ChatOpenAI` (like `OpenAiChatProvider`), and adds a `transcribe_image(base64_image, mime_type) -> str` wrapper that internally calls `self.get_llm()`, constructs the multimodal `HumanMessage` (with prompt, data URI, and `detail` from config), invokes it, and returns `response.content`.

  The factory then:
  1. Detects it as a `ChatCompletionProvider` (existing `isinstance` check)
  2. Calls `provider.get_llm()`, attaches `TokenTrackingCallback` — **reusing existing logic**
  3. For `ImageTranscriptionProvider` subtype specifically, returns the **provider** (not the raw LLM), so the caller can use `provider.transcribe_image()`

  The processor calls `provider.transcribe_image(base64_image, mime_type)` — clean API, no vision internals exposed.

  This gives:
  - **Token tracking works automatically** via the existing `ChatCompletionProvider` factory path — no new branch, no constructor injection
  - **Encapsulation preserved** — `ImageVisionProcessor` calls `transcribe_image()`, knows nothing about multimodal messages, prompts, or `detail`
  - **`detail` stays in the provider** — read from `self.config.detail`, not leaked to the processor
  - **Consistent hierarchy** — the provider IS a `ChatCompletionProvider`, just with a domain-specific wrapper method on top
- **Status:** READY
- **Required Actions:** Revise the spec's provider architecture: `OpenAiImageTranscriptionProvider` should extend `ChatCompletionProvider` (via `OpenAiChatProvider` or directly), implementing `get_llm()` to return a `ChatOpenAI`, and adding a `transcribe_image(base64_image, mime_type) -> str` method that wraps the LLM invocation with vision-specific logic. The abstract `ImageTranscriptionProvider` base class in `model_providers/image_transcription.py` should extend `ChatCompletionProvider` (not `BaseModelProvider`) and declare `transcribe_image` as an abstract method. In `create_model_provider`, the existing `ChatCompletionProvider` isinstance check will match; add a sub-check for `ImageTranscriptionProvider` to return the provider object instead of the raw LLM. Additionally, add an `"image_transcription"` entry to the `token_menu` in `global_configurations` with appropriate pricing.

---

### ITS-10: Incomplete default propagation and migration strategy

- **Priority:** MEDIUM
- **ID:** ITS-10
- **Title:** Incomplete default propagation and migration strategy
- **Detailed Description:**  
  The spec states that `image_transcription` is "added as a new per-bot tier in `LLMConfigurations`" with "defaults matching the `low` tier (`OpenAiChatProvider` with `gpt-5-mini`)." While the intent is clear, the spec does not address the full set of changes required for this tier to actually work at runtime — especially for existing bots in production.

  Examining the precedent set by the `image_moderation` tier addition, the following were required:

  1. **Migration script** (`scripts/migrate_image_moderation.py`): Iterates all existing bot configurations in MongoDB and adds the new tier with default values. Without this, `resolve_model_config(bot_id, "image_transcription")` will raise `ValueError("Tier 'image_transcription' not found...")` for every existing bot.

  2. **`DefaultConfigurations` class** (`config_models.py`): Needs a new class-level default for the image transcription provider name (e.g., `model_provider_name_image_transcription = "openAiImageTranscription"`). Note: the default `provider_name` **must be** `"openAiImageTranscription"` (the new module), not `"openAi"` (the `low` tier's module). The spec says "defaults matching the `low` tier" referring to model/settings, but the dynamic module loading (`importlib.import_module(f"model_providers.{config.provider_name}")`) requires the correct module name. Using `"openAi"` would load `OpenAiChatProvider`, which is a `ChatCompletionProvider` — not an `ImageTranscriptionProvider` — causing the factory's isinstance check to route to the wrong branch.

  3. **`get_bot_defaults` endpoint** (`routers/bot_management.py:375-422`): Constructs the default `LLMConfigurations` object used when creating new bots via PATCH. It currently builds `high`, `low`, and `image_moderation` entries explicitly. The new `image_transcription` entry must be added here with `ImageTranscriptionProviderConfig`.

  4. **Pydantic model default**: The `LLMConfigurations.image_transcription` field needs either a `default_factory` or must remain required (`...`). If required, all code paths that construct `LLMConfigurations` or validate full `BotConfiguration` (including `save_bot_configuration` PUT endpoint at `bot_management.py:591`) will fail for configs missing the field. Using `default_factory` is safer but requires constructing a complete `ImageTranscriptionProviderConfig` with all required nested fields.

  None of these are mentioned in the spec. They follow an established pattern (the `image_moderation` addition), so an experienced implementer could infer them, but they represent non-trivial deployment steps that should be documented.
- **Status:** READY
- **Required Actions:** Add a "Deployment Checklist" section to the spec listing the four required supporting changes:
  1. **Migration script** (`scripts/migrate_image_transcription.py`): iterate all existing bot configs in MongoDB and add `image_transcription` tier with defaults to `config_data.configurations.llm_configs` where missing — following the `migrate_image_moderation.py` pattern.
  2. **`DefaultConfigurations`** (`config_models.py`): add `model_provider_name_image_transcription = "openAiImageTranscription"` (not `"openAi"` — must match the new provider module name).
  3. **`get_bot_defaults`** (`routers/bot_management.py`): add the `image_transcription` entry to the `LLMConfigurations` construction using `ImageTranscriptionProviderConfig` with values from `DefaultConfigurations`.
  4. **Pydantic `default_factory`** (`config_models.py`): define `LLMConfigurations.image_transcription` with a `default_factory` that builds a complete `ImageTranscriptionProviderConfig` (provider_name, model, settings) so validation doesn't fail for configs missing the field.

---

### ITS-11: `detail` Literal excludes `"original"` value from OpenAI spec

- **Priority:** LOW
- **ID:** ITS-11
- **Title:** `detail` Literal excludes `"original"` value from OpenAI spec
- **Detailed Description:**  
  The spec defines `detail: Literal["low", "high", "auto"] = "auto"` on `ImageTranscriptionProviderConfig`. However, the [OpenAI Vision docs](https://developers.openai.com/api/docs/guides/images-vision?format=base64-encoded) list four valid values: `"low"`, `"high"`, `"original"`, and `"auto"`.

  The `"original"` detail level is described as: *"Large, dense, spatially sensitive, or computer-use images. Available on gpt-5.4 and future models."* It allows up to 10,000 patches with a 6000-pixel maximum dimension — significantly higher fidelity than `"high"` (2,500 patches, 2048px).

  While the default model (`gpt-5-mini`) does not support `"original"`, the spec explicitly states that "individual bots may override to any compatible chat model (e.g. `gpt-5`) through their config." If a bot is configured with `gpt-5.4` (or a future model), the `Literal` type would prevent using `"original"` without a code change.

  Including `"original"` in the Literal now is a zero-cost future-proofing measure: `detail: Literal["low", "high", "original", "auto"] = "auto"`.
- **Status:** READY
- **Required Actions:** Update the `ImageTranscriptionProviderConfig.detail` field type from `Literal["low", "high", "auto"]` to `Literal["low", "high", "original", "auto"]`. Default remains `"auto"`.

---
