import unittest
from unittest.mock import patch, MagicMock
import chatbot

class TestChatbotMain(unittest.TestCase):

    @patch('time.sleep', side_effect=KeyboardInterrupt)
    @patch('chatbot.Orchestrator')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_default_config(self, mock_parse_args, mock_orchestrator, mock_sleep):
        """
        Tests if the main function uses the default config path when no args are provided.
        """
        # Simulate the parsed arguments object
        mock_parse_args.return_value = MagicMock(config='configurations/users.json')

        # Mock the start and stop methods to prevent them from running indefinitely
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator.return_value = mock_orchestrator_instance

        # Call the main function
        chatbot.main()

        # Assert that Orchestrator was initialized with the default config path
        mock_orchestrator.assert_called_once_with(config_path='configurations/users.json')
        # Assert that the start and stop methods were called
        mock_orchestrator_instance.start.assert_called_once()
        mock_orchestrator_instance.stop.assert_called_once()

    @patch('time.sleep', side_effect=KeyboardInterrupt)
    @patch('chatbot.Orchestrator')
    @patch('argparse.ArgumentParser.parse_args')
    def test_main_custom_config(self, mock_parse_args, mock_orchestrator, mock_sleep):
        """
        Tests if the main function uses the provided config path from command-line args.
        """
        # Simulate the parsed arguments object for a custom config
        custom_path = 'path/to/my/custom_config.json'
        mock_parse_args.return_value = MagicMock(config=custom_path)

        # Mock the start and stop methods
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator.return_value = mock_orchestrator_instance

        # Call the main function
        chatbot.main()

        # Assert that Orchestrator was initialized with the custom config path
        mock_orchestrator.assert_called_once_with(config_path=custom_path)
        # Assert that the start and stop methods were called
        mock_orchestrator_instance.start.assert_called_once()
        mock_orchestrator_instance.stop.assert_called_once()


class TestOrchestrator(unittest.TestCase):

    @patch('chatbot.ChatPromptTemplate.from_messages')
    def test_initialization_and_prompt(self, mock_from_messages):
        """Tests that the orchestrator initializes components and sets the correct system prompt."""

        # We need a dummy runnable to be returned by the mock, because the code
        # that follows `from_messages` will try to pipe it with other runnables.
        mock_from_messages.return_value = MagicMock()

        orchestrator = chatbot.Orchestrator(config_path='testConfigurations/test_config.json')
        orchestrator._initialize_components()

        # Check if the user queue was created
        self.assertIn('test_user', orchestrator.user_queues)

        # Check if the chatbot model was created
        self.assertIn('test_user', orchestrator.chatbot_models)

        # Check if ChatPromptTemplate.from_messages was called
        mock_from_messages.assert_called()

        # Check if the system prompt was set correctly
        expected_prompt_str = "Test system prompt for test_user"

        # The first argument to from_messages is a list of messages.
        call_args_list = mock_from_messages.call_args[0][0]
        # The first message in that list is a tuple: ("system", system_prompt)
        system_message_tuple = call_args_list[0]

        self.assertEqual(system_message_tuple[0], "system")
        self.assertEqual(system_message_tuple[1], expected_prompt_str)

    def test_e2e_response(self):
        """Tests a full message-response cycle."""
        orchestrator = chatbot.Orchestrator(config_path='testConfigurations/test_config.json')
        orchestrator._initialize_components()
        chatbot_model = orchestrator.chatbot_models['test_user']

        # Get a response from the chatbot
        response = chatbot_model.get_response("Hello")

        # The response should come from the fakeLlm's responseArray
        self.assertEqual(response, "Test response")


class TestOpenAIProvider(unittest.TestCase):

    @patch('chatbot.ChatPromptTemplate.from_messages')
    @patch('llmProviders.openAi.ChatOpenAI')
    def test_openai_provider_initialization(self, mock_chat_openai, mock_from_messages):
        """Tests that the OpenAI provider is initialized correctly."""

        # We need a dummy LLM and a dummy runnable to be returned by the mocks
        mock_chat_openai.return_value = MagicMock()
        mock_from_messages.return_value = MagicMock()

        orchestrator = chatbot.Orchestrator(config_path='testConfigurations/users_openai.json')
        orchestrator._initialize_components()

        # Check if the user queue was created
        self.assertIn('user_openai', orchestrator.user_queues)

        # Check if the chatbot model was created
        self.assertIn('user_openai', orchestrator.chatbot_models)

        # Check if ChatOpenAI was called with the correct parameters
        mock_chat_openai.assert_called_once_with(
            api_key='OPENAI_API_KEY_PLACEHOLDER',
            model='gpt-3.5-turbo',
            temperature=0.7
        )

        # Check if ChatPromptTemplate.from_messages was called with the correct system prompt
        expected_prompt_str = "You are an OpenAI assistant for user_openai."

        call_args_list = mock_from_messages.call_args[0][0]
        system_message_tuple = call_args_list[0]

        self.assertEqual(system_message_tuple[0], "system")
        self.assertEqual(system_message_tuple[1], expected_prompt_str)


if __name__ == '__main__':
    unittest.main()
