# Specification: Image Moderation Provider Separation

## 1. Overview
The current LLM Provider architecture forces all models, including specialized ones like `omni-moderation-latest`, to conform to the standard OpenAI Chat Completion interface. This causes issues because the Moderation API:
1. Does not utilize Langchain's chat interface (it requires direct SDK calls to `client.moderations.create`).
2. Does not accept chat-specific configuration parameters (like `temperature`, `reasoning_effort`, `seed`, `record_model_interactions`).
3. Does not report tokens in the standard `metadata_usage` fashion.

To resolve this, the provider hierarchy and its corresponding configurations will be restructured. This will cleanly separate base API functionality from generative Chat Completion functionality. Furthermore, tracking this change, we will update our nomenclature from "LLM Provider" to "Model Provider" to more accurately reflect that not all tracked models are Large Language Models (e.g., Image Moderation models).

## 2. Configuration Restructuring (`config_models.py`)

The existing `LLMProviderSettings` encapsulates both base API credentials and chat-specific settings. This will be split and renamed.

### 2.1 Base Configuration
```python
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field

class BaseModelProviderSettings(BaseModel):
    api_key_source: Literal["environment", "explicit"] = Field(default="environment", title="API Key Source")
    api_key: Optional[str] = Field(default=None, title="API Key")
    model: str
    
    class Config:
        extra = 'allow'

class BaseModelProviderConfig(BaseModel):
    provider_name: str
    provider_config: BaseModelProviderSettings
```

### 2.2 Chat Completion Configuration
```python
class ChatCompletionProviderSettings(BaseModelProviderSettings):
    temperature: float = 0.7
    reasoning_effort: Optional[Literal["low", "medium", "high", "minimal"]] = None
    seed: Optional[int] = Field(default=None, title="Seed")
    record_model_interactions: bool = Field(default=False, title="Record Model Interactions")
    
class ChatCompletionProviderConfig(BaseModel):
    provider_name: str
    provider_config: ChatCompletionProviderSettings
```

### 2.3 Updating Global Bot Settings (`BotGeneralSettings`)
Within `config_models.py`, the core configuration for a bot is defined in the `BotGeneralSettings` class. Currently, it holds a property named `llm_configs` typed as `LLMConfigurations` (which will be renamed). 

This property and its type will be renamed to reflect the broader scope of "Model Providers":

```python
class ModelConfigurations(BaseModel):
    high: ChatCompletionProviderConfig = Field(..., title="High Performance Model")
    low: ChatCompletionProviderConfig = Field(..., title="Low Cost Model")
    image_moderation: BaseModelProviderConfig = Field(..., title="Media Moderation Model")

class BotGeneralSettings(BaseModel):
    # Other settings...
    # RENAMED from llm_configs:
    model_provider_configs: ModelConfigurations = Field(..., title="Model Configurations") 
```

## 3. Provider Architecture Refactor (`llm_providers/` -> `model_providers/` ?)

*(Note: Consider renaming the package `llm_providers` to `model_providers` for consistency, if desired.)*

### 3.1 `base.py`
The `BaseLlmProvider` becomes `BaseModelProvider`, a pure base abstract class that only expects a `BaseModelProviderConfig`. It defines **no abstract methods** on its own — subclasses are free to expose whichever interface is appropriate for their use case (e.g., `get_llm()` for chat, `moderate_image()` for image moderation).
```python
class BaseModelProvider(ABC):
    def __init__(self, config: BaseModelProviderConfig):
        self.config = config
```

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

### 3.3 `openAi.py`
The existing `OpenAiLlmProvider` (rename to `OpenAiChatProvider` or similar) will be updated to inherit from `ChatCompletionProvider`. It will utilize parameters like `temperature` and `seed` natively.

### 3.4 `openAiModeration.py` [NEW]
A dedicated `OpenAiModerationProvider` will be created.
- Inherits directly from `BaseModelProvider`.
- Exposes a `moderate_image(image_url: str) -> ModerationResult` method (not a Langchain `get_llm()`).
- **Scope**: This provider handles **image moderation only**. While the underlying OpenAI Moderation API supports text inputs as well, text moderation is explicitly out of scope for this provider.
- Directly utilizes the `AsyncOpenAI` SDK to call the `moderations.create` API with an `image_url` input.

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
    config_tier: Literal["high", "low", "image_moderation"]
) -> Union[BaseChatModel, BaseModelProvider]
```

**Behavior**:
- **Future Caching**: While the factory signature implies resolving configs and users from the DB on every invocation (introducing latency), this is a temporary architectural stage. A future `model_provider_cache` layer will be implemented to intercept these calls and yield already-instantiated clients.
- The factory will utilize the new centralized `services/resolver.py` to `await` the fetch of the `user_id` and the specific `ModelProviderConfig` (based on the `config_tier`). Because these resolvers are async, **the factory itself must be asynchronous**.
- It will internally resolve the `token_consumption_collection` singleton using `get_global_state().token_consumption_collection` (from `dependencies.py`), avoiding explicit parameter passing. **Note**: `GlobalStateManager` is a true, thread-safe application-layout Singleton, making this fetching perfectly safe even for background workers like `APScheduler` without risk of context-loss.
- **For `ChatCompletionProviderConfig` (high/low)**: The factory will instantiate the corresponding chat provider, attach the `TokenTrackingCallback`, and return the Langchain `BaseChatModel`. 
- **For `BaseModelProviderConfig` (image_moderation)**: The factory will instantiate the underlying model provider (e.g., `OpenAiModerationProvider`), skip the Langchain token tracker, and return the `BaseModelProvider` instance itself.

**Caller Requirement**:
Because the factory is polymorphic and returns `Union[BaseChatModel, BaseModelProvider]`, any caller expecting a specific type *must* perform a runtime type check and cast before usage to satisfy type checkers and prevent Langchain pipeline errors (e.g., `if not isinstance(model, BaseChatModel): raise ...`).

### 4.3 Centralized Resolvers (`services/resolver.py`)
To prevent duplicated database fetching logic across the application (especially when migrating from `llm_configs` to `model_provider_configs`), we will centralize the translation of `bot_id` to its corresponding models and users.

A new file, `services/resolver.py`, will be created containing core resolution utilities:
- `async def resolve_user(bot_id: str) -> str:` Returns the `user_id` mapped to the bot.
- `async def resolve_model_config(bot_id: str, model_config_tier: Literal["high", "low", "image_moderation"]) -> Union[ChatCompletionProviderConfig, BaseModelProviderConfig]:` Returns the exact extracted model configuration for the requested tier.

The factory `create_model_provider` will consume these resolver functions instead of querying the database directly.

### 4.4 UI Ramifications
Renaming `llm_configs` to `model_provider_configs` implies a significant data contract change between the Backend and Frontend.
1. **API Payloads**: Any API endpoint that expects `llm_configs` to create or update a Bot will need to be updated to expect `model_provider_configs`.
2. **Frontend State & Components**:
    - The structural definition of the bot in the UI state manager (e.g., Redux, React Context) must be updated.
    - Components bound to `llm_configs.high`, `llm_configs.low` must be mapped to `model_provider_configs.high`, etc.
3. **Dynamic Forms**: If the configuration form renders dynamically based on the schema, ensure the schema generation reflects `BaseModelProviderSettings` for the `image_moderation` tier (meaning it will NO LONGER show sliders for Temperature, Seed, or Reasoning Effort).
4. **Database Migrations**: Existing bots stored in the database with the `llm_configs` key MUST be migrated to use `model_provider_configs`.

### 4.5 Safety and Downstream Code Refactoring
1. **Async Factory Cascade (`AutomaticBotReplyService`)**: Because `create_model_provider` is now an asynchronous function, it can no longer be invoked from a class constructor (`__init__`). **Mandatory Refactoring**: The `AutomaticBotReplyService` (and any similar service) MUST be refactored to remove naive synchronous LLM initialization from its constructor. Instead, introduce an asynchronous setup method (e.g., `async def start(self)`) that awaits the factory and is invoked by the service manager during the bot's startup phase.
2. **TokenConsumptionService Expansion**: The `TokenConsumptionService.record_event` function currently enforces `config_tier: Literal["high", "low"]`. This `Literal` MUST be explicitly expanded to include `"image_moderation"` to prevent runtime type crashes.
    - **Note on Exhaustive Omission**: Because image moderation requests are free and do not consume generative tokens, they are intentionally excluded from 0-token audit logging. The `TokenConsumptionService` will not be invoked for this tier, and the expansion of the `Literal` is purely a defensive type safety measure.
3. **Broken Import Resolution**: Renaming `llm_providers.base` to `model_providers.base` and `BaseLlmProvider` to `BaseModelProvider` will break existing downstream feature imports. Areas known to require immediate import updates include:
   - `features/automatic_bot_reply/service.py`
   - `features/periodic_group_tracking/extractor.py`
