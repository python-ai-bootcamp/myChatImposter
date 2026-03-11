# Implementation Tasks: Image Moderation Provider Separation
## Cursor Composer 1.5 Edition

---

## Task Summary Table

| Task ID | Task Description | Status | Spec Section |
|---------|------------------|--------|--------------|
| 1 | Add `inspect.isabstract()` filter to `find_provider_class` in `utils/provider_utils.py` | Pending | 4.5.3 |
| 2 | Add centralized `ConfigTier` type alias in `config_models.py` | Pending | 2.1 |
| 3 | Add `BaseModelProviderSettings` and `BaseModelProviderConfig` in `config_models.py` | Pending | 2.2 |
| 4 | Add `ChatCompletionProviderSettings` and `ChatCompletionProviderConfig` in `config_models.py` | Pending | 2.3 |
| 5 | Update `LLMConfigurations.image_moderation` type to `BaseModelProviderConfig` | Pending | 2.4 |
| 6 | Rename `DefaultConfigurations` attributes and env vars from `llm_` to `model_` prefix; split provider defaults | Pending | 2.5 |
| 7 | Rename `llm_providers` directory to `model_providers` | Pending | 3 |
| 8 | Refactor `base.py` to `BaseModelProvider` (drop `user_id`, add `_resolve_api_key`) | Pending | 3.1 |
| 9 | Create `model_providers/chat_completion.py` with `ChatCompletionProvider` abstract class | Pending | 3.2 |
| 10 | Create `model_providers/image_moderation.py` with `ModerationResult` and `ImageModerationProvider` | Pending | 3.3 |
| 11 | Refactor `openAi.py` to `OpenAiChatProvider` (inherit `ChatCompletionProvider`, consolidate httpx blocks) | Pending | 3.4 |
| 12 | Create `model_providers/openAiModeration.py` with `OpenAiModerationProvider` | Pending | 3.5 |
| 13 | Fix `FakeLlmProvider` (drop `user_id`, add missing imports, update response formatting) | Pending | 4.5.3 |
| 14 | Create `services/resolver.py` with `resolve_user()` and `resolve_model_config()` | Pending | 4.3 |
| 15 | Rename `llm_factory.py` to `model_factory.py` and implement async `create_model_provider()` | Pending | 4.2 |
| 16 | Update `TokenTrackingCallback` and factory polymorphic branching (skip tracker for image_moderation) | Pending | 4.1, 4.2 |
| 17 | Expand `ConfigTier` in `token_consumption_service.py`, `quota_service.py`, `tracked_llm.py` | Pending | 4.5.2 |
| 18 | Update factory: remove local `find_provider_class`, import from `utils.provider_utils` | Pending | 4.5.3 |
| 19 | Update imports in `features/automatic_bot_reply/service.py` | Pending | 4.5.3 |
| 20 | Update imports in `features/periodic_group_tracking/extractor.py` | Pending | 4.5.3 |
| 21 | Update imports in `routers/bot_management.py` and `routers/bot_ui.py` | Pending | 4.5.3 |
| 22 | Update imports in `tests/services/test_token_services.py` and `tests/integration/test_token_flow_component.py` | Pending | 4.5.3 |
| 23 | Refactor `AutomaticBotReplyService`: remove sync `_initialize_llm()` from `__init__`, make it async | Pending | 4.5.1 |
| 24 | Update `BotLifecycleService.create_bot_session()`: call `await bot_service._initialize_llm()` after construction | Pending | 4.5.1 |
| 25 | Replace inline owner resolution in `create_bot_session()` with `await resolve_user(bot_id)` | Pending | 4.5.5 |
| 26 | Delete owner resolution block in `BotLifecycleService.on_bot_connected()` entirely | Pending | 4.5.5 |
| 27 | Delete `_setup_session()` and update `link_bot` route to use `state.bot_lifecycle_service.create_bot_session()` | Pending | 4.5.1 |
| 28 | Update `get_configuration_schema()`: generalize api_key_source oneOf patch for all settings types | Pending | 4.5.3 |
| 29 | Update `get_configuration_schema()`: patch `reasoning_effort` in `ChatCompletionProviderSettings` only | Pending | 4.5.3 |
| 30 | Update `get_bot_defaults()` and default config builders in `bot_management.py` for new types and defaults | Pending | 4.5.3 |
| 31 | Simplify `ActionItemExtractor.extract()` signature; remove dead params; use `create_model_provider` | Pending | 4.5.4 |
| 32 | Replace recorder setup block in `extractor.py` to use `resolve_model_config()`; remove duplicate `__init__` | Pending | 4.5.4 |
| 33 | Remove `owner_user_id` from `GroupTracker.update_jobs()` and `run_tracking_cycle()`; purge from cron args | Pending | 4.5.4 |
| 34 | Remove `token_consumption_collection` from `GroupTracker`, `GroupTrackingRunner`, and `main.py` | Pending | 4.5.4 |
| 35 | Add `image_moderation` to `bot_ui.py` full_settings in creation path | Pending | 4.5.3 |
| 36 | Add `BaseModelProviderConfig` and `BaseModelProviderSettings` JS classes in `frontend/src/configModels.js` | Pending | 4.4, 4.5.3 |
| 37 | Update `LLMConfigurations` constructor and `validate()` to route `image_moderation` to `BaseModelProviderConfig` | Pending | 4.4, 4.5.3 |
| 38 | Sweep unit/integration tests for `AutomaticBotReplyService`, `FakeLlmProvider`, and factory patches | Pending | 4.5.1, 4.5.3 |
| 39 | Create database migration script (assign owners, strip chat fields, update `provider_name`) | Pending | 4.6 |

---

## Detailed Implementation Tasks

### Task 1: Add `inspect.isabstract()` filter to `find_provider_class`
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** Update `utils/provider_utils.py` so that `find_provider_class` skips abstract classes via `inspect.isabstract(obj)`. This prevents the factory from attempting to instantiate `ChatCompletionProvider` or `ImageModerationProvider` (abstract intermediate classes) at runtime. Do this **first** before creating new provider classes.

---

### Task 2: Add centralized `ConfigTier` type alias in `config_models.py`
- **Status:** Pending
- **Spec Section:** 2.1
- **Description:** Add `ConfigTier = Literal["high", "low", "image_moderation"]` in `config_models.py`. All locations that currently define `config_tier: Literal["high", "low"]` inline must eventually import and use this alias.

---

### Task 3: Add `BaseModelProviderSettings` and `BaseModelProviderConfig` in `config_models.py`
- **Status:** Pending
- **Spec Section:** 2.2
- **Description:** Define `BaseModelProviderSettings` with `api_key_source`, `api_key`, `model` only (no `extra = 'allow'`). Define `BaseModelProviderConfig` with `provider_name` and `provider_config: BaseModelProviderSettings`.

---

### Task 4: Add `ChatCompletionProviderSettings` and `ChatCompletionProviderConfig` in `config_models.py`
- **Status:** Pending
- **Spec Section:** 2.3
- **Description:** Define `ChatCompletionProviderSettings(BaseModelProviderSettings)` adding `temperature`, `reasoning_effort`, `seed`, `record_llm_interactions`. Define `ChatCompletionProviderConfig(BaseModelProviderConfig)` with `provider_config: ChatCompletionProviderSettings`. Neither includes `extra = 'allow'`.

---

### Task 5: Update `LLMConfigurations.image_moderation` type to `BaseModelProviderConfig`
- **Status:** Pending
- **Spec Section:** 2.4
- **Description:** Update `LLMConfigurations` so that `high` and `low` use `ChatCompletionProviderConfig` and `image_moderation` uses `BaseModelProviderConfig`. Retain `llm_configs` field name and `LLMConfigurations` class name (deferred rename per Section 1).

---

### Task 6: Rename `DefaultConfigurations` attributes and env vars from `llm_` to `model_` prefix
- **Status:** Pending
- **Spec Section:** 2.5
- **Description:** Replace `llm_provider_name` with `model_provider_name_chat` (env: `DEFAULT_MODEL_PROVIDER_CHAT`, default `"openAi"`) and `model_provider_name_moderation` (env: `DEFAULT_MODEL_PROVIDER_MODERATION`, default `"openAiModeration"`). Rename `llm_model_high`→`model_high`, `llm_model_low`→`model_low`, `llm_model_image_moderation`→`model_image_moderation`, `llm_api_key_source`→`model_api_key_source`, `llm_temperature`→`model_temperature`, `llm_reasoning_effort`→`model_reasoning_effort`. **Delete** `llm_provider_name` entirely (do not merely rename) for self-enforcing refactor.

---

### Task 7: Rename `llm_providers` directory to `model_providers`
- **Status:** Pending
- **Spec Section:** 3
- **Description:** Rename the package `llm_providers` to `model_providers`. Continue as implicit namespace package (no `__init__.py` required).

---

### Task 8: Refactor `base.py` to `BaseModelProvider` (drop `user_id`, add `_resolve_api_key`)
- **Status:** Pending
- **Spec Section:** 3.1
- **Description:** Convert `BaseLlmProvider` to `BaseModelProvider`: accept only `config: BaseModelProviderConfig`, remove `user_id` from constructor, remove abstract `get_llm()`, add `_resolve_api_key()` utility that handles `api_key_source` ("environment" vs "explicit").

---

### Task 9: Create `model_providers/chat_completion.py` with `ChatCompletionProvider` abstract class
- **Status:** Pending
- **Spec Section:** 3.2
- **Description:** Create new file `model_providers/chat_completion.py` defining `ChatCompletionProvider(BaseModelProvider)` with abstract method `get_llm() -> BaseChatModel`. Establishes the Langchain integration contract for chat completion providers.

---

### Task 10: Create `model_providers/image_moderation.py` with `ModerationResult` and `ImageModerationProvider`
- **Status:** Pending
- **Spec Section:** 3.3
- **Description:** Create new file `model_providers/image_moderation.py` defining:
  - `ModerationResult` Pydantic model (`flagged`, `categories`, `category_scores`)
  - `ImageModerationProvider(BaseModelProvider)` abstract class with `async def moderate_image(self, image_url: str) -> ModerationResult`

---

### Task 11: Refactor `openAi.py` to `OpenAiChatProvider` (inherit `ChatCompletionProvider`, consolidate httpx blocks)
- **Status:** Pending
- **Spec Section:** 3.4
- **Description:** Rename `OpenAiLlmProvider` to `OpenAiChatProvider`, inherit from `ChatCompletionProvider`. Remove `user_id` from `__init__`. Use inherited `_resolve_api_key()`. Consolidate duplicate httpx logger setup (lines 52–59 and 68–74) into a single block. Switch config type to `ChatCompletionProviderConfig`.

---

### Task 12: Create `model_providers/openAiModeration.py` with `OpenAiModerationProvider`
- **Status:** Pending
- **Spec Section:** 3.5
- **Description:** Create new file `model_providers/openAiModeration.py`. Implement `OpenAiModerationProvider(ImageModerationProvider)`. Use `AsyncOpenAI` SDK, call `client.moderations.create(model=self.config.provider_config.model, input=...)`. Use inherited `_resolve_api_key()`. Map SDK response to `ModerationResult`. **CRITICAL:** Pass `model` explicitly to avoid SDK falling back to text-only model. Provider name for configs must be `"openAiModeration"`.

---

### Task 13: Fix `FakeLlmProvider` (drop `user_id`, add missing imports, update response formatting)
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** In `model_providers/fakeLlm.py`: remove `user_id` from constructor and `super().__init__()`. Remove `self.user_id` usage in `resp.format(user_id=self.user_id)` (use non-user-dependent response). Add missing `from typing import Optional, List, Any`. Inherit from `ChatCompletionProvider` and use `ChatCompletionProviderConfig`.

---

### Task 14: Create `services/resolver.py` with `resolve_user()` and `resolve_model_config()`
- **Status:** Pending
- **Spec Section:** 4.3
- **Description:** Create `services/resolver.py`:
  - `async def resolve_user(bot_id: str) -> str`: query `credentials_collection` for `owned_bots` containing `bot_id`, return `user_id`; raise `ValueError` if none.
  - `async def resolve_model_config(bot_id: str, config_tier: ConfigTier) -> BaseModelProviderConfig`: query configurations for `llm_configs.{config_tier}`, parse with `BaseModelProviderConfig` for `image_moderation` else `ChatCompletionProviderConfig`; use overloads for return type. Use `get_global_state()` for DB access.

---

### Task 15: Rename `llm_factory.py` to `model_factory.py` and implement async `create_model_provider()`
- **Status:** Pending
- **Spec Section:** 4.2
- **Description:** Rename `services/llm_factory.py` to `services/model_factory.py`. New signature: `async def create_model_provider(bot_id: str, feature_name: str, config_tier: ConfigTier) -> Union[BaseChatModel, ImageModerationProvider]`. Use `await resolve_user(bot_id)` and `await resolve_model_config(bot_id, config_tier)`. Obtain `token_consumption_collection` via `get_global_state().token_consumption_collection`. Remove `find_provider_class` local definition; import from `utils.provider_utils`. Load module via `importlib.import_module(f"model_providers.{provider_name}")`.

---

### Task 16: Update `TokenTrackingCallback` and factory polymorphic branching (skip tracker for image_moderation)
- **Status:** Pending
- **Spec Section:** 4.1, 4.2
- **Description:** In factory: after instantiating provider, branch with `isinstance`:
  - If `ChatCompletionProvider`: call `provider.get_llm()`, attach `TokenTrackingCallback`, return `BaseChatModel`.
  - If `ImageModerationProvider`: skip tracker, return `provider` directly.
  - Expand `TokenTrackingCallback.__init__` `config_tier` to use `ConfigTier` (add `image_moderation` for type safety; tracker is never attached for that tier).

---

### Task 17: Expand `ConfigTier` in `token_consumption_service.py`, `quota_service.py`, `tracked_llm.py`
- **Status:** Pending
- **Spec Section:** 4.5.2
- **Description:** Replace `Literal["high", "low"]` with imported `ConfigTier` in:
  - `TokenConsumptionService.record_event` (`config_tier`)
  - `QuotaService.calculate_cost` (`config_tier`)
  - `TokenTrackingCallback.__init__` (`config_tier`)

---

### Task 18: Update factory: remove local `find_provider_class`, import from `utils.provider_utils`
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** In `services/model_factory.py`, remove the local `find_provider_class` definition (lines 14–20) and `from utils.provider_utils import find_provider_class`. Update `find_provider_class` call to use `BaseModelProvider` (or appropriate base) for discovery — factory will need to resolve the correct base per tier (e.g. `ChatCompletionProvider` for high/low, `ImageModerationProvider` for image_moderation) or use a shared base. Per spec, provider class resolution is driven by `provider_name`; `find_provider_class` should accept the base that matches the tier (see Section 4.2 note on Resolution vs Dispatch).

---

### Task 19: Update imports in `features/automatic_bot_reply/service.py`
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** Replace `from llm_providers.base import BaseLlmProvider` with `from model_providers.base import BaseModelProvider`. Replace `from services.llm_factory import create_tracked_llm` with `from services.model_factory import create_model_provider`. Remove unused `from utils.provider_utils import find_provider_class`.

---

### Task 20: Update imports in `features/periodic_group_tracking/extractor.py`
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** Replace `from llm_providers.base import BaseLlmProvider` with `from model_providers.base import BaseModelProvider`. Replace `from config_models import LLMProviderConfig` with `ChatCompletionProviderConfig`. Replace `from services.llm_factory import create_tracked_llm` with `from services.model_factory import create_model_provider`. Replace `from llm_providers.recorder import LLMRecorder` with `from model_providers.recorder import LLMRecorder`.

---

### Task 21: Update imports in `routers/bot_management.py` and `routers/bot_ui.py`
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** In both routers: add `ChatCompletionProviderConfig`, `ChatCompletionProviderSettings`, `BaseModelProviderConfig`, `BaseModelProviderSettings` to imports. Update all `LLMProviderConfig`/`LLMProviderSettings` usages for high/low to `ChatCompletionProviderConfig`/`ChatCompletionProviderSettings`, and for image_moderation to `BaseModelProviderConfig`/`BaseModelProviderSettings`. Use `DefaultConfigurations.model_provider_name_chat` for high/low and `DefaultConfigurations.model_provider_name_moderation` for image_moderation.

---

### Task 22: Update imports in `tests/services/test_token_services.py` and `tests/integration/test_token_flow_component.py`
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** Replace `from services.llm_factory import create_tracked_llm` with `from services.model_factory import create_model_provider`. Replace `LLMProviderConfig`, `LLMProviderSettings` with `ChatCompletionProviderConfig`, `ChatCompletionProviderSettings`. Update `@patch('services.llm_factory.find_provider_class')` to `@patch('services.model_factory.find_provider_class')` (or patch at import site). Update any assertions against `fakeLlm` output that referenced `user_id`.

---

### Task 23: Refactor `AutomaticBotReplyService`: remove sync `_initialize_llm()` from `__init__`, make it async
- **Status:** Pending
- **Spec Section:** 4.5.1
- **Description:** Remove the `self._initialize_llm()` call from `AutomaticBotReplyService.__init__`. Change `def _initialize_llm(self)` to `async def _initialize_llm(self)`. Update implementation to use `await create_model_provider(self.bot_id, "automatic_bot_reply", "high")` instead of `create_tracked_llm(...)`. Remove `token_consumption_collection` and manual config/user passing.

---

### Task 24: Update `BotLifecycleService.create_bot_session()`: call `await bot_service._initialize_llm()` after construction
- **Status:** Pending
- **Spec Section:** 4.5.1
- **Description:** After constructing `AutomaticBotReplyService(instance)`, add `await bot_service._initialize_llm()` before `instance.register_message_handler(bot_service.handle_message)`.

---

### Task 25: Replace inline owner resolution in `create_bot_session()` with `await resolve_user(bot_id)`
- **Status:** Pending
- **Spec Section:** 4.5.5
- **Description:** In `BotLifecycleService.create_bot_session()`, replace the inline `credentials_collection.find_one({"owned_bots": config.bot_id})` block with `owner_user_id = await resolve_user(config.bot_id)`. Note: `resolve_user` raises `ValueError` when no owner; previously the code returned `None` — this stricter behavior is intended per spec.

---

### Task 26: Delete owner resolution block in `BotLifecycleService.on_bot_connected()` entirely
- **Status:** Pending
- **Spec Section:** 4.5.5
- **Description:** Delete the block at lines 69–77 that resolves `owner_user_id` from credentials. After cron state purge (Task 33), this value has no consumer. Do not refactor — delete outright.

---

### Task 27: Delete `_setup_session()` and update `link_bot` route to use `create_bot_session()`
- **Status:** Pending
- **Spec Section:** 4.5.1
- **Description:** Delete the private `_setup_session()` function from `routers/bot_management.py`. In the `link_bot` route (line 751), replace `instance = await _setup_session(config, state)` with `instance = await state.bot_lifecycle_service.create_bot_session(config)`. Ensures single code path for bot session creation.

---

### Task 28: Update `get_configuration_schema()`: generalize api_key_source oneOf patch for all settings types
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** In `routers/bot_management.py` `get_configuration_schema()`, replace the hardcoded `'LLMProviderSettings'` oneOf patch with a loop: iterate over all `schema[defs_key]` entries whose `properties` contain both `api_key_source` and `api_key`; apply the oneOf conditional visibility patch to each. Covers `ChatCompletionProviderSettings` and `BaseModelProviderSettings` automatically.

---

### Task 29: Update `get_configuration_schema()`: patch `reasoning_effort` in `ChatCompletionProviderSettings` only
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** Update the `reasoning_effort` titles patch to target `'ChatCompletionProviderSettings'` instead of `'LLMProviderSettings'`. `BaseModelProviderSettings` has no `reasoning_effort` field.

---

### Task 30: Update `get_bot_defaults()` and default config builders in `bot_management.py` for new types and defaults
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** In `get_bot_defaults()`: for high/low tiers use `ChatCompletionProviderConfig`/`ChatCompletionProviderSettings` with `model_provider_name_chat`; for image_moderation use `BaseModelProviderConfig`/`BaseModelProviderSettings` with `model_provider_name_moderation` — strip `temperature`, `reasoning_effort`, `record_llm_interactions`. Update all `DefaultConfigurations.llm_*` references to `model_*` equivalents. Apply same changes to any other default config builder functions in this file.

---

### Task 31: Simplify `ActionItemExtractor.extract()` signature; remove dead params; use `create_model_provider`
- **Status:** Pending
- **Spec Section:** 4.5.4
- **Description:** New signature: `async def extract(self, messages, bot_id, timezone, group_id="", language_code="en")`. Remove `llm_config`, `user_id`, `llm_config_high`, `token_consumption_collection`. Replace factory calls with `llm = await create_model_provider(bot_id, "periodic_group_tracking", "low")` and `high_llm = await create_model_provider(bot_id, "periodic_group_tracking", "high")`. Remove `if llm_config_high:` check; unconditionally execute Phase 2; catch resolution exception and degrade to Phase 1 results.

---

### Task 32: Replace recorder setup block in `extractor.py` to use `resolve_model_config()`; remove duplicate `__init__`
- **Status:** Pending
- **Spec Section:** 4.5.4
- **Description:** Replace the recorder setup block (lines 103–122) with config from `await resolve_model_config(bot_id, "low")` for `record_enabled`, `config_dict`, `provider_name`. Remove the duplicate `def __init__(self): pass` definitions (retain one).

---

### Task 33: Remove `owner_user_id` from `GroupTracker.update_jobs()` and `run_tracking_cycle()`; purge from cron args
- **Status:** Pending
- **Spec Section:** 4.5.4
- **Description:** Remove `owner_user_id` parameter from `GroupTracker.update_jobs()` and `GroupTrackingRunner.run_tracking_cycle()`. Remove it from the APScheduler `args` payload in `add_job` calls. Update `track_group_context` signature to drop `owner_user_id`. Factory resolves owner at execution time.

---

### Task 34: Remove `token_consumption_collection` from `GroupTracker`, `GroupTrackingRunner`, and `main.py`
- **Status:** Pending
- **Spec Section:** 4.5.4
- **Description:** Remove `token_consumption_collection` from `GroupTracker.__init__`, `GroupTrackingRunner.__init__`, and the `GroupTracker(...)` construction call in `main.py`. Factory obtains it via `get_global_state().token_consumption_collection` internally.

---

### Task 35: Add `image_moderation` to `bot_ui.py` full_settings in creation path
- **Status:** Pending
- **Spec Section:** 4.5.3
- **Description:** In `routers/bot_ui.py` PATCH creation path, add `image_moderation=BaseModelProviderConfig(provider_name=DefaultConfigurations.model_provider_name_moderation, provider_config=BaseModelProviderSettings(model=DefaultConfigurations.model_image_moderation, api_key_source=DefaultConfigurations.model_api_key_source))` to the `LLMConfigurations` passed to `full_settings`. Required because `LLMConfigurations.image_moderation` is non-optional (`Field(...)`).

---

### Task 36: Add `BaseModelProviderConfig` and `BaseModelProviderSettings` JS classes in `frontend/src/configModels.js`
- **Status:** Pending
- **Spec Section:** 4.4, 4.5.3
- **Description:** Create `BaseModelProviderSettings` JS class with only `api_key_source`, `api_key`, `model` (and `provider_name` at config level). Create `BaseModelProviderConfig` that wraps `BaseModelProviderSettings`. Implement `validate()` for each that checks only these fields — **not** `temperature`, `record_llm_interactions`, or other chat-specific fields.

---

### Task 37: Update `LLMConfigurations` constructor and `validate()` to route `image_moderation` to `BaseModelProviderConfig`
- **Status:** Pending
- **Spec Section:** 4.4, 4.5.3
- **Description:** In `LLMConfigurations` constructor: use `BaseModelProviderConfig` for `image_moderation`, keep `LLMProviderConfig` for `high`/`low`. In `LLMConfigurations.validate()`: route `image_moderation` to `BaseModelProviderConfig.validate()` instead of `LLMProviderConfig.validate()`. **CRITICAL:** Prevents `ValidationError` when stripped backend configs (no `temperature`, etc.) reach the UI.

---

### Task 38: Sweep unit/integration tests for `AutomaticBotReplyService`, `FakeLlmProvider`, and factory patches
- **Status:** Pending
- **Spec Section:** 4.5.1, 4.5.3
- **Description:** In `tests/features/test_automatic_bot_reply.py` (and any similar): patch tests that instantiate `AutomaticBotReplyService` to `await bot_service._initialize_llm()` immediately after construction. Update `tests/integration/test_token_flow_component.py` and `tests/services/test_token_services.py` for new factory signature, config types, and `FakeLlmProvider` output (no `user_id` in response).

---

### Task 39: Create database migration script (assign owners, strip chat fields, update `provider_name`)
- **Status:** Pending
- **Spec Section:** 4.6
- **Description:** Create migration script that:
  1. Assigns a designated "system" or "admin" owner ID to any bot without an assigned owner.
  2. Strips `temperature`, `seed`, `reasoning_effort`, `record_llm_interactions` from existing `image_moderation` entries.
  3. Updates `provider_name` in `image_moderation` entries from `"openAi"` to `"openAiModeration"`.
  4. Strips stray fields from `high` and `low` tier entries if any exist.
