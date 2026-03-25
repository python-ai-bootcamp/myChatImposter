# Spec Review: imageTranscriptSupport

**Review ID:** 01_cursor_opus_4_6  
**Spec File:** `/docs/imageTranscriptSupport/imageTranscriptSupport_specFile.md`  
**Date:** 2026-03-14

## Summary Table

| Priority | ID | Title | Link | Status |
|----------|----|-------|------|--------|
| HIGH | ITS-01 | Flagged image behavior undefined | [Details](#its-01-flagged-image-behavior-undefined) | READY |
| HIGH | ITS-02 | Config placement and runtime access pattern for `image_transcription_tier` undefined | [Details](#its-02-config-placement-and-runtime-access-pattern-for-image_transcription_tier-undefined) | SUPERSEDED |
| HIGH | ITS-03 | OpenAI parameter is `detail`, not `resize` | [Details](#its-03-openai-parameter-is-detail-not-resize) | READY |
| MEDIUM | ITS-04 | Transcription prompt / system instruction not specified | [Details](#its-04-transcription-prompt--system-instruction-not-specified) | READY |
| MEDIUM | ITS-05 | LangChain vision invocation pattern not detailed | [Details](#its-05-langchain-vision-invocation-pattern-not-detailed) | READY |
| MEDIUM | ITS-08 | Config type for `image_transcription` tier not specified | [Details](#its-08-config-type-for-image_transcription-tier-not-specified) | READY |
| LOW | ITS-07 | Caption handling not addressed | [Details](#its-07-caption-handling-not-addressed) | READY |

---

## Detailed Findings

### ITS-01: Flagged image behavior undefined

- **Priority:** HIGH
- **ID:** ITS-01
- **Title:** Flagged image behavior undefined
- **Detailed Description:**  
  The spec states: *"if moderation_result.flagged==false, it will also attempt to transcribe the image."* However, it does not specify what `ProcessingResult` should be returned when `moderation_result.flagged == true`. The current `ImageVisionProcessor` returns a generic stub message (`"[Transcripted image multimedia message...]"`) regardless of the moderation outcome. After this feature is implemented, there must be a clear definition of what happens on the flagged path:
  - Should a specific error/placeholder message be returned (e.g. `"[Image blocked by content moderation]"`)?
  - Should `ProcessingResult.failed_reason` be set (which triggers archival to the `_failed` collection via `BaseMediaProcessor._archive_to_failed`)?
  - Or should the message be silently dropped?

  Without this, the implementer must guess at the intended behavior for flagged images, which is a core branch in the processing logic.
- **Status:** READY
- **Required Actions:** Return a clean placeholder (no `failed_reason`, no failure archival) with a descriptive message that includes the flagged category names. The content will be: `"[Transcribed image multimedia message was flagged with following problematic tags: ('tag1', 'tag2', ...)]"` where the tags are the keys from `moderation_result.categories` whose value is `true`. Moderation flagging is treated as a normal processing outcome, not an error.

---

### ITS-02: Config placement and runtime access pattern for `image_transcription_tier` undefined

- **Priority:** HIGH
- **ID:** ITS-02
- **Title:** Config placement and runtime access pattern for `image_transcription_tier` undefined
- **Detailed Description:**  
  The spec says *"a new configuration will be added to configurations collection (image_transcription_tier) with a default value of `low`"* and *"The bot's configured model_configs[config_tier] is authoritative at runtime."*

  Several things are unspecified:

  1. **Where in the config hierarchy does `image_transcription_tier` live?** The existing bot config structure is `BotConfiguration → BotGeneralSettings` (containing `llm_configs: LLMConfigurations`). The spec doesn't say whether `image_transcription_tier` is a field on `BotGeneralSettings`, on `LLMConfigurations`, or elsewhere. Note: the spec references `model_configs[config_tier]` but the actual codebase field is `llm_configs`.

  2. **How does `ImageVisionProcessor` access this config at runtime?** The `process_media` method signature is `(self, file_path, mime_type, caption, bot_id) -> ProcessingResult`. It only receives `bot_id`, not the bot configuration. To resolve `image_transcription_tier`, the processor would need to query the database or call a resolver function (similar to how `resolve_model_config` works in `services/resolver.py`). This access pattern needs to be defined — either a new resolver like `resolve_image_transcription_tier(bot_id) -> ConfigTier`, or extending the existing `create_model_provider` to accept a meta-tier that resolves internally.

  3. **Default propagation:** The spec says default is `"low"`, but doesn't specify how existing bot configurations in MongoDB get this default. Should it be set at Pydantic model level? Should a migration populate it? New bots would get it from the default, but existing bots would have `None`/missing.
- **Status:** SUPERSEDED
- **Required Actions:** **Superseded by ITS-05.** The global config `image_transcription_tier` is dropped entirely. Instead, `image_transcription` becomes a proper per-bot tier in `LLMConfigurations` (alongside `high`, `low`, `image_moderation`), with defaults matching the `low` tier (`OpenAiChatProvider` with `gpt-5-mini`). This is resolved by a dedicated `ImageTranscriptionProvider` — see ITS-05 for full details.

---

### ITS-03: OpenAI parameter is `detail`, not `resize`

- **Priority:** HIGH
- **ID:** ITS-03
- **Title:** OpenAI parameter is `detail`, not `resize`
- **Detailed Description:**  
  The spec states: *"for now the provider will use the same OpenAiChatProvider settings with an additional 'resize' parameter as 'auto' (see openai docs about image text transcriptions)."*

  The OpenAI API does not have a `resize` parameter. The correct parameter is **`detail`**, which controls the fidelity level for image understanding. From the [OpenAI Vision docs](https://developers.openai.com/api/docs/guides/images-vision?format=base64-encoded):

  > *"The `detail` parameter tells the model what level of detail to use when processing and understanding the image (`low`, `high`, `original`, or `auto` to let the model decide)."*

  Valid values are: `"low"`, `"high"`, `"original"` (newer models), `"auto"`. The spec should be corrected to reference `detail` with value `"auto"`.

  Additionally, the spec refers to *"openai docs about image text transcriptions"* — the correct documentation topic is **"Images and vision"** (image analysis/understanding), not "image text transcriptions" (which is not a standard OpenAI concept).
- **Status:** READY
- **Required Actions:** Correct spec terminology: replace `resize` with `detail` and `"image text transcriptions"` with `"Images and vision"`. The `detail` parameter controls image tokenization fidelity (how many patches/tiles the image is broken into). The value defaults to `"auto"` via `ImageTranscriptionProviderConfig` and is overridable per-bot through config (see ITS-08).

---

### ITS-04: Transcription prompt / system instruction not specified

- **Priority:** MEDIUM
- **ID:** ITS-04
- **Title:** Transcription prompt / system instruction not specified
- **Detailed Description:**  
  The spec says the image will be processed *"in order to produce a textual representation describing the image content"* using the chat completion API. However, it doesn't specify:

  1. **What prompt to send alongside the image.** The quality, format, and verbosity of the transcription depend entirely on the text prompt. For example, *"Describe this image"* produces very different output from *"Provide a detailed description of the contents of this image including people, objects, text, and setting."*

  2. **Whether a system message should be included** to set the tone/style of the description (e.g., *"You are a concise image descriptor for a chat context. Describe images in 1-3 sentences."*).

  3. **Whether the prompt should be configurable** (stored in bot config or hardcoded).

  Since the transcription output goes directly into the bot's message queue and will be consumed by features like `AutomaticBotReply` (which feeds it to the bot's LLM), the format matters — overly verbose descriptions waste context tokens, while overly terse ones lose information.
- **Status:** READY
- **Required Actions:** Hardcode a fixed user-message prompt in the processor (no system message). The prompt will be: *"Describe the contents of this image concisely in 1-3 sentences, if there is text in the image add the text inside image to description as well"*

---

### ITS-05: LangChain vision invocation pattern not detailed

- **Priority:** MEDIUM
- **ID:** ITS-05
- **Title:** LangChain vision invocation pattern not detailed
- **Detailed Description:**  
  The spec says to use *"the regular chat completion api"* for image transcription. The existing codebase uses LangChain's `ChatOpenAI` wrapper (via `OpenAiChatProvider.get_llm()`), and `create_model_provider` returns a `BaseChatModel` for `"high"`/`"low"` tiers.

  Sending an image through LangChain's `ChatOpenAI` requires constructing a `HumanMessage` with multimodal content blocks — this is not the same as a simple text invocation. The correct pattern is:

  ```python
  from langchain_core.messages import HumanMessage

  message = HumanMessage(content=[
      {"type": "text", "text": "<prompt>"},
      {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}", "detail": "auto"}}
  ])
  response = await llm.ainvoke([message])
  transcript = response.content
  ```

  This is a non-trivial departure from how the LLM is used elsewhere in the codebase (e.g., `AutomaticBotReply` uses `RunnableWithMessageHistory` with text-only messages). The spec should acknowledge this invocation pattern or at minimum note that the LangChain multimodal message format is required.

  Additionally, the `ainvoke` call returns an `AIMessage` whose `.content` is the transcription text. The spec should clarify that this text becomes the `ProcessingResult.content`.
- **Status:** READY
- **Required Actions:** Create a dedicated `ImageTranscriptionProvider` abstract class (in `model_providers/image_transcription.py`) with a `transcribe_image(base64_image, mime_type) -> str` method, mirroring the `ImageModerationProvider` pattern. Create a concrete `OpenAiImageTranscriptionProvider` (in `model_providers/openAiImageTranscription.py`) that internally builds a `ChatOpenAI` LLM, constructs the multimodal `HumanMessage` with content blocks (text prompt + `image_url` with `detail="auto"`), invokes it, and returns `response.content`. Add `"image_transcription"` as a new value in `ConfigTier`, add an `image_transcription` field to `LLMConfigurations` as a per-bot tier (defaults matching `"low"` — `OpenAiChatProvider` with `gpt-5-mini`). Extend `create_model_provider` in `services/model_factory.py` to handle `ImageTranscriptionProvider` as a third branch. The processor simply calls `provider.transcribe_image()` — all vision-specific logic (prompt, detail, LangChain multimodal message) is encapsulated in the provider. **This supersedes ITS-02** — the global config `image_transcription_tier` is dropped in favor of a proper per-bot tier.

---

### ITS-08: Config type for `image_transcription` tier not specified

- **Priority:** MEDIUM
- **ID:** ITS-08
- **Title:** Config type for `image_transcription` tier not specified
- **Detailed Description:**  
  The spec states `image_transcription` is a per-bot tier in `LLMConfigurations` with "defaults matching the `low` tier", and that the provider "internally builds a `ChatOpenAI` LLM." However, it does not specify the Pydantic config type for this new tier field. Currently:
  - `high` / `low` use `ChatCompletionProviderConfig` (includes temperature, reasoning_effort, seed, etc.)
  - `image_moderation` uses `BaseModelProviderConfig` (just model + api_key)

  The `OpenAiImageTranscriptionProvider` needs all the `ChatCompletionProviderConfig` settings to build a `ChatOpenAI`, **plus** an additional `detail` parameter (controlling image tokenization fidelity). Without specifying the config type, the implementer must guess which Pydantic model to use, and the `detail` parameter has no home in the config hierarchy.
- **Status:** READY
- **Required Actions:** Create `ImageTranscriptionProviderConfig` extending `ChatCompletionProviderConfig` with an additional `detail: Literal["low", "high", "auto"] = "auto"` field. The `LLMConfigurations.image_transcription` field type is `ImageTranscriptionProviderConfig`. The `resolve_model_config` function in `services/resolver.py` returns `ImageTranscriptionProviderConfig` for the `"image_transcription"` tier. `ConfigTier` is updated to include `"image_transcription"`. This keeps `detail` as a first-class config field — defaulting to `"auto"` but overridable per-bot without code changes.

---

### ITS-07: Caption handling not addressed

- **Priority:** LOW
- **ID:** ITS-07
- **Title:** Caption handling not addressed
- **Detailed Description:**  
  WhatsApp images can include a text caption sent alongside the image. The current `process_media` method receives this `caption` parameter, and other processors (e.g., `CorruptMediaProcessor`, `UnsupportedMediaProcessor`) append the caption to their output.

  The spec doesn't mention how captions should interact with image transcription:
  - Should the caption be included in the prompt to the LLM (e.g., *"The sender also included this caption: ..."*)?
  - Should the final `ProcessingResult.content` combine the caption with the transcription?
  - Or should the caption be ignored since the transcription replaces the image semantically?

  This is a low-priority item since a reasonable default (ignoring or appending) can be chosen during implementation, but it should be considered.
- **Status:** READY
- **Required Actions:** Append caption to the transcription output using the following format:

  With caption:
  ```
  [Attached image description: <transcription>]
  [Image caption: <caption>]
  ```

  Without caption:
  ```
  [Attached image description: <transcription>]
  ```

  This format is concise, sender-agnostic, and clearly delineates the AI-generated description from the sender's original caption text for downstream LLM consumption.

---
