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
  - model_providers\openai.py
  - model_providers\openai_moderation.py
  - model_providers\image_moderation.py
  - services\media_processing_service.py
  - services\resolver.py

### Project Links
  - https://developers.openai.com/api/docs/guides/moderation/


## Technical Details

### Image Processing Workflow (`ImageVisionProcessor` in `image_vision_processor.py`)
1. **Seperate ImageVisionProcessor**: ImageVisionProcessor will no longer be handled by media_processors\stub_processors.py, and will be extracted into its own file (media_processors\image_vision_processor.py). the core logic will remain the same as in stub_processors.py for now. only difference is that there will be an actual moderation api call in the ImageVisionProcessor based on the media file.
2. current process_media() signature will be updated to, self.process_media(file_path, job.mime_type, job.bot_id) since these are all the arguments any media processor needs to run (old stub processors signature will be updated as well as the new ImageVisionProcessor for receiving them correctly)
3. **Image Data Loading**: The ImageVisionProcessor will load the image bytes from `file_path` into memory, encode it as a raw base64 string
4. **Moderation call**: 
    - the ImageVisionProcessor will use the openAiModeration Provider to call the moderation api with the base64 encoded    image data
    - provider will use the `openai` sdk to call the moderation api directly without using any langchain wrapper
    - all sdk calls will be called in an async manner so we will not block the event loop
    - **Input Array Structure**: The SDK requires image moderation requests to pass the base64 dataURI inside a structured    array. The `OpenAiLlmProvider` must take the raw `base64_image` and `mime_type` passed to its `moderate_image` method   and construct the data-URI `f"data:{mime_type};base64,{base64_image}"` internally. The `input` parameter for the SDK   method must then be constructed exactly like: `[{"type": "image_url", "image_url": {"url": data_uri}}]`.
    - **Return Type Conversion**: Call `.model_dump()` on the returned Pydantic `ModerationCreateResponse` object.

5. **Error Fallback**: If the wrapper throws an exception (e.g., `ConfigurationMissingError`, or if the SDK fails after all internal retries), do **not** attempt to catch it inside `process_media` to return a manually constructed `ProcessingResult`. Simply allow the exception to bubble up unhandled. The `BaseMediaProcessor.process_job` lifecycle already possesses a robust error-handling mechanism (`_handle_unhandled_exception`) that will automatically construct a safe `ProcessingResult` with the message `"[Media processing failed]"`, save the error reason to the fail log, and safely deliver the fallback message.
6. **Log**: If successful, log the full moderation result dictionary returned by the wrapper using `logger.info()`.
7. **Result**:
   - return `ProcessingResult` without the moderation result similarly to the way the stub processors work. 
   - ProcessingResult(content=f"[Transcripted image multimedia message with guid='{os.path.basename(file_path)}']")
 

