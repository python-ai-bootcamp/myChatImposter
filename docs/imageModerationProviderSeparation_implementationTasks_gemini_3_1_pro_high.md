# Image Moderation Provider Separation - Implementation Tasks

## Summary

| Task ID | Task Group / Scope | Spec Reference | Status |
|---|---|---|---|
| 1 | `config_models.py` Type Definitions | 2.1, 2.2, 2.3, 2.4, 2.5 | Pending |
| 2 | Create Centralized Resolvers | 4.3 | Pending |
| 3 | Rename Provider Package | 3 | Pending |
| 4 | Update `provider_utils.py` | 4.5.3 | Pending |
| 5 | Abstract Provider Base Classes | 3.1, 3.2, 3.3 | Pending |
| 6 | OpenAI Chat Provider Refactor | 3.4 | Pending |
| 7 | OpenAI Moderation Provider | 3.5 | Pending |
| 8 | Fake LLM Provider Fixes | 4.5.3 | Pending |
| 9 | ConfigTier Literal Expansion | 4.5.2 | Pending |
| 10 | Model Factory Refactor | 4.1, 4.2 | Pending |
| 11 | Auto Bot Reply Cascade Fixes | 4.5.1 | Pending |
| 12 | Bot Lifecycle & Route Cleanup | 4.5.1, 4.5.5 | Pending |
| 13 | Periodic Tracking Extractor | 4.5.4 | Pending |
| 14 | Periodic Tracking Cron & Runner | 4.5.4 | Pending |
| 15 | System-Wide Import Sweep | 4.5.3 | Pending |
| 16 | Backend UI Routers | 4.4, 4.5.3 | Pending |
| 17 | Frontend Config Models | 4.4, 4.5.3 | Pending |
| 18 | Test Suite Sweep | 4.5.1, 4.5.3 | Pending |
| 19 | Database Migration Script | 4.6 | Pending |

---

## Task Details

### 1. `config_models.py` Type Definitions
- **Spec Section:** 2.1, 2.2, 2.3, 2.4, 2.5
- **Description:** Centralize the `ConfigTier` alias. Split configurations into `BaseModelProviderSettings/Config` and `ChatCompletionProviderSettings/Config`. Drop `extra = 'allow'`. Change `LLMConfigurations.image_moderation` type to `BaseModelProviderConfig`. Split and rename `DefaultConfigurations` prefixes from `llm_` to `model_`.
- **Status:** Pending

### 2. Create Centralized Resolvers
- **Spec Section:** 4.3
- **Description:** Create `services/resolver.py` with async `resolve_user()` and `resolve_model_config()` functions parsing direct DB queries and leveraging `GlobalStateManager`.
- **Status:** Pending

### 3. Rename Provider Package
- **Spec Section:** 3
- **Description:** Rename the directory `llm_providers/` to `model_providers/`.
- **Status:** Pending

### 4. Update `provider_utils.py`
- **Spec Section:** 4.5.3
- **Description:** Update `find_provider_class` to include an `inspect.isabstract(obj)` check to skip intermediate abstract classes during dynamic loading.
- **Status:** Pending

### 5. Abstract Provider Base Classes
- **Spec Section:** 3.1, 3.2, 3.3
- **Description:** Refactor `base.py` to `BaseModelProvider` (dropping `user_id` and implementing `_resolve_api_key`). Create `chat_completion.py` (with `ChatCompletionProvider`) and `image_moderation.py` (with `ImageModerationProvider` and `ModerationResult` config).
- **Status:** Pending

### 6. OpenAI Chat Provider Refactor
- **Spec Section:** 3.4
- **Description:** Rename `openAi.py` class to `OpenAiChatProvider`, inherit from `ChatCompletionProvider`, drop `user_id`, and consolidate httpx duplicate loggers.
- **Status:** Pending

### 7. OpenAI Moderation Provider
- **Spec Section:** 3.5
- **Description:** Implement `openAiModeration.py` hosting `OpenAiModerationProvider`. Inherit from `ImageModerationProvider`, directly invoke the `AsyncOpenAI` SDK with explicitly extracted model and API key.
- **Status:** Pending

### 8. Fake LLM Provider Fixes
- **Spec Section:** 4.5.3
- **Description:** Remove `self.user_id` dependencies causing test crashes in `fakeLlm.py`, and restore missing `typing` imports.
- **Status:** Pending

### 9. ConfigTier Literal Expansion
- **Spec Section:** 4.5.2
- **Description:** Update tracking components (`token_consumption_service.py`, `quota_service.py`, `tracked_llm.py`) to import the `ConfigTier` alias rather than hardcoded literals.
- **Status:** Pending

### 10. Model Factory Refactor
- **Spec Section:** 4.1, 4.2
- **Description:** Rename `services/llm_factory.py` to `services/model_factory.py`. Replace synchronous factory with `async def create_model_provider` using new explicit subtype branches (`BaseChatModel` or `ImageModerationProvider`) based on `isinstance` checks, calling the new centralized resolvers.
- **Status:** Pending

### 11. Auto Bot Reply Cascade Fixes
- **Spec Section:** 4.5.1
- **Description:** Remove synchronous `_initialize_llm()` from `AutomaticBotReplyService.__init__`. Make it async and explicitly `await` it inside `BotLifecycleService.create_bot_session()`.
- **Status:** Pending

### 12. Bot Lifecycle & Route Cleanup
- **Spec Section:** 4.5.1, 4.5.5
- **Description:** Delete `_setup_session()` in `routers/bot_management.py` and replace it with `create_bot_session()`. Replace inline owner resolution in `create_bot_session` with `resolve_user()`. Delete useless `on_bot_connected()` owner resolution block.
- **Status:** Pending

### 13. Periodic Tracking Extractor
- **Spec Section:** 4.5.4
- **Description:** Simplify `ActionItemExtractor.extract()` signature. Repoint internal logic to async `create_model_provider`. Remove `if llm_config_high` restriction. Rewrite `LLMRecorder` parameter population logic. Remove duplicate `__init__`.
- **Status:** Pending

### 14. Periodic Tracking Cron & Runner
- **Spec Section:** 4.5.4
- **Description:** Rip out `token_consumption_collection` threading through `GroupTrackingRunner`, `GroupTracker`, and `main.py`. Remove `owner_user_id` from APScheduler signatures.
- **Status:** Pending

### 15. System-Wide Import Sweep
- **Spec Section:** 4.5.3
- **Description:** Comb through the Import Resolution table replacing references to `llm_providers`, `LLMProviderConfig`, `create_tracked_llm`, and updated config types across `tests`, `features`, and `routers`.
- **Status:** Pending

### 16. Backend UI Routers
- **Spec Section:** 4.4, 4.5.3
- **Description:** Overhaul `routers/bot_management.py` config schema loops for `api_key_source` and `reasoning_effort` specific constraints. Update `routers/bot_ui.py` with static initializers using new defaults.
- **Status:** Pending

### 17. Frontend Config Models
- **Spec Section:** 4.4, 4.5.3
- **Description:** In `frontend/src/configModels.js`, implement JS `BaseModelProviderConfig` class that checks only base fields. Update `LLMConfigurations.validate()` conditionally routing image moderation properties.
- **Status:** Pending

### 18. Test Suite Sweep
- **Spec Section:** 4.5.1, 4.5.3
- **Description:** Update tests handling `AutomaticBotReplyService` to explicitly await `_initialize_llm()`. Adapt `fakeLlm.py` reliant tests due to `user_id` formatting removal. Shift `llm_factory` patch targets to `model_factory`.
- **Status:** Pending

### 19. Database Migration Script
- **Spec Section:** 4.6
- **Description:** Create standalone migration script to assign default owners, clean legacy chat fields from `image_moderation`, `high`, and `low` models, and rename config `provider_name` to `"openAiModeration"`.
- **Status:** Pending
