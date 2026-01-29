
import unittest
from unittest.mock import MagicMock
from features.periodic_group_tracking.service import GroupTracker
from features.periodic_group_tracking.history_service import GroupHistoryService
from features.periodic_group_tracking.runner import GroupTrackingRunner

class TestGroupTrackerRefactor(unittest.TestCase):
    def test_initialization(self):
        """Verify GroupTracker initializes sub-services correctly."""
        mongo_url = "mongodb://localhost:27017"
        chatbot_instances = {}
        queue_manager = MagicMock()
        
        # We need to mock MongoClient inside services to avoid real connection failure if no DB
        # But GroupTracker.__init__ creates MongoClient INDIRECTLY via HistoryService.
        # We patch 'features.periodic_group_tracking.history_service.MongoClient' to avoid side effects.
        
        with unittest.mock.patch('features.periodic_group_tracking.history_service.MongoClient') as mock_client_history:
             
            tracker = GroupTracker(mongo_url, chatbot_instances, queue_manager)
            
            # Check Services
            self.assertIsInstance(tracker.history, GroupHistoryService)
            self.assertIsInstance(tracker.runner, GroupTrackingRunner)
            
            # Check Dependencies passed to Runner
            self.assertEqual(tracker.runner.chatbot_instances, chatbot_instances)
            self.assertEqual(tracker.runner.queue_manager, queue_manager)
            self.assertEqual(tracker.runner.history, tracker.history)
            
            # Check Scheduler
            self.assertTrue(hasattr(tracker.scheduler, 'start'))

    def test_lifecycle(self):
        """Verify start/stop methods."""
        # Tracker does not create MongoClient directly anymore.
        # But for this test we mock it anyway to prevent side effects if we instantiated HistoryService.
        # But wait, GroupTracker instantiation WILL create HistoryService.
        # So we must patch HistoryService MongoClient.
        
        with unittest.mock.patch('features.periodic_group_tracking.history_service.MongoClient'):
             tracker = GroupTracker("m", {}, MagicMock())
             tracker.scheduler = MagicMock()
             
             tracker.start()
             tracker.scheduler.start.assert_called_once()
             
             tracker.shutdown()
             tracker.scheduler.shutdown.assert_called_once()
