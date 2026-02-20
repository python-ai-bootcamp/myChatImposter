
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from main import app
from dependencies import global_state

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MONGODB_URL", "mongodb://localhost:27017/")
    with TestClient(app) as tc:
        yield tc

def test_get_tracked_messages_calls_history_service(client):
    """
    Verify that GET /api/features/periodic_group_tracking/trackedGroupMessages/{user_id}
    calls global_state.group_tracker.history.get_tracked_periods.
    """
    bot_id = "test_user_tracker"
    
    # Mock GroupTracker and its HistoryService
    mock_tracker = MagicMock()
    mock_history = AsyncMock()
    mock_tracker.history = mock_history
    
    # Mock return value
    # get_tracked_periods returns List[Dict]
    mock_history.get_tracked_periods.return_value = [
        {"_id": "1", "bot_id": bot_id, "display_name": "Group A", "messageCount": 10}
    ]
    
    # Patch global_state
    # We need to patch 'dependencies.global_state.group_tracker'
    # But global_state is an instance. We can set attribute.
    
    original_tracker = global_state.group_tracker
    global_state.group_tracker = mock_tracker
    
    try:
        response = client.get(f"/api/internal/features/periodic_group_tracking/trackedGroupMessages/{bot_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Group A"
        
        # Verify call
        mock_history.get_tracked_periods.assert_called_once_with(bot_id=bot_id)
        
    finally:
        # Restore
        global_state.group_tracker = original_tracker

def test_get_group_tracked_messages_calls_history_service(client):
    """
    Verify that GET /api/features/periodic_group_tracking/trackedGroupMessages/{user_id}/{group_id}
    calls global_state.group_tracker.history.get_tracked_periods.
    """
    bot_id = "test_user_tracker"
    group_id = "g1"
    
    mock_tracker = MagicMock()
    mock_history = AsyncMock()
    mock_tracker.history = mock_history
    
    mock_history.get_tracked_periods.return_value = [
        {"_id": "2", "bot_id": bot_id, "display_name": "Group B", "messageCount": 5}
    ]
    
    original_tracker = global_state.group_tracker
    global_state.group_tracker = mock_tracker
    
    try:
        response = client.get(f"/api/internal/features/periodic_group_tracking/trackedGroupMessages/{bot_id}/{group_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Group B"
        
        mock_history.get_tracked_periods.assert_called_once_with(bot_id=bot_id, group_id=group_id)
        
    finally:
        global_state.group_tracker = original_tracker
