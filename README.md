# My Chat Imposter

**My Chat Imposter** is a sophisticated, modular chatbot framework designed to mimic human personalities on messaging platforms (currently WhatsApp via Baileys). It decouples the chatbot logic (LLM) from the communication layer, allowing for powerful, customized interactions.


---

## <a id="main-menu"></a>📑 Table of Contents
*   [🚀 Key Features](#key-features)
*   [🐳 Deployment & Installation](#deployment)
*   [🛠️ Configuration Reference](#configuration)
    *   [1. Identity & Whitelisting](#identity)
    *   [2. Periodic Group Tracking](#tracking)
    *   [3. Messaging Config](#messaging-config)
    *   [4. AI Brain Config](#ai-config)
    *   [5. Context & Memory](#context-config)
*   [💻 Usage](#usage)
*   [📚 Complete API Reference](#api-reference)
*   [📝 Logging & Debugging](#logging)
*   [🏗️ System Architecture](#architecture)

---

## <a id="key-features"></a>🚀 Key Features <small>[↑](#main-menu)</small>

-   **Modular Architecture**: Easily swap Chat Providers (WhatsApp, etc.) and LLM Providers (OpenAI, Local, etc.).
-   **Context Management**: Sophisticated handling of chat history, including shared context across different correspondents or isolated sessions.
-   **Smart Whitelisting**: Granular control over who the bot replies to—supports both individual contacts and specific groups.
-   **Group Tracking**: distinct from chatting, the bot can periodically "scrape" or track messages from specific groups on a CRON schedule.
-   **Robust Linking**: Features a heartbeat-monitored QR linking process to prevent "zombie" sessions.
-   **Message Queuing**: Configurable limits on message history and character counts to manage LLM costs and context window.

---

## <a id="deployment"></a>🐳 Deployment & Installation <small>[↑](#main-menu)</small>

Recommended method for installation and deployment is using **docker compose**.

#### **Prerequisites**
*   **Docker** & **Docker Compose** installed on your machine.
*   *(Optional)* `git` to clone the repository.
*   **No other dependencies required** (Node.js, Python, and MongoDB are handled automatically by Docker).

1.  **Configure Environment**:
    -   Ensure `docker-compose.yml` is present.
    -   Set `OPENAI_API_KEY` in `.env` or `docker-compose.yml` if using "environment" source.
2.  **Run**:
    ```bash
    docker-compose up --build
    ```
3.  **Access**:
    -   Frontend: `http://localhost:3000` (default)
    -   Backend API: `http://localhost:8000`

---

## <a id="configuration"></a>🛠️ Configuration Reference <small>[↑](#main-menu)</small>

The system is configured via a JSON object (the **User Configuration**). Below is the complete reference for every available field.

### <a id="identity"></a>**1. Identity & Whitelisting** <small>[↑](#main-menu)</small>

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | `string` | **Yes** | Unique identifier for this bot instance (e.g., "yahav"). Used for database keys and API routes. |
| `respond_to_whitelist` | `string[]` | No | List of phone numbers or contact display names the bot is allowed to reply to *specifically*. Empty list = no direct replies. |
| `respond_to_whitelist_group` | `string[]` | No | List of **Group Names** or Group IDs tracking the bot is allowed to reply in. |

### <a id="tracking"></a>**2. Periodic Group Tracking** <small>[↑](#main-menu)</small>

Allows the bot to silently monitor specific groups on a schedule without necessarily replying.

| Field | Type | Description |
| :--- | :--- | :--- |
| `groupIdentifier` | `string` | The stable JID of the group (e.g., `123456789@g.us`). |
| `displayName` | `string` | Human-readable name for the group (for logs/UI). |
| `cronTrackingSchedule` | `string` | CRON expression for tracking frequency (e.g., `0/20 * * * *` for every 20 mins). |

> **⚠️ Important Constraint**: You cannot add new groups or change the group identifier unless the bot is **CONNECTED**.
> Efficiently configuring this requires fetching the list of groups from WhatsApp, which is only possible with an active session.
> *You can, however, edit the CRON schedule of existing tracked groups even while disconnected.*
>
> **Note on History**: When tracking starts, the bot attempts to fetch recent message history (up to `max_messages` limit) from the group to seed its context.

### <a id="messaging-config"></a>**3. chatbot_provider_config** (Messaging) <small>[↑](#main-menu)</small>

Configures the connection to the messaging platform.
**Provider Name**: `whatsAppBaileyes`

#### `provider_config` Options:
| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `allow_group_messages` | `boolean` | `false` | If `true`, the bot *can* process messages from groups (subject to whitelist). If `false`, it acts as if it left all groups. |
| `process_offline_messages` | `boolean` | `false` | If `true`, processes startup backlog. **RISKY**. <br>1. **Crash Loop**: A bad message can endlessly crash & restart the bot.<br>2. **Flooding**: Mass replies on startup can trigger spam bans. |
| `sync_full_history` | `boolean` | `true` | If `true`, attempts to fetch available history from the phone on connection. Essential for context awareness. |

```json
"chat_provider_config": {
  "provider_name": "whatsAppBaileyes",
  "provider_config": {
    "allow_group_messages": true,
    "process_offline_messages": false,
    "sync_full_history": true
  }
}
```

### <a id="ai-config"></a>**4. llm_provider_config** (AI Brain) <small>[↑](#main-menu)</small>

Configures the Large Language Model.
**Provider Name**: `openAi`

#### `provider_config` Options:
| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `api_key_source` | `string` | `"environment"` | `"environment"` (use `OPENAI_API_KEY` env var) or `"explicit"` (use `api_key` field). |
| `api_key` | `string` | `null` | The actual API key string. Required if source is `"explicit"`. |
| `model` | `string` | **Required** | The model ID (e.g., `gpt-4`, `gpt-4o`, `gpt-3.5-turbo`, `o1-mini`). |
| `temperature` | `float` | `0.7` | Randomness of the output (0.0 to 1.0). Lower is more deterministic. |
| `reasoning_effort` | `string` | `null` | **For o1 models only.** Controls reasoning depth. <br>Values: `"low"`, `"medium"`, `"high"`, `"minimal"`. |
| `system` | `string` | `""` | The **System Prompt**. Core personality instruction. Supports `{user_id}` variable (autoloads user's ID). |

```json
"llm_provider_config": {
  "provider_name": "openAi",
  "provider_config": {
    "api_key_source": "explicit",
    "api_key": "sk-...",
    "model": "gpt-4o",
    "temperature": 0.8,
    "reasoning_effort": "medium",
    "system": "You are a witty chatbot..."
  }
}
```

### <a id="context-config"></a>**5. Context & Memory Management** <small>[↑](#main-menu)</small>

Controls how much history the bot "remembers" when generating a reply. This is crucial for managing token costs and staying within context windows.

#### `context_config` (LLM Context)
| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_messages` | `int` | `10` | Max count of recent messages to include in the prompt. |
| `max_characters` | `int` | `1000` | Hard cap on total characters in history (trims oldest). |
| `max_days` | `int` | `1` | Max age of messages to include (e.g., forget yesterday's chat). |
| `max_characters_single_message` | `int` | `300` | Truncate individual messages longer than this before adding to context. |
| `shared_context` | `boolean` | `true` | **Experimental**. If `true`, the bot maintains a single history across ALL contacts (knows what it said to Bob while talking to Alice). If `false`, every chat is isolated. |

#### `queue_config` (Incoming Buffer)
Controls the raw message buffer before processing.
| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_messages` | `int` | `10` | Max incoming messages to hold in memory. |
| `max_characters` | `int` | `1000` | Max total characters in buffer. |
| `max_days` | `int` | `1` | Max age of messages to keep in buffer. |
| `max_characters_single_message` | `int` | `300` | Truncate incoming messages longer than this before queuing. |

```json
"context_config": {
  "max_messages": 20,
  "max_characters": 4000,
  "max_days": 1,
  "max_characters_single_message": 500,
  "shared_context": false
},
"queue_config": {
  "max_messages": 10,
  "max_characters": 1000,
  "max_days": 1,
  "max_characters_single_message": 300
}
```

---

## <a id="usage"></a>💻 Usage <small>[↑](#main-menu)</small>

### 1. Linking a User
1.  Go to the homepage (http://<FRONTEND>/).
2.  Click **"Link"** on a user card.
3.  A QR code will appear. **You must keep this modal open.**
4.  Scan the QR with WhatsApp.
5.  If you close the modal, the backend will detect the heartbeat loss and kill the linking session within 5 seconds.

---

## <a id="api-reference"></a>📚 Complete API Reference <small>[↑](#main-menu)</small>

Base URL: `http://localhost:8000`

### **1. Session Management**
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `PUT` | `/chatbot` | **Create/Start Session**. Body: `[UserConfiguration]`.<br>Starts the bot process for the user(s). |
| `GET` | `/chatbot/{user_id}/status` | **Get Status**. Params: `?heartbeat=true` (optional).<br>Returns `connecting`, `connected`, or `disconnected`. Includes QR code if linking. |
| `DELETE` | `/chatbot/{user_id}` | **Unlink Session**. Stops the bot and deletes WhatsApp credentials. Users must rescind link on their phone or wait for timeout. |

### **2. Configuration Management**
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/configurations` | List all configured `user_id`s. |
| `GET` | `/api/configurations/status` | List all configs with their current connection status & authentication state. |
| `GET` | `/api/configurations/{user_id}` | Get the full JSON config for a user. |
| `PUT` | `/api/configurations/{user_id}` | Insert/Update a config without starting the session. |
| `DELETE`| `/api/configurations/{user_id}` | Delete a configuration from the DB. |

### **3. Debug & Inspection (Backstage)**
These APIs help you see what the bot "sees".

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/queue/{user_id}` | **View Queue**. Returns all pending messages buffer, grouped by contact key. |
| `DELETE`| `/api/queue/{user_id}` | **Clear All Queues**. Nuke all pending messages for this user. |
| `DELETE`| `/api/queue/{user_id}/{contact_id}`| **Clear Specific Queue**. Nuke pending messages for one contact. |
| `GET` | `/api/context/{user_id}` | **View Context**. Returns the actual prompt history the LLM will see for each contact. |

---

## <a id="logging"></a>📝 Logging & Debugging <small>[↑](#main-menu)</small>

The system provides robust, granular logging to help you diagnose issues. Logs are stored in the `log/` directory.

### **Log Directory Structure**
*   **`log/all_providers.log`**: The "Firehose". Chronological stream of *every* message from *every* user and provider. Good for spotting global issues.
*   **`log/{provider}_{user}_{contact}.log`**: Granular conversations.
    *   Example: `whatsappBaileyes_yahav_123456@s.whatsapp.net.log`
    *   Contains only the conversation history between bot `yahav` and contact `123456`.
    *   Also contains **Retention Events** (when messages are evicted from memory due to limits).

### **Reading Logs**
Logs use a tagged format:
`[TIMESTAMP][tag1][tag2] :: Message Content`

Example of an eviction event (Queue limit reached):
```
202X-XX-XX... :: [event_type=EVICT]::[reason=total_characters]...
```

---

## <a id="architecture"></a>🏗️ System Architecture <small>[↑](#main-menu)</small>

The project follows a microservices-inspired architecture, orchestrated via Docker Compose.

### **1. 🖥️ Frontend (React)**
*   **Path**: `frontend/`
*   **Port**: `3000`
*   **Tech**: React, TailwindCSS, `react-jsonschema-form`.
*   **Role**: Provides a UI for managing users.

#### **Main Pages**
| Page | Route | Purpose |
| :--- | :--- | :--- |
| **Home Page** | `/` | **Dashboard**. Lists all bots with real-time status (`Connected`, `Disconnected`, `Linking`). Handles the **QR Code Linking** process via modal. |
| **Edit Config** | `/edit/:userId` | **Configuration Editor**. A dynamic form for editing `UserConfiguration`. Features: <br>• JSON editor with live validation.<br>• Smart "Group Tracking" UI for CRON schedules.<br>• "Save & Reload" to apply changes instantly. |

### **2. 🐍 Backend (Python / FastAPI)**
*   **Path**: Root directory
*   **Port**: `8000`
*   **Role**: The central brain. Manages API requests, orchestrates chatbot instances, and handles the logic loop.

#### **Key Modules**
| Module | Purpose |
| :--- | :--- |
| **`main.py`** | **Entry Point**. FastAPI app. Handles REST API, global exceptions, and startup/shutdown lifecycle. |
| **`chatbot_manager.py`** | **Orchestrator**. The `ChatbotInstance` class manages a *single* user session. It glues together the Queue, the LLM, and the Chat Provider. Handles the main event loop. |
| **`queue_manager.py`** | **Memory/Buffer**. Manages `UserQueue` and `CorrespondentQueue`. Enforces limits (max msgs, max chars) and handles eviction logic. |
| **`group_tracker.py`** | **Cron Jobs**. A background thread that triggers periodic checks on specific groups (completely separate from the reactive chat flow). |
| **`config_models.py`** | **Validation**. Pydantic models defining the detailed structure of the User Configuration JSON. |
| **`logging_lock.py`** | **Thread Safety**. Provides a thread-safe timestamped logger to ensure logs from multiple async workers don't interleave chaotically. |

### **3. 💬 Chat Provider (Node.js / Baileys)**
*   **Path**: `chat_providers/whatsapp_baileys_server/`
*   **Role**: Acts as the bridge to WhatsApp.
*   **Tech**: Node.js, `@whiskeysockets/baileys`.
*   **Function**:
    *   Maintains the WebSocket connection to WhatsApp.
    *   Handles encryption/decryption of messages.
    *   Exposes an internal HTTP API for the Python backend to send messages/check status.
    *   **Heartbeat Monitor**: Actively kills sessions if the frontend stops polling during linking.

### **4. 🧠 LLM Providers**
*   **Path**: `llm_providers/`
*   **Role**: The "Intelligence" layer.
*   **Current Implementations**:
    *   **`openAi.py`**: Integration with OpenAI's Chat Completion API (GPT-4, o1, etc.). Handles system prompts and history formatting.
    *   *(Extensible)*: You can add `anthropic.py` or `local_llama.py` here easily.

### **5. 🗄️ Database (MongoDB)**
*   **Container**: `mongodb`
*   **Role**: Persistence.
*   **Collections**:
    *   `configurations`: Stores the JSON config for each user.
    *   `queues`: Persists unrelated/unprocessed messages so they survive restarts.
    *   `baileys_sessions`: Stores WhatsApp auth credentials (keys, tokens) to allow reconnection without scanning QR codes again.

---

*Created by the MyChatImposter Team*
