# My WhatsApp Imposter

This project is a modular chatbot framework designed for easy extension to various messaging platforms. It provides a robust architecture for managing multiple users, each with their own dedicated chatbot instance, message queue, and integration with a specific messaging service (a "vendor").

The core design philosophy is to isolate the chatbot logic from the specifics of the communication platform, allowing developers to add support for new platforms without modifying the core application code.

## Core Components

The project is composed of a few key Python modules:

-   **`chatbot.py`**: This is the heart of the application. The `Orchestrator` class reads the user configurations, dynamically loads the required "vendor" for each user, and manages the entire lifecycle of the chatbot instances. It wires up the message queues to the chatbot models and vendors.

-   **`queue_manager.py`**: This module provides a `UserQueue` class that manages a queue of messages for each user. It's designed to be resilient, with configurable limits on the number of messages, total characters, and message age to prevent memory issues.

-   **`vendor/`**: This directory is the key to the project's extensibility. Each file within this directory is expected to be a self-contained module that provides a connection to a specific messaging platform (like WhatsApp, Slack, etc.).

## Configuration

All user-specific setups are defined in `configurations/users.json`. This file contains a list of user objects, where each object defines:

-   `user_id`: A unique identifier for the user.
-   `vendor_name`: The name of the vendor module to use for this user (e.g., `dummy_vendor`). This must correspond to a file named `{vendor_name}.py` in the `vendor/` directory.
-   `vendor_config`: A dictionary containing any configuration needed for the vendor, such as API keys or tokens.
-   `queue_config`: A dictionary defining the behavior of the user's message queue (`max_messages`, `max_characters`, `max_days`).

### Example Configuration:

```json
[
  {
    "user_id": "user_a",
    "vendor_name": "dummy_vendor",
    "vendor_config": {
      "api_key": "dummy_key_for_user_a"
    },
    "queue_config": {
      "max_messages": 5,
      "max_characters": 100,
      "max_days": 1
    }
  }
]
```

## Extensibility: Adding New Vendors

The primary extension point of this project is the **Vendor System**. A "vendor" is a Python class responsible for handling all communication with a specific messaging service. To add support for a new platform, you simply need to create a new vendor file and update the configuration.

Here is a step-by-step guide:

**1. Create the Vendor File**

Create a new file in the `vendor/` directory, for example, `vendor/my_new_vendor.py`.

**2. Create the Vendor Class**

Inside your new file, create a class that follows the interface defined by the existing vendors. The `Orchestrator` currently assumes the class is named `DummyVendor`, so for now, it's best to stick to that name or modify the `Orchestrator` to handle different class names.

Your class must implement the following methods:

-   `__init__(self, user_id: str, config: Dict, user_queues: Dict[str, UserQueue])`:
    -   The constructor receives the `user_id` it's responsible for, its specific `config` from `users.json`, and a dictionary of *all* user queues in the system.

-   `start_listening(self)`:
    -   This method should start the process of listening for incoming messages from the external platform.
    -   **Crucially**, this should be a non-blocking operation. The recommended approach is to start a new thread for any long-running tasks like polling an API or maintaining a WebSocket connection.

-   `sendMessage(self, message: str)`:
    -   This method is called by the `Orchestrator` to send a reply back to the user via the vendor's platform.

**3. Implement the Listening Logic**

Inside your `start_listening` method (or the thread it spawns), you will implement the logic to receive messages. When a message is received from the platform, you must add it to this user's queue.

```python
# Inside your listening loop:
queue = self.user_queues.get(self.user_id)
if queue:
    queue.add_message(content=received_message_content, sending_user=self.user_id)
```

Adding a message to the queue will trigger the callback in the `Orchestrator`, which will then process the message with the chatbot and eventually call your `sendMessage` method with the response.

**4. Update the Configuration**

Finally, update `configurations/users.json` to tell a user to use your new vendor.

```json
{
  "user_id": "user_c",
  "vendor_name": "my_new_vendor", // The name of your Python file
  "vendor_config": {
    "api_key": "secret_api_key_for_new_vendor",
    "endpoint": "https://api.newvendor.com"
  },
  // ... queue config
}
```

## How to Run

1.  Ensure you have the required dependencies installed:
    ```bash
    pip install langchain langchain_community
    ```
2.  Run the main chatbot application:
    ```bash
    python chatbot.py
    ```
The application will start, initialize all configured users and their vendors, and begin listening for messages. The `dummy_vendor` will simulate receiving messages and print the conversation to the console.
