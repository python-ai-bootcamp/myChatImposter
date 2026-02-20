
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dependencies import GlobalStateManager, get_global_state
from routers.bot_management import router as bot_router

# Setup App for Testing
app = FastAPI()
app.include_router(bot_router)

class TestBotManagementAPI:
    
    @pytest.fixture
    def mock_global_state(self):
        """Mock the Global State Manager."""
        mock_state = MagicMock(spec=GlobalStateManager)
        
        # Mock Collections
        mock_state.configurations_collection = AsyncMock()
        mock_state.configurations_collection.find_one.return_value = None
        mock_state.queues_collection = AsyncMock()
        mock_state.baileys_sessions_collection = AsyncMock()
        mock_state.baileys_sessions_collection.find_one.return_value = None
        mock_state.credentials_collection = AsyncMock()
        mock_state.credentials_collection.find_one.return_value = None # Default to None to avoid AsyncMock propagation
        mock_state.active_bots = {}
        mock_state.chatbot_instances = {}
        
        # Mock Managers
        mock_state.group_tracker = MagicMock()
        mock_state.async_message_delivery_queue_manager = MagicMock()
        mock_state.bot_lifecycle_service = MagicMock() 
        mock_state.bot_lifecycle_service.create_status_change_callback.return_value = AsyncMock()
        
        return mock_state

    @pytest.fixture
    def client(self, mock_global_state):
        """Test Client with dependency override."""
        app.dependency_overrides[get_global_state] = lambda: mock_global_state
        yield TestClient(app)
        app.dependency_overrides.clear()

    def test_list_bots_success(self, client, mock_global_state):
        """Test GET /api/internal/bots"""
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
            {"config_data": {"bot_id": "bot1"}},
            {"config_data": {"bot_id": "bot2"}}
        ])
        # Find is SYNC in Motor, returns cursor
        mock_global_state.configurations_collection.find = MagicMock(return_value=mock_cursor)
        
        response = client.get("/api/internal/bots")
        assert response.status_code == 200
        # Check expected response key. Assuming router returns {"bot_ids": [...]}
        assert response.json() == {"bot_ids": ["bot1", "bot2"]}

    def test_get_bot_info_success(self, client, mock_global_state):
        """Test GET /api/internal/bots/{bot_id}/info"""
        bot_id = "test_bot"
        
        # Mock Find One (Config)
        mock_global_state.configurations_collection.find_one = AsyncMock(return_value={
            "config_data": {"bot_id": bot_id, "some": "config"}
        })
        
        # Mock Instance Status
        mock_instance = AsyncMock()
        mock_instance.get_status.return_value = {"status": "connected"}
        mock_global_state.get_chatbot_instance_by_bot.return_value = mock_instance # Updated method name (presumed)
        
        response = client.get(f"/api/internal/bots/{bot_id}/info")
        assert response.status_code == 200
        data = response.json()
        assert data["configurations"][0]["bot_id"] == bot_id
        assert data["configurations"][0]["status"] == "connected"

    def test_get_bot_info_not_found(self, client, mock_global_state):
        """Test GET /api/internal/bots/{bot_id}/info not found"""
        mock_global_state.configurations_collection.find_one = AsyncMock(return_value=None)
        
        response = client.get("/api/internal/bots/unknown/info")
        assert response.status_code == 404

    @patch("routers.bot_management.SessionManager")
    @patch("routers.bot_management.IngestionService")
    def test_link_bot_success(self, mock_ingest, mock_session_cls, client, mock_global_state):
        """Test POST /api/internal/bots/{bot_id}/actions/link"""
        bot_id = "test_bot_link"
        
        # Mock Config Found
        mock_global_state.configurations_collection.find_one = AsyncMock(return_value={
            "config_data": {
                "bot_id": bot_id,
                "configurations": {
                    "user_details": {},
                    "chat_provider_config": {"provider_name": "mock", "provider_config": {}},
                    "llm_configs": {
                        "high": {"provider_name": "mock", "provider_config": {"model": "gpt-4"}},
                        "low": {"provider_name": "mock", "provider_config": {"model": "gpt-3.5"}}
                    },
                    "queue_config": {},
                    "context_config": {}
                },
                "features": {
                    "automatic_bot_reply": {"enabled": True},
                    "kid_phone_safety_tracking": {"enabled": False}
                }
            }
        })
        
        # Mock Session Instance
        mock_instance = AsyncMock()
        mock_instance.start = AsyncMock()
        mock_instance.register_service = MagicMock()
        mock_instance.register_message_handler = MagicMock()
        mock_instance.register_feature = MagicMock()
        
        # Setup config on instance for service initialization
        from config_models import BotConfiguration
        config_obj = BotConfiguration.model_validate(mock_global_state.configurations_collection.find_one.return_value["config_data"])
        mock_instance.config = config_obj
        mock_instance.bot_id = bot_id
        
        mock_session_cls.return_value = mock_instance
        
        # Patch AutomaticBotReplyService to avoid real LLM init
        with patch("routers.bot_management.AutomaticBotReplyService") as mock_auto_reply:
             mock_auto_service = MagicMock()
             mock_auto_reply.return_value = mock_auto_service
             
             response = client.post(f"/api/internal/bots/{bot_id}/actions/link")
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify Session Started
        mock_instance.start.assert_called_once()
        # Verify added to active bots (mock_global_state.active_bots is a dict)
        assert bot_id in mock_global_state.active_bots

    @pytest.mark.asyncio
    async def test_delete_bot_success(self, client, mock_global_state):
        """Test DELETE /api/internal/bots/{bot_id}"""
        bot_id = "test_bot_del"
        
        # Setup active bot
        mock_global_state.active_bots[bot_id] = "inst1"
        mock_instance = AsyncMock()
        mock_global_state.chatbot_instances["inst1"] = mock_instance
        
        # Mock Delete Result
        mock_result = MagicMock()
        mock_result.deleted_count = 1
        mock_global_state.bot_lifecycle_service.delete_bot_data = AsyncMock(return_value=True)
        
        response = client.delete(f"/api/internal/bots/{bot_id}")
        assert response.status_code == 200
