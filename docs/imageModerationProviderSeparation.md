# Specification: Image Moderation Provider Separation

## 1. Overview
The current LLM Provider architecture forces all models, including specialized ones like `omni-moderation-latest`, to conform to the standard OpenAI Chat Completion interface. This causes issues because the Moderation API:
1. Does not utilize Langchain's chat interface (it requires direct SDK calls to `client.moderations.create`).
2. Does not accept chat-specific configuration parameters (like `temperature`, `reasoning_effort`, `seed`, `record_llm_interactions`).
3. Does not report tokens in the standard `metadata_usage` fashion.

To resolve this, the provider hierarchy and its corresponding configurations will be restructured. This will cleanly separate base API functionality from generative Chat Completion functionality. Furthermore, tracking this change, we will update our nomenclature from "LLM Provider" to "Model Provider" to more accurately reflect that not all tracked models are Large Language Models (e.g., Image Moderation models).

> **Note — Deferred Rename**: While the internal class hierarchy and factory are being renamed to use "Model Provider" terminology, the existing `llm_configs` field name in `BotGeneralSettings` and the `LLMConfigurations` class name will **NOT** be renamed as part of this spec. The blast radius of that rename (27+ code references, database migration, API payload changes, frontend state updates, schema introspection rewrites) is too large for a purely nomenclature change with zero functional benefit. This rename is deferred to a future task.

## 2. Configuration Restructuring (`config_models.py`)

The existing `LLMProviderSettings` encapsulates both base API credentials and chat-specific settings. This will be split.

### 2.1 Centralized Type Alias
A centralized `Literal` type alias will be defined in `config_models.py` to avoid duplicating the tier definition across multiple files:
```python
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field

ConfigTier = Literal["high", "low", "image_moderation"]
```

All locations that currently define `config_tier: Literal["high", "low"]` inline (see Section 4.5.2) **must** import and use this `ConfigTier` alias instead.

### 2.2 Base Configuration
```python
class BaseModelProviderSettings(BaseModel):
    api_key_source: Literal["environment", "explicit"] = Field(default="environment", title="API Key Source")
    api_key: Optional[str] = Field(default=None, title="API Key")
    model: str

class BaseModelProviderConfig(BaseModel):
    provider_name: str
    provider_config: BaseModelProviderSettings
```

> **Note**: `BaseModelProviderSettings` does **not** include `extra = 'allow'`. A database migration script (see Section 4.6) will strip chat-specific fields from existing `image_moderation` entries, making backward-compatibility padding unnecessary.

### 2.3 Chat Completion Configuration
```python
class ChatCompletionProviderSettings(BaseModelProviderSettings):
    temperature: float = 0.7
    reasoning_effort: Optional[Literal["low", "medium", "high", "minimal"]] = None
    seed: Optional[int] = Field(default=None, title="Seed")
    record_llm_interactions: bool = Field(default=False, title="Record Traffic")
    
class ChatCompletionProviderConfig(BaseModelProviderConfig):
    provider_config: ChatCompletionProviderSettings
```

> **Note — Inheritance**: `ChatCompletionProviderConfig` inherits from `BaseModelProviderConfig`, overriding `provider_config` to `ChatCompletionProviderSettings`. This provides Liskov substitutability — the factory and resolver can uniformly accept `BaseModelProviderConfig` without `Union` handling for the input config types. Pydantic v2 correctly handles the field type override since `ChatCompletionProviderSettings` extends `BaseModelProviderSettings`.

> **Note — `extra = 'allow'`**: Neither `BaseModelProviderSettings` nor `ChatCompletionProviderSettings` include `Config.extra = 'allow'`. The existing `LLMProviderSettings` has this setting, but it is intentionally dropped. The database migration script (Section 4.6) will strip any stray fields from `high`, `low`, and `image_moderation` entries to ensure clean deserialization.

> **Note — Field Name**: The field name remains `record_llm_interactions` (not `record_model_interactions`). Since this field lives exclusively in `ChatCompletionProviderSettings` and exclusively tracks LLM chat completion interactions, the "LLM" semantics are accurate. Renaming it would trigger a blast radius across the codebase, database documents, and the `LLMRecorder` class with zero functional benefit.

### 2.4 Updating `LLMConfigurations` Internal Types
The `LLMConfigurations` class (and the `llm_configs` field name in `BotGeneralSettings`) will **retain their current names** (see Deferred Rename note in Section 1). However, the `image_moderation` field's **type** will be updated from `LLMProviderConfig` to `BaseModelProviderConfig`:

```python
class LLMConfigurations(BaseModel):
    high: ChatCompletionProviderConfig = Field(..., title="High Performance Model")
    low: ChatCompletionProviderConfig = Field(..., title="Low Cost Model")
    image_moderation: BaseModelProviderConfig = Field(..., title="Media Moderation Model")
```

### 2.5 `DefaultConfigurations` Attribute Rename
The `DefaultConfigurations` class in `config_models.py` currently uses `llm_` prefixed attribute names (e.g., `llm_provider_name`, `llm_model_high`). These internal Python attributes will be renamed to use `model_` prefix for consistency:
- `llm_provider_name` → **split into two**:
  - `model_provider_name_chat` (default: `"openAi"`) — used for `high` and `low` tiers
  - `model_provider_name_moderation` (default: `"openAiModeration"`) — used for `image_moderation` tier
- `llm_model_high` → `model_high`
- `llm_model_low` → `model_low`
- `llm_model_image_moderation` → `model_image_moderation`
- `llm_api_key_source` → `model_api_key_source`
- `llm_temperature` → `model_temperature`
- `llm_reasoning_effort` → `model_reasoning_effort`

> **Note — Provider Name Divergence**: A single `model_provider_name` default can no longer serve all tiers because `image_moderation` requires `provider_name: "openAiModeration"` (Section 3.5) while `high`/`low` use `"openAi"`. The default configuration builder must use the appropriate default when constructing each tier's config.

> **Note**: The underlying **environment variable names** (`DEFAULT_LLM_PROVIDER`, `DEFAULT_LLM_MODEL_HIGH`, etc.) remain unchanged to avoid silent deployment fallback issues. Only the Python attribute names change.

## 3. Provider Architecture Refactor (`llm_providers/` → `model_providers/`)

The package `llm_providers` will be renamed to `model_providers` for consistency with the new class naming convention.

> **Note — Python Package**: The current `llm_providers/` directory works as an implicit namespace package (no `__init__.py`). The renamed `model_providers/` directory will continue to function as an implicit namespace package — `importlib.import_module("model_providers.openAi")` works correctly without an explicit `__init__.py` in Python 3.3+.

### 3.1 `base.py`
The `BaseLlmProvider` becomes `BaseModelProvider`, a pure base abstract class that only expects a `BaseModelProviderConfig`. It defines **no abstract methods** on its own — subclasses are free to expose whichever interface is appropriate for their use case via intermediate abstract classes (see Sections 3.2 and 3.3).

```python
from abc import ABC
from typing import Optional

class BaseModelProvider(ABC):
    def __init__(self, config: BaseModelProviderConfig):
        self.config = config

    def _resolve_api_key(self) -> Optional[str]:
        """Shared utility: resolves the API key based on api_key_source."""
        settings = self.config.provider_config
        if settings.api_key_source == "explicit":
            if not settings.api_key:
                raise ValueError("api_key_source is 'explicit' but no api_key provided.")
            return settings.api_key
        # "environment" — return None, letting the SDK fall back to OPENAI_API_KEY env var
        return None
```

> **Note — `user_id` Removal**: The current `BaseLlmProvider.__init__` accepts both `config` and `user_id`. The new `BaseModelProvider` drops `user_id` from its constructor entirely. The `user_id` is now resolved internally by the factory (Section 4.2) and used exclusively for the `TokenTrackingCallback`. Providers no longer need to know which user owns them.

> **Note — Shared API Key Resolution**: The `_resolve_api_key()` method centralizes the `api_key_source` logic ("environment" vs "explicit") that previously lived in `OpenAiLlmProvider._build_llm_params()`. Both `OpenAiChatProvider` and `OpenAiModerationProvider` inherit this method, eliminating code duplication.

### 3.2 `chat_completion.py` [NEW]
A new intermediate abstract class, `ChatCompletionProvider`, will inherit from `BaseModelProvider`. It defines `get_llm()` as its own abstract method, establishing the Langchain integration contract that all Chat Completion providers (like `OpenAiChatProvider`) must fulfill.
```python
from abc import abstractmethod
from langchain_core.language_models.chat_models import BaseChatModel

class ChatCompletionProvider(BaseModelProvider):
    @abstractmethod
    def get_llm(self) -> BaseChatModel:
        pass
```

### 3.3 `image_moderation.py` [NEW]

**`ModerationResult` Data Model**:
```python
from pydantic import BaseModel
from typing import Dict

class ModerationResult(BaseModel):
    """Normalized result from an image moderation API call."""
    flagged: bool
    categories: Dict[str, bool]
    category_scores: Dict[str, float]
```

> **Note**: This is a custom wrapper around the OpenAI SDK's `openai.types.ModerationCreateResponse`. The provider implementation is responsible for mapping the SDK response into this stable contract. This decouples consumers from the specific SDK type.

**`ImageModerationProvider` Abstract Class**:

A new intermediate abstract class, `ImageModerationProvider`, will inherit from `BaseModelProvider`. It defines `moderate_image()` as its own abstract method, mirroring the `ChatCompletionProvider` pattern and providing compile-time contract enforcement:
```python
from abc import abstractmethod

class ImageModerationProvider(BaseModelProvider):
    @abstractmethod
    async def moderate_image(self, image_url: str) -> ModerationResult:
        pass
```

This provides cleaner typing for the factory return type: `Union[BaseChatModel, ImageModerationProvider]`.

### 3.4 `openAi.py`
The existing `OpenAiLlmProvider` (rename to `OpenAiChatProvider`) will be updated to inherit from `ChatCompletionProvider`. It will utilize parameters like `temperature` and `seed` natively.

**Mandatory changes**:
- Update `__init__` to remove the `user_id` parameter from both its own signature and the `super().__init__()` call.
- Consolidate the **duplicate httpx logger setup blocks** (currently at lines 52-59 and 68-74) into a single setup during this refactoring.

### 3.5 `openAiModeration.py` [NEW]
A dedicated `OpenAiModerationProvider` will be created.
- Inherits from `ImageModerationProvider`.
- Implements `moderate_image(image_url: str) -> ModerationResult`.
- **Scope**: This provider handles **image moderation only**. While the underlying OpenAI Moderation API supports text inputs as well, text moderation is explicitly out of scope for this provider.
- Directly utilizes the `AsyncOpenAI` SDK to call the `moderations.create` API with an `image_url` input.
- **API Key Resolution**: Uses the inherited `self._resolve_api_key()` method (from `BaseModelProvider`, Section 3.1) to obtain the API key for `AsyncOpenAI(api_key=...)`. If `api_key_source` is `"environment"`, passes `None` to let the SDK fall back to the `OPENAI_API_KEY` environment variable.
- **Module-Provider Matching**: The `provider_name` in `image_moderation` database configs **must** be set to `"openAiModeration"` (matching this module's filename). This is what the factory's `importlib.import_module(f"model_providers.{provider_name}")` uses to locate the correct provider class. The migration script (Section 4.6) must update existing entries accordingly.

## 4. Downstream Impact

### 4.1 Token Tracking (`services/tracked_llm.py`)
Since moderation requests do not yield generative tokens, they will not be routed through the default LLM `TokenTrackingCallback`. 

**Architectural Flow:** The *Factory* (Section 4.2) is the sole arbiter of tracking logic. It determines whether to attach the `TokenTrackingCallback` based strictly on the configuration tier it resolves. The tracker itself does not need to inspect configurations; it simply wraps the models the factory tells it to wrap.

### 4.2 Factory Instantiation (`services/llm_factory.py` → `services/model_factory.py`)
The file `services/llm_factory.py` will be renamed to `services/model_factory.py` to align with the project-wide nomenclature change. Within it, the central factory method `create_tracked_llm()` will be renamed to the broader `create_model_provider(...)`.

Its signature will be radically simplified. Instead of requiring the caller to pass in the `llm_config`, `user_id`, and the database collection, the factory will infer these from the environment and database using the `bot_id`.

**New Signature**:
```python
async def create_model_provider(
    bot_id: str,
    feature_name: str,
    config_tier: ConfigTier
) -> Union[BaseChatModel, ImageModerationProvider]
```

**Behavior**:
- **Future Caching**: While the factory signature implies resolving configs and users from the DB on every invocation (introducing latency), this is a temporary architectural stage. A future `model_provider_cache` layer will be implemented to intercept these calls and yield already-instantiated clients.
- The factory will utilize the new centralized `services/resolver.py` to `await` the fetch of the `user_id` and the specific model provider config (based on the `config_tier`). Because these resolvers are async, **the factory itself must be asynchronous**.
- It will internally resolve the `token_consumption_collection` singleton using `get_global_state().token_consumption_collection` (from `dependencies.py`), avoiding explicit parameter passing. **Note**: `GlobalStateManager` is a true, thread-safe application-layout Singleton, making this fetching perfectly safe even for background workers like `APScheduler` without risk of context-loss.
- **For `ChatCompletionProviderConfig` (high/low)**: The factory will instantiate the corresponding chat provider, attach the `TokenTrackingCallback`, and return the Langchain `BaseChatModel`. 
- **For `BaseModelProviderConfig` (image_moderation)**: The factory will instantiate the underlying model provider (e.g., `OpenAiModerationProvider`), skip the Langchain token tracker, and return the `ImageModerationProvider` instance itself.

> **Note — Resolution vs. Dispatch**: The factory uses two independent mechanisms that should not be confused:
> 1. **Provider class resolution** is driven by `provider_name` — the factory calls `importlib.import_module(f"model_providers.{config.provider_name}")` to load the correct module, then `find_provider_class()` to discover the provider class within it. This is how `"openAi"` loads `OpenAiChatProvider` and `"openAiModeration"` loads `OpenAiModerationProvider`.
> 2. **Post-instantiation behavior** is driven by `config_tier` — it determines whether the `TokenTrackingCallback` is attached (for `"high"`/`"low"`) or skipped (for `"image_moderation"`), and what return type the caller receives.

**Caller Requirement**:
Because the factory is polymorphic and returns `Union[BaseChatModel, ImageModerationProvider]`, any caller expecting a specific type *must* perform a runtime type check and cast before usage to satisfy type checkers and prevent Langchain pipeline errors.

> **Clarification**: Callers requesting `"high"` or `"low"` tiers will **always** receive a `BaseChatModel`. The `Union` is only polymorphic when `config_tier="image_moderation"` is used. Existing callers (`AutomaticBotReplyService`, `extractor.py`, `runner.py`) can safely assume `BaseChatModel` for these tiers.

**Example — Image Moderation Tier Usage**:
```python
# In media_processing_service.py or similar:
provider = await create_model_provider(bot_id, "media_processing", "image_moderation")
assert isinstance(provider, ImageModerationProvider)
result = await provider.moderate_image(image_url="https://...")
```

### 4.3 Centralized Resolvers (`services/resolver.py`)
To prevent duplicated database fetching logic across the application, we will centralize the translation of `bot_id` to its corresponding models and users.

A new file, `services/resolver.py`, will be created containing standalone resolution utilities. These functions will use `GlobalStateManager.get_instance()` for database access, consistent with the factory's approach.

```python
from dependencies import get_global_state

async def resolve_user(bot_id: str) -> str:
    """Returns the user_id of the owner of the given bot."""
    state = get_global_state()
    owner_doc = await state.credentials_collection.find_one(
        {"owned_bots": bot_id},
        {"user_id": 1}
    )
    if not owner_doc:
        raise ValueError(f"No owner found for bot_id: {bot_id}")
    return owner_doc["user_id"]

async def resolve_model_config(
    bot_id: str,
    config_tier: ConfigTier
) -> BaseModelProviderConfig:
    """Returns the specific model provider config for the given bot and tier.
    Returns BaseModelProviderConfig (or ChatCompletionProviderConfig subclass for high/low).
    """
    state = get_global_state()
    db_config = await state.configurations_collection.find_one(
        {"config_data.bot_id": bot_id},
        {f"config_data.configurations.llm_configs.{config_tier}": 1}
    )
    if not db_config:
        raise ValueError(f"No configuration found for bot_id: {bot_id}")
    tier_data = (
        db_config.get("config_data", {})
        .get("configurations", {})
        .get("llm_configs", {})
        .get(config_tier)
    )
    if not tier_data:
        raise ValueError(f"Tier '{config_tier}' not found in configuration for bot_id: {bot_id}")
    # Parse with the appropriate config model based on tier
    if config_tier == "image_moderation":
        return BaseModelProviderConfig.model_validate(tier_data)
    else:
        return ChatCompletionProviderConfig.model_validate(tier_data)
```

The factory `create_model_provider` will consume these resolver functions instead of querying the database directly.

### 4.4 UI Ramifications
> **Note**: Since the `llm_configs` field name and `LLMConfigurations` class name are NOT being renamed (see Deferred Rename in Section 1), API payloads, frontend state, and database field names remain unchanged for this spec.

The only UI-facing change is:
1. **Dynamic Forms**: If the configuration form renders dynamically based on the schema, ensure the schema generation reflects `BaseModelProviderSettings` for the `image_moderation` tier (meaning it will NO LONGER show sliders for Temperature, Seed, or Reasoning Effort).

### 4.5 Safety and Downstream Code Refactoring

#### 4.5.1 Async Factory Cascade (`AutomaticBotReplyService`)
Because `create_model_provider` is now an asynchronous function, it can no longer be invoked from a class constructor (`__init__`).

**Mandatory Refactoring**: `AutomaticBotReplyService` currently calls `self._initialize_llm()` synchronously from its `__init__` (line 189). Since the service is constructed inside the already-async `BotLifecycleService.create_bot_session()` (line 218), the fix is straightforward:
- Remove the `self._initialize_llm()` call from `__init__`.
- Make `_initialize_llm` async: `async def _initialize_llm(self)`.
- Call `await bot_service._initialize_llm()` right after construction, inside `create_bot_session()`.

**Before** (`AutomaticBotReplyService.__init__`, line 189):
```python
def __init__(self, session_manager):
    ...
    self._initialize_llm()  # ← REMOVE this line
```

**After** (`BotLifecycleService.create_bot_session()`, line 218):
```python
if config.features.automatic_bot_reply.enabled:
    bot_service = AutomaticBotReplyService(instance)  # __init__ no longer calls _initialize_llm
    await bot_service._initialize_llm()                # ← NEW: explicit async init
    instance.register_message_handler(bot_service.handle_message)
    instance.register_feature("automatic_bot_reply", bot_service)  # (existing line)
```

#### 4.5.2 Centralized `ConfigTier` Literal Expansion
The following three locations currently hardcode `config_tier: Literal["high", "low"]`. All three **must** be updated to import and use the centralized `ConfigTier` alias from `config_models.py` (defined in Section 2.1):

| Location | Parameter |
|---|---|
| `services/token_consumption_service.py` — `TokenConsumptionService.record_event` | `config_tier` |
| `services/quota_service.py` — `QuotaService.calculate_cost` | `config_tier` |
| `services/tracked_llm.py` — `TokenTrackingCallback.__init__` | `config_tier` |

> **Note on Exhaustive Omission**: Because image moderation requests are free and do not consume generative tokens, they are intentionally excluded from 0-token audit logging. The `TokenConsumptionService` will not be invoked for this tier, and the expansion of the `Literal` is purely a defensive type safety measure.

#### 4.5.3 Broken Import Resolution
The following comprehensive import migration table covers all files affected by the refactoring:

| File | Old Import / Reference | New Import / Reference |
|---|---|---|
| `features/automatic_bot_reply/service.py` | `from llm_providers.base import BaseLlmProvider` | `from model_providers.base import BaseModelProvider` |
| `features/automatic_bot_reply/service.py` | `from services.llm_factory import create_tracked_llm` | `from services.model_factory import create_model_provider` |
| `features/automatic_bot_reply/service.py` | `from utils.provider_utils import find_provider_class` | **REMOVE** (dead import — unused in current code) |
| `features/periodic_group_tracking/extractor.py` | `from llm_providers.base import BaseLlmProvider` | `from model_providers.base import BaseModelProvider` |
| `features/periodic_group_tracking/extractor.py` | `from config_models import LLMProviderConfig` | `from config_models import ChatCompletionProviderConfig` |
| `features/periodic_group_tracking/extractor.py` | `from services.llm_factory import create_tracked_llm` | `from services.model_factory import create_model_provider` |
| `features/periodic_group_tracking/extractor.py` | `from llm_providers.recorder import LLMRecorder` | `from model_providers.recorder import LLMRecorder` |
| `services/llm_factory.py` (itself renamed) | `from llm_providers.base import BaseLlmProvider` | `from model_providers.base import BaseModelProvider` |
| `services/llm_factory.py` (itself renamed) | `from config_models import LLMProviderConfig` | `from config_models import ChatCompletionProviderConfig, BaseModelProviderConfig` |
| `services/llm_factory.py` (itself renamed) | local `find_provider_class` definition (lines 14-20) | **REMOVE** — import from `utils.provider_utils` instead |
| `model_providers/openAi.py` | `from .base import BaseLlmProvider` | `from .base import BaseModelProvider` (via `ChatCompletionProvider`) |
| `model_providers/openAi.py` | `from config_models import LLMProviderConfig` | `from config_models import ChatCompletionProviderConfig` |
| `model_providers/base.py` | `from config_models import LLMProviderConfig` | `from config_models import BaseModelProviderConfig` |
| `model_providers/fakeLlm.py` | `from config_models import LLMProviderConfig` | `from config_models import ChatCompletionProviderConfig` |
| `model_providers/recorder.py` | *(file moved with package rename)* | No internal import changes needed |
| `tests/services/test_token_services.py` | `from services.llm_factory import create_tracked_llm` | `from services.model_factory import create_model_provider` |
| `tests/services/test_token_services.py` | `from config_models import LLMProviderConfig, LLMProviderSettings` | `from config_models import ChatCompletionProviderConfig, ChatCompletionProviderSettings` |
| `tests/services/test_token_services.py` | `@patch('services.llm_factory.find_provider_class')` | `@patch('services.model_factory.find_provider_class')` (patched at import site) |
| `tests/integration/test_token_flow_component.py` | `from services.llm_factory import create_tracked_llm` | `from services.model_factory import create_model_provider` |
| `tests/integration/test_token_flow_component.py` | `from config_models import LLMProviderConfig, LLMProviderSettings` | `from config_models import ChatCompletionProviderConfig, ChatCompletionProviderSettings` |

> **Note — `fakeLlm.py` Behavioral Breakage**: Beyond the import change, `FakeLlmProvider` in `model_providers/fakeLlm.py` currently uses `self.user_id` (line 88: `resp.format(user_id=self.user_id)`). Since `user_id` is dropped from the provider hierarchy (Section 3.1), this reference will crash at runtime. The `FakeLlmProvider` must be refactored to remove this dependency. Additionally, `fakeLlm.py` is missing `from typing import Optional, List, Any` — a pre-existing bug that should be fixed during this refactoring pass.

#### 4.5.4 Async Factory Cascade (`extractor.py` / `runner.py` / `GroupTracker`)
The `periodic_group_tracking` feature has a deeper parameter cascade than `AutomaticBotReplyService`. The factory redesign eliminates several parameters that are currently threaded through multiple layers:

**`ActionItemExtractor.extract()` Parameter Simplification**:
The current signature accepts `llm_config`, `user_id`, `llm_config_high`, and `token_consumption_collection` — all of which become dead after the factory internalizes config and user resolution. The simplified call body becomes:
```python
# Before: llm = create_tracked_llm(llm_config=llm_config, user_id=user_id, ...)
# After:
llm = await create_model_provider(bot_id, "periodic_group_tracking", "low")
high_llm = await create_model_provider(bot_id, "periodic_group_tracking", "high")
```

> **Note — `record_llm_interactions` Access**: The extractor currently reads `llm_config.provider_config.record_llm_interactions` (line 104) **before** the factory call to decide whether to activate the `LLMRecorder`. Since `llm_config` is removed, the extractor must call the resolver directly to obtain this flag:
> ```python
> config = await resolve_model_config(bot_id, "low")
> record_enabled = config.provider_config.record_llm_interactions
> llm = await create_model_provider(bot_id, "periodic_group_tracking", "low")
> ```
> This keeps the factory's interface clean while giving callers access to config flags they need.

**Dead Parameter Cascade**:

| Layer | Dead Parameter | Reason |
|---|---|---|
| `ActionItemExtractor.extract()` | `llm_config`, `user_id`, `llm_config_high`, `token_consumption_collection` | Factory resolves all internally |
| `GroupTrackingRunner.__init__` | `token_consumption_collection` | Factory resolves via `GlobalStateManager` |
| `GroupTracker.__init__` | `token_consumption_collection` | No longer threaded to `GroupTrackingRunner` |
| `runner.py` call site (lines 171-186) | Manual config/user resolution code | Replaced by factory calls |

All listed parameters and their resolution code in `runner.py` must be removed as part of this refactoring.

#### 4.5.5 `bot_lifecycle_service.py` Owner Resolution Consolidation
`bot_lifecycle_service.py` contains two duplicate inline owner resolution blocks that perform the exact same query as the new `resolve_user()` (Section 4.3):

1. **`on_bot_connected()`** (lines 69-77)
2. **`create_bot_session()`** (lines 189-197)

Both blocks should be replaced with `await resolve_user(bot_id)` from `services/resolver.py`.

> **Note — Behavioral Change**: The existing inline code silently returns `None` when no owner is found. The centralized `resolve_user()` raises `ValueError`. This stricter behavior is appropriate — a bot without an owner should not be starting.

### 4.6 Database Migration
A migration script will be created to perform the following:
1. **Strip chat-specific fields** (`temperature`, `seed`, `reasoning_effort`, `record_llm_interactions`) from existing `image_moderation` entries in the database. This ensures clean deserialization with the new `BaseModelProviderSettings` (which does not include `extra = 'allow'`).
2. **Update `provider_name`** in `image_moderation` entries from `"openAi"` to `"openAiModeration"` so the factory's `importlib` resolution loads the correct module (see Section 3.5).
3. **Strip stray fields** from `high` and `low` tier entries if any exist from past experiments, since `ChatCompletionProviderSettings` also drops `extra = 'allow'`.
