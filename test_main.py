import json
from fastapi.testclient import TestClient
from main import app
import pytest
from pymongo import MongoClient
import os

# It's better to use a separate test database
# For this example, we'll use the same DB but clean up after.
# A more robust solution would use a dedicated test DB and mock the client.
client = TestClient(app)
mongo_client: MongoClient = None

import time

@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown_function(monkeypatch):
    global mongo_client

    # Set the environment variable for the application to use the correct MongoDB URL for tests.
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/")

    # When running tests from outside the docker-compose network, we connect via localhost.
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/")

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
        db.get_collection("configurations").delete_many({})
        db.get_collection("queues").delete_many({})
        mongo_client.close()


def test_save_and_get_single_configuration():
    user_id = "test_user_single"
    config_data = {
        "user_id": user_id,
        "configurations": {
            "chat_provider_config": {"provider_name": "dummy", "provider_config": {}},
            "queue_config": {"max_messages": 5},
            "llm_provider_config": {
                "provider_name": "fakeLlm",
                "provider_config": {"model": "fake", "temperature": 0.7}
            }
        },
        "features": {
            "automatic_bot_reply": {
                "enabled": False,
                "respond_to_whitelist": ["12345"],
                "respond_to_whitelist_group": [],
                "chat_system_prompt": ""
            }
        }
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
            "configurations": {
                "chat_provider_config": {"provider_name": "dummy", "provider_config": {}},
                "queue_config": {"max_messages": 10},
                "llm_provider_config": {
                    "provider_name": "fakeLlm",
                    "provider_config": {"model": "fake", "temperature": 0.7}
                }
            },
            "features": {
                "automatic_bot_reply": {
                    "enabled": False,
                    "respond_to_whitelist": ["67890"],
                    "respond_to_whitelist_group": [],
                    "chat_system_prompt": ""
                }
            }
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

def test_get_configuration_schema_api_key_logic():
    response = client.get("/api/configurations/schema")
    assert response.status_code == 200
    schema = response.json()

    defs_key = '$defs' if '$defs' in schema else 'definitions'
    llm_settings_schema = schema[defs_key]['LLMProviderSettings']

    # Check that the top level is a oneOf
    assert 'oneOf' in llm_settings_schema
    assert len(llm_settings_schema['oneOf']) == 2

    # Find the 'environment' and 'explicit' schemas
    env_schema = next((s for s in llm_settings_schema['oneOf'] if s['properties']['api_key_source']['const'] == 'environment'), None)
    explicit_schema = next((s for s in llm_settings_schema['oneOf'] if s['properties']['api_key_source']['const'] == 'explicit'), None)

    assert env_schema is not None
    assert explicit_schema is not None

    # The environment schema should NOT have 'api_key' as a property
    assert 'api_key' not in env_schema['properties']

    # The explicit schema SHOULD have 'api_key' as a required property
    assert 'api_key' in explicit_schema['properties']
    assert 'api_key' in explicit_schema['required']

def test_delete_configuration():
    user_id = "test_user_to_delete"
    config_data = {
        "user_id": user_id,
        "configurations": {
            "chat_provider_config": {"provider_name": "dummy", "provider_config": {}},
            "queue_config": {},
            "llm_provider_config": {
                "provider_name": "fakeLlm",
                "provider_config": {"model": "fake", "temperature": 0.7}
            }
        },
        "features": {
            "automatic_bot_reply": {
                "enabled": False,
                "respond_to_whitelist": [],
                "respond_to_whitelist_group": [],
                "chat_system_prompt": ""
            }
        }
    }

    # Create it first
    client.put(f"/api/configurations/{user_id}", json=config_data)

    # Delete it
    response_delete = client.delete(f"/api/configurations/{user_id}")
    assert response_delete.status_code == 200
    assert response_delete.json() == {"status": "success", "user_id": user_id}

    # Verify it's gone
    response_get = client.get(f"/api/configurations/{user_id}")
    assert response_get.status_code == 404


from unittest.mock import patch, MagicMock

def test_get_user_queue_empty():
    """ Test getting a queue for a user with no messages, should return 200 OK and an empty object. """
    response = client.get("/api/queue/non_existent_user")
    assert response.status_code == 200
    assert response.json() == {}

def test_get_user_queue_success():
    """ Test getting queues for a user, which should be grouped by correspondent ID. """
    user_id = "test_user_queue_success"
    db = mongo_client.get_database("chat_manager")
    queues_collection = db.get_collection("queues")

    # Insert some mock messages for the test user from different correspondents
    mock_messages = [
        {"id": 1, "content": "Hello from cor1", "sender": {"identifier": "user1", "display_name": "User 1"}, "source": "user", "user_id": user_id, "provider_name": "test", "correspondent_id": "cor1"},
        {"id": 1, "content": "Hello from cor2", "sender": {"identifier": "user2", "display_name": "User 2"}, "source": "user", "user_id": user_id, "provider_name": "test", "correspondent_id": "cor2"},
        {"id": 2, "content": "Hi there from cor1", "sender": {"identifier": "bot", "display_name": "Bot"}, "source": "bot", "user_id": user_id, "provider_name": "test", "correspondent_id": "cor1"}
    ]
    queues_collection.insert_many(mock_messages)

    response = client.get(f"/api/queue/{user_id}")
    assert response.status_code == 200

    data = response.json()

    # We should have keys for each correspondent
    assert "cor1" in data
    assert "cor2" in data

    # Check the contents of each correspondent's queue
    assert len(data["cor1"]) == 2
    assert data["cor1"][0]["content"] == "Hello from cor1"
    assert data["cor1"][1]["id"] == 2

    assert len(data["cor2"]) == 1
    assert data["cor2"][0]["content"] == "Hello from cor2"

    # The API should not return the internal DB fields
    assert "user_id" not in data["cor1"][0]
    assert "provider_name" not in data["cor1"][0]
    assert "correspondent_id" not in data["cor1"][0]
    assert "_id" not in data["cor1"][0]

def test_get_user_context():
    user_id = "test_user_context"
    with patch('main.active_users', {user_id: "instance_id"}), \
         patch('main.chatbot_instances') as mock_instances:

        # Mock instance and model
        mock_instance = MagicMock()
        mock_model = MagicMock()
        mock_instance.chatbot_model = mock_model
        mock_instances.get.return_value = mock_instance

        # Mock history
        mock_history = MagicMock()
        mock_history.messages = [
            MagicMock(type='human', content='Hello'),
            MagicMock(type='ai', content='Bot: Hi')
        ]
        mock_model.get_all_histories.return_value = {"corr1": mock_history}

        response = client.get(f"/api/context/{user_id}")
        assert response.status_code == 200
        assert response.json() == {"corr1": ["Hello", "Bot: Hi"]}
