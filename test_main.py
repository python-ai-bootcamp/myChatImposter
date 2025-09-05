import json
from fastapi.testclient import TestClient
from main import app, CONFIGURATIONS_DIR
import os
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup: ensure the configurations directory exists
    if not CONFIGURATIONS_DIR.exists():
        CONFIGURATIONS_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Teardown: clean up any created files
    for f in os.listdir(CONFIGURATIONS_DIR):
        if f.endswith('.json'):
            os.remove(CONFIGURATIONS_DIR / f)

def test_save_single_configuration():
    config_data = {
        "user_id": "test_user_single",
        "respond_to_whitelist": ["12345"],
        "chat_provider_config": {
            "provider_name": "dummy",
            "provider_config": {}
        },
        "queue_config": {
            "max_messages": 5
        },
        "llm_provider_config": None
    }
    response = client.put("/api/configurations/test_single.json", json=config_data)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "filename": "test_single.json"}

    # Verify the file was created and has the correct content
    file_path = CONFIGURATIONS_DIR / "test_single.json"
    assert file_path.exists()
    with open(file_path, 'r') as f:
        saved_data = json.load(f)
    assert saved_data["user_id"] == "test_user_single"

def test_save_array_configuration():
    config_data = [
        {
            "user_id": "test_user_array",
            "respond_to_whitelist": ["67890"],
            "chat_provider_config": {
                "provider_name": "dummy",
                "provider_config": {}
            },
            "queue_config": {
                "max_messages": 10
            },
            "llm_provider_config": None
        }
    ]
    response = client.put("/api/configurations/test_array.json", json=config_data)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "filename": "test_array.json"}

    # Verify the file was created and has the correct content
    file_path = CONFIGURATIONS_DIR / "test_array.json"
    assert file_path.exists()
    with open(file_path, 'r') as f:
        saved_data = json.load(f)
    assert isinstance(saved_data, list)
    assert len(saved_data) == 1
    assert saved_data[0]["user_id"] == "test_user_array"

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
