# Audio Transcript Support Specification Review
## Review ID: `05_ag_opus_4_6_thinking_strictMode`

## Summary of Findings

| Priority | ID | Title | Link | Status |
| :--- | :--- | :--- | :--- | :--- |
| High | `ATS-05-01` | Soniox SDK API Mismatch: `transcribe()` vs `create()` and Missing `CreateTranscriptionConfig` | [Details](#ats-05-01-soniox-sdk-api-mismatch-transcribe-vs-create-and-missing-createtranscriptionconfig) | READY |
| High | `ATS-05-02` | `AsyncSonioxClient` Lifecycle Management Not Addressed | [Details](#ats-05-02-asyncsonioxclient-lifecycle-management-not-addressed) | READY |
| High | `ATS-05-03` | `format_processing_result` Prefix Injection Breaks Existing Image Pipeline Output | [Details](#ats-05-03-format_processing_result-prefix-injection-breaks-existing-image-pipeline-output) | READY |
| Medium | `ATS-05-04` | `temperature` Field in `AudioTranscriptionProviderSettings` Is Unused by Soniox API | [Details](#ats-05-04-temperature-field-in-audiotranscriptionprovidersettings-is-unused-by-soniox-api) | READY |
| Medium | `ATS-05-05` | Token Tracker Closure Signature Mismatch with `TokenConsumptionService.record_event` | [Details](#ats-05-05-token-tracker-closure-signature-mismatch-with-tokenconsumptionservicerecord_event) | READY |
| Medium | `ATS-05-06` | Incorrect `token_menu` Migration Pricing Values | [Details](#ats-05-06-incorrect-token_menu-migration-pricing-values) | READY |
| Low | `ATS-05-07` | Spec Omits `audio/mpeg` Supported Format Mismatch with Soniox Docs | [Details](#ats-05-07-spec-omits-audiompeg-supported-format-mismatch-with-soniox-docs) | READY |

---

## Detailed Review Items

### `ATS-05-01`: Soniox SDK API Mismatch: `transcribe()` vs `create()` and Missing `CreateTranscriptionConfig`
- **Priority**: High
- **ID**: `ATS-05-01`
- **Title**: Soniox SDK API Mismatch: `transcribe()` vs `create()` and Missing `CreateTranscriptionConfig`
- **Detailed Description**:
  The spec's code snippet (lines 128–145) shows the following API call:
  ```python
  transcription = await client.stt.transcribe(
      model=self.config.provider_config.model,
      file=audio_path
  )
  ```
  However, the official Soniox Python SDK examples (see [soniox_sdk_async.py on GitHub](https://github.com/soniox/soniox_examples/blob/master/speech_to_text/python_sdk/soniox_sdk_async.py)) reveal two distinct SDK calling patterns:

  1. **Convenience method**: `client.stt.transcribe(model=..., file=...)` — This is a "convenience" wrapper documented in the [Python SDK quickstart](https://soniox.com/docs/stt/SDKs/python-SDK/async-transcription#quickstart). It accepts `model` and `file` directly as parameters, handles file upload internally, and returns a transcription object. **The spec correctly uses this method**, but there is an important subtlety: when using `transcribe()`, the file upload is handled implicitly by the SDK.

  2. **Explicit 3-step method**: The official GitHub example uses `client.stt.create(config=config, file_id=file.id)` (NOT `transcribe()`), where a `CreateTranscriptionConfig` object is used and the file is uploaded separately via `client.files.upload()`.

  The spec text at line 29 states the flow "must precisely be" a "3-step async pattern" using `transcribe()` → `wait()` → `get_transcript()`. This is internally contradictory because `transcribe()` is itself the convenience wrapper that combines file upload + job creation into one call — it IS the simplified alternative to the explicit 3-step pattern of `files.upload()` → `stt.create()` → `stt.wait()`.

  The critical risk here is that the `transcribe()` convenience method may implicitly wait for completion (the spec explicitly warns against the `wait=True` shortcut at line 29 to avoid blocking the event loop). The spec must clarify whether:
  - **(a)** To use the `transcribe()` convenience method (which may or may not wait internally), or
  - **(b)** To use the explicit `files.upload()` → `stt.create(config)` → `stt.wait()` → `stt.get_transcript()` → `stt.destroy()` pattern for full async control.

  If option (a), the spec should verify that `AsyncSonioxClient.stt.transcribe()` does NOT synchronously poll. If option (b), the spec's code snippet must be rewritten entirely to use `create()` with a `CreateTranscriptionConfig` and explicit file upload.
- **Status**: READY
- **Required Actions**: Rewrite the spec's code snippet to abandon the `transcribe()` convenience wrapper. Instruct the developer to explicitly use `client.files.upload()`, instantiate a `CreateTranscriptionConfig` object (passing the `model` property there), and then call `client.stt.create(config=..., file_id=...)`. Finally, ensure the `finally` block deletes both the file and the transcription job to avoid quota leaks.
---

### `ATS-05-02`: `AsyncSonioxClient` Lifecycle Management Not Addressed
- **Priority**: High
- **ID**: `ATS-05-02`
- **Title**: `AsyncSonioxClient` Lifecycle Management Not Addressed
- **Detailed Description**:
  The spec's code snippet creates an `AsyncSonioxClient` per transcription call:
  ```python
  client = AsyncSonioxClient(api_key=self._resolve_api_key())
  ```
  The spec does not address the lifecycle management of this client. Async HTTP clients (which `AsyncSonioxClient` wraps) typically maintain connection pools and must be properly closed via `await client.close()` or used as async context managers (`async with AsyncSonioxClient(...) as client:`). Failing to close the client after each transcription call will leak HTTP connections, which will compound over time as multiple audio messages are processed concurrently by the 2-worker pool.

  The `try/finally` block in the spec snippet only calls `await client.stt.destroy(transcription.id)` but never closes the client itself. This creates a resource leak. The spec should either:
  1. Use `async with AsyncSonioxClient(...) as client:` pattern to guarantee cleanup, or
  2. Explicitly add `await client.close()` in the outer `finally` block, or
  3. Create the client once at provider initialization and reuse it across calls (requires verifying thread safety of the async client)
- **Status**: READY
- **Required Actions**: Instruct the developer to implement a two-phase initialization pattern. The `AsyncSonioxClient` (for audio transcription) and the `AsyncOpenAI` client (for the existing image moderation provider) must be instantiated once per provider instance. This instantiation should happen inside an `async def initialize(self):` method (or similar) called immediately after the provider's creation inside the `services.model_factory.create_model_provider()` factory method. The spec must explicitly note that this is a known, intentionally leaky solution regarding client teardown, but it is acceptable because a future provider caching layer will be introduced in the factory, capping the maximum number of active HTTP clients to the number of active bot combinations.

---

### `ATS-05-03`: `format_processing_result` Prefix Injection Breaks Existing Image Pipeline Output
- **Priority**: High
- **ID**: `ATS-05-03`
- **Title**: `format_processing_result` Prefix Injection Breaks Existing Image Pipeline Output
- **Detailed Description**:
  The spec (line 40) instructs refactoring `format_processing_result` to accept a `mime_type` parameter and dynamically prepend `"{MediaType} Transcription: "` to content when `unprocessable_media` is `False` and `failed_reason` is empty.

  However, this refactoring has a significant side-effect: the `format_processing_result` function is the **single centralized formatter** used by **ALL** media processors (as documented in its own docstring: "This is the SINGLE SOURCE OF TRUTH for output formatting. ALL processors...must route their output through this function"). This includes:

  1. **`ImageVisionProcessor`** — currently returns raw transcription text like `"A photo of a dog sitting on a park bench"`. After this change, successful image transcription results would be prefixed with `"Image Transcription: "`, changing the output format from `[A photo of a dog...]` to `[Image Transcription: A photo of a dog...]`.

  2. **`StubSleepProcessor` subclasses** (`VideoDescriptionProcessor`, `DocumentProcessor`) — these would get `"Video Transcription: "`, `"Application Transcription: "` (from `application/pdf`) prefixes, which are semantically incorrect (documents aren't "transcribed" in the audio sense; PDFs would get "Application Transcription" from the MIME type prefix `application/`).

  3. **Error/corrupt processors** — `CorruptMediaProcessor` and `UnsupportedMediaProcessor` would also receive prefixes like `"Media_corrupt_image Transcription: "` from their synthetic MIME types like `media_corrupt_image`, which is nonsensical.

  The spec claims (line 39) "Do not add explicit brackets [...] as formatting is **centralized** inside `format_processing_result()`...introduced during image transcription." But the spec MUST clarify that this prefix injection should only apply to specific MIME type classes (audio), OR provide a mechanism for processors to opt-in/opt-out of the prefix. As written, the refactoring would globally break the output format for all existing processors.
- **Status**: READY
- **Required Actions**: Add an explicit clarification note to the specification's output formatting section. The note must explicitly state: "The injection of the `{MediaType} Transcription:` prefix into `format_processing_result()` is an intentionally global change. It is designed to apply to all successful media processors (e.g., `ImageVisionProcessor` will now output `Image Transcription: ...`). Processors handling corrupt or unsupported media are safely excluded from this prefix because their `unprocessable_media` flag is set to `True`." This prevents future reviewers from incorrectly flagging the global scope of this formatting update as a regression.

---

### `ATS-05-04`: `temperature` Field in `AudioTranscriptionProviderSettings` Is Unused by Soniox API
- **Priority**: Medium
- **ID**: `ATS-05-04`
- **Title**: `temperature` Field in `AudioTranscriptionProviderSettings` Is Unused by Soniox API
- **Detailed Description**:
  The spec (line 12) instructs creating `AudioTranscriptionProviderSettings` with a `temperature: float = 0.0` field, and `DefaultConfigurations` (line 175) exposes it via `DEFAULT_AUDIO_TRANSCRIPTION_TEMPERATURE`. However, the Soniox async transcription API does not accept a `temperature` parameter. The API accepts `model`, `file`/`file_id`/`audio_url`, and a `CreateTranscriptionConfig`, none of which include temperature.

  The spec's own code snippet (lines 128–131) confirms this: `transcribe()` is only called with `model=` and `file=` — no temperature is passed. This means the `temperature` field is configured, stored in MongoDB, exposed in the UI, but never actually used by the provider implementation. This creates dead configuration surface area that:
  - Misleads operators into thinking temperature affects audio transcription behavior
  - Adds unnecessary complexity to the migration script and configuration schema
  - Deviates from the principle of minimal, functional configuration

  If temperature is included purely for forward-compatibility with hypothetical future models, this should be explicitly documented. Otherwise, it should be removed from `AudioTranscriptionProviderSettings`.
- **Status**: READY
- **Required Actions**: Keep the `temperature` field in the configuration schemas to ensure future-proofing (e.g., if switching to another provider that utilizes temperature). However, update the specification to explicitly document that this value is currently a dummy variable specifically ignored by the Soniox provider implementation.

---

### `ATS-05-05`: Token Tracker Closure Signature Mismatch with `TokenConsumptionService.record_event`
- **Priority**: Medium
- **ID**: `ATS-05-05`
- **Title**: Token Tracker Closure Signature Mismatch with `TokenConsumptionService.record_event`
- **Detailed Description**:
  The spec's `model_factory.py` snippet (lines 156–165) defines the token tracker closure as:
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
  ```
  Examining `TokenConsumptionService.record_event()` signature:
  ```python
  async def record_event(self, user_id, bot_id, feature_name, input_tokens, output_tokens, config_tier, cached_input_tokens=0)
  ```
  The parameter ordering in the closure's `await token_service.record_event(...)` call uses keyword arguments, so the positional mismatch is not a runtime error. However, the closure **hardcodes** `feature_name="audio_transcription"` rather than using the `feature_name` variable from the enclosing `create_model_provider` function scope. The `create_model_provider` function already receives `feature_name` as a parameter. If the calling code ever passes a different `feature_name` (e.g., `"media_processing"`), the closure would silently ignore it and always record as `"audio_transcription"`. This hardcoding contradicts the existing LangChain callback pattern (line 62 of `model_factory.py`) which correctly passes through the `feature_name` parameter.

  The spec should use `feature_name=feature_name` to maintain consistency with the existing tracking pattern.
- **Status**: READY
- **Required Actions**: Update the specification's token tracker code snippet to dynamically utilize the enclosing function's variable (i.e., `feature_name=feature_name`), matching the exact behavior of the existing LangChain callback pattern and preserving feature decoupling.

---

### `ATS-05-06`: Incorrect `token_menu` Migration Pricing Values
- **Priority**: Medium
- **ID**: `ATS-05-06`
- **Title**: Incorrect `token_menu` Migration Pricing Values
- **Detailed Description**:
  The `QuotaService.calculate_cost()` method (called from within `TokenConsumptionService.record_event()`) uses the `config_tier` to determine pricing. These prices are dynamically defined in `global_configurations.token_menu`, which is a MongoDB document. 

  The spec mentions pricing values of `{input_tokens: 2, cached_input_tokens: 2, output_tokens: 4}` for the new tier. However, these proposed multiplier values are incorrect for audio transcription.
- **Status**: READY
- **Required Actions**: Update the Configuration section in the specification to replace the incorrect pricing numbers. The exact pricing JSON to specify is: `{"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}`.

---

### `ATS-05-07`: Spec Omits `audio/mpeg` Supported Format Mismatch with Soniox Docs
- **Priority**: Low
- **ID**: `ATS-05-07`
- **Title**: Spec Omits `audio/mpeg` Supported Format Mismatch with Soniox Docs
- **Detailed Description**:
  The `DEFAULT_POOL_DEFINITIONS` in `media_processing_service.py` (line 16) routes `audio/ogg` and `audio/mpeg` to `AudioTranscriptionProcessor`. The Soniox docs list supported formats as: `aac, aiff, amr, asf, flac, mp3, ogg, wav, webm, m4a, mp4`.

  The MIME type `audio/mpeg` corresponds to MP3 files, which Soniox supports. The MIME type `audio/ogg` corresponds to OGG Vorbis/Opus files, also supported. So the existing pool definitions are compatible with Soniox.

  However, the spec does not discuss or acknowledge this format mapping at all. While the current pool definitions happen to work, the spec should explicitly note:
  1. That the existing MIME type routing is compatible with Soniox's supported formats.
  2. Whether additional audio MIME types should be considered (e.g., `audio/wav`, `audio/flac`, `audio/webm` are all supported by Soniox but not routed to `AudioTranscriptionProcessor`). This may be intentional (WhatsApp only sends `audio/ogg` and `audio/mpeg`), but it should be explicitly stated.
- **Status**: READY
- **Required Actions**: Update the specification to instruct the developer to expand the `DEFAULT_POOL_DEFINITIONS` dictionary in `media_processing_service.py`. The update should mandate routing additional Soniox-supported audio MIME types (such as `audio/wav`, `audio/webm`, `audio/mp4`, `audio/aac`, `audio/flac`, and `audio/amr`) to the `AudioTranscriptionProcessor` to ensure the bot can seamlessly process a wider variety of user audio uploads.

---
