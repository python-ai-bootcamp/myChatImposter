# Implementation Tasks for Image Transcription Support

| Task ID | Description | Status |
|---------|-------------|--------|
| 1 | Add `unprocessable_media: bool = False` to `ProcessingResult` dataclass in infrastructure/models.py with docstring comment | <PENDING> |
| 2 | Update `DEFAULT_POOL_DEFINITIONS` in services/media_processing_service.py to include "image/gif" in ImageVisionProcessor mime types list | <PENDING> |
| 3 | Create migration script scripts/migrations/migrate_pool_definitions_gif.py to delete _mediaProcessorDefinitions document from MongoDB configurations collection | <PENDING> |
| 4 | Update ImageVisionProcessor.process_media to moderate image first, then transcribe if not flagged | <PENDING> |
| 5 | Implement resolve_bot_language function in services/resolver.py that fetches language_code from bot's UserDetails configuration with fallback to "en" | <PENDING> |
| 6 | Update ImageVisionProcessor to call resolve_bot_language and use bot's image_transcription tier for transcription | <PENDING> |
| 7 | Implement transcription response normalization contract in OpenAiImageTranscriptionProvider.transcribe_image | <PENDING> |
| 8 | Update BaseMediaProcessor.process_job to remove caption parameter from process_media call and implement new shared lifecycle logic | <PENDING> |
| 9 | Update process_media method signature in BaseMediaProcessor and all 7 affected subclasses to remove caption parameter | <PENDING> |
| 10 | Implement format_processing_result function in media_processors/base.py as a module-level pure function | <PENDING> |
| 11 | Update BaseMediaProcessor._handle_unhandled_exception to invoke format_processing_result and set content to "Media processing failed" | <PENDING> |
| 12 | Update asyncio.TimeoutError handling in BaseMediaProcessor.process_job to return "Processing timed out" without brackets | <PENDING> |
| 13 | Update CorruptMediaProcessor.process_media to return ProcessingResult with content=f"Corrupted {media_type} media could not be downloaded" | <PENDING> |
| 14 | Update UnsupportedMediaProcessor.process_media to return ProcessingResult with content=f"Unsupported media type: {mime_type}" | <PENDING> |
| 15 | Update StubSleepProcessor.process_media to return ProcessingResult with content=f"multimedia message with guid='{...}'" | <PENDING> |
| 16 | Add image_transcription as new per-bot tier in LLMConfigurations with defaults matching low tier but using dedicated environment variables | <PENDING> |
| 17 | Create ImageTranscriptionProviderSettings class inheriting from ChatCompletionProviderSettings with detail field | <PENDING> |
| 18 | Modify ImageTranscriptionProviderConfig to extend ChatCompletionProviderConfig and redefine provider_config | <PENDING> |
| 19 | Update ConfigTier to include "image_transcription" | <PENDING> |
| 20 | Update resolve_model_config in services/resolver.py to return ImageTranscriptionProviderConfig for "image_transcription" tier | <PENDING> |
| 21 | Extend global_configurations.token_menu with image_transcription pricing entry | <PENDING> |
| 22 | Update get_configuration_schema in routers/bot_management.py to dynamically extract LLM configuration tiers | <PENDING> |
| 23 | Define LLMProvider abstract base class in model_providers/base.py with get_llm() abstract method | <PENDING> |
| 24 | Modify ChatCompletionProvider to inherit from LLMProvider and become empty type-marker class | <PENDING> |
| 25 | Define ImageTranscriptionProvider abstract class extending LLMProvider with transcribe_image abstract method | <PENDING> |
| 26 | Define OpenAiMixin with _build_llm_params() method | <PENDING> |
| 27 | Refactor OpenAiChatProvider to use OpenAiMixin and move httpx logger configuration to main.py | <PENDING> |
| 28 | Implement OpenAiImageTranscriptionProvider extending ImageTranscriptionProvider and OpenAiMixin | <PENDING> |
| 29 | Update create_model_provider return type annotation and docstring | <PENDING> |
| 30 | Refactor create_model_provider in services/model_factory.py to use unified isinstance(provider, LLMProvider) branch | <PENDING> |
| 31 | Update find_provider_class in utils/provider_utils.py to include obj.__module__ == module.__name__ filter | <PENDING> |
| 32 | Add migration script scripts/migrations/migrate_image_transcription.py to backfill image_transcription tier in bot configs | <PENDING> |
| 33 | Extend DefaultConfigurations in config_models.py with model_provider_name_image_transcription and defaults | <PENDING> |
| 34 | Update get_bot_defaults in routers/bot_management.py to include image_transcription in LLMConfigurations | <PENDING> |
| 35 | Define LLMConfigurations.image_transcription as strictly required field using Field(...) | <PENDING> |
| 36 | Update scripts/migrations/initialize_quota_and_bots.py to include image_transcription tier in token_menu | <PENDING> |
| 37 | Create scripts/migrations/migrate_token_menu_image_transcription.py to patch existing environments | <PENDING> |
| 38 | Ensure QuotaService.load_token_menu() remains read-only fetch without self-healing insert logic | <PENDING> |
| 39 | Verify migration scripts use infrastructure/db_schema.py constants | <PENDING> |
| 40 | Capture pre/post document counts for COLLECTION_BOT_CONFIGURATIONS and COLLECTION_GLOBAL_CONFIGURATIONS | <PENDING> |
| 41 | Validate sample bot documents include config_data.configurations.llm_configs.image_transcription | <PENDING> |
| 42 | Validate global token menu includes image_transcription tier with expected pricing fields | <PENDING> |
| 43 | Delete unused dead code LLMProviderSettings and LLMProviderConfig from config_models.py | <PENDING> |
| 44 | Add ConfigTier update to include "image_transcription" (duplicate of task 18, but listed separately in spec) | <PENDING> |
| 45 | Add comment in config_models.py stating ConfigTier and LLMConfigurations are ONLY places where tier structure is defined | <PENDING> |
| 46 | Add @overload type hint for resolve_model_config with image_transcription literal in services/resolver.py | <PENDING> |
| 47 | Ensure schema surgery loop in routers/bot_management.py iterates dynamically over actual keys in schema definition | <PENDING> |
| 48 | Apply reasoning_effort title patches to both ChatCompletionProviderSettings and ImageTranscriptionProviderSettings | <PENDING> |
| 49 | Create GET /api/internal/bots/tiers endpoint in routers/bot_management.py | <PENDING> |
| 50 | Update frontend/src/pages/EditPage.js to fetch tiers from new endpoint and replace hardcoded tier arrays | <PENDING> |
| 51 | Add image_transcription entry to uiSchema in frontend/src/pages/EditPage.js with proper structure | <PENDING> |
| 52 | Add tests verifying detail is filtered from ChatOpenAI constructor kwargs and used in transcription payload | <PENDING> |
| 53 | Add tests for callback continuity between create_model_provider and transcribe_image | <PENDING> |
| 54 | Add tests for transcription normalization covering string content, content blocks, and unsupported content | <PENDING> |
| 55 | Add test for moderation_result.flagged == True returning ProcessingResult with unprocessable_media=True | <PENDING> |
| 56 | Add test for format_processing_result formatting strings with bracket wrapping and caption handling | <PENDING> |
| 57 | Add test for asyncio.TimeoutError path returning ProcessingResult with unprocessable_media=True | <PENDING> |
| 58 | Update existing tests for process_media to assert raw unbracketed content strings | <PENDING> |
| 59 | Add integration tests for process_job end-to-end asserting fully formatted string delivered to bot queue | <PENDING> |
| 60 | Update existing tests for UnsupportedMediaProcessor and CorruptMediaProcessor content strings | <PENDING> |
| 61 | Update test_process_media_bot_id_signature test in tests/test_image_vision_processor.py to use robust dictionary key lookup | <PENDING> |
