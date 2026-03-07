# Specification: Image Moderation Provider Separation

## 1. Overview
The current LLM Provider architecture forces all models, including specialized ones like `omni-moderation-latest`, to conform to the standard OpenAI Chat Completion interface. This causes issues because the Moderation API:
1. Does not utilize Langchain's chat interface (it requires direct SDK calls to `client.moderations.create`).
2. Does not accept chat-specific configuration parameters (like `temperature`, `reasoning_effort`, `seed`, `record_llm_interactions`).
3. Does not report tokens in the standard `metadata_usage` fashion.

To resolve this, the provider hierarchy and its corresponding configurations will be restructured. This will cleanly separate base API functionality from generative Chat Completion functionality. Furthermore, tracking this change, we will update our nomenclature from "LLM Provider" to "Model Provider" to more accurately reflect that not all tracked models are Large Language Models (e.g., Image Moderation models).

## 2. Configuration Restructuring (`config_models.py`)

The existing `LLMProviderSettings` encapsulates both base API credentials and chat-specific settings. This will be split and renamed.

### 2.1 Base Configuration
```python
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
    record_llm_interactions: bool = Field(default=False, title="Record Traffic")
    
class ChatCompletionProviderConfig(BaseModel):
    provider_name: str
    provider_config: ChatCompletionProviderSettings
```

### 2.3 Updating Global Bot Settings (`BotGeneralSettings`)
Within `config_models.py`, the core configuration for a bot is defined in the `BotGeneralSettings` class. Currently, it holds a property named `llm_configs` typed as `LLMConfigurations`. 

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
The `BaseLlmProvider` becomes `BaseModelProvider`, a pure base abstract class that only expects a `BaseModelProviderConfig`.
```python
class BaseModelProvider(ABC):
    def __init__(self, config: BaseModelProviderConfig, user_id: str):
        self.config = config
        self.user_id = user_id
```

### 3.2 `chat_completion.py` [NEW]
A new intermediate abstract class, `ChatCompletionProvider`, will inherit from `BaseModelProvider`. It will specifically handle the `ChatCompletionProviderConfig` and establish the contract for chat generation models (like integrating Langchain).

### 3.3 `openAi.py`
The existing `OpenAiLlmProvider` (rename to `OpenAiChatProvider` or similar) will be updated to inherit from `ChatCompletionProvider`. It will utilize parameters like `temperature` and `seed` natively.

### 3.4 `openAiModeration.py` [NEW]
A dedicated `OpenAiModerationProvider` will be created.
- Inherits directly from `BaseModelProvider`.
- Exposes a custom `moderate_image(image_url: str)` or similar function (not a standard Langchain `get_llm()`).
- Directly utilizes the `AsyncOpenAI` SDK to call the `moderations.create` API.

## 4. Downstream Impact

### 4.1 Token Tracking (`services/tracked_llm.py`)
Since moderation requests do not yield generative tokens, they will not be routed through the default LLM `TokenTrackingCallback`. Tracked factories or decorators must differentiate between `ChatCompletionProviderConfig` (which gets tracked by token usage) and `BaseModelProviderConfig` (which does not, or has custom reporting).

### 4.2 Factory Instantiation
The central factory (or resolver) that instantiates these providers based on `provider_name` must map `openAiModeration` to the new `OpenAiModerationProvider`. 

### 4.3 UI Ramifications
Renaming `llm_configs` to `model_provider_configs` implies a significant data contract change between the Backend and Frontend.
1. **API Payloads**: Any API endpoint that expects `llm_configs` to create or update a Bot will need to be updated to expect `model_provider_configs`.
2. **Frontend State & Components**:
    - The structural definition of the bot in the UI state manager (e.g., Redux, React Context) must be updated.
    - Components bound to `llm_configs.high`, `llm_configs.low` must be mapped to `model_provider_configs.high`, etc.
3. **Dynamic Forms**: If the configuration form renders dynamically based on the schema, ensure the schema generation reflects `BaseModelProviderSettings` for the `image_moderation` tier (meaning it will NO LONGER show sliders for Temperature, Seed, or Reasoning Effort).
4. **Database Migrations**: Existing bots stored in the database with the `llm_configs` key MUST be migrated to use `model_provider_configs`.
