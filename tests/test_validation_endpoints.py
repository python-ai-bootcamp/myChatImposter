import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from main import app
from dependencies import get_global_state, GlobalStateManager

# Mock State
mock_state = MagicMock(spec=GlobalStateManager)
mock_state.credentials_collection = AsyncMock()
mock_state.configurations_collection = AsyncMock()
mock_state.credentials_collection.find_one.return_value = None # Default: Not found (Available)
mock_state.configurations_collection.find_one.return_value = None # Default: Not found (Available)

# Override Dependency
app.dependency_overrides[get_global_state] = lambda: mock_state

client = TestClient(app)

def test_validate_user_id_endpoint():
    # Setup Mock: User ID available
    mock_state.credentials_collection.find_one.return_value = None
    
    response = client.get("/api/internal/users/validate/user_id?value=new_user")
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["error_message"] is None

def test_validate_user_id_taken():
    # Setup Mock: User ID taken
    mock_state.credentials_collection.find_one.return_value = {"user_id": "existing"}
    
    response = client.get("/api/internal/users/validate/user_id?value=existing")
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["error_message"] == "User ID already exists."

def test_validate_bot_id_endpoint():
    # Setup Mock: Bot ID available
    mock_state.configurations_collection.find_one.return_value = None
    
    # Check bot_ui.py route
    response = client.get("/api/internal/ui/bots/validate/new_bot")
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["error_message"] is None

def test_validate_bot_id_taken():
    # Setup Mock: Bot ID taken
    mock_state.configurations_collection.find_one.return_value = {"config_data": {"bot_id": "existing_bot"}}
    
    response = client.get("/api/internal/ui/bots/validate/existing_bot")
    
    assert response.status_code == 200
    data = response.json()
    # bot_ui.py returns valid=False if exists
    assert data["valid"] is False
    assert data["error_message"] is not None

def test_validate_bot_id_invalid_format():
    # Invalid chars
    response = client.get("/api/internal/ui/bots/validate/Invalid@ID")
    
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["error_code"] == "invalid_format"
