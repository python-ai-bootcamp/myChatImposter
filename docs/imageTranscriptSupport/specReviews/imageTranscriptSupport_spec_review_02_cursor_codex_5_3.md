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
| MEDIUM | ITS-09 | Token tracking and quota enforcement gap for image transcription | [Details](#its-09-token-tracking-and-quota-enforcement-gap-for-image-transcription) | PENDING |
| MEDIUM | ITS-10 | Incomplete default propagation and migration strategy | [Details](#its-10-incomplete-default-propagation-and-migration-strategy) | PENDING |
| LOW | ITS-11 | `detail` Literal excludes `"original"` value from OpenAI spec | [Details](#its-11-detail-literal-excludes-original-value-from-openai-spec) | PENDING |

---

## Detailed Findings

### ITS-09: Token tracking and quota enforcement gap for image transcription

- **Priority:** MEDIUM
- **ID:** ITS-09
- **Title:** Token tracking and quota enforcement gap for image transcription
- **Detailed Description:**  
  The spec defines `OpenAiImageTranscriptionProvider` as a self-contained provider that "internally builds a `ChatOpenAI` LLM, constructs a multimodal `HumanMessage`... invokes it, and returns `response.content`." This mirrors the `ImageModerationProvider` pattern where the provider owns its API client internally.

  However, the current `create_model_provider` factory (`services/model_factory.py`) only attaches `TokenTrackingCallback` in the `ChatCompletionProvider` branch — where it extracts the LLM via `provider.get_llm()`, attaches the callback, and returns the raw LLM. For `ImageModerationProvider` (and now `ImageTranscriptionProvider`), the factory returns the provider object directly, with no token tracking attached.

  For image moderation this is a non-issue — the OpenAI moderation endpoint is free and uses a specialized model (`omni-moderation-latest`). But image transcription uses a **standard chat completion model** (`gpt-5-mini` by default) with **vision input**, which is billed per-token. Vision inputs are particularly token-heavy: the OpenAI docs describe patch-based tokenization where even a modest image at `"auto"` detail can consume hundreds to thousands of tokens.

  Because the LLM is created and invoked inside the provider:
  1. Token consumption is **not recorded** to the `token_consumption` MongoDB collection
  2. Token cost is **not counted** against the user's `llm_quota` (via `QuotaService`)
  3. The `token_menu` in `global_configurations` has no `"image_transcription"` pricing entry

  This means image transcription usage is invisible to the billing/quota system. For bots processing many images, this could represent significant unbilled spend and quota leakage.
- **Status:** PENDING
- **Required Actions:**

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
- **Status:** PENDING
- **Required Actions:**

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
- **Status:** PENDING
- **Required Actions:**

---
