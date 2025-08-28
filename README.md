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

## Extensibility: Adding New Chat Providers

To add support for a new platform, you simply need to create a new provider file.

**1. Create the Provider File**

Create a new file in the `chat_providers/` directory, for example, `chat_providers/my_new_provider.py`.

**2. Create the Provider Class**

Your class must implement the following methods:

-   `__init__(self, user_id: str, config: Dict, user_queues: Dict[str, UserQueue])`: The constructor receives the `user_id`, its specific `provider_config` block, and the user's queue.
-   `start_listening(self)`: A non-blocking method to start listening for incoming messages.
-   `sendMessage(self, recipient: str, message: str)`: A method to send an outgoing message.

When a message is received, add it to the queue:
```python
# Inside your listening loop:
queue = self.user_queues.get(self.user_id)
if queue:
    # ... create sender, group objects
    queue.add_message(content=received_content, sender=sender, source='user', group=group)
```

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
