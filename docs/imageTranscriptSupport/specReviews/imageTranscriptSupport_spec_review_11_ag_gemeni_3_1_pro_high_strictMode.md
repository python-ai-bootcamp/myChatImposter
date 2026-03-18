# Spec Review: Image Transcription Support

## Overview Table

| Priority | ID | Title | Link | Status |
| :--- | :--- | :--- | :--- | :--- |
| High | `unhandled_exception_caption_loss` | Unhandled exceptions bypass caption appending logic | [Details](#unhandled_exception_caption_loss) | READY |
| Medium | `hardcoded_brackets_timeout_unhandled` | Hardcoded brackets should be removed from error processor fallbacks due to centralized wrapping | [Details](#hardcoded_brackets_timeout_unhandled) | READY |
| Low | `default_configurations_missing_params` | Clarify `temperature` and `reasoning_effort` defaults for image transcription | [Details](#default_configurations_missing_params) | READY |

---

## Detailed Descriptions

### <a id="unhandled_exception_caption_loss"></a>unhandled_exception_caption_loss
* **Priority**: High
* **ID**: `unhandled_exception_caption_loss`
* **Title**: Unhandled exceptions bypass caption appending logic
* **Detailed Description**: The spec states: *"Update `BaseMediaProcessor.process_job` to always append the original caption... regardless of whether the processing was a success or a failure"*. However, in `BaseMediaProcessor.process_job`, the `except Exception as e:` block delegates to the `_handle_unhandled_exception` method. This method internally constructs a new `ProcessingResult(content="[Media processing failed]", ...)` and proceeds to persist and deliver it natively, completely bypassing the new bracket wrapping and caption appending logic that will be placed inside `process_job`. This will result in dropped captions whenever a catastrophic unhandled code exception occurs during processing. Either `_handle_unhandled_exception` should be updated to format the caption and use the `unprocessable_media` flag, or the formatting logic must encompass the `_handle_unhandled_exception` invocation.
* **Status**: READY
* **Required actions**: 
    * Update `_handle_unhandled_exception` to perform a "best-effort" inline check for the original caption.
    * If `job.placeholder_message.content` exists, append `\n[Caption: <caption_text>]` to the hardcoded `[Media processing failed]` content before returning or persisting the `ProcessingResult`.
    * Ensure the `ProcessingResult` correctly sets `unprocessable_media=True`.
    * Example snippet:
      ```python
      content = "[Media processing failed]"
      if job.placeholder_message.content:
          content += f"\n[Caption: {job.placeholder_message.content}]"
      result = ProcessingResult(content=content, failed_reason=error, unprocessable_media=True)
      ```

### <a id="hardcoded_brackets_timeout_unhandled"></a>hardcoded_brackets_timeout_unhandled
* **Priority**: Medium
* **ID**: `hardcoded_brackets_timeout_unhandled`
* **Title**: Hardcoded brackets should be removed from error processor fallbacks due to centralized wrapping
* **Detailed Description**: The spec introduces centralized bracket wrapping based on the `unprocessable_media: bool` flag: *"wrap result.content in brackets if and only if result.unprocessable_media is True"*. The `asyncio.TimeoutError` block is correctly instructed to return `unprocessable_media=True`. However, currently this block hardcodes the string as `content="[Processing timed out]"`. If not explicitly removed, this will result in double bracket wrapping: `[[Processing timed out]]`. The same applies to `_handle_unhandled_exception` which uses `"[Media processing failed]"`. The spec should explicitly dictate removing hardcoded brackets from these fallback strings to align with the new centralized wrapping.
* **Status**: READY
* **Required actions**: 
    * Update the spec to dictate that the hardcoded brackets must be removed from the fallback strings in `base.py`.
    * Specifically, change `"[Processing timed out]"` to `"Processing timed out"` in the `asyncio.TimeoutError` exception block.
    * Specifically, change `"[Media processing failed]"` to `"Media processing failed"` in `_handle_unhandled_exception`.
    * This ensures the new centralized wrapping logic accurately applies exactly one set of brackets.

### <a id="default_configurations_missing_params"></a>default_configurations_missing_params
* **Priority**: Low
* **ID**: `default_configurations_missing_params`
* **Title**: Clarify `temperature` and `reasoning_effort` defaults for image transcription
* **Detailed Description**: The spec says to *"Extend `DefaultConfigurations`... and defaults for the image transcription model/settings"*. It specifically mentions `DEFAULT_MODEL_IMAGE_TRANSCRIPTION`. Since the new `ImageTranscriptionProviderConfig` inherits from `ChatCompletionProviderConfig`, it requires inherited fields like `temperature` and `reasoning_effort`. The spec does not explicitly mandate whether we should reuse `model_temperature` and `model_reasoning_effort` for these fields, or introduce new environment variables. Reusing the existing globals is recommended but should be confirmed in the spec to prevent developer ambiguity during implementation.
* **Status**: READY
* **Required actions**: 
    * Update the spec to introduce new dedicated environment variables (e.g., `DEFAULT_IMAGE_TRANSCRIPTION_TEMPERATURE` and `DEFAULT_IMAGE_TRANSCRIPTION_REASONING_EFFORT`).
    * This allows completely independent tuning of the image transcription provider configuration from the main chat completion settings.
