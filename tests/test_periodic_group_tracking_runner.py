
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from zoneinfo import ZoneInfo

from features.periodic_group_tracking.runner import GroupTrackingRunner
from config_models import PeriodicGroupTrackingConfig, BotConfiguration
from services.session_manager import SessionManager

class TestGroupTrackingRunner(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Mocks for dependencies
        self.mock_chatbot_instances = {}
        self.mock_history_service = AsyncMock()
        self.mock_queue_manager = AsyncMock()
        self.mock_extractor = AsyncMock()
        self.mock_window_calculator = MagicMock()
        self.mock_token_consumption = AsyncMock()
        self.runner = GroupTrackingRunner(
            chatbot_instances=self.mock_chatbot_instances,
            history_service=self.mock_history_service,
            queue_manager=self.mock_queue_manager,
            extractor=self.mock_extractor,
            window_calculator=self.mock_window_calculator,
            token_consumption_collection=self.mock_token_consumption
        )
        
        # Patch sleep to avoid jitter delays
        self.sleep_patcher = patch('asyncio.sleep', new_callable=AsyncMock)
        self.mock_sleep = self.sleep_patcher.start()
        self.addCleanup(self.sleep_patcher.stop)
        
        # Default Test Data
        self.bot_id = "test_bot_123"
        self.group_id = "group@g.us"
        self.config = PeriodicGroupTrackingConfig(
            groupIdentifier=self.group_id,
            displayName="Test Group",
            cronTrackingSchedule="0 18 * * *"
        )
        
        # Setup Mock Session
        self.mock_session = MagicMock(spec=SessionManager)
        self.mock_session.bot_id = self.bot_id
        self.mock_session.provider_instance = AsyncMock()
        # FIX: is_bot_message is synchronous
        self.mock_session.provider_instance.is_bot_message = MagicMock(return_value=False)
        self.mock_session.provider_instance.is_connected = True
        
        # FIX: Mock Config Structure deeply
        self.mock_session.config = MagicMock()
        self.mock_session.config.configurations.llm_provider_config = MagicMock()
        self.mock_session.config.configurations.user_details.language_code = "en"
        
        # Add to instances dict
        self.mock_chatbot_instances["session_id_1"] = self.mock_session

    async def test_aborts_if_chatbot_not_active(self):
        """Test that the runner aborts if no active session is found for the user."""
        # Clear instances
        self.mock_chatbot_instances.clear()
        
        await self.runner.run_tracking_cycle(self.bot_id, "test_owner", self.config)
        
        # Should not fetch messages or calculate window
        self.mock_session.provider_instance.fetch_historic_messages.assert_not_called()
        self.mock_window_calculator.calculate_window.assert_not_called()

    async def test_aborts_if_provider_disconnected(self):
        """Test that the runner aborts if the provider is not connected."""
        self.mock_session.provider_instance.is_connected = False
        
        await self.runner.run_tracking_cycle(self.bot_id, "test_owner", self.config)
        
        self.mock_session.provider_instance.fetch_historic_messages.assert_not_called()

    async def test_aborts_if_fetch_returns_none(self):
        """Test that the runner aborts if fetch_historic_messages returns None (error)."""
        self.mock_session.provider_instance.fetch_historic_messages.return_value = None
        
        await self.runner.run_tracking_cycle(self.bot_id, "test_owner", self.config)
        
        self.mock_window_calculator.calculate_window.assert_not_called()

    async def test_successful_run_flow(self):
        """Test a complete successful run with messages."""
        # 1. Mock Fetch
        messages = [
            {"provider_message_id": "m1", "originating_time": 1000, "message": "hello", "sender": "alice"},
            {"provider_message_id": "m2", "originating_time": 2000, "message": "world", "sender": "bob"}
        ]
        self.mock_session.provider_instance.fetch_historic_messages.return_value = messages
        
        # 2. Mock History Last Run
        self.mock_history_service.get_last_run.return_value = 0
        self.mock_history_service.get_recent_message_ids.return_value = set()
        
        # 3. Mock Window
        start_dt = datetime.fromtimestamp(0, tz=ZoneInfo("UTC"))
        end_dt = datetime.fromtimestamp(10, tz=ZoneInfo("UTC"))
        self.mock_window_calculator.calculate_window.return_value = (start_dt, end_dt)
        
        # 4. Mock Extraction
        self.mock_extractor.extract.return_value = [{"task_title": "Test Task"}]
        
        # Run
        await self.runner.run_tracking_cycle(self.bot_id, "test_owner", self.config)
            
        # Verify
        # Should call window calculator
        self.mock_window_calculator.calculate_window.assert_called_once()
        
        # Should save tracking result
        self.mock_history_service.save_tracking_result.assert_called_once()
        saved_messages = self.mock_history_service.save_tracking_result.call_args[1]['messages']
        self.assertEqual(len(saved_messages), 2) # Both messages in window
        
        # Should extract
        self.mock_extractor.extract.assert_called_once()
        
        # Should queue
        self.mock_queue_manager.add_item.assert_called_once()
        item = self.mock_queue_manager.add_item.call_args[1]['content']
        self.assertEqual(item['task_title'], 'Test Task')

    async def test_deduplication(self):
        """Test that duplicate messages are filtered out."""
        # Mock fetch (m1 is duplicate)
        messages = [
            {"provider_message_id": "m1", "originating_time": 1000},
            {"provider_message_id": "m2", "originating_time": 2000}
        ]
        self.mock_session.provider_instance.fetch_historic_messages.return_value = messages
        
        # Mock History returns m1 as seen
        self.mock_history_service.get_recent_message_ids.return_value = {"m1"}
        
        # Mock Window covering these messages
        start_dt = datetime.fromtimestamp(0, tz=ZoneInfo("UTC"))
        end_dt = datetime.fromtimestamp(10, tz=ZoneInfo("UTC"))
        self.mock_window_calculator.calculate_window.return_value = (start_dt, end_dt)
        
        await self.runner.run_tracking_cycle(self.bot_id, "test_owner", self.config)
            
        # Verify saved messages (only m2)
        saved_messages = self.mock_history_service.save_tracking_result.call_args[1]['messages']
        self.assertEqual(len(saved_messages), 1)
        self.assertEqual(saved_messages[0]['provider_message_id'], 'm2')

if __name__ == '__main__':
    unittest.main()
