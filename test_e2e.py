
import json
from fastapi.testclient import TestClient
from main import app
import pytest
from pymongo import MongoClient
import os
import time

client = TestClient(app)
mongo_client: MongoClient = None

@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown_function(monkeypatch):
    global mongo_client
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/")
    mongodb_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017/")
    retries = 5
    while retries > 0:
        try:
            mongo_client = MongoClient(mongodb_url, serverSelectionTimeoutMS=2000)
            mongo_client.admin.command('ismaster')
            break
        except Exception:
            retries -= 1
            time.sleep(3)
    if retries == 0:
        pytest.fail("Could not connect to MongoDB after several retries.")
    with TestClient(app):
        yield
    if mongo_client:
        db = mongo_client.get_database("chat_manager")
        db.get_collection("configurations").delete_many({"config_data.user_id": {"$regex": "^test_user_"}})
        db.get_collection("queues").delete_many({"user_id": {"$regex": "^test_user_"}})
        mongo_client.close()

def test_group_and_direct_message_queues():
    user_id = "test_user_e2e"
    direct_correspondent_id = "direct_user@s.whatsapp.net"
    group_correspondent_id = "group_id@g.us"

    # 1. Create a test user and configuration
    config_data = {
        "user_id": user_id,
        "respond_to_whitelist": [direct_correspondent_id],
        "respond_to_whitelist_group": [group_correspondent_id],
        "chat_provider_config": {"provider_name": "dummy", "provider_config": {}},
        "queue_config": {"max_messages": 5},
        "llm_provider_config": None
    }
    response_put = client.put(f"/api/configurations/{user_id}", json=config_data)
    assert response_put.status_code == 200

    # 2. Simulate the chat provider sending messages
    db = mongo_client.get_database("chat_manager")
    queues_collection = db.get_collection("queues")
    mock_messages = [
        {"id": 1, "content": "Direct message", "sender": {"identifier": direct_correspondent_id, "display_name": "Direct User"}, "source": "user", "user_id": user_id, "provider_name": "whatsAppBaileyes", "correspondent_id": direct_correspondent_id},
        {"id": 1, "content": "Group message", "sender": {"identifier": "another_user@s.whatsapp.net", "display_name": "Group User"}, "source": "user", "user_id": user_id, "provider_name": "whatsAppBaileyes", "correspondent_id": group_correspondent_id, "group": {"identifier": group_correspondent_id, "display_name": "Test Group"}}
    ]
    queues_collection.insert_many(mock_messages)

    # 3. Call the /api/queue/{user_id} endpoint
    response_get = client.get(f"/api/queue/{user_id}")
    assert response_get.status_code == 200
    data = response_get.json()

    # 4. Assert that the response contains two separate queues
    assert direct_correspondent_id in data
    assert group_correspondent_id in data
    assert len(data[direct_correspondent_id]) == 1
    assert data[direct_correspondent_id][0]['content'] == "Direct message"
    assert len(data[group_correspondent_id]) == 1
    assert data[group_correspondent_id][0]['content'] == "Group message"

    # 5. I will also check the `log/` directory to confirm that two separate log files have been created.
    # This part of the verification will be done manually, as the test environment does not have access to the log files.
