import unittest
from unittest.mock import patch, MagicMock
import chatbot

class TestChatbotMain(unittest.TestCase):

    @patch('chatbot.Orchestrator')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_default_config(self, mock_parse_args, mock_orchestrator):
        """
        Tests if the main function uses the default config path when no args are provided.
        """
        # Simulate the parsed arguments object
        mock_parse_args.return_value = MagicMock(config='configurations/users.json')

        # Mock the start method to prevent it from running indefinitely
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator.return_value = mock_orchestrator_instance

        # Call the main function
        chatbot.main()

        # Assert that Orchestrator was initialized with the default config path
        mock_orchestrator.assert_called_once_with(config_path='configurations/users.json')
        # Assert that the start method was called
        mock_orchestrator_instance.start.assert_called_once()

    @patch('chatbot.Orchestrator')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_custom_config(self, mock_parse_args, mock_orchestrator):
        """
        Tests if the main function uses the provided config path from command-line args.
        """
        # Simulate the parsed arguments object for a custom config
        custom_path = 'path/to/my/custom_config.json'
        mock_parse_args.return_value = MagicMock(config=custom_path)

        # Mock the start method
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator.return_value = mock_orchestrator_instance

        # Call the main function
        chatbot.main()

        # Assert that Orchestrator was initialized with the custom config path
        mock_orchestrator.assert_called_once_with(config_path=custom_path)
        # Assert that the start method was called
        mock_orchestrator_instance.start.assert_called_once()

if __name__ == '__main__':
    unittest.main()
