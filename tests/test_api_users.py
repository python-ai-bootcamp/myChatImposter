
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dependencies import GlobalStateManager, get_global_state
from routers.user_management import router as user_router

# Setup App for Testing
app = FastAPI()
app.include_router(user_router)

class TestUserManagementAPI:
    
    @pytest.fixture
    def mock_global_state(self):
        """Mock the Global State Manager."""
        mock_state = MagicMock(spec=GlobalStateManager)
        
        # Mock Collections
        mock_state.configurations_collection = AsyncMock()
        mock_state.queues_collection = AsyncMock()
        mock_state.baileys_sessions_collection = AsyncMock()
        mock_state.active_users = {}
        mock_state.chatbot_instances = {}
        
        # Mock Managers
        mock_state.group_tracker = MagicMock()
        mock_state.async_message_delivery_queue_manager = MagicMock()
        mock_state.user_lifecycle_service = MagicMock()
        mock_state.user_lifecycle_service.create_status_change_callback.return_value = AsyncMock()
        
        return mock_state

    @pytest.fixture
    def client(self, mock_global_state):
        """Test Client with dependency override."""
        app.dependency_overrides[get_global_state] = lambda: mock_global_state
        return TestClient(app)

    def test_list_users_success(self, client, mock_global_state):
        """Test GET /api/internal/users"""
        # Mock DB Cursor
        mock_cursor = MagicMock()
        
        class AsyncIterator:
            def __init__(self, items):
                self.items = iter(items)
            def __aiter__(self): return self
            async def __anext__(self):
                try: return next(self.items)
                except StopIteration: raise StopAsyncIteration
                
        mock_cursor.__aiter__.side_effect = lambda: AsyncIterator([
            {"config_data": {"user_id": "user1"}},
            {"config_data": {"user_id": "user2"}}
        ])
        # Find is SYNC in Motor, returns cursor
        mock_global_state.configurations_collection.find = MagicMock(return_value=mock_cursor)
        
        response = client.get("/api/internal/users")
        assert response.status_code == 200
        assert response.json() == {"user_ids": ["user1", "user2"]}

    def test_get_user_info_success(self, client, mock_global_state):
        """Test GET /api/internal/users/{user_id}/info"""
        user_id = "test_user"
        
        # Mock Find One (Config)
        mock_global_state.configurations_collection.find_one = AsyncMock(return_value={
            "config_data": {"user_id": user_id, "some": "config"}
        })
        
        # Mock Instance Status
        mock_instance = AsyncMock()
        mock_instance.get_status.return_value = {"status": "connected"}
        mock_global_state.get_chatbot_instance_by_user.return_value = mock_instance
        
        response = client.get(f"/api/internal/users/{user_id}/info")
        assert response.status_code == 200
        data = response.json()
        assert data["configurations"][0]["user_id"] == user_id
        assert data["configurations"][0]["status"] == "connected"

    def test_get_user_info_not_found(self, client, mock_global_state):
        """Test GET /api/internal/users/{user_id}/info not found"""
        mock_global_state.configurations_collection.find_one = AsyncMock(return_value=None)
        
        response = client.get("/api/internal/users/unknown/info")
        assert response.status_code == 404

    @patch("routers.user_management.SessionManager")
    @patch("routers.user_management.IngestionService")
    def test_link_user_success(self, mock_ingest, mock_session_cls, client, mock_global_state):
        """Test POST /api/internal/users/{user_id}/actions/link"""
        user_id = "test_user_link"
        
        # Mock Config Found
        mock_global_state.configurations_collection.find_one = AsyncMock(return_value={
            "config_data": {
                "user_id": user_id,
                "configurations": {
                    "user_details": {},
                    "chat_provider_config": {"provider_name": "mock", "provider_config": {}},
                    "llm_provider_config": {"provider_name": "mock", "provider_config": {"model": "gpt-4"}},
                    "queue_config": {},
                    "context_config": {}
                },
                "features": {}
            }
        })
        
        # Mock Session Instance
        mock_instance = AsyncMock()
        mock_instance.start = AsyncMock()
        mock_session_cls.return_value = mock_instance
        
        response = client.post(f"/api/internal/users/{user_id}/actions/link")
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify Session Started
        mock_instance.start.assert_called_once()
        # Verify added to active users
        assert user_id in mock_global_state.active_users

    def test_delete_user_success(self, client, mock_global_state):
        """Test DELETE /api/internal/users/{user_id}"""
        user_id = "test_user_del"
        
        # Setup active user
        mock_global_state.active_users[user_id] = "inst1"
        mock_instance = AsyncMock()
        mock_global_state.chatbot_instances["inst1"] = mock_instance
        
        # Mock Delete Result
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_global_state.configurations_collection.delete_one.return_value = mock_result
        
        response = client.delete(f"/api/internal/users/{user_id}")
        assert response.status_code == 200
        
        # Verify cleanup
        mock_instance.stop.assert_called_with(cleanup_session=True)
        # remove_active_user is mocked, verify call
        # mock_global_state.remove_active_user(user_id) called inside delete endpoint
