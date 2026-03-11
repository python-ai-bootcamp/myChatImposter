# Image Moderation Provider Separation - Implementation Tasks (Cursor Codex 5.3)

## Task Summary Table

| ID | Task | Spec Sections | Status |
|---|---|---|---|
| T01 | Add centralized `ConfigTier` alias and split provider config models in `config_models.py` | 2.1, 2.2, 2.3, 2.4 | Pending |
| T02 | Rename `DefaultConfigurations` model-related attributes and env vars to `model_*` + split provider defaults | 2.5 | Pending |
| T03 | Update `utils/provider_utils.find_provider_class` to skip abstract classes | 4.5.3 | Pending |
| T04 | Rename package `llm_providers/` to `model_providers/` and migrate modules | 3, 4.5.3 | Pending |
| T05 | Refactor provider base hierarchy (`BaseModelProvider`, `ChatCompletionProvider`, `ImageModerationProvider`, `ModerationResult`) | 3.1, 3.2, 3.3 | Pending |
| T06 | Refactor OpenAI chat provider (`openAi.py`) to `OpenAiChatProvider` with no `user_id` and deduplicated httpx logging | 3.4 | Pending |
| T07 | Add `OpenAiModerationProvider` using `AsyncOpenAI.moderations.create` with explicit model parameter | 3.5 | Pending |
| T08 | Fix `fakeLlm` compatibility with removed `user_id` and missing typing imports | 3.1, 4.5.3 warning | Pending |
| T09 | Create `services/resolver.py` (`resolve_user`, tier-aware `resolve_model_config`) | 4.3 | Pending |
| T10 | Replace `services/llm_factory.py` with async `services/model_factory.py:create_model_provider(...)` | 4.2 | Pending |
| T11 | Implement factory polymorphic behavior: attach token tracking only for chat tiers, return moderation provider for image tier | 4.1, 4.2 | Pending |
| T12 | Expand `config_tier` typing usages to centralized `ConfigTier` in token/quota/tracker services | 2.1, 4.5.2 | Pending |
| T13 | Refactor `AutomaticBotReplyService` async initialization flow and update lifecycle call site | 4.5.1 | Pending |
| T14 | Remove duplicate `_setup_session()` path in `routers/bot_management.py` and route link flow through `BotLifecycleService.create_bot_session()` | 4.5.1 note | Pending |
| T15 | Refactor periodic group tracking async cascade (`extractor.py`, `runner.py`, `service.py`, `main.py`) to use async model factory and remove dead parameters | 4.5.4 | Pending |
| T16 | Purge `owner_user_id` from cron scheduling payload/signatures in group tracking flow | 4.5.4 note | Pending |
| T17 | Apply owner-resolution cleanup in `bot_lifecycle_service.py` (`on_bot_connected` delete block, `create_bot_session` use `resolve_user`) | 4.5.5 | Pending |
| T18 | Update backend default builders and imports in `routers/bot_management.py` and `routers/bot_ui.py` for split chat/moderation config types | 4.5.3, 4.4 | Pending |
| T19 | Update backend schema patching logic for both provider settings types (`api_key` conditional + `reasoning_effort` targeting) | 4.5.3, 4.4 | Pending |
| T20 | Add frontend base model provider validation path for `image_moderation` (`frontend/src/configModels.js`) | 4.4, 4.5.3 | Pending |
| T21 | Add image moderation provider consumption path in media processing flow (or equivalent moderation entrypoint) via `create_model_provider(..., "image_moderation")` | 1, 4.2 example | Pending |
| T22 | Create DB migration script: assign owners, normalize moderation provider name, strip chat-only/stray fields | 4.6, 2.2 note, 2.3 note, 3.5 | Pending |
| T23 | Update and run tests impacted by factory/package/config refactor (unit + integration + feature tests) | 4.5.1, 4.5.3 warning, 4.5.4 | Pending |

## Flat Implementation Task List

1. **[Pending] T01 - Introduce split model provider configuration types in `config_models.py`**  
   Implement `ConfigTier = Literal["high", "low", "image_moderation"]`, add `BaseModelProviderSettings/BaseModelProviderConfig`, add `ChatCompletionProviderSettings/ChatCompletionProviderConfig`, and change `LLMConfigurations.image_moderation` to `BaseModelProviderConfig` while keeping `llm_configs`/`LLMConfigurations` names unchanged.

2. **[Pending] T02 - Rename model defaults in `DefaultConfigurations` and env mappings**  
   Replace `llm_*` model default attributes with `model_*`, split chat vs moderation provider defaults (`model_provider_name_chat`, `model_provider_name_moderation`), and delete old `llm_provider_name` to enforce call-site updates.

3. **[Pending] T03 - Harden provider class discovery before adding abstract intermediates**  
   Update `utils/provider_utils.find_provider_class` to ignore abstract classes (`inspect.isabstract`) so abstract intermediary providers are not selected during dynamic loading.

4. **[Pending] T04 - Rename provider package from `llm_providers` to `model_providers`**  
   Move provider modules (`base`, `openAi`, `fakeLlm`, `recorder`) under `model_providers/` and update imports/code paths accordingly.

5. **[Pending] T05 - Implement new provider hierarchy primitives**  
   Replace `BaseLlmProvider` with non-abstract-operation `BaseModelProvider(config only)` and shared `_resolve_api_key()`, then add `chat_completion.py` and `image_moderation.py` with `ChatCompletionProvider`, `ImageModerationProvider`, and `ModerationResult`.

6. **[Pending] T06 - Refactor OpenAI chat provider to new hierarchy**  
   Rename `OpenAiLlmProvider` to `OpenAiChatProvider`, remove `user_id` from constructor/super call, consume `ChatCompletionProviderConfig`, and consolidate duplicate httpx logger setup blocks.

7. **[Pending] T07 - Implement dedicated moderation provider module**  
   Add `model_providers/openAiModeration.py` with `OpenAiModerationProvider` implementing `moderate_image(image_url)` using `AsyncOpenAI.moderations.create`, explicitly passing `model=self.config.provider_config.model`.

8. **[Pending] T08 - Repair fake provider for post-`user_id` architecture**  
   Update `model_providers/fakeLlm.py` to stop referencing `self.user_id`, import missing typing symbols (`Optional`, `List`, `Any`), and keep test fake responses compatible with new constructor contract.

9. **[Pending] T09 - Create centralized resolver service**  
   Add `services/resolver.py` with async `resolve_user(bot_id)` and overloaded `resolve_model_config(bot_id, config_tier)` returning chat vs moderation config models.

10. **[Pending] T10 - Replace old factory with async model factory**  
    Rename/create `services/model_factory.py` and implement async `create_model_provider(bot_id, feature_name, config_tier)` that resolves user/config internally and no longer accepts raw config/user/collection params from callers.

11. **[Pending] T11 - Implement factory polymorphism and tracking policy**  
    In `create_model_provider`, dynamically load module by `provider_name`, branch by provider interface (`ChatCompletionProvider` vs `ImageModerationProvider`), attach `TokenTrackingCallback` only for high/low chat tiers, and skip tracking for image moderation.

12. **[Pending] T12 - Centralize `config_tier` typing usage**  
    Replace inline `Literal["high","low"]` with imported `ConfigTier` in `services/token_consumption_service.py`, `services/quota_service.py`, and `services/tracked_llm.py`.

13. **[Pending] T13 - Refactor automatic reply async initialization cascade**  
    Remove synchronous `_initialize_llm()` call from `AutomaticBotReplyService.__init__`, make `_initialize_llm` async with `await create_model_provider(...)`, and invoke it explicitly from `BotLifecycleService.create_bot_session()`.

14. **[Pending] T14 - Remove duplicated session setup path in bot router**  
    Delete private `_setup_session()` in `routers/bot_management.py` and update `link_bot` to call `await state.bot_lifecycle_service.create_bot_session(config)` so there is one lifecycle path.

15. **[Pending] T15 - Refactor periodic tracking extraction/runner/service/main to async model factory**  
    Simplify `ActionItemExtractor.extract()` signature (remove dead params), replace low/high model construction with awaited factory calls, remove duplicate `__init__`, remove `token_consumption_collection` parameter threading from `GroupTrackingRunner`, `GroupTracker`, and `main.py` constructor call.

16. **[Pending] T16 - Purge `owner_user_id` from cron job scheduling contract**  
    Remove `owner_user_id` from `GroupTracker.update_jobs`, APScheduler `args`, `track_group_context`, and `GroupTrackingRunner.run_tracking_cycle`; owner resolution must happen at execution time through resolvers/factory.

17. **[Pending] T17 - Apply bot lifecycle owner-resolution cleanup**  
    Delete owner lookup block in `on_bot_connected()` (no longer consumed) and replace `create_bot_session()` inline owner query with `await resolve_user(bot_id)` for strict ownership enforcement.

18. **[Pending] T18 - Update backend config defaults/imports for split provider types**  
    In `routers/bot_management.py` and `routers/bot_ui.py`, replace `LLMProvider*` usage with chat/base model provider configs per tier, update default provider-name references to chat/moderation split, and ensure `image_moderation` is always populated in UI-created defaults.

19. **[Pending] T19 - Generalize backend JSON schema patching for provider settings**  
    In `get_configuration_schema()`, replace hardcoded `LLMProviderSettings` patching with a generic pass for all settings types that include `api_key_source` + `api_key`; apply `reasoning_effort` patch only to `ChatCompletionProviderSettings`.

20. **[Pending] T20 - Update frontend validation model for moderation tier**  
    In `frontend/src/configModels.js`, add `BaseModelProviderSettings/BaseModelProviderConfig` validation classes and route `LLMConfigurations.image_moderation` constructor + validation through them (chat-only fields must not be required there).

21. **[Pending] T21 - Integrate image moderation tier usage into media processing path**  
    Introduce/adjust media moderation flow to call `await create_model_provider(bot_id, "media_processing", "image_moderation")`, assert moderation provider type, and consume normalized `ModerationResult`.

22. **[Pending] T22 - Implement database migration for ownership and model config hygiene**  
    Create migration script to assign ownerless bots, update `image_moderation.provider_name` to `openAiModeration`, strip chat-only fields from `image_moderation`, and strip stray fields from `high`/`low`.

23. **[Pending] T23 - Update and execute refactor test sweep**  
    Update test imports/usages for new package/factory/config names (`tests/services/test_token_services.py`, `tests/integration/test_token_flow_component.py`, and auto-reply/periodic-group-tracking tests), adjust fake provider expectation changes, and run targeted suites to validate behavior.
