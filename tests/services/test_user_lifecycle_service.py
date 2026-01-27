"""
Unit tests for UserLifecycleService.
Tests the lifecycle callbacks for user connection/disconnection events.

Note: Uses asyncio.run() instead of pytest-asyncio to avoid external dependency.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.user_lifecycle_service import UserLifecycleService
from config_models import UserConfiguration


class TestUserLifecycleService:
    """Tests for UserLifecycleService class."""

    def setup_method(self):
        """Set up mocks before each test."""
        # Create mock GlobalStateManager
        self.mock_global_state = MagicMock()
        
        # Mock queue manager
        self.mock_queue_manager = MagicMock()
        self.mock_global_state.async_message_delivery_queue_manager = self.mock_queue_manager
        
        # Mock group tracker
        self.mock_group_tracker = MagicMock()
        self.mock_global_state.group_tracker = self.mock_group_tracker
        
        # Mock configurations collection
        self.mock_configurations_collection = MagicMock()
        self.mock_global_state.configurations_collection = self.mock_configurations_collection
        
        # Create service instance
        self.service = UserLifecycleService(self.mock_global_state)

    # --- on_user_connected tests ---

    def test_on_user_connected_moves_queue_to_active(self):
        """Test that connecting moves user's queued messages to active."""
        user_id = "test_user_connected_queue"
        
        # Mock DB to return None (no config)
        self.mock_configurations_collection.find_one = MagicMock(return_value=None)
        
        asyncio.run(self.service.on_user_connected(user_id))
        
        # Verify queue manager was called
        self.mock_queue_manager.move_user_to_active.assert_called_once_with(user_id)

    def test_on_user_connected_starts_group_tracking_when_enabled(self):
        """Test that group tracking starts when user connects and feature is enabled."""
        user_id = "test_user_tracking_enabled"
        
        # Create a valid config with tracking enabled (all required fields)
        config_dict = {
            "user_id": user_id,
            "features": {
                "periodic_group_tracking": {
                    "enabled": True,
                    "tracked_groups": [
                        {
                            "groupIdentifier": "group1@g.us",
                            "cronTrackingSchedule": "0 9 * * *",
                            "displayName": "Test Group"
                        }
                    ]
                }
            },
            "configurations": {
                "user_details": {
                    "timezone": "Asia/Jerusalem"
                },
                "chat_provider_config": {
                    "provider_name": "dummy",
                    "provider_config": {}
                },
                "llm_provider_config": {
                    "provider_name": "fakeLlm",
                    "provider_config": {"model": "test", "temperature": 0.7}
                }
            }
        }
        
        self.mock_configurations_collection.find_one = MagicMock(
            return_value={"config_data": config_dict}
        )
        
        asyncio.run(self.service.on_user_connected(user_id))
        
        # Verify group tracker was called with the groups
        self.mock_group_tracker.update_jobs.assert_called_once()
        call_args = self.mock_group_tracker.update_jobs.call_args
        assert call_args[0][0] == user_id
        assert len(call_args[0][1]) == 1  # One tracked group
        assert call_args[0][2] == "Asia/Jerusalem"

    def test_on_user_connected_clears_tracking_when_disabled(self):
        """Test that group tracking is cleared when feature is disabled."""
        user_id = "test_user_tracking_disabled"
        
        config_dict = {
            "user_id": user_id,
            "features": {
                "periodic_group_tracking": {
                    "enabled": False,
                    "tracked_groups": []
                }
            },
            "configurations": {
                "user_details": {
                    "timezone": "UTC"
                },
                "chat_provider_config": {
                    "provider_name": "dummy",
                    "provider_config": {}
                },
                "llm_provider_config": {
                    "provider_name": "fakeLlm",
                    "provider_config": {"model": "test", "temperature": 0.7}
                }
            }
        }
        
        self.mock_configurations_collection.find_one = MagicMock(
            return_value={"config_data": config_dict}
        )
        
        asyncio.run(self.service.on_user_connected(user_id))
        
        # Verify tracker was called with empty list
        self.mock_group_tracker.update_jobs.assert_called_once_with(user_id, [])

    def test_on_user_connected_handles_missing_config(self):
        """Test graceful handling when user config doesn't exist."""
        user_id = "test_user_no_config"
        
        self.mock_configurations_collection.find_one = MagicMock(return_value=None)
        
        # Should not raise
        asyncio.run(self.service.on_user_connected(user_id))
        
        # Queue should still be moved
        self.mock_queue_manager.move_user_to_active.assert_called_once_with(user_id)
        
        # Tracker should not be called (no config)
        self.mock_group_tracker.update_jobs.assert_not_called()

    def test_on_user_connected_handles_db_error(self):
        """Test graceful handling of database errors."""
        user_id = "test_user_db_error"
        
        self.mock_configurations_collection.find_one = MagicMock(
            side_effect=Exception("DB connection failed")
        )
        
        # Should not raise
        asyncio.run(self.service.on_user_connected(user_id))
        
        # Queue should still be moved
        self.mock_queue_manager.move_user_to_active.assert_called_once_with(user_id)

    # --- on_user_disconnected tests ---

    def test_on_user_disconnected_stops_tracking_jobs(self):
        """Test that disconnecting stops group tracking jobs."""
        user_id = "test_user_disconnected"
        
        asyncio.run(self.service.on_user_disconnected(user_id))
        
        self.mock_group_tracker.stop_tracking_jobs.assert_called_once_with(user_id)

    def test_on_user_disconnected_handles_no_tracker(self):
        """Test graceful handling when group tracker is None."""
        user_id = "test_user_no_tracker"
        self.mock_global_state.group_tracker = None
        
        # Recreate service with updated state
        service = UserLifecycleService(self.mock_global_state)
        
        # Should not raise
        asyncio.run(service.on_user_disconnected(user_id))

    # --- create_status_change_callback tests ---

    def test_callback_dispatches_connected_status(self):
        """Test callback correctly dispatches 'connected' status."""
        user_id = "test_callback_connected"
        
        self.mock_configurations_collection.find_one = MagicMock(return_value=None)
        
        callback = self.service.create_status_change_callback()
        
        asyncio.run(callback(user_id, "connected"))
        
        # Verify on_user_connected was triggered (queue was moved)
        self.mock_queue_manager.move_user_to_active.assert_called_once_with(user_id)

    def test_callback_dispatches_disconnected_status(self):
        """Test callback correctly dispatches 'disconnected' status."""
        user_id = "test_callback_disconnected"
        
        callback = self.service.create_status_change_callback()
        
        asyncio.run(callback(user_id, "disconnected"))
        
        # Verify on_user_disconnected was triggered
        self.mock_group_tracker.stop_tracking_jobs.assert_called_once_with(user_id)

    def test_callback_ignores_unknown_status(self):
        """Test callback ignores unknown status values."""
        user_id = "test_callback_unknown"
        
        callback = self.service.create_status_change_callback()
        
        # Should not raise or trigger any action
        asyncio.run(callback(user_id, "unknown_status"))
        
        # Nothing should be called
        self.mock_queue_manager.move_user_to_active.assert_not_called()
        self.mock_group_tracker.stop_tracking_jobs.assert_not_called()

    # --- _get_user_config tests ---

    def test_get_user_config_returns_config_data(self):
        """Test successful config retrieval."""
        user_id = "test_config_retrieval"
        expected_config = {"user_id": user_id, "features": {}}
        
        self.mock_configurations_collection.find_one = MagicMock(
            return_value={"config_data": expected_config}
        )
        
        result = asyncio.run(self.service._get_user_config(user_id))
        
        assert result == expected_config

    def test_get_user_config_returns_none_for_missing(self):
        """Test None return when config doesn't exist."""
        user_id = "test_config_missing"
        
        self.mock_configurations_collection.find_one = MagicMock(return_value=None)
        
        result = asyncio.run(self.service._get_user_config(user_id))
        
        assert result is None

    def test_get_user_config_returns_none_on_error(self):
        """Test None return when database errors occur."""
        user_id = "test_config_error"
        
        self.mock_configurations_collection.find_one = MagicMock(
            side_effect=Exception("Network error")
        )
        
        result = asyncio.run(self.service._get_user_config(user_id))
        
        assert result is None
