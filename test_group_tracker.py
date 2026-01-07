
import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
import time

from group_tracker import GroupTracker
from config_models import PeriodicGroupTrackingConfig
from chat_providers.whatsAppBaileyes import WhatsAppBaileysProvider

class TestGroupTrackerLogic(unittest.TestCase):
    def setUp(self):
        self.mock_mongo_client = MagicMock()
        self.mock_db = MagicMock()
        self.mock_mongo_client.__getitem__.return_value = self.mock_db

        # Mock collections
        self.mock_tracking_state = MagicMock()
        self.mock_tracked_groups = MagicMock()
        self.mock_periods = MagicMock()

        self.mock_db.__getitem__.side_effect = lambda name: {
            'group_tracking_state': self.mock_tracking_state,
            'tracked_groups': self.mock_tracked_groups,
            'tracked_group_periods': self.mock_periods
        }.get(name)

        # Chatbot instances
        self.mock_provider = MagicMock(spec=WhatsAppBaileysProvider)
        # Use AsyncMock for the async method
        self.mock_provider.fetch_historic_messages = AsyncMock()

        self.mock_instance = MagicMock()
        self.mock_instance.user_id = 'user1'
        self.mock_instance.provider_instance = self.mock_provider
        self.chatbot_instances = {'instance1': self.mock_instance}

        with patch('group_tracker.MongoClient', return_value=self.mock_mongo_client):
            self.tracker = GroupTracker('mongodb://localhost:27017', self.chatbot_instances)

    def test_strict_cron_window(self):
        # Setup
        user_id = 'user1'
        config = PeriodicGroupTrackingConfig(
            groupIdentifier='group1@g.us',
            cronTrackingSchedule='0/15 * * * *',
            displayName='Test Group'
        )

        # Scenario:
        # Schedule: Every 15 mins (00, 15, 30, 45)
        # Current time: 16:35:00 (5 mins late)

        # Mock time.time() to 16:35:00
        # 2026-01-07 16:35:00
        fixed_now = datetime(2026, 1, 7, 16, 35, 0)
        fixed_now_ts = fixed_now.timestamp() # float seconds

        # Calculate expected timestamps
        # Window should be: 16:15 to 16:30
        expected_end = datetime(2026, 1, 7, 16, 30, 0)
        expected_start = datetime(2026, 1, 7, 16, 15, 0)

        ts_16_20 = expected_start + timedelta(minutes=5)
        ts_16_32 = expected_end + timedelta(minutes=2)
        ts_14_05 = datetime(2026, 1, 7, 14, 5, 0)

        msg1 = {'sender': 's1', 'message': 'm1', 'originating_time': int(ts_14_05.timestamp() * 1000)} # ~14:05
        msg2 = {'sender': 's1', 'message': 'm2', 'originating_time': int(ts_16_20.timestamp() * 1000)} # ~16:20
        msg3 = {'sender': 's1', 'message': 'm3', 'originating_time': int(ts_16_32.timestamp() * 1000)} # ~16:32

        self.mock_provider.fetch_historic_messages.return_value = [msg1, msg2, msg3]

        # Mock DB state to have old last_run_ts
        self.mock_tracking_state.find_one.return_value = {'last_run_ts': int(ts_14_05.timestamp() * 1000)}

        # Run with patched time
        with patch('time.time', return_value=fixed_now_ts):
            asyncio.run(self.tracker.track_group_context(user_id, config))

        # Verification

        # 1. Verify fetch_historic_messages called
        self.mock_provider.fetch_historic_messages.assert_called_with('group1@g.us', limit=500)

        # 2. Verify only 1 message saved (msg2)
        # Check insert_one call on tracked_group_periods_collection
        self.assertTrue(self.mock_periods.insert_one.called)
        args, _ = self.mock_periods.insert_one.call_args
        period_doc = args[0]

        print(f"Period Start: {datetime.fromtimestamp(period_doc['periodStart']/1000)}")
        print(f"Period End: {datetime.fromtimestamp(period_doc['periodEnd']/1000)}")
        print(f"Messages: {len(period_doc['messages'])}")

        self.assertEqual(period_doc['periodStart'], int(expected_start.timestamp() * 1000))
        self.assertEqual(period_doc['periodEnd'], int(expected_end.timestamp() * 1000))
        self.assertEqual(len(period_doc['messages']), 1)
        self.assertEqual(period_doc['messages'][0]['message'], 'm2')

        # 3. Verify state updated to periodEnd
        self.assertTrue(self.mock_tracking_state.update_one.called)
        args, _ = self.mock_tracking_state.update_one.call_args
        update_doc = args[1]
        self.assertEqual(update_doc['$set']['last_run_ts'], int(expected_end.timestamp() * 1000))

if __name__ == '__main__':
    unittest.main()
