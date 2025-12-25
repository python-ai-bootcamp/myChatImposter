import json
from fastapi.testclient import TestClient
from main import app, active_users, chatbot_instances
from queue_manager import Message, Sender
from unittest.mock import MagicMock
import pytest
from pymongo import MongoClient
import os

# It's better to use a separate test database
# For this example, we'll use the same DB but clean up after.
# A more robust solution would use a dedicated test DB and mock the client.
client = TestClient(app)
mongo_client: MongoClient = None

import time

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_module():
    global mongo_client

    # Use the service name from docker-compose, which is the correct way to connect between containers.
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017/")

    # Add a retry loop to wait for the MongoDB container to be ready.
    retries = 5
    while retries > 0:
        try:
            mongo_client = MongoClient(mongodb_url, serverSelectionTimeoutMS=2000)
            mongo_client.admin.command('ismaster') # The ismaster command is cheap and does not require auth.
            print("Successfully connected to MongoDB for testing.")
            break
        except Exception:
            retries -= 1
            print(f"Waiting for MongoDB... retries left: {retries}")
            time.sleep(3)

    if retries == 0:
        pytest.fail("Could not connect to MongoDB after several retries.")

    # This context manager will trigger the app's startup event.
    # The app should now be able to connect to the DB as we've waited for it.
    with TestClient(app):
        yield

    # Teardown: clean up any created test data
    if mongo_client:
        db = mongo_client.get_database("chat_manager")
        collection = db.get_collection("configurations")
        collection.delete_many({"config_data.user_id": {"$regex": "^test_user_"}})
        mongo_client.close()


def test_save_and_get_single_configuration():
    user_id = "test_user_single"
    config_data = {
        "user_id": user_id,
        "respond_to_whitelist": ["12345"],
        "chat_provider_config": {"provider_name": "dummy", "provider_config": {}},
        "queue_config": {"max_messages": 5},
        "llm_provider_config": None
    }

    # PUT to save
    response_put = client.put(f"/api/configurations/{user_id}", json=config_data)
    assert response_put.status_code == 200
    assert response_put.json() == {"status": "success", "user_id": user_id}

    # GET to verify
    response_get = client.get(f"/api/configurations/{user_id}")
    assert response_get.status_code == 200
    saved_data = response_get.json()
    assert saved_data["user_id"] == user_id

def test_save_and_get_array_configuration():
    user_id = "test_user_array"
    config_data = [
        {
            "user_id": user_id,
            "respond_to_whitelist": ["67890"],
            "chat_provider_config": {"provider_name": "dummy", "provider_config": {}},
            "queue_config": {"max_messages": 10},
            "llm_provider_config": None
        }
    ]

    # PUT to save
    response_put = client.put(f"/api/configurations/{user_id}", json=config_data)
    assert response_put.status_code == 200
    assert response_put.json() == {"status": "success", "user_id": user_id}

    # GET to verify
    response_get = client.get(f"/api/configurations/{user_id}")
    assert response_get.status_code == 200
    saved_data = response_get.json()
    assert isinstance(saved_data, list)
    assert len(saved_data) == 1
    assert saved_data[0]["user_id"] == user_id

def test_get_configuration_schema_allows_null_api_key():
    response = client.get("/api/configurations/schema")
    assert response.status_code == 200
    schema = response.json()

    defs_key = '$defs' if '$defs' in schema else 'definitions'

    llm_provider_settings = schema[defs_key]['LLMProviderSettings']
    api_key_schema = llm_provider_settings['properties']['api_key']

    assert 'anyOf' in api_key_schema

    type_options = [item.get('type') for item in api_key_schema['anyOf']]
    assert 'string' in type_options
    assert 'null' in type_options

def test_delete_configuration():
    user_id = "test_user_to_delete"
    config_data = {"user_id": user_id, "respond_to_whitelist": [], "chat_provider_config": {"provider_name": "dummy", "provider_config": {}}, "queue_config": {}}

    # Create it first
    client.put(f"/api/configurations/{user_id}", json=config_data)

    # Delete it
    response_delete = client.delete(f"/api/configurations/{user_id}")
    assert response_delete.status_code == 200
    assert response_delete.json() == {"status": "success", "user_id": user_id}

    # Verify it's gone
    response_get = client.get(f"/api/configurations/{user_id}")
    assert response_get.status_code == 404


def test_get_user_queue_success():
    user_id = "test_user"
    instance_id = "test_instance"

    # Mock the chatbot instance and its queue
    mock_instance = MagicMock()
    mock_queue = MagicMock()
    mock_instance.user_queue = mock_queue

    # Mock the return value of get_messages
    mock_messages = [
        Message(id=1, content="Hello", sender=Sender(identifier="user1", display_name="User 1"), source="user"),
        Message(id=2, content="Hi there", sender=Sender(identifier="bot1", display_name="Bot 1"), source="bot")
    ]
    mock_queue.get_messages.return_value = mock_messages

    # Add the mock instance to the active users and chatbot instances
    active_users[user_id] = instance_id
    chatbot_instances[instance_id] = mock_instance

    response = client.get(f"/api/queue/{user_id}")

    assert response.status_code == 200

    # Convert mock_messages to a JSON-serializable format
    response_json = response.json()

    # We need to manually construct the expected JSON because the dataclass-to-JSON
    # conversion is handled by FastAPI, and we need to match its output.
    # The `accepted_time` is dynamic, so we'll copy it from the response.
    expected_json = [
        {
            "id": msg.id,
            "content": msg.content,
            "sender": {
                "identifier": msg.sender.identifier,
                "display_name": msg.sender.display_name,
                "alternate_identifiers": msg.sender.alternate_identifiers
            },
            "source": msg.source,
            "accepted_time": resp_msg["accepted_time"], # Use the actual timestamp from the response
            "message_size": msg.message_size,
            "originating_time": msg.originating_time,
            "group": msg.group,
            "provider_message_id": msg.provider_message_id
        } for msg, resp_msg in zip(mock_messages, response_json)
    ]

    assert response_json == expected_json

    # Clean up
    del active_users[user_id]
    del chatbot_instances[instance_id]


def test_get_user_queue_not_found():
    response = client.get("/api/queue/non_existent_user")
    assert response.status_code == 404
