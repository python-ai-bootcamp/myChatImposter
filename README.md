# My WhatsApp Imposter

This project is a modular chatbot framework designed for easy extension to various messaging platforms. It operates as an API server that dynamically manages multiple users, each with their own dedicated chatbot instance, message queue, and integration with a specific messaging service (a "vendor").

The core design philosophy is to isolate the chatbot logic from the specifics of the communication platform, allowing developers to add support for new platforms without modifying the core application code.

## Core Components

The project is composed of a few key Python modules:

-   **`main.py`**: This is the main entry point of the application. It runs a FastAPI web server that exposes endpoints for creating, managing, and polling the status of chatbot instances.

-   **`chatbot_manager.py`**: This module provides the `ChatbotInstance` class, which encapsulates all the components for a single user's session (message queue, LLM model, and vendor connection).

-   **`queue_manager.py`**: This module provides a `UserQueue` class that manages a queue of messages for each user. It's designed to be resilient, with configurable limits on the number of messages, total characters, and message age.

-   **`chat_vendors/`**: This directory is the key to the project's extensibility. Each file within this directory is expected to be a self-contained module that provides a connection to a specific messaging platform (like WhatsApp, Slack, etc.).

-   **`llm_providers/`**: Similar to vendors, this directory contains modules for different Large Language Model providers (like OpenAI, or a local Fake LLM for testing).

## API Usage

The server is controlled via a RESTful API.

### Create a Chatbot Instance

To create a new chatbot instance, send a `PUT` request to the `/chatbot` endpoint with a JSON body containing the user's configuration.

**Endpoint:** `PUT /chatbot`

**Body:**
```json
{
  "user_id": "user_wa_1",
  "respond_to_whitelist": [
    "1234567890"
  ],
  "chat_vendor_config": {
    "vendor_name": "whatsAppBaileyes",
    "vendor_config": {
      "allow_group_messages": false,
      "process_offline_messages": false
    }
  },
  "queue_config": {
    "max_messages": 10,
    "max_characters": 1000,
    "max_days": 1
  },
  "llm_vendor_config": {
    "vendor_name": "openAi",
    "vendor_config": {
      "model": "gpt-4",
      "temperature": 0.7,
      "system": "You are a helpful assistant."
    }
  }
}
```
The server will respond with a unique `instance_id`.

### Poll for Status

You can poll the status of an instance (e.g., to get a QR code for linking) by sending a `GET` request.

**Endpoint:** `GET /chatbot/{instance_id}/status`

## Extensibility: Adding New Chat Vendors

To add support for a new platform, you simply need to create a new vendor file.

**1. Create the Vendor File**

Create a new file in the `chat_vendors/` directory, for example, `chat_vendors/my_new_vendor.py`.

**2. Create the Vendor Class**

Your class must implement the following methods:

-   `__init__(self, user_id: str, config: Dict, user_queues: Dict[str, UserQueue])`: The constructor receives the `user_id`, its specific `vendor_config` block, and the user's queue.
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
2.  Install the Node.js dependencies for the WhatsApp vendor:
    ```bash
    npm install --prefix chat_vendors/whatsapp_baileys_server
    ```
3.  Set your OpenAI API key as an environment variable (if using the OpenAI provider):
    ```bash
    export OPENAI_API_KEY='your-api-key'
    ```
4.  Run the FastAPI server:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```
The server will start, and you can begin creating chatbot instances via the API.
