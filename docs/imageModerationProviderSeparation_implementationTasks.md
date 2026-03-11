# Implementation Tasks: Image Moderation Provider Separation

## Task Summary

| Task ID | Task Description                                                                 | Status  | Spec Section |
|---------|----------------------------------------------------------------------------------|---------|--------------|
| 1       | Add `inspect.isabstract` check to `find_provider_class`                          | Pending | 4.5.3        |
| 2       | Update Configuration Models (`config_models.py`)                                 | Pending | 2.1-2.5      |
| 3       | Rename `llm_providers` package to `model_providers`                              | Pending | 3            |
| 4       | Refactor base provider interfaces (`base.py`, `chat_completion.py`...)           | Pending | 3.1-3.3      |
| 5       | Create `OpenAiChatProvider` and `OpenAiModerationProvider`                       | Pending | 3.4-3.5      |
| 6       | Fix `FakeLlmProvider` and update imports                                         | Pending | 4.5.3        |
| 7       | Create centralized resolvers (`services/resolver.py`)                            | Pending | 4.3          |
| 8       | Refactor factory & tracking service (`model_factory.py`, `tracked_llm.py`)       | Pending | 4.1-4.2      |
| 9       | Update configuration tier litrals across services (`QuotaService` etc.)          | Pending | 4.5.2        |
| 10      | Fix imports across the application (`features/`, `routers/`, `tests/`)           | Pending | 4.5.3        |
| 11      | Update `AutomaticBotReplyService` & `BotLifecycleService` async cascade          | Pending | 4.5.1, 4.5.5 |
| 12      | Update `bot_management.py` HTTP endpoints & schema generation                    | Pending | 4.5.1, 4.5.3 |
| 13      | Update Group Tracking Feature (`extractor.py`, `runner.py`, `service.py`, `main`)| Pending | 4.5.4        |
| 14      | Update Configuration Form validation & init (`bot_ui.py`, `configModels.js`)     | Pending | 4.4, 4.5.3   |
| 15      | Sweep and update unit/integration tests                                          | Pending | 4.5.1, 4.5.3 |
| 16      | Create Database Migration Script                                                 | Pending | 4.6          |

***

## Detailed Implementation Tasks

### 1. Update `find_provider_class` helper
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** Update `utils/provider_utils.py` to add `inspect.isabstract(obj)` check when finding provider classes. Must be done first before creating abstract subclasses to prevent instantiation crashes.

### 2. Configuration Restructuring
- **Status:** Pending
- **Spec Section:** 2.1, 2.2, 2.3, 2.4, 2.5
- **Description:** 
  - Add centralized type alias `ConfigTier = Literal["high", "low", "image_moderation"]` in `config_models.py`.
  - Add base classes `BaseModelProviderSettings` and `BaseModelProviderConfig`.
  - Add chat completion classes `ChatCompletionProviderSettings` and `ChatCompletionProviderConfig`.
  - Update `LLMConfigurations` model property types.
  - Rename `DefaultConfigurations` parameters and their corresponding string literals / defaults, fully deleting `llm_provider_name`.

### 3. Rename Provider Package
- **Status:** Pending
- **Spec Section:** 3
- **Description:** Rename the directory `llm_providers` to `model_providers` using file system tools. Keep it an implicit namespace package.

### 4. Refactor Base Models
- **Status:** Pending
- **Spec Section:** 3.1, 3.2, 3.3
- **Description:** 
  - Modify `model_providers/base.py` to build `BaseModelProvider` (remove `user_id` and add `_resolve_api_key()`).
  - Create new `model_providers/chat_completion.py` inheriting `BaseModelProvider` and defining `get_llm()`.
  - Create new `model_providers/image_moderation.py` defining `ModerationResult` and an abstract `moderate_image()`.

### 5. Implementation of Concrete Providers
- **Status:** Pending
- **Spec Section:** 3.4, 3.5
- **Description:** 
  - Refactor `model_providers/openAi.py` to inherit from `ChatCompletionProvider`, consolidate duplicated `httpx` logger setup blocks, and remove `user_id` dependencies.
  - Create new `model_providers/openAiModeration.py` for image moderation utilizing `self.config.provider_config.model`.

### 6. Fix Test Mock Dependencies (`fakeLlm.py`)
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** Update `FakeLlmProvider` in `model_providers/fakeLlm.py` to drop `user_id`, fix missing python typing imports (`Optional, List, Any`), and adjust behavior.

### 7. Centralized Architecture Resolvers
- **Status:** Pending
- **Spec Section:** 4.3
- **Description:** Create `services/resolver.py` extracting and centralizing DB lookups mapping from `bot_id` to `user_id` and bot-specific configurations.

### 8. Async Factory & Token Tracker Adjustments
- **Status:** Pending
- **Spec Section:** 4.1, 4.2
- **Description:** 
  - Rename `services/llm_factory.py` to `services/model_factory.py`.
  - Update the central factory method to `async def create_model_provider(...)`, simplifying its parameters (no `user_id`, no config, no collection).
  - Use polymorphic branching: `isinstance(ChatCompletionProvider)` vs `isinstance(ImageModerationProvider)`.
  - Track tokens ONLY if returning a Langchain standard module.

### 9. Component Signature Overhauls (`ConfigTier`)
- **Status:** Pending
- **Spec Section:** 4.5.2
- **Description:** Change `config_tier: Literal["high", "low"]` inline definitions to use the centralized `ConfigTier` enum in `token_consumption_service.py` (`record_event`), `quota_service.py` (`calculate_cost`), and `tracked_llm.py` (`TokenTrackingCallback`).

### 10. Widescale Import Swaps
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** Methodical sweep across all modules to change legacy `from llm_providers...` imports to `model_providers...`, swap `LLMProviderConfig` for `ChatCompletionProviderConfig`, and use the `create_model_provider` function.

### 11. `AutomaticBotReplyService` & `BotLifecycleService` Updates
- **Status:** Pending
- **Spec Section:** 4.5.1, 4.5.5
- **Description:** 
  - Remove synchronous `_initialize_llm()` out of constructor in `AutomaticBotReplyService`. Keep it async and call explicitly in `create_bot_session()`.
  - Wipe `on_bot_connected` owner resolution block in `BotLifecycleService` entirely.
  - Swap inline DB lookup in `create_bot_session()` with a call to `await resolve_user()`.

### 12. Management Router Fixes (`routers/bot_management.py`)
- **Status:** Pending
- **Spec Section:** 4.5.1, 4.5.3
- **Description:** 
  - Remove `get_configuration_schema` nested property hardcodes (`LLMProviderSettings`) and refactor to use dynamic iteration over `api_key_source`.
  - Fix default assignments from `DefaultConfigurations.model_provider_name_chat`, etc.
  - Delete `_setup_session()` function and re-point `link_bot` route to use `create_bot_session()`.

### 13. Periodic Group Tracking Async Extents
- **Status:** Pending
- **Spec Section:** 4.5.4
- **Description:** 
  - Strip missing fields (`llm_config`, `user_id`, `llm_config_high`, `token_consumption_collection`) out of extractor and runner layers.
  - Refactor `extractor.py` to instantiate models natively. Remove conditional phase 2 check.
  - Replace `LLMRecorder` setup block within extractor via resolver. Handle duplicate `__init__`.
  - Purge `owner_user_id` from cron schedule parameters (`update_jobs` & `run_tracking_cycle`).
  - Strip positional argument in `GroupTracker(...)` constructor.

### 14. UI Data & Formatting Fallbacks
- **Status:** Pending
- **Spec Section:** 4.4, 4.5.3
- **Description:** 
  - Include an explicit payload object in `routers/bot_ui.py` referencing the `image_moderation` property.
  - Expose a `BaseModelProviderConfig` in `frontend/src/configModels.js`, wire it to `LLMConfigurations.image_moderation`, and fix validation logic.

### 15. Comprehensive Test Adjustments
- **Status:** Pending
- **Spec Section:** 4.5.1, 4.5.3
- **Description:** Target unit test code initializing `AutomaticBotReplyService` to explicitly await the newly Async `_initialize_llm()`. Adapt `FakeLlm` tests and patch the new import paths for the factory.

### 16. Database Migration File
- **Status:** Pending
- **Spec Section:** 4.6
- **Description:** Write a DB script to:
  - Assign system default `user_id` to ownerless bots.
  - Sweep `provider_name="openAiModeration"` under `image_moderation` tier.
  - Strip keys like `temperature`/`seed` out of existing DB objects.
