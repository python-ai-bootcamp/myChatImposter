# Feature Specification: Media Processor Image Moderation

## Overview
This feature introduces automatic image moderation for the `ImageVisionProcessor`. Every image processed by the system will be sent to the OpenAI Moderation API to identify potentially harmful content. This ensures that the system can flag or filter out inappropriate visuals before they are delivered to users.

## Requirements
- Use the `image_moderation` LLM configuration defined in the bot's settings.
- Utilize the OpenAI `omni-moderation-latest` model.
- Moderation must be performed on the actual image data (base64 encoded).
- Moderation results must be printed to the console for auditing and debugging.

## Technical Details

### 1. Provider Abstraction (`llm_providers/base.py`)
To ensure we can switch moderation engines in the future, we will add a standard moderation method to the `BaseLlmProvider`.
- **New Method**: `moderate_image(base64_image: str, mime_type: str) -> Dict[str, Any]`

### 2. OpenAI Implementation (`llm_providers/openAi.py`)
The `OpenAiLlmProvider` will implement the moderation logic using the official SDK.
- **Model**: `omni-moderation-latest`
- **Logic**: Handles the client initialization and API call internally.

### 3. Factory Support (`services/llm_factory.py`)
The `llm_factory` will be enhanced to provide moderation-capable provider instances.
- **New Function**: `get_llm_provider(llm_config: LLMProviderConfig, user_id: str) -> BaseLlmProvider`

### 4. Image Processing Workflow (`ImageVisionProcessor`)
1. **Fetch Config**: Retrieve `bot_configurations` and find `llm_configs.image_moderation`.
2. **Get Provider**: Use `llm_factory.get_llm_provider` to get the appropriate provider instance.
3. **Encode**: Convert image bytes to base64.
4. **Moderate**: Call `provider.moderate_image(base64_data, mime_type)`.
5. **Log**: Print the full result to the console.
6. **Result**: Return `ProcessingResult`.

## Proposed Code Changes

### `llm_providers/base.py`
- Add abstract method `moderate_image`.

### `llm_providers/openAi.py`
- Implement `moderate_image` using `openai.moderations.create`.

### `services/llm_factory.py`
- Add `get_llm_provider` helper.

### `media_processors/stub_processors.py`
- Update `ImageVisionProcessor` to use the abstracted provider.

## Constraints & Considerations
- **Provider Consistency**: New providers must implement `moderate_image` to be compatible with `ImageVisionProcessor`.
- **Result Format**: While raw results are printed to the console, the `moderate_image` method should return a dictionary for potential future automated logic.
- **Latency**: Provider-level abstraction adds negligible overhead compared to the network call.
