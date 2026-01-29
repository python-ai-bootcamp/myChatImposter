
import unittest
from unittest.mock import MagicMock, AsyncMock
from features.periodic_group_tracking.runner import GroupTrackingRunner
from config_models import PeriodicGroupTrackingConfig
from zoneinfo import ZoneInfo
from datetime import datetime

class TestTrackerDeduplication(unittest.IsolatedAsyncioTestCase):
    async def test_deduplication_of_historical_messages(self):
        """
        Verify that messages with IDs already in history are skipped,
        even if they fall within the current time window.
        """
        user_id = "test_user_dedup"
        group_id = "g_dedup"
        
        # Mocks
        instances = {}
        history = MagicMock()
        queue = MagicMock()
        
        # Setup specific mock behavior
        # 1. History returns existing ID 'MSG_OLD_ID'
        history.get_recent_message_ids.return_value = {'MSG_OLD_ID'}
        history.get_last_run.return_value = 1000
        
        # 2. Setup Runner
        runner = GroupTrackingRunner(instances, history, queue)
        
        # 3. Use a fake chatbot instance
        fake_instance = MagicMock()
        fake_provider = AsyncMock()
        fake_instance.provider_instance = fake_provider
        fake_instance.user_id = user_id
        instances["inst_1"] = fake_instance
        
        # 4. Mock window calculator to return a fixed window
        runner.window_calculator = MagicMock()
        runner.window_calculator.calculate_window.return_value = (
            datetime.fromtimestamp(1000/1000, tz=ZoneInfo("UTC")),
            datetime.fromtimestamp(2000/1000, tz=ZoneInfo("UTC"))
        )
        
        # 5. FETCHED MESSAGES
        # Return 2 messages:
        # - MSG_OLD_ID (Duplicate, but new timestamp inside window) -> SHOULD BE SKIPPED
        # - MSG_NEW_ID (New, inside window) -> SHOULD BE SAVED
        fake_provider.fetch_historic_messages.return_value = [
            {
                "provider_message_id": "MSG_OLD_ID",
                "originating_time": 1500, # Inside window (1000-2000)
                "message": "Duplicate Text",
                "sender": "sender1"
            },
            {
                "provider_message_id": "MSG_NEW_ID",
                "originating_time": 1600, # Inside window
                "message": "New Text",
                "sender": "sender1"
            }
        ]
        fake_provider.is_bot_message.return_value = False
        
        # Config
        config = PeriodicGroupTrackingConfig(
            groupIdentifier=group_id,
            displayName="Test Group",
            cronTrackingSchedule="* * * * *"
        )
        
        # EXECUTE
        # Patch sleep to avoid waiting for jitter
        with unittest.mock.patch('asyncio.sleep', new_callable=AsyncMock):
            await runner.run_tracking_cycle(user_id, config)
        
        # ASSERT
        history.save_tracking_result.assert_called_once()
        call_args = history.save_tracking_result.call_args
        kwargs = call_args.kwargs
        messages_saved = kwargs['messages']
        
        # Verify deduplication
        self.assertEqual(len(messages_saved), 1, "Should filter out historical duplicate")
        self.assertEqual(messages_saved[0]['provider_message_id'], "MSG_NEW_ID")
        self.assertEqual(messages_saved[0]['message'], "New Text")
