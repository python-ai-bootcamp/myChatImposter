# My Chat Imposter

**My Chat Imposter** is a sophisticated, modular chatbot framework designed to mimic human personalities on messaging platforms (currently WhatsApp via Baileys). It decouples the chatbot logic (LLM) from the communication layer, allowing for powerful, customized interactions.

## 🚀 Key Features

-   **Modular Architecture**: Easily swap Chat Providers (WhatsApp, etc.) and LLM Providers (OpenAI, Local, etc.).
-   **Context Management**: Sophisticated handling of chat history, including shared context across different correspondents or isolated sessions.
-   **Smart Whitelisting**: Granular control over who the bot replies to—supports both individual contacts and specific groups.
-   **Group Tracking**: distinct from chatting, the bot can periodically "scrape" or track messages from specific groups on a CRON schedule.
-   **Robust Linking**: Features a heartbeat-monitored QR linking process to prevent "zombie" sessions.
-   **Message Queuing**: Configurable limits on message history and character counts to manage LLM costs and context window.

---

## 🛠️ Configuration Reference

The system is configured via a JSON object (the **User Configuration**). Below is the complete reference for every available field.

### **1. Identity & Whitelisting**

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | `string` | **Yes** | Unique identifier for this bot instance (e.g., "yahav"). Used for database keys and API routes. |
| `respond_to_whitelist` | `string[]` | No | List of phone numbers or contact display names the bot is allowed to reply to *specifically*. Empty list = no direct replies. |
| `respond_to_whitelist_group` | `string[]` | No | List of **Group Names** or Group IDs tracking the bot is allowed to reply in. |

### **2. Periodic Group Tracking**

Allows the bot to silently monitor specific groups on a schedule without necessarily replying.

> **⚠️ Important Constraint**: You cannot add new groups or change the group identifier unless the bot is **CONNECTED**.
> Efficiently configuring this requires fetching the list of groups from WhatsApp, which is only possible with an active session.
> *You can, however, edit the CRON schedule of existing tracked groups even while disconnected.*

| Field | Type | Description |
| :--- | :--- | :--- |
| `groupIdentifier` | `string` | The stable JID of the group (e.g., `123456789@g.us`). |
| `displayName` | `string` | Human-readable name for the group (for logs/UI). |
| `cronTrackingSchedule` | `string` | CRON expression for tracking frequency (e.g., `0/20 * * * *` for every 20 mins). |

### **3. chatbot_provider_config** (Messaging)

Configures the connection to the messaging platform.
**Provider Name**: `whatsAppBaileyes`

#### `provider_config` Options:
| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `allow_group_messages` | `boolean` | `false` | If `true`, the bot *can* process messages from groups (subject to whitelist). If `false`, it acts as if it left all groups. |
| `process_offline_messages` | `boolean` | `false` | If `true`, the bot will attempt to reply to messages received while it was disconnected (startup backlog). Be careful with loops. |
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

### **4. llm_provider_config** (AI Brain)

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
| `system` | `string` | `""` | The **System Prompt**. This is the core personality instruction for the bot. |

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

### **5. Context & Memory Management**

Controls how much history the bot "remembers" when generating a reply. This is crucial for managing token costs and staying within context windows.

#### `context_config` (LLM Context)
| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_messages` | `int` | `10` | Max count of recent messages to include in the prompt. |
| `max_characters` | `int` | `1000` | Hard cap on total characters in history (trims oldest). |
| `max_days` | `int` | `1` | Max age of messages to include (e.g., forget yesterday's chat). |
| `shared_context` | `boolean` | `true` | **Experimental**. If `true`, the bot maintains a single history across ALL contacts (knows what it said to Bob while talking to Alice). If `false`, every chat is isolated. |

#### `queue_config` (Incoming Buffer)
Controls the raw message buffer before processing.
| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_messages` | `int` | `10` | Max incoming messages to hold in memory. |
| `max_characters` | `int` | `1000` | Max total characters in buffer. |

```json
"context_config": {
  "max_messages": 20,
  "max_characters": 4000,
  "max_days": 1,
  "shared_context": false
}
```

---

## 💻 Usage

### 1. Linking a User
The system uses a **Heartbeat-Monitored QR Linking** process.
1.  Go to the frontend (Home Page).
2.  Click **"Link"** on a user card.
3.  A QR code will appear. **You must keep this modal open.**
4.  Scan the QR with WhatsApp.
5.  If you close the modal, the backend will detect the heartbeat loss and kill the linking session within 5 seconds.

### 2. API Endpoints

-   **PUT `/chatbot`**: Create or Update a bot instance.
    -   Body: `[ { ...UserConfiguration... } ]`
-   **GET `/chatbot/{id}/status`**: Get connection status / QR code.
    -   *Note*: This endpoint acts as a heartbeat when called with query param `?heartbeat=true`.

---

## 🏗️ Architecture & Extension

-   **`main.py`**: FastAPI entry point.
-   **`chatbot_manager.py`**: Orchestrator for a single user session.
-   **`chat_providers/`**: Pluggable modules for messaging logic.
    -   To add a provider, inherit from `BaseChatProvider` and implement `start_listening`, `sendMessage`.
-   **`llm_providers/`**: Pluggable modules for AI logic.
    -   To add a provider, inherit from `BaseLlmProvider`.

## 📦 Installation (Docker)

Recommended method for deployment.

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
*Created by the MyChatImposter Team*
