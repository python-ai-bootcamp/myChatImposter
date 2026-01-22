# My Chat Imposter

**My Chat Imposter** is a sophisticated, modular chatbot framework designed to mimic human personalities on messaging platforms (currently WhatsApp via Baileys). It decouples the chatbot logic (LLM) from the communication layer, allowing for powerful, customized interactions.


---

## <a id="main-menu"></a>📑 Table of Contents
*   [🚀 Key Features](#key-features)
*   [🐳 Deployment & Installation](#deployment)
*   [🛠️ Configuration Reference](#configuration)
    *   [A. General Configurations](#general-config)
    *   [B. Feature Configurations](#feature-config)
*   [💻 Usage](#usage)
*   [📚 Complete API Reference](#api-reference)
*   [📝 Logging & Debugging](#logging)
*   [🏗️ System Architecture](#architecture)
*   [🗃️ Persistency Schema](#persistency-schema)

---

## <a id="key-features"></a>🚀 Key Features <small>[↑](#main-menu)</small>

*   **🤖 Automatic Bot Reply**: Your digital twin. It learns your style and replies to whitelisted contacts or groups on your behalf, so you never leave anyone hanging.
*   **🕵️ Periodic Group Tracking**: The ultimate lurker. It silently monitors group chats on a schedule you define and sends you AI-powered digests with action items, events, and summaries.
*   **👶 Kid Phone Safety**: (Coming Soon) A safety guardian that monitors your child's phone for risky interactions without being invasive.

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

The system is configured via a JSON object. The configuration is split into **General Settings** (core plumbing) and **Feature Settings** (what the bot actually does).

### <a id="general-config"></a>**A. General Configurations** (Under `configurations` key)

This section details the sub-objects within the `configurations` key.

#### **1. Identity & Locals** (`configurations.user_details`)
Defines the user's identity and localization settings.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `first_name` | `string` | `""` | User's first name. |
| `last_name` | `string` | `""` | User's last name. |
| `timezone` | `string` | `"UTC"` | IANA Timezone (e.g., `America/New_York`). Controls tracking schedules and log timestamps. |
| `language_code` | `string` | `"en"` | ISO Code (e.g., `en`, `he`). Controls the language of AI digests. |

#### **2. Messaging Provider** (`configurations.chat_provider_config`)
Settings for the WhatsApp connection.

*   `provider_name`: `string` (Fixed: `"whatsAppBaileyes"`)
*   `provider_config`: Object containing specific settings:

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `allow_group_messages` | `boolean` | `false` | If `false`, ignores ALL group traffic. |
| `process_offline_messages` | `boolean` | `false` | If `true`, processes startup backlog. **Use with caution**. |
| `sync_full_history` | `boolean` | `true` | Fetches phone history on connection for context. |

#### **3. AI Brain** (`configurations.llm_provider_config`)
Settings for the LLM provider.

*   `provider_name`: `string` (Fixed: `"openAi"`)
*   `provider_config`: Object containing specific settings:

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `api_key_source` | `string` | `"environment"` | `"environment"` (use `OPENAI_API_KEY` env var) or `"explicit"`. |
| `api_key` | `string` | `null` | Required if source is `"explicit"`. |
| `model` | `string` | **Required** | The model ID (e.g., `gpt-4o`, `gpt-3.5-turbo`, `o1-mini`). |
| `temperature` | `float` | `0.7` | Creativity (0.0: strict, 1.0: creative). |
| `reasoning_effort` | `string` | `null` | **o1 models only**: `"low"`, `"medium"`, `"high"`, `"minimal"`. |
| `seed` | `int` | `null` | Optional deterministic seed. |
| `record_llm_interactions` | `boolean` | `false` | If `true`, logs inputs/outputs for debugging/evals. |

#### **4. Context Memory** (`configurations.context_config`)
Settings for the conversation context window.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_messages` | `int` | `10` | Max recent messages to include in the prompt. |
| `max_characters` | `int` | `1000` | Hard cap on total characters in history (trims oldest). |
| `max_days` | `int` | `1` | Max age of messages to include (e.g., forget yesterday's chat). |
| `max_characters_single_message` | `int` | `300` | Truncate individual messages longer than this before adding to context. |
| `shared_context` | `boolean` | `true` | If `true`, bot uses one shared history for ALL contacts. If `false`, each chat has isolated memory. |

#### **5. Inbound Queue** (`configurations.queue_config`)
Settings for the message buffer.

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `max_messages` | `int` | `10` | Max incoming messages to hold in memory. |
| `max_characters` | `int` | `1000` | Max total characters in buffer. |
| `max_days` | `int` | `1` | Max age of messages to keep in buffer. |
| `max_characters_single_message` | `int` | `300` | Truncate incoming messages longer than this before queuing. |

---

### <a id="feature-config"></a>**B. Feature Configurations**

These settings live under the `features` object.

#### **1. Automatic Bot Reply** (`features.automatic_bot_reply`)
The core chatbot functionality.

| Field | Type | Description |
| :--- | :--- | :--- |
| `enabled` | `boolean` | Master switch. |
| `respond_to_whitelist` | `string[]` | Phone numbers/names to reply to. |
| `respond_to_whitelist_group` | `string[]` | Group names/IDs to reply in. |
| `chat_system_prompt` | `string` | **The Persona**. Instructions on how the bot should behave. |

#### **2. Periodic Group Tracking** (`features.periodic_group_tracking`)
Silent monitoring and digests (Task Extraction).

| Field | Type | Description |
| :--- | :--- | :--- |
| `enabled` | `boolean` | Master switch. |
| `tracked_groups` | `array` | List of groups to monitor. |

**Tracked Group Configuration**:
*   `groupIdentifier`: WhatsApp JID.
*   `displayName`: Friendly name.
*   `cronTrackingSchedule`: Execution schedule (uses your `timezone`).

> **Feature Note**: This generates a "Digest" message to yourself with extracted tasks and events found in the group chat.
>
> **Technical Details**:
> *   **Scheduling**: Calculated relative to your configured `timezone` with "Wiggle Recovery" for DST transitions.
> *   **Integrity**: Uses strict cron-based windows to ensure no message is missed or duplicated.
> *   **Language**: Extracts tasks in your configured `language_code`.

#### **3. Kid Phone Safety** (`features.kid_phone_safety_tracking`)
*Coming Soon*

| Field | Type | Description |
| :--- | :--- | :--- |
| `enabled` | `boolean` | Master switch. |

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
| `PUT` | `/chatbot` | **Create/Start Session**. Body: `UserConfiguration`.<br>Starts the bot process for the user. |
| `GET` | `/chatbot/{user_id}/status` | **Get Status**. Returns `connecting`, `connected`, or `disconnected`. Includes QR code if linking.<br>**Query Params**: `?heartbeat=true` — Resets the heartbeat timer. Use only from linking modals, not background polling. |
| `POST` | `/chatbot/{user_id}/reload` | **Reload Config**. Gracefully restarts the bot with the latest config from DB.<br>Does NOT re-link WhatsApp. |
| `DELETE` | `/chatbot/{user_id}` | **Unlink Session**. Stops the bot and deletes WhatsApp credentials. |
| `GET` | `/chatbot/{user_id}/groups` | **List Groups**. Fetches all WhatsApp groups the user is a member of.<br>Requires active (connected) session. |

### **2. Configuration Management**
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/configurations` | List all configured `user_id`s. |
| `GET` | `/api/configurations/status` | List all configs with their current connection status & authentication state. |
| `GET` | `/api/configurations/schema` | **Get Config Schema**. Returns the JSON Schema for `UserConfiguration`.<br>Used by the frontend to render dynamic forms. |
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

### **4. Group Tracking Data**
These APIs access data collected by **Periodic Group Tracking** (distinct from chat queues).

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/trackedGroupMessages/{user_id}` | **All Tracked Groups**. Returns message periods for all tracked groups.<br>**Query Params**: `lastPeriods`, `from`, `until`. |
| `GET` | `/api/trackedGroupMessages/{user_id}/{group_id}` | **Single Group**. Returns message periods for a specific group. |
| `DELETE`| `/api/trackedGroupMessages/{user_id}` | **Delete All**. Deletes tracked message periods for all groups. |
| `DELETE`| `/api/trackedGroupMessages/{user_id}/{group_id}` | **Delete Group**. Deletes tracked message periods for a specific group. |

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
    *   **LID Resolution**: Automatically learns and caches WhatsApp's internal LID-to-PN (Linked ID to Phone Number) mappings. This ensures consistent user identification across individual and group chats, even when WhatsApp's API returns different identifier formats.

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
## <a id="persistency-schema"></a>🗃️ Persistency Schema <small>[↑](#main-menu)</small>

The system uses MongoDB for persistence. All collections live in the `chat_manager` database.

| Collection | Purpose |
| :--- | :--- |
| `configurations` | Stores the JSON config (`UserConfiguration`) for each bot instance. Keyed by `user_id`. |
| `queues` | Persists unprocessed messages from the message buffer. Allows recovery after restarts. |
| `baileys_sessions` | WhatsApp authentication credentials (keys, tokens). Allows reconnection without re-scanning QR. |
| `tracked_groups` | Metadata for groups being tracked by `periodic_group_tracking`. |
| `tracked_group_periods` | Individual snapshot "periods" of tracked group messages, with timestamps and message lists. |
| `group_tracking_state` | Last run timestamps for each tracking cron job. Used to calculate time windows. |
