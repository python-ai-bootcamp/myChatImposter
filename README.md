# My WhatsApp Imposter

This project is a modular chatbot framework designed for easy extension to various messaging platforms. It operates as an API server that dynamically manages multiple users, each with their own dedicated chatbot instance, message queue, and integration with a specific messaging service (a "chat provider").

The core design philosophy is to isolate the chatbot logic from the specifics of the communication platform, allowing developers to add support for new platforms without modifying the core application code.

## Core Components

The project is composed of a few key Python modules:

-   **`main.py`**: This is the main entry point of the application. It runs a FastAPI web server that exposes endpoints for creating, managing, and polling the status of chatbot instances.

-   **`chatbot_manager.py`**: This module provides the `ChatbotInstance` class, which encapsulates all the components for a single user's session (message queue, LLM model, and chat provider connection).

-   **`queue_manager.py`**: This module provides a `UserQueue` class that manages a queue of messages for each user. It's designed to be resilient, with configurable limits on the number of messages, total characters, and message age.

-   **`chat_providers/`**: This directory is the key to the project's extensibility. Each file within this directory is expected to be a self-contained module that provides a connection to a specific messaging platform (like WhatsApp, Slack, etc.).

-   **`llm_providers/`**: Similar to chat providers, this directory contains modules for different Large Language Model providers (like OpenAI, or a local Fake LLM for testing).

## API Usage

The server is controlled via a RESTful API.

### Create Chatbot Instance(s)

To create one or more new chatbot instances, send a `PUT` request to the `/chatbot` endpoint with a JSON array of configuration objects.

**Endpoint:** `PUT /chatbot`

**Body:**
```json
[
  {
    "user_id": "user_wa_1",
    "respond_to_whitelist": [
      "1234567890"
    ],
    "chat_provider_config": {
      "provider_name": "whatsAppBaileyes",
      "provider_config": {
        "allow_group_messages": false
      }
    },
    "queue_config": {
      "max_messages": 10,
      "max_characters": 1000,
      "max_days": 1
    },
    "llm_provider_config": {
      "provider_name": "openAi",
      "provider_config": {
        "api_key": "sk-...",
        "model": "gpt-4",
        "system": "You are helpful assistant #1."
      }
    }
  },
  {
    "user_id": "user_wa_2",
    "chat_provider_config": {
      "provider_name": "dummy",
      "provider_config": {}
    },
    "queue_config": {
      "max_messages": 5,
      "max_characters": 500,
      "max_days": 1
    },
    "llm_provider_config": {
      "provider_name": "openAi",
      "provider_config": {
        "api_key": "sk-...",
        "model": "gpt-3.5-turbo",
        "system": "You are helpful assistant #2."
      }
    }
  }
]
```
The server will respond with an array of objects, each containing the `user_id` and a unique `instance_id` for each successfully created instance.

**Example Response:**
```json
[
    {
        "user_id": "user_wa_1",
        "instance_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
    },
    {
        "user_id": "user_wa_2",
        "instance_id": "f6e5d4c3-b2a1-0987-6543-210987fedcba"
    }
]
```

### Poll for Status

You can poll the status of an instance (e.g., to get a QR code for linking) by sending a `GET` request.

**Endpoint:** `GET /chatbot/{instance_id}/status`

## Extensibility: Adding New Providers

The application is designed to be easily extensible with new chat and LLM providers.

### Adding a New Chat Provider

To add support for a new messaging platform, you need to create a new provider file in the `chat_providers/` directory.

**1. Create the Provider File**

Create a new file, for example, `chat_providers/my_new_provider.py`.

**2. Create the Provider Class**

Inside your new file, create a class that inherits from `chat_providers.base.BaseChatProvider`. This base class ensures your provider implements the required interface.

Your class must implement the following abstract methods:

-   `__init__(self, user_id: str, config: Dict, user_queues: Dict[str, UserQueue])`: The constructor receives the `user_id`, its specific `provider_config` block, and the user's queue. You must call `super().__init__(...)`.
-   `start_listening(self)`: A non-blocking method to start listening for incoming messages.
-   `stop_listening(self)`: A method to gracefully stop the listening process.
-   `sendMessage(self, recipient: str, message: str)`: A method to send an outgoing message.
-   `get_status(self) -> Dict`: A method to return the current status of the provider (e.g., for connection health checks).

When a message is received, you can add it to the user's queue like this:
```python
# Inside your listening loop:
queue = self.user_queues.get(self.user_id)
if queue:
    # ... create sender, group objects from the received message
    queue.add_message(content=received_content, sender=sender, source='user', group=group)
```

The application will automatically discover your new provider class as long as it's the only class in the file that inherits from `BaseChatProvider`.

### Adding a New LLM Provider

Similarly, you can add a new Large Language Model provider by creating a file in the `llm_providers/` directory.

**1. Create the Provider File**

Create a new file, for example, `llm_providers/my_new_llm.py`.

**2. Create the Provider Class**

Create a class that inherits from `llm_providers.base.BaseLlmProvider`.

Your class must implement the following abstract methods:

-   `__init__(self, config: dict, user_id: str)`: The constructor. Remember to call `super().__init__(...)`.
-   `get_llm(self)`: This method should return an instance of the LLM client, typically a LangChain-compatible object.
-   `get_system_prompt(self) -> str`: This method should return the system prompt to be used for the chatbot.

The application will discover your new LLM provider class automatically.

## Troubleshooting WhatsApp Baileys sessions

If a WhatsApp session oscillates between `connecting` and `closed`, check the Node container logs (`whatsapp_baileys_server`). The server now auto-fetches the most recent WhatsApp Web version via `fetchLatestBaileysVersion`, so version drift should resolve automatically when the container restarts.

If you still see rapid-fire HTTP 405 disconnects, the server will retry up to three times within 30 seconds. When every attempt fails with 405, it logs a message such as:

```
[tal] Persistent 405 errors: 3 hits over 12000ms. POPs: vll, lla, cln
```

At that point the server deletes the stored auth keys for the user and starts a fresh session so a new QR can be presented. This usually resolves real protocol mismatches or WhatsApp forcing a relink. If 405 errors continue even after a relink, double-check that your network/firewall allows WebSocket traffic, and consider restarting the entire Docker stack to force a clean environment.

## How to Run


1.  Install the required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Install the Node.js dependencies for the WhatsApp provider:
    ```bash
    npm install --prefix chat_providers/whatsapp_baileys_server
    ```
3.  **Provide OpenAI API Key:** You can provide your API key in one of two ways. The JSON method takes precedence.
    -   **Method 1: Environment Variable (recommended for development)**
        Set the `OPENAI_API_KEY` environment variable before running the server. The key will be used for any OpenAI session that doesn't have an API key specified in its JSON config.
        ```bash
        export OPENAI_API_KEY='your-api-key'
        uvicorn main:app --host 0.0.0.0 --port 8000
        ```
    -   **Method 2: In the JSON request**
        Include the `api_key` directly in the `provider_config` for the `llm_provider_config` when you create a session via the API. This is useful for production environments where each user might have a different key. See the example in the "API Usage" section.

4.  Run the FastAPI server:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```
The server will start, and you can begin creating chatbot instances via the API.
