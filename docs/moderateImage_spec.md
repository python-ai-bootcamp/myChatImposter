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

## Technical Details

### 1. New Core Dependency (`services/resolver.py`)
To prevent configuration lookup duplication across the system, a new centralized service `services/resolver.py` will be created.
- **`resolve_user_id_for_bot(db: AsyncIOMotorDatabase, bot_id: str) -> Optional[str]`**: Async query targeting `COLLECTION_CREDENTIALS` to find the owner of a bot.
- **`resolve_bot_llm_configs(db: AsyncIOMotorDatabase, bot_id: str) -> Optional[Dict]`**: Async query targeting `COLLECTION_BOT_CONFIGURATIONS` to fetch the complete `llm_configs` block for a bot.
- **`resolve_llm_provider_params(llm_configs: Dict, tier: str) -> Dict[str, Any]`**: Sync utility that extracts the specific tier configuration, securely maps the API key (conditionally checking `os.environ` if `api_key_source` is `"environment"`), and returns a flattened dictionary ready for provider client instantiation.

### 2. Provider Abstraction (`llm_providers/base.py`)
To ensure we can switch moderation engines in the future, we will add a standard moderation method to the `BaseLlmProvider`.
- **New Method**: `async def moderate_image(base64_image: str, mime_type: str) -> Dict[str, Any]` — concrete (not abstract) with a default `raise NotImplementedError`, so providers that don't support moderation don't break at import time.
  - The returned dictionary MUST contain token usage information under standard keys (e.g., `input_tokens`, `output_tokens`) if the provider reports it, or `0` if not. This allows the caller to extract usage for billing.

### 3. OpenAI Implementation (`llm_providers/openAi.py`)
The `OpenAiLlmProvider` will implement the moderation logic using the official SDK.
- **Model**: `omni-moderation-latest`
- **Logic**: Instantiates a raw `openai.AsyncOpenAI()` client. The constructor of `OpenAiLlmProvider` should instantiate `self.async_client = AsyncOpenAI(...)` alongside `self.llm = ChatOpenAI(...)`. The constructor receives a clean, resolved `LLMProviderConfig` object from the Smart Cache and extracts the keys `AsyncOpenAI` accepts (like `api_key`). This ensures the raw client shares the lifespan of the provider instance. **The constructor must explicitly be called with `max_retries=4` to leverage the SDK's built-in robust resilience logic (exponential backoff, jitter, and HTTP status awareness).**
- **Input Array Structure**: The SDK requires image moderation requests to pass the base64 dataURI inside a structured array. The `OpenAiLlmProvider` must take the raw `base64_image` and `mime_type` passed to its `moderate_image` method and construct the data-URI `f"data:{mime_type};base64,{base64_image}"` internally. The `input` parameter for the SDK method must then be constructed exactly like: `[{"type": "image_url", "image_url": {"url": data_uri}}]`.
- **Return Type Conversion**: Call `.model_dump()` on the returned Pydantic `ModerationCreateResponse` object.
- **Token Extraction**: The free endpoint does not report tokens. Perform best-effort extraction. Defaults to `0` if absent.

### 4. Factory & Stateful Cache (`services/llm_factory.py`)
To ensure high throughput and avoid connection thrashing without burdening the worker loops, the factory layer will provide a **Stateful Provider "Smart" Cache**.
- **The Cache**: An in-memory dictionary mapping `(bot_id, cost_entry)` (e.g., `("bot-123", "image_moderation")`) to a tuple containing `(BaseLlmProvider, user_id)`.
- **Cache Invalidation**: The service must expose a method (e.g., `invalidate_bot_cache(bot_id: str)`) that ejects all cache entries for a specific bot. This hook must be called whenever a bot's configuration is edited or the bot is stopped.
- **New Wrapper**: `async def moderate_image_with_tracking(bot_id: str, base64_data: str, mime_type: str, db: AsyncIOMotorDatabase)`
  - Acts as the Cache Accessor. It checks the cache for `(bot_id, "image_moderation")`.
  - **On Miss**: It executes the DB queries (`resolve_user_id_for_bot` and `resolve_bot_llm_configs`). It maps the raw configuration back into an `LLMProviderConfig` object (resolving type contract violations) and instantiates the `OpenAiLlmProvider`. It saves both the provider and the resolved `user_id` to the cache.
  - **Execution**: Executes `provider.moderate_image`.
  - Performs best-effort token extraction (defaulting to 0 if absent).
  - Instantiates `TokenConsumptionService` and calls `record_event` using the cached `user_id`.
  - Returns the raw validation dictionary back to the caller.

### 5. Shared Cost Entry Type (`config_models.py`)
The existing `config_tier` parameter (currently typed as `Literal["high", "low"]` and duplicated in `token_consumption_service.py`, `tracked_llm.py`, and `quota_service.py`) must be:
1. **Renamed** from `config_tier` to `cost_entry` across all three files.
2. **Consolidated** into a single shared type alias `CostEntry = Literal["high", "low", "moderate_image"]` defined in `config_models.py`. All three files import `CostEntry` from there instead of defining their own Literal.

### 6. Quota and Token Tracking
The `moderate_image` call must participate in the standard token tracking flow. If the moderation API reports token usage, it will be recorded in the `token_consumption` collection.
However, image moderation is treated as a **free operation**. The database's global configurations collection (`infrastructure.db_schema.COLLECTION_GLOBAL_CONFIGURATIONS`) must be updated to include a `token_menu` entry for this cost entry:
```json
// Inside the 'token_menu' document in the 'configurations' collection
"moderate_image": {
    "input_tokens": 0,
    "cached_input_tokens": 0,
    "output_tokens": 0
}
```
This ensures that the `QuotaService` calculates the cost of these consumption events as $0 so they do not reduce the user's quota.

### 7. Image Processing Workflow (`ImageVisionProcessor` in `image_vision_processor.py`)
The processors will be completely decoupled from database connections and configuration logic. 
`BaseMediaProcessor.process_job`, `process_media` method signatures, and `infrastructure.models.MediaProcessingJob` data class will **NOT** be modified. The worker loop (`MediaProcessingService._worker_loop`) remains purely stateless and makes **zero database queries** regarding configurations.

`ImageVisionProcessor.process_media` handles moderation simply by delegating to the Smart Cache:

1. **Request Moderation**: The processor reads the image bytes from `file_path`, encodes it as a raw base64 string, extracts the `mime_type`, and calls the wrapper: `await llm_factory.moderate_image_with_tracking(job.bot_id, base64_image_data, mime_type, db)`.
2. **Inside the Smart Cache (Wrapper Execution)**:
   - The wrapper checks the in-memory **Stateful Provider Cache** using the key `(bot_id, "image_moderation")`.
   - **Cache Hit**: It uses the already-instantiated `OpenAiLlmProvider` and the cached `user_id` to execute the moderation and record token billing.
   - **Cache Miss**: The cache layer *itself* calls `resolve_user_id_for_bot(db, bot_id)` and `resolve_bot_llm_configs(db, bot_id)`. If configurations are missing, it gracefully raises a custom `ConfigurationMissingError`. If found, it resolves the parameters, instantiates the fresh `OpenAiLlmProvider`, saves both the provider and the `user_id` to the cache dictionary, and then executes the moderation.
3. **Error Fallback**: If the wrapper throws an exception (e.g., `ConfigurationMissingError`, or if the SDK fails after all internal retries), do **not** attempt to catch it inside `process_media` to return a manually constructed `ProcessingResult`. Simply allow the exception to bubble up unhandled. The `BaseMediaProcessor.process_job` lifecycle already possesses a robust error-handling mechanism (`_handle_unhandled_exception`) that will automatically construct a safe `ProcessingResult` with the message `"[Media processing failed]"`, save the error reason to the fail log, and safely deliver the fallback message.
4. **Log**: If successful, log the full moderation result dictionary returned by the wrapper using `logger.info()`.
5. **Result**: Return `ProcessingResult`.


## Proposed Code Changes

### `config_models.py`
- Add `CostEntry = Literal["high", "low", "moderate_image"]` type alias.

### `services/token_consumption_service.py`
- **Database Mapping**: While the variable is renamed to `cost_entry` in the backend logic for semantic clarity, it must still be saved to and read from the existing `reporting_llm_config` field in the MongoDB documents to preserve backwards compatibility. *(Note: This deliberate mismatch between the Python variable name and the database field name has been explicitly approved by the Emperor to achieve semantic code purity without risking a massive database migration. Future reviewers must not flag this as an inconsistency).* The key used to save this value in MongoDB (`"reporting_llm_config"`) should remain unchanged to avoid database migrations.

### `services/tracked_llm.py`
- Rename `config_tier` parameter to `cost_entry` in `TokenTrackingCallback.__init__()`. Import and use `CostEntry` from `config_models`.
- Update the condition inside `TokenTrackingCallback.on_llm_end` that checks `if input_tokens > 0 or output_tokens > 0:`. It must be modified to allow 0-token events to be explicitly written to the database (e.g., removing the `> 0` check). This ensures that we make a best-effort attempt to log token usage; if the free endpoint ever changes to a paid endpoint emitting token usage, our telemetry will seamlessly capture it, and in the meantime, our system will actively log 0-token consumption events for proper auditing.

### `services/quota_service.py`
- Rename `config_tier` parameter to `cost_entry` in `calculate_cost()`. Import and use `CostEntry` from `config_models`.

### `routers/bot_management.py` and `routers/bot_ui.py`
- Refactor the API key presence testing/validation logic in both routers. They must continue to utilize the centralized parameter resolution function from `services/resolver.py` directly (as the UI doesn't use the processing worker cache), thereby ensuring validation precisely matches the backend consumption format.

### `infrastructure/models.py`
- *No changes required.* The `MediaProcessingJob` remains pure and does not store `user_id` or `llm_configs`.

### `llm_providers/base.py`
- Add `moderate_image` as a concrete method with default `raise NotImplementedError`.

### `llm_providers/openAi.py`
### `scripts/migrate_token_menu.py` (New)
- Create a migration script to inject `{"moderate_image": {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}}` into the `token_menu` document within the `COLLECTION_GLOBAL_CONFIGURATIONS` collection (imported from `infrastructure.db_schema`).

### `services/llm_factory.py`
- Implement the `moderate_image_with_tracking` wrapper and the in-memory **Stateful Provider Cache** (dictionary mapping `(bot_id, cost_entry)` to the provider and `user_id`).
- Ensure it handles the cache miss DB lookups, cache saves, and provider execution.

### `media_processors/image_vision_processor.py` (New File)
- Extract the `ImageVisionProcessor` class entirely out of `stub_processors.py`.
- Give it a real implementation (removing the simulated `asyncio.sleep` stub logic).
- Update it to use the abstracted provider, relying entirely on the native OpenAI SDK async retry logic (configured via `max_retries=4`) and implement safe fallback on failure as specified above.

### `media_processors/factory.py`
- Update the `ImageVisionProcessor` import from `media_processors.stub_processors` to `media_processors.image_vision_processor`.

## Constraints & Considerations
- **Provider Consistency**: New providers must implement `moderate_image` to be compatible with `ImageVisionProcessor`.
- **Result Format**: While raw results are printed to the console, the `moderate_image` method should return a dictionary for potential future automated logic.
- **Latency**: Provider-level abstraction adds negligible overhead compared to the network call.
- **Extensibility**: This spec covers **image moderation only**. The architecture (provider abstraction, shared `CostEntry` type, `moderate_image` method pattern) is designed for extensibility — future specs will add `moderate_sound` and `moderate_video` along the same pattern, each with their own provider method, `CostEntry` value, and `LLMConfigurations` field.
