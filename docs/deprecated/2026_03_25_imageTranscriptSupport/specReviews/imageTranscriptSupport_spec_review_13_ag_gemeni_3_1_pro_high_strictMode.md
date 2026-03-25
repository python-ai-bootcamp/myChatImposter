# Spec Review: Image Transcript Support

## Review Summary

| priority | id | title | link | status |
| :--- | :--- | :--- | :--- | :--- |
| High | `issue-01` | Transcription Prompt Localization / Language Mismatch | [View Details](#issue-01) | READY |
| Medium | `issue-02` | Test Breakage Risk for Stub Processors & Successful Outcomes | [View Details](#issue-02) | READY |

---

## Detailed Findings

### <a id="issue-01"></a>Issue `issue-01`: Transcription Prompt Localization / Language Mismatch
**Priority**: High
**Status**: READY

**Detailed Description**: 
The spec defines a hardcoded English prompt for the `ImageTranscriptionProvider`: *"Describe the contents of this image concisely in 1-3 sentences, if there is text in the image add the text inside image to description as well"*. 
However, according to `config_models.py`, `UserDetails` contains a `language_code` setting (defaulting to `"en"`). If a bot is configured with a different language (e.g., Spanish, Arabic), providing a hardcoded English prompt without explicit language instructions may cause the LLM to consistently output the transcription in English, causing a jarring user experience where the bot speaks one language but transcribes media in another.

**Required Actions**: 
- Create a new resolving function `resolve_bot_language(bot_id: str) -> str` inside `services/resolver.py` that fetches the `language_code` originating from the bot's `UserDetails` configuration.
- Update `ImageVisionProcessor.process_media` to call this new function and explicitly retrieve the bot's configured language.
- Update the `ImageTranscriptionProvider.transcribe_image` method signature to pass in this language parameter: `async def transcribe_image(self, base64_image: str, mime_type: str, language_code: str) -> str`.
- Modify `OpenAiImageTranscriptionProvider.transcribe_image` to inject the requested `language_code` clearly into the multimodal prompt instructions sent to the LLM. 


---

### <a id="issue-02"></a>Issue `issue-02`: Test Breakage Risk for Stub Processors & Successful Outcomes
**Priority**: Medium
**Status**: READY

**Detailed Description**: 
The spec introduces a correct and cleaner centralized formatting logic in `BaseMediaProcessor.process_job()` via `format_processing_result()`, dictating that successful output must be clean text, and bracket wrapping (`[<content>]`) should exclusively happen when `unprocessable_media = True`. It requires standardizing all Stubs (`StubSleepProcessor`, etc.) to return clean text. 
Previously, successful outputs from stubs and `ImageVisionProcessor` literally returned strings with brackets (e.g., `[Transcripted image multimedia message...]`). Because the new architecture guarantees successful transcripions will NOT have brackets, any existing test suites that specifically assert the existence of brackets for successfully processed media endpoints will fail. The spec misses updating the "Test Expectations" section to account for modifying existing stub/processor tests to expect unbracketed plain strings on success.

**Required Actions**: 
- Add an explicit bullet point to the "Test Expectations" section of the specification mandating that all existing automated tests covering `StubSleepProcessor`, along with other stubs and success-path implementations, must be updated.
- These tests must now assert that successfully processed media returns plain, unbracketed strings, verifying the removal of legacy bracket wrapping (`[Transcripted...]`).
