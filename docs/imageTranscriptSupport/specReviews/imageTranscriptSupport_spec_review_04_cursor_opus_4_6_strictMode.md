# Spec Review: imageTranscriptSupport

**Review ID:** 04_cursor_opus_4_6_strictMode  
**Spec File:** `/docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`  
**Date:** 2026-03-15

## Overall Assessment

The spec has matured significantly through three prior review cycles. The core feature design — provider architecture, config hierarchy, processing flow, output format, and deployment checklist — is well-defined and aligns closely with established codebase patterns. The incorporation of findings ITS-01 through ITS-14 is thorough.

This review focuses on **implementation-blocking gaps** that remain, primarily in the interaction between `create_model_provider`, token tracking, and the dynamic provider loading utility. Seven items were identified: two HIGH priority (token tracking will silently fail; provider class resolution may return the wrong class), three MEDIUM (path inconsistencies, missing pricing values, unspecified error handling), and two LOW (detail/model validation, feature_name granularity).

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| HIGH | ITS-15 | Token tracking silently fails — `get_llm()` creates fresh instances, factory-attached callbacks are lost | [Details](#its-15-token-tracking-silently-fails--get_llm-creates-fresh-instances-factory-attached-callbacks-are-lost) | READY |
| HIGH | ITS-16 | `find_provider_class` may return `OpenAiChatProvider` instead of `OpenAiImageTranscriptionProvider` | [Details](#its-16-find_provider_class-may-return-openaichatprovider-instead-of-openaiimagetranscriptionprovider) | READY |
| MEDIUM | ITS-17 | Migration/initialization script path references are inconsistent with actual file locations | [Details](#its-17-migrationinitialization-script-path-references-are-inconsistent-with-actual-file-locations) | READY |
| MEDIUM | ITS-18 | Token menu `image_transcription` pricing values not specified | [Details](#its-18-token-menu-image_transcription-pricing-values-not-specified) | READY |
| MEDIUM | ITS-19 | Error handling strategy for `transcribe_image` failures unspecified | [Details](#its-19-error-handling-strategy-for-transcribe_image-failures-unspecified) | READY |
| LOW | ITS-20 | No validation or warning for `"original"` detail with incompatible models | [Details](#its-20-no-validation-or-warning-for-original-detail-with-incompatible-models) | READY |
| LOW | ITS-21 | `feature_name` parameter value for transcription token tracking unspecified | [Details](#its-21-feature_name-parameter-value-for-transcription-token-tracking-unspecified) | READY |

---

## Detailed Findings

### ITS-15: Token tracking silently fails — `get_llm()` creates fresh instances, factory-attached callbacks are lost

- **Priority:** HIGH
- **ID:** ITS-15
- **Title:** Token tracking silently fails — `get_llm()` creates fresh instances, factory-attached callbacks are lost
- **Detailed Description:**  
  The spec's Technical Details §1 states:

  > `create_model_provider` in `services/model_factory.py` keeps the existing `ChatCompletionProvider` tracking path: resolve provider → call `get_llm()` → attach `TokenTrackingCallback`. For the `ImageTranscriptionProvider` subtype specifically, the factory returns the provider object (not raw LLM) so callers can `await provider.transcribe_image(...)`.

  The intended flow is:
  1. Factory creates the provider
  2. Factory calls `provider.get_llm()` — gets a `ChatOpenAI` instance
  3. Factory attaches `TokenTrackingCallback` to that instance's `callbacks` list
  4. Factory returns the **provider** (not the LLM)
  5. Caller calls `provider.transcribe_image(base64_image, mime_type)`

  The gap is in step 5. The `transcribe_image` method needs to invoke the LLM. Its natural implementation would be:

  ```python
  async def transcribe_image(self, base64_image: str, mime_type: str) -> str:
      llm = self.get_llm()  # Creates a NEW ChatOpenAI — no callbacks!
      message = HumanMessage(content=[...])
      response = await llm.ainvoke([message])
      return response.content
  ```

  `OpenAiChatProvider.get_llm()` (`model_providers/openAi.py:41-56`) creates a **new** `ChatOpenAI` instance on every call — there is no caching. The `TokenTrackingCallback` attached in step 3 lives on the LLM instance from step 2, which is never stored on the provider and is never used again. The provider's `transcribe_image` calls `get_llm()` again (step 5), getting a fresh instance without any callbacks.

  **Result:** Vision tokens consumed during image transcription are **never tracked**. `TokenConsumptionService.record_event` is never called. `QuotaService.calculate_cost` never runs. Users are not billed for potentially expensive vision API usage.

  This is not hypothetical — it follows directly from the existing `get_llm()` implementation pattern and the spec's factory design.
- **Status:** READY
- **Required Actions:**
  Modify `OpenAiChatProvider.get_llm()` to construct and cache the `ChatOpenAI` instance on the provider object (`self._llm = ChatOpenAI(...)`) the first time it is called, and return the cached instance on subsequent calls. This ensures the instance that receives the `TokenTrackingCallback` in the factory is the exact same instance used by `transcribe_image`.

---

### ITS-16: `find_provider_class` may return `OpenAiChatProvider` instead of `OpenAiImageTranscriptionProvider`

- **Priority:** HIGH
- **ID:** ITS-16
- **Title:** `find_provider_class` may return `OpenAiChatProvider` instead of `OpenAiImageTranscriptionProvider`
- **Detailed Description:**  
  The spec's Technical Details §1 states:

  > `OpenAiImageTranscriptionProvider` (in `model_providers/openAiImageTranscription.py`) extends this class (optionally via `OpenAiChatProvider`)

  The "optionally via `OpenAiChatProvider`" guidance suggests the implementer may write:

  ```python
  # model_providers/openAiImageTranscription.py
  from model_providers.openAi import OpenAiChatProvider
  from model_providers.image_transcription import ImageTranscriptionProvider

  class OpenAiImageTranscriptionProvider(OpenAiChatProvider, ImageTranscriptionProvider):
      async def transcribe_image(self, base64_image, mime_type) -> str:
          ...
  ```

  The factory in `services/model_factory.py:37-38` resolves the provider class via:

  ```python
  provider_module = importlib.import_module(f"model_providers.{config.provider_name}")
  ProviderClass = find_provider_class(provider_module, BaseModelProvider)
  ```

  `find_provider_class` (`utils/provider_utils.py:15-17`) uses `inspect.getmembers(module)` which returns **all** attributes of the module object — including imported names — sorted alphabetically by name. It returns the **first** non-abstract subclass of `BaseModelProvider` it encounters.

  If `OpenAiChatProvider` is imported into the `openAiImageTranscription` module, both classes are visible to `inspect.getmembers`:
  - `OpenAiChatProvider` — concrete (implements `get_llm()`), subclass of `BaseModelProvider`, not abstract
  - `OpenAiImageTranscriptionProvider` — concrete, subclass of `BaseModelProvider`, not abstract

  Alphabetically: `"OpenAiChatProvider"` (C=67) sorts before `"OpenAiImageTranscriptionProvider"` (I=73). The function returns `OpenAiChatProvider` — the **wrong class**.

  The provider instance would be an `OpenAiChatProvider` instead of `OpenAiImageTranscriptionProvider`. It would lack the `transcribe_image` method entirely, and the `isinstance(provider, ImageTranscriptionProvider)` check in the factory would fail, causing the factory to return a raw `BaseChatModel` — completely wrong behavior for image transcription.

  Note: This bug does NOT affect the existing `openAiModeration.py` module because it only imports `ImageModerationProvider` (which has `@abstractmethod moderate_image` and is therefore filtered out by `inspect.isabstract`). The issue is specific to importing a **concrete** parent class.
- **Status:** READY
- **Required Actions:**
  Modify `utils/provider_utils.py`'s `find_provider_class` to add an `obj.__module__ == module.__name__` filter to the existing `inspect.getmembers` loop. This excludes imported classes (e.g., `OpenAiChatProvider` imported into `openAiImageTranscription.py`) because their `__module__` attribute points to their defining module, not the importing module. This fix is backward-compatible — no changes required to existing provider modules (`openAi.py`, `openAiModeration.py`).

---

### ITS-17: Migration/initialization script path references are inconsistent with actual file locations

- **Priority:** MEDIUM
- **ID:** ITS-17
- **Title:** Migration/initialization script path references are inconsistent with actual file locations
- **Detailed Description:**  
  The spec's Deployment Checklist and Project Files section reference:
  - `scripts/initialize_quota_and_bots.py` (Deployment Checklist item 5)
  - `scripts/migrate_image_transcription.py` (Deployment Checklist item 1)
  - `scripts/migrate_token_menu_image_transcription.py` (Deployment Checklist item 5)

  However, examining the actual project file structure:
  - `initialize_quota_and_bots.py` lives at `scripts/migrations/initialize_quota_and_bots.py` (inside a `migrations/` subdirectory), not `scripts/initialize_quota_and_bots.py`.
  - The existing `migrate_image_moderation.py` lives at `scripts/migrate_image_moderation.py` (root `scripts/`), NOT inside `migrations/`.

  The project has two different locations for migration scripts: `scripts/` (root) and `scripts/migrations/`. The spec doesn't clarify which subdirectory the new scripts should reside in. An implementer following the `migrate_image_moderation.py` pattern would place new files in `scripts/`, but following `initialize_quota_and_bots.py` would place them in `scripts/migrations/`.

  Additionally, the path `scripts/initialize_quota_and_bots.py` in the spec would cause an implementer to look for a file that doesn't exist at that location.
- **Status:** READY
- **Required Actions:**
  Adopt Option 2: Update the spec to standardize all migration scripts under the `scripts/migrations/` directory. Specifically, change references to create `scripts/migrations/migrate_image_transcription.py` and `scripts/migrations/migrate_token_menu_image_transcription.py`, and correct the path reference to update `scripts/migrations/initialize_quota_and_bots.py`.

---

### ITS-18: Token menu `image_transcription` pricing values not specified

- **Priority:** MEDIUM
- **ID:** ITS-18
- **Title:** Token menu `image_transcription` pricing values not specified
- **Detailed Description:**  
  The spec states (Requirements §Configuration):

  > `global_configurations.token_menu` is extended with an `"image_transcription"` pricing entry so vision usage is tracked and priced under the correct tier.

  And Deployment Checklist item 5:

  > Update `scripts/initialize_quota_and_bots.py` so new deployments are initialized with the `image_transcription` token menu tier. Create `scripts/migrate_token_menu_image_transcription.py` to patch existing staging and production environments.

  Neither section specifies the actual pricing values — `input_tokens`, `output_tokens`, and `cached_input_tokens` rates per 1M tokens — that the migration and initialization scripts must insert. The existing `token_menu` structure (from `scripts/migrations/initialize_quota_and_bots.py`) is:

  ```python
  token_menu = {
      "high": {
          "input_tokens": 1.25,
          "cached_input_tokens": 0.125,
          "output_tokens": 10
      },
      "low": {
          "input_tokens": 0.25,
          "cached_input_tokens": 0.025,
          "output_tokens": 2
      }
  }
  ```

  Vision tokens on OpenAI have different pricing than text-only tokens and vary by model and `detail` level. The `image_transcription` tier defaults to `gpt-5-mini`, which uses patch-based tokenization with a 1.62× multiplier. The implementer would need to determine the correct per-1M-token rates for vision usage and may set them incorrectly without guidance.

  The spec should either provide concrete values or explicitly state that the pricing matches the `low` tier rates (since the default model is the same, `gpt-5-mini`, and vision tokens are billed at the same per-token rate as text tokens — just more tokens are consumed per image).
- **Status:** READY
- **Required Actions:**
  Adopt Option 1: Update the spec to explicitly mandate that the `image_transcription` tier must be added as a completely distinct, independent entry in the `token_menu` global configuration (do not reuse the `low` tier). The specified pricing values for this new tier should match the default model rates: `input_tokens: 0.25`, `cached_input_tokens: 0.025`, and `output_tokens: 2.0`.
---

### ITS-19: Error handling strategy for `transcribe_image` failures unspecified

- **Priority:** MEDIUM
- **ID:** ITS-19
- **Title:** Error handling strategy for `transcribe_image` failures unspecified
- **Detailed Description:**  
  The spec defines the happy path (moderation → transcription → format output) and the flagged path (moderation flags → return placeholder). However, it does not address what happens when the LLM invocation inside `transcribe_image` fails — for example, due to an OpenAI API error, rate limiting (HTTP 429), network timeout, content policy rejection, or an invalid `detail`/model combination.

  There are two possible strategies, with different implications for the user experience and the `BaseMediaProcessor` error handling pipeline:

  **Strategy A — Let exceptions propagate (implicit):**  
  If `transcribe_image` raises an unhandled exception, `BaseMediaProcessor.process_job` catches it in the outer `except Exception` block (`base.py:72-74`), calls `_handle_unhandled_exception`, which sets `ProcessingResult(content="[Media processing failed]", failed_reason=error)`, archives to the `_failed` collection, and attempts best-effort delivery. The user sees `"[Media processing failed]"` in their chat.

  **Strategy B — Catch and return a descriptive `ProcessingResult` (explicit):**  
  `ImageVisionProcessor.process_media` wraps the `transcribe_image` call in a try/except and returns a specific `ProcessingResult` like `ProcessingResult(content="[Image transcription failed]", failed_reason=str(e))`. This provides a more descriptive message and allows the processor to decide whether specific errors (e.g., content policy) should be treated differently.

  The existing `moderate_image` in `ImageVisionProcessor` follows Strategy A (no error handling — exceptions propagate). For consistency, Strategy A would be the natural choice. But the spec should confirm this, especially since transcription is a higher-latency operation (2-5s vs <1s for moderation) with different failure modes (e.g., the model might refuse to describe certain non-flagged-but-borderline images).
- **Status:** READY
- **Required Actions:**
  Adopt Option 1: Update the spec to explicitly state that no custom error handling (`try/except`) should be added around `transcribe_image` within `ImageVisionProcessor`. By design, all exceptions must propagate up to `BaseMediaProcessor.process_job()`, which handles failures gracefully by logging the error, archiving the job to the failed collection, and returning the standard `[Media processing failed]` placeholder to the user. This maintains consistency with the existing `moderate_image` implementation.
---

### ITS-20: No validation or warning for `"original"` detail with incompatible models

- **Priority:** LOW
- **ID:** ITS-20
- **Title:** No validation or warning for `"original"` detail with incompatible models
- **Detailed Description:**  
  The spec includes `"original"` in the `detail` Literal type (`Literal["low", "high", "original", "auto"]`), following ITS-11's recommendation for future-proofing. However, according to the [OpenAI Vision docs](https://developers.openai.com/api/docs/guides/images-vision?format=base64-encoded):

  > `"original"`: Large, dense, spatially sensitive, or computer-use images. Available on `gpt-5.4` and future models.

  The default model for the `image_transcription` tier is `gpt-5-mini`, which supports only `"low"`, `"high"`, and `"auto"`. If a user configures `detail: "original"` while keeping the default model, the OpenAI API call will likely fail with an unsupported parameter error.

  The spec does not address:
  - Whether `resolve_model_config` or the provider should validate the `detail`/`model` combination
  - Whether a warning should be logged if `"original"` is set with a model that doesn't support it
  - Whether the provider should silently fall back to `"auto"` for unsupported combinations

  This is low priority because: (a) the default is `"auto"`, (b) `"original"` requires explicit override by an admin user, and (c) the API error would propagate through the standard error handling path. But a validation note in the spec would prevent confusion.
- **Status:** READY
- **Required Actions:**
  Adopt Option 3: Update the spec to explicitly state that no validation should be added for the `"original"` detail level against the configured model. If a database administrator misconfigures the system by combining `"original"` with an unsupported model (like `gpt-5-mini`), the resulting OpenAI API validation error will safely propagate through the standard implicit error handling strategy confirmed in ITS-19.

---

### ITS-21: `feature_name` parameter value for transcription token tracking unspecified

- **Priority:** LOW
- **ID:** ITS-21
- **Title:** `feature_name` parameter value for transcription token tracking unspecified
- **Detailed Description:**  
  `create_model_provider` accepts a `feature_name` parameter which is passed to `TokenTrackingCallback` and ultimately recorded in the `token_consumption_events` collection as `feature_name`. This field enables per-feature billing reports and usage analytics.

  The current `ImageVisionProcessor` calls the factory as:
  ```python
  provider = await create_model_provider(bot_id, "media_processing", "image_moderation")
  ```

  For the `image_moderation` tier, no token tracking occurs because `ImageModerationProvider` follows a different factory branch (no `TokenTrackingCallback` attachment). So the `feature_name="media_processing"` is never recorded.

  For the new `image_transcription` tier, token tracking **will** occur (via the `ChatCompletionProvider` branch). The spec doesn't specify what `feature_name` value should be used when calling the factory for transcription. Options include:
  - `"media_processing"` — groups all media-related LLM usage together
  - `"image_transcription"` — enables finer-grained billing and usage analysis

  This affects the ability to distinguish image transcription costs from other media processing costs in billing reports and quota dashboards.
- **Status:** READY
- **Required Actions:**
  Adopt Option 2: Update the `ImageVisionProcessor` section of the spec to specify that the `feature_name` string passed to `create_model_provider` during image transcription must be exactly `"image_transcription"`. This explicit string ensures fine-grained token tracking and billing reports can distinguish transcription costs from other potential media processing tasks.

---
