# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**My Chat Imposter** is a modular chatbot framework that mimics human personalities on WhatsApp. It uses a layered architecture with FastAPI (Python) backend, React frontend, and Node.js Baileys for WhatsApp integration.

## Development Commands

### Running the Application
```bash
# Start all services (MongoDB, backend, frontend, WhatsApp server)
docker-compose up --build

# Access points:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - MongoDB: localhost:27017
```

### Testing

**Backend (Python):**
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_queue_manager.py

# Run with verbose output
pytest -v

# Run specific test function
pytest tests/test_main.py::test_user_status
```

**Frontend (React):**
```bash
cd frontend
npm test           # Interactive test runner
npm test -- --coverage  # With coverage report
```

### Python Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run backend directly (outside Docker)
uvicorn main:app --reload --port 8000
```

### Frontend Development
```bash
cd frontend
npm install        # Install dependencies
npm start          # Development server
npm run build      # Production build
```

## Architecture Overview

### System Components

**1. Backend (Python/FastAPI)** - Port 8000
- **main.py**: Application entry point with lifespan management
- **dependencies.py**: GlobalStateManager singleton for application-wide state
- **services/session_manager.py**: Manages per-user chatbot sessions (one per connected user)
- **queue_manager.py**: Message buffer with per-correspondent queues
- **async_message_delivery_queue_manager.py**: Three-state delivery queue (active/holding/failed)

**2. Frontend (React)** - Port 3000
- Dynamic form generation using `react-jsonschema-form` (`@rjsf/core`)
- **src/pages/HomePage.js**: User dashboard with session management
- **src/pages/EditPage.js**: Configuration editor with JSON Schema validation
- **src/configModels.js**: Mirrors backend Pydantic models

**3. WhatsApp Provider (Node.js/Baileys)** - Port 9000
- **chat_providers/whatsapp_baileys_server/**: Separate Node.js service
- Communicates via HTTP + WebSocket with backend
- Handles QR code authentication and message encryption

**4. Database (MongoDB)** - Port 27017
- **configurations**: User configurations
- **queues**: Persisted message history
- **baileys_sessions**: WhatsApp authentication credentials
- **async_message_delivery_queue_***: Three collections for message delivery states

### Key Design Patterns

**Observer Pattern**: SessionManager notifies feature handlers of incoming messages through registered callbacks.

**Factory Pattern**: Dynamic loading of chat providers and LLM providers by name using reflection.

**Queue Pattern**: Three-state delivery queue (active → holding on disconnect, holding → active on connect, active → failed after 3 attempts).

**Singleton Pattern**: GlobalStateManager maintains single instance of application state including active chatbot instances dictionary.

## Code Organization

### Backend Structure
```
├── main.py                          # FastAPI app, lifespan, routers
├── config_models.py                 # Pydantic configuration models
├── dependencies.py                  # Global state manager
├── queue_manager.py                 # Message queues (UserQueuesManager)
├── async_message_delivery_queue_manager.py  # Async delivery system
├── routers/
│   ├── user_management.py           # User CRUD and session control
│   ├── async_message_delivery_queue.py
│   └── features/
│       ├── automatic_bot_reply.py
│       └── periodic_group_tracking.py
├── services/
│   ├── session_manager.py           # Per-user session orchestrator
│   ├── ingestion_service.py         # Message archival to MongoDB
│   └── user_lifecycle_service.py    # Connect/disconnect event handler
├── features/
│   ├── automatic_bot_reply/
│   │   └── service.py               # AI-powered auto-reply
│   └── periodic_group_tracking/
│       └── service.py               # Cron-based group monitoring
├── chat_providers/
│   ├── base.py                      # Abstract provider interface
│   └── whatsAppBaileyes.py          # WhatsApp implementation
├── llm_providers/
│   ├── base.py                      # Abstract LLM interface
│   └── openAi.py                    # OpenAI ChatCompletion
└── message_processors/
    ├── factory.py                   # Message type routing
    ├── text_processor.py
    └── ics_processor.py
```

### Features Architecture

Features are registered as message handlers on SessionManager and receive notifications through observer pattern:

**Automatic Bot Reply** (`features/automatic_bot_reply/`):
- Uses LangChain with `RunnableWithMessageHistory` for stateful conversations
- Whitelist-based filtering (contacts and groups)
- Supports shared or per-correspondent conversation history
- Custom `TimestampedAndPrefixedChatMessageHistory` for context window management

**Periodic Group Tracking** (`features/periodic_group_tracking/`):
- APScheduler with CronTrigger for timezone-aware scheduling
- Extracts actionable items (tasks/events) from group chat history using LLM
- Generates ICS calendar format messages
- Queues digests via AsyncMessageDeliveryQueueManager

### Message Flow

```
WhatsApp → Node.js Baileys (WebSocket) → WhatsAppBaileysProvider
  → UserQueuesManager (per-correspondent queues)
  → SessionManager (observer dispatch)
  → Feature Handlers (AutomaticBotReply, PeriodicGroupTracking)
  → LLM Provider (OpenAI)
  → Response → Provider → WhatsApp
```

### Configuration System

The entire system is configured via JSON validated by Pydantic models in `config_models.py`:

```
UserConfiguration
├── user_id: str
├── configurations: ConfigurationsSettings
│   ├── user_details: UserDetails (timezone, language, name)
│   ├── chat_provider_config: ChatProviderConfig
│   ├── llm_provider_config: LLMProviderConfig (model, temperature, api_key)
│   ├── queue_config: QueueConfig (max_messages, max_characters, max_days)
│   └── context_config: ContextConfig (conversation history limits)
└── features: FeaturesConfiguration
    ├── automatic_bot_reply: AutomaticBotReplyFeature
    ├── periodic_group_tracking: PeriodicGroupTrackingFeature
    └── kid_phone_safety_tracking: KidPhoneSafetyTrackingFeature
```

Frontend generates dynamic forms using JSON Schema (`/api/configurations/schema` endpoint).

## Important Implementation Details

### Session Lifecycle

**Startup (main.py:38-91 lifespan):**
1. Connect to MongoDB
2. Initialize AsyncMessageDeliveryQueueManager (move active → holding)
3. Initialize GroupTracker scheduler (APScheduler)
4. Initialize UserLifecycleService

**User Session Start:**
1. Create SessionManager instance
2. Initialize WhatsApp provider (HTTP + WebSocket connection)
3. Initialize UserQueuesManager (load from MongoDB)
4. Register feature handlers
5. Add to active users map in GlobalStateManager
6. Start provider listening loop

**User Session Stop:**
1. Stop provider WebSocket connection
2. Remove from active users map
3. Pause (don't delete) group tracking jobs
4. Move delivery queue messages to holding state

### Queue Management

**UserQueuesManager**: Per-user message buffer with per-correspondent queues
- Each contact/group has its own `CorrespondentQueue` (deque-based)
- Enforces limits: max_messages, max_characters, max_days, max_characters_single_message
- Messages persist to MongoDB via IngestionService

**AsyncMessageDeliveryQueueManager**: Three-state delivery system
- **Active**: User connected, ready to send (1-12s random jitter between sends)
- **Holding**: User disconnected, waiting for reconnect
- **Failed**: 3 attempts exhausted, moved to dead-letter queue

### WebSocket Reliability

WhatsAppBaileysProvider implements auto-reconnect:
- Max 3 reconnect attempts with 2s delay
- Message ID cache (100 item LRU deque) prevents duplicate bot responses
- Pending message buffer with 30s TTL handles HTTP/WebSocket race conditions
- Connection state validation before sending

### LLM Integration

LLM providers use factory pattern for dynamic loading:
- `llm_providers/openAi.py` - ChatOpenAI via LangChain
- Supports `reasoning_effort` parameter for o1 models
- Optional `record_llm_interactions` for debugging/evals
- Temperature, seed, and model configurability

### Testing Conventions

**Backend Tests:**
- Use `test_` prefix for user_ids (allows safe cleanup: `{"user_id": {"$regex": "^test_"}}`)
- pytest fixtures with function-level scope for isolation
- TestClient from FastAPI for API integration tests
- MongoDB connection retry (5 attempts, 3s delay)
- Teardown deletes test data using regex filter

**Frontend Tests:**
- Jest + React Testing Library
- Tests co-located with components
- Use `npm test` for interactive runner

## Key Files Reference

| File | Purpose | Line References |
|------|---------|-----------------|
| main.py | FastAPI app, startup/shutdown lifecycle | lifespan:38-91 |
| dependencies.py | GlobalStateManager singleton | - |
| services/session_manager.py | Per-user session orchestrator | - |
| queue_manager.py | Message queues and limits | - |
| async_message_delivery_queue_manager.py | Three-state delivery queue | consumer_loop:100-150 |
| chat_providers/whatsAppBaileyes.py | WhatsApp WebSocket integration | auto_reconnect:180-220 |
| features/automatic_bot_reply/service.py | AI auto-reply feature | - |
| features/periodic_group_tracking/service.py | Cron-based group monitoring | - |
| llm_providers/openAi.py | OpenAI ChatCompletion integration | - |

## Common Workflows

### Adding a New Feature

1. Create feature directory under `features/`
2. Implement feature service with message handler method
3. Register handler in SessionManager via `register_message_handler()`
4. Add configuration model to `config_models.py` FeaturesConfiguration
5. Create API router in `routers/features/` if needed
6. Register router in main.py

### Adding a New LLM Provider

1. Create provider file in `llm_providers/` (e.g., `anthropic.py`)
2. Inherit from `BaseLlmProvider`
3. Implement abstract methods: `get_llm()`, `validate_config()`
4. Add provider name to dynamic loading in feature services

### Adding a New Chat Provider

1. Create provider file in `chat_providers/` (e.g., `telegram.py`)
2. Inherit from `BaseChatProvider`
3. Implement abstract methods: `start_listening()`, `stop_listening()`, `sendMessage()`, etc.
4. Add provider name to dynamic loading in SessionManager

## Environment Variables

```bash
OPENAI_API_KEY=your_api_key_here        # Required for LLM
MONGODB_URL=mongodb://mongodb:27017     # MongoDB connection
WHATSAPP_SERVER_URL=http://whatsapp_baileys_server:9000  # Baileys server
PYTHONUNBUFFERED=1                      # Python logging
```

## Debugging

**Logs**: Check `./log/` directory (mounted volume)

**Queue Inspection APIs:**
- `GET /api/async-message-delivery-queue/{queue_type}/{user_id}` - View queue contents (queue_type: active, holding, failed)
- `DELETE /api/async-message-delivery-queue/{queue_type}/{message_id}` - Delete specific message

**MongoDB Collections:**
- Use MongoDB Compass to inspect: `mongodb://localhost:27017`
- Collections: configurations, queues, baileys_sessions, async_message_delivery_queue_*

**Test Data Cleanup:**
```python
# Backend automatically cleans test data using:
db.collection.delete_many({"user_id": {"$regex": "^test_"}})
```

## Caveats and Gotchas

1. **User IDs must be unique** - They're used as keys in GlobalStateManager's active_users dict
2. **WebSocket reconnect has max 3 attempts** - After that, session must be manually restarted
3. **Message deduplication uses 100-item cache** - Very old message IDs may be processed twice
4. **Timezone-aware scheduling** - All cron schedules use user's configured timezone
5. **Group tracking windows are strict** - Uses cron-based time windows to prevent duplicate/missed messages
6. **Pending message TTL is 30s** - Messages in pending cache expire after 30 seconds
7. **Frontend proxy assumes backend at `http://backend:8000`** - Change in package.json if needed
8. **QR code linking requires open modal** - Closing modal kills session within 5s (heartbeat-based)
