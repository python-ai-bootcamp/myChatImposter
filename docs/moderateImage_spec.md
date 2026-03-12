# Feature Specification: Media Processor Image Moderation

## Overview
This feature introduces automatic image moderation for the `ImageVisionProcessor`. Every image processed by the system will be sent to the OpenAI Moderation API to identify potentially harmful content. This serves as a preparation step for the system to be able to detect inappropriate visuals before we will start to implement image processing part of the `ImageVisionProcessor`.

## Requirements
- Use the `image_moderation` LLM configuration defined in the bot's settings.
- Utilize the OpenAI `omni-moderation-latest` model using openAiModeration Provider.
- Moderation must be performed on the actual image data (base64 encoded).
- Moderation results must be logged (using the Python `logging` module) for auditing and debugging.
- this is just a preparation step for both actual image moderation and actual image processing
  - actual image moderation will be performed by the `ImageVisionProcessor` on a later phase, currently it will just use moderation api in image data and print the reults to log. 
  - actual image processing will be performed by the `ImageVisionProcessor` on a later phase, currently it will just print stub message pretending to describe the processed image. 

## Relevant Backround Information
### Project Files
  - media_processors\base.py
  - media_processors\stub_processors.py
  - media_processors\media_file_utils.py
  - media_processors\factory.py
  - model_providers\base.py
  - model_providers\openAi.py
  - model_providers\openAiModeration.py
  - model_providers\image_moderation.py
  - services\media_processing_service.py
  - services\model_factory.py,
  - services\resolver.py
  - config_models.py
  - queue_manager.py

### Project Links
  - https://developers.openai.com/api/docs/guides/moderation/


## Technical Details

### Image Processing Workflow (`ImageVisionProcessor` in `image_vision_processor.py`)
1. **Seperate ImageVisionProcessor**: ImageVisionProcessor will no longer be handled by media_processors\stub_processors.py, and will be extracted into its own file (media_processors\image_vision_processor.py). the core logic will remain the same as in stub_processors.py for now. only difference is that there will be an actual moderation api call in the ImageVisionProcessor based on the media file.
2. current process_media() signature will be updated to `self.process_media(file_path, job.mime_type, job.placeholder_message.content, job.bot_id)`.
   - this keeps `caption` support for existing error processors.
   - `quota_exceeded` will be removed from the `process_media()` method contract.
   - old stub processors signature will be updated as well as the new ImageVisionProcessor for receiving these arguments correctly.
3. **Image Data Loading**: The ImageVisionProcessor will load the image bytes from `file_path` into memory, encode it as a raw base64 string
4. **Moderation call**: 
    - the ImageVisionProcessor will use the `OpenAiModerationProvider` to call the moderation api with the base64 encoded image data
    - provider will use the `openai` sdk to call the moderation api directly without using any langchain wrapper
    - all sdk calls will be called in an async manner so we will not block the event loop
    - **Provider Method Contract**: `ImageModerationProvider.moderate_image()` and `OpenAiModerationProvider.moderate_image()` signatures will be updated to `(base64_image: str, mime_type: str) -> ModerationResult`.
    - **Input Array Structure**: The SDK requires image moderation requests to pass the base64 dataURI inside a structured array. The `OpenAiModerationProvider` must take the raw `base64_image` and `mime_type` passed to its `moderate_image` method and construct the data-URI `f"data:{mime_type};base64,{base64_image}"` internally. The `input` parameter for the SDK method must then be constructed exactly like: `[{"type": "image_url", "image_url": {"url": data_uri}}]`.
    - **Return Type Conversion**: `OpenAiModerationProvider` keeps returning normalized `ModerationResult`. `ImageVisionProcessor` will call `.model_dump()` on that `ModerationResult` for structured audit logging.

5. **Error Fallback**: If the wrapper throws an exception (e.g., configuration resolution errors, or if the SDK fails after all internal retries), do **not** attempt to catch it inside `process_media` to return a manually constructed `ProcessingResult`. Simply allow the exception to bubble up unhandled. The `BaseMediaProcessor.process_job` lifecycle already possesses a robust error-handling mechanism (`_handle_unhandled_exception`) that will automatically construct a safe `ProcessingResult` with the message `"[Media processing failed]"`, save the error reason to the fail log, and safely deliver the fallback message.
6. **Log**:
   - inside `OpenAiModerationProvider.moderate_image()`, raw sdk response logging is mandatory (for full debugging visibility).
   - inside `ImageVisionProcessor.process_media()`, if successful, log the normalized moderation result dictionary via `moderation_result.model_dump()` using `logger.info()` for auditing.
7. **Result**:
   - return `ProcessingResult` without the moderation result similarly to the way the stub processors work. 
   - ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")
 

