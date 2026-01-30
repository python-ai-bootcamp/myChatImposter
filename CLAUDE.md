# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**My Chat Imposter** is a modular chatbot framework that mimics human personalities on WhatsApp. It uses a layered architecture with FastAPI (Python) backend, React frontend, and Node.js Baileys for WhatsApp integration.

## Development Commands

### Running the Application
```bash
# Start all services (MongoDB, gateway, backend, frontend, WhatsApp server)
docker-compose up --build

# Access points:
# - Frontend: http://localhost:3000
# - Gateway (authenticated API): http://localhost:8001
# - Backend: Internal only (not exposed, accessible via gateway)
# - MongoDB: localhost:27017 (requires authentication)

# First-time setup: Create admin user
docker exec -it backend python scripts/create_admin_user.py admin
# You'll be prompted for a password (not visible in terminal)
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

**1. Gateway (Python/FastAPI)** - Port 8001 (PUBLIC)
- **gateway/main.py**: Authentication gateway with session management
- **gateway/session_manager.py**: Session lifecycle with in-memory caching (5min TTL)
- **gateway/rate_limiter.py**: Login rate limiting (10 attempts/min per IP)
- **gateway/account_lockout.py**: Account lockout manager (10 failed attempts = 5min lock)
- **gateway/audit_logger.py**: Security event logging with 30-day retention
- **gateway/permission_validator.py**: User ownership validation (admin vs user roles)
- **gateway/middleware.py**: Authentication + request size limit (80KB) enforcement
- **gateway/routers/auth.py**: Login/logout endpoints
- **gateway/routers/proxy.py**: Proxies `/api/external/*` → Backend `/api/internal/*`
- **Security Features**: Bcrypt password hashing, HTTPOnly cookies, session expiration (24h)

**2. Backend (Python/FastAPI)** - Port 8000 (INTERNAL ONLY)
- **main.py**: Application entry point with lifespan management
- **dependencies.py**: GlobalStateManager singleton for application-wide state
- **services/session_manager.py**: Manages per-user chatbot sessions (one per connected user)
- **services/user_auth_service.py**: Password hashing and credential management
- **queue_manager.py**: Message buffer with per-correspondent queues
- **async_message_delivery_queue_manager.py**: Three-state delivery queue (active/holding/failed)
- **auth_models.py**: Authentication data models (UserAuthCredentials, SessionData, AuditLog)
- **All routers**: Use `/api/internal/*` prefix (only accessible via gateway)

**3. Frontend (React)** - Port 3000
- Dynamic form generation using `react-jsonschema-form` (`@rjsf/core`)
- **src/pages/LoginPage.js**: Authentication interface
- **src/pages/HomePage.js**: User dashboard with session management
- **src/pages/EditPage.js**: Configuration editor with JSON Schema validation
- **src/utils/authApi.js**: Authentication API client
- **Proxy**: All API calls routed through gateway (port 8001)

**4. WhatsApp Provider (Node.js/Baileys)** - Port 9000
- **chat_providers/whatsapp_baileys_server/**: Separate Node.js service
- Communicates via HTTP + WebSocket with backend
- Handles QR code authentication and message encryption

**5. Database (MongoDB)** - Port 27017
- **Authentication required**: Username: `admin`, Password: from `MONGO_PASSWORD` env var
- **configurations**: User configurations
- **queues**: Persisted message history
- **baileys_sessions**: WhatsApp authentication credentials
- **async_message_delivery_queue_***: Three collections for message delivery states
- **authenticated_sessions**: Active user sessions (24h TTL)
- **stale_authenticated_sessions**: Invalidated sessions (30-day retention)
- **user_auth_credentials**: User credentials with bcrypt hashed passwords
- **audit_logs**: Security events (30-day TTL auto-cleanup)
- **account_lockouts**: Failed login attempt tracking

### Key Design Patterns

**Gateway Pattern**: Reverse proxy for authentication and authorization before forwarding to backend services.

**Observer Pattern**: SessionManager notifies feature handlers of incoming messages through registered callbacks.

**Factory Pattern**: Dynamic loading of chat providers and LLM providers by name using reflection.

**Queue Pattern**: Three-state delivery queue (active → holding on disconnect, holding → active on connect, active → failed after 3 attempts).

**Singleton Pattern**: GlobalStateManager maintains single instance of application state including active chatbot instances dictionary.

**Middleware Pattern**: Authentication and permission checks applied transparently to all requests via FastAPI middleware.

## Code Organization

### Backend Structure
```
├── main.py                          # FastAPI app, lifespan, routers
├── config_models.py                 # Pydantic configuration models
├── auth_models.py                   # Authentication data models (NEW)
├── dependencies.py                  # Global state manager
├── queue_manager.py                 # Message queues (UserQueuesManager)
├── async_message_delivery_queue_manager.py  # Async delivery system
├── gateway/                         # Authentication Gateway (NEW)
│   ├── main.py                      # Gateway FastAPI app
│   ├── dependencies.py              # GatewayStateManager
│   ├── session_manager.py           # Session lifecycle
│   ├── rate_limiter.py              # Login rate limiting
│   ├── account_lockout.py           # Account lockout manager
│   ├── audit_logger.py              # Security event logging
│   ├── permission_validator.py      # Permission checks
│   ├── middleware.py                # Auth + size limit middleware
│   └── routers/
│       ├── auth.py                  # Login/logout endpoints
│       └── proxy.py                 # Request forwarding
├── routers/                         # All use /api/internal/* prefix
│   ├── user_management.py           # User CRUD and session control
│   ├── async_message_delivery_queue.py
│   ├── resources.py                 # Languages, timezones
│   └── features/
│       ├── automatic_bot_reply.py
│       └── periodic_group_tracking.py
├── services/
│   ├── session_manager.py           # Per-user session orchestrator
│   ├── user_auth_service.py         # Password hashing (NEW)
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
├── message_processors/
│   ├── factory.py                   # Message type routing
│   ├── text_processor.py
│   └── ics_processor.py
└── scripts/
    └── create_admin_user.py         # Admin user creation (NEW)
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

**External Request Flow (via Gateway):**
```
Client (Browser/API) → Gateway:8001
  ↓ Check session cookie
  ↓ Validate session (MongoDB + cache)
  ↓ Check permissions (admin vs user)
  ↓ Transform /api/external/* → /api/internal/*
  → Backend:8000 (internal) → Process → Response
  → Gateway → Client
```

**WhatsApp Message Flow:**
```
WhatsApp → Node.js Baileys (WebSocket) → WhatsAppBaileysProvider
  → UserQueuesManager (per-correspondent queues)
  → SessionManager (observer dispatch)
  → Feature Handlers (AutomaticBotReply, PeriodicGroupTracking)
  → LLM Provider (OpenAI)
  → Response → Provider → WhatsApp
```

**Authentication Flow:**
```
1. POST /api/external/auth/login
   ↓ Rate limit check (10 attempts/min per IP)
   ↓ Account lockout check (10 attempts = 5min lock)
   ↓ Password verification (bcrypt)
   ↓ Create session (24h expiration)
   ↓ Set HTTPOnly cookie
   ↓ Log to audit_logs
   → Return success + user info

2. Subsequent requests
   ↓ Middleware extracts session_id cookie
   ↓ Validate session (check expiration)
   ↓ Extract user_id from path
   ↓ Check permission (admin=bypass, user=match)
   ↓ Forward to backend
   → Return response
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
| gateway/main.py | Gateway app with auth and background tasks | lifespan, cleanup tasks |
| gateway/session_manager.py | Session lifecycle (24h expiration, 5min cache) | - |
| gateway/middleware.py | Auth + permission + size limit checks | - |
| auth_models.py | Authentication data models | - |
| services/user_auth_service.py | Password hashing and validation | bcrypt 12 rounds |
| dependencies.py | GlobalStateManager singleton | - |
| services/session_manager.py | Per-user session orchestrator | - |
| queue_manager.py | Message queues and limits | - |
| async_message_delivery_queue_manager.py | Three-state delivery queue | consumer_loop:100-150 |
| chat_providers/whatsAppBaileyes.py | WhatsApp WebSocket integration | auto_reconnect:180-220 |
| features/automatic_bot_reply/service.py | AI auto-reply feature | - |
| features/periodic_group_tracking/service.py | Cron-based group monitoring | - |
| llm_providers/openAi.py | OpenAI ChatCompletion integration | - |
| scripts/create_admin_user.py | Admin user creation with password prompt | - |

## Common Workflows

### Creating Admin Users

```bash
# After docker-compose up, create admin user
docker exec -it backend python scripts/create_admin_user.py admin

# You'll be prompted for password (not visible)
# Password must meet requirements:
# - Min 8 characters
# - Uppercase + lowercase + digit + symbol
```

### Creating Regular Users

Admin users can create regular users via the frontend:
1. Login as admin at http://localhost:3000
2. Navigate to user management
3. Create new user with role="user"
4. Regular users can only access their own resources

### Adding a New Feature

1. Create feature directory under `features/`
2. Implement feature service with message handler method
3. Register handler in SessionManager via `register_message_handler()`
4. Add configuration model to `config_models.py` FeaturesConfiguration
5. Create API router in `routers/features/` with `/api/internal/features/*` prefix
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

**Required in `.env` file:**
```bash
# OpenAI API Key (required for LLM features)
OPENAI_API_KEY=your_openai_api_key_here

# MongoDB Password (required for authentication)
MONGO_PASSWORD=your_secure_mongo_password_here
```

**Automatically set by docker-compose:**
```bash
MONGODB_URL=mongodb://admin:${MONGO_PASSWORD}@mongodb:27017  # MongoDB with auth
BACKEND_URL=http://backend:8000         # Gateway → Backend URL
GATEWAY_PORT=8001                       # Gateway port
WHATSAPP_SERVER_URL=http://whatsapp_baileys_server:9000  # Baileys server
PYTHONUNBUFFERED=1                      # Python logging
```

**IMPORTANT:** Never commit `.env` file to git (already in `.gitignore`).

## Debugging

**Logs**: Check `./log/` directory (mounted volume)

**Authentication APIs:**
- `POST /api/external/auth/login` - Login with credentials
- `POST /api/external/auth/logout` - Logout and invalidate session
- All other APIs require authentication (session cookie)

**Queue Inspection APIs (requires authentication):**
- `GET /api/external/async-message-delivery-queue/{queue_type}/{user_id}` - View queue contents
- `DELETE /api/external/async-message-delivery-queue/{queue_type}/{message_id}` - Delete message

**MongoDB Collections:**
- Connect with authentication: `mongodb://admin:your_password@localhost:27017`
```bash
# Using mongosh
docker exec -it mongodb mongosh -u admin -p your_password

use chat_manager

# View recent audit logs
db.audit_logs.find().sort({timestamp: -1}).limit(10).pretty()

# Check active sessions
db.authenticated_sessions.find().pretty()

# Check lockouts
db.account_lockouts.find().pretty()
```

**Collections:**
- **configurations**: User configurations
- **queues**: Persisted message history
- **baileys_sessions**: WhatsApp authentication
- **async_message_delivery_queue_***: Message delivery states
- **authenticated_sessions**: Active user sessions (24h TTL)
- **stale_authenticated_sessions**: Invalidated sessions (30-day retention)
- **user_auth_credentials**: User credentials (bcrypt hashed)
- **audit_logs**: Security events (30-day TTL)
- **account_lockouts**: Failed login tracking

**Test Data Cleanup:**
```python
# Backend automatically cleans test data using:
db.collection.delete_many({"user_id": {"$regex": "^test_"}})
```

**Security Testing:**
```bash
# Test rate limiting (should return 429 on 11th attempt)
for i in {1..11}; do curl -X POST http://localhost:8001/api/external/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","password":"wrong"}'; done

# Check audit logs
docker exec -it mongodb mongosh -u admin -p your_password \
  --eval "db.audit_logs.find({event_type: 'login_failed'}).limit(5).pretty()"
```

## Caveats and Gotchas

### Authentication & Security
1. **All API requests require authentication** - Except `/api/external/auth/login`, `/api/external/auth/logout`, `/`, `/docs`, `/health`
2. **Sessions expire after 24 hours** - Absolute expiration (not sliding window)
3. **Rate limiting is per IP** - 10 login attempts per minute per IP address
4. **Account lockout is per user_id** - 10 failed attempts locks account for 5 minutes
5. **Password requirements are strict** - Min 8 chars, uppercase, lowercase, digit, symbol
6. **User IDs must match `^[a-zA-Z0-9_-]+$`** - Prevents path traversal attacks
7. **Backend not directly accessible** - All requests must go through gateway (port 8001)
8. **MongoDB requires authentication** - Use `admin:${MONGO_PASSWORD}` credentials
9. **Admin bypass** - Admin role bypasses all permission checks (full access)
10. **Regular users are isolated** - Can only access resources where path contains their user_id
11. **Frontend proxy points to gateway** - NOT backend (changed from `backend:8000` to `gateway:8001`)

### System Behavior
12. **User IDs must be unique** - Used as keys in GlobalStateManager's active_users dict
13. **WebSocket reconnect has max 3 attempts** - After that, session must be manually restarted
14. **Message deduplication uses 100-item cache** - Very old message IDs may be processed twice
15. **Timezone-aware scheduling** - All cron schedules use user's configured timezone
16. **Group tracking windows are strict** - Uses cron-based time windows to prevent duplicate/missed messages
17. **Pending message TTL is 30s** - Messages in pending cache expire after 30 seconds
18. **QR code linking requires open modal** - Closing modal kills session within 5s (heartbeat-based)
19. **Audit logs auto-delete after 30 days** - MongoDB TTL index handles cleanup
20. **Session cache TTL is 5 minutes** - In-memory cache refreshes from MongoDB after 5min
