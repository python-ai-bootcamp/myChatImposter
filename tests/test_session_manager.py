
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from services.session_manager import SessionManager
from config_models import UserConfiguration
from chat_providers.base import BaseChatProvider

class TestSessionManager(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.user_id = "test_user"
        
        # Mock Config
        self.mock_config = MagicMock()
        self.mock_config.user_id = self.user_id
        # Need correct structure
        self.mock_config.configurations.chat_provider_config.provider_name = "mock_provider"
        self.mock_config.features.automatic_bot_reply.enabled = False
        
        # Mock queues collection (just need an object)
        self.mock_queues_collection = MagicMock()
        
    async def test_initialization_success(self):
        """Test that SessionManager initializes correctly when provider is found."""
        
        with patch("services.session_manager.find_provider_class") as mock_find_class, \
             patch("services.session_manager.importlib.import_module") as mock_import:
            
            # Setup Mock Provider Class
            MockProviderClass = MagicMock()
            mock_find_class.return_value = MockProviderClass
            
            # Setup import module
            mock_module = MagicMock()
            mock_import.return_value = mock_module
            
            # Instantiate
            manager = SessionManager(
                config=self.mock_config,
                main_loop=asyncio.get_running_loop(),
                queues_collection=self.mock_queues_collection
            )
            
            # Verify provider loaded
            mock_import.assert_called_with("chat_providers.mock_provider")
            mock_find_class.assert_called_with(mock_module, BaseChatProvider)
            
            # Verify provider instantiated
            self.assertIsNotNone(manager.provider_instance)
            
            # Verify queue manager initialized
            self.assertIsNotNone(manager.user_queues_manager)
            self.assertEqual(manager.user_queues_manager.user_id, self.user_id)

    async def test_initialization_failure_no_provider(self):
        """Test that SessionManager raises ImportError if provider class not found."""
        
        with patch("services.session_manager.find_provider_class") as mock_find_class, \
             patch("services.session_manager.importlib.import_module") as mock_import:
            
            mock_find_class.return_value = None # No class found
            mock_import.return_value = MagicMock()
            
            with self.assertRaises(RuntimeError):
                SessionManager(
                    config=self.mock_config,
                    main_loop=asyncio.get_running_loop(),
                    queues_collection=self.mock_queues_collection
                )

    async def test_registration_methods(self):
        """Test registration of handlers, services, and features."""
        
        with patch("services.session_manager.find_provider_class") as mock_find_class, \
             patch("services.session_manager.importlib.import_module") as mock_import:
            
            # Setup valid provider
            MockProviderClass = MagicMock()
            mock_find_class.return_value = MockProviderClass
            mock_import.return_value = MagicMock()
            
            manager = SessionManager(
                config=self.mock_config,
                main_loop=asyncio.get_running_loop(),
                queues_collection=self.mock_queues_collection
            )
            
            # 1. Test register_message_handler
            mock_handler = AsyncMock()
            manager.register_message_handler(mock_handler)
            self.assertIn(mock_handler, manager._message_handlers)
            
            # 2. Test register_service
            mock_service = MagicMock()
            manager.register_service(mock_service)
            self.assertIn(mock_service, manager._associated_services)
            
            # 3. Test register_feature
            mock_feature = MagicMock()
            manager.register_feature("my_feature", mock_feature)
            self.assertEqual(manager.features["my_feature"], mock_feature)

if __name__ == '__main__':
    unittest.main()
