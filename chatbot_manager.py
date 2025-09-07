import json
import importlib
import time
import threading
import sys
import inspect
from typing import Dict, Any, Optional, Type, List

from logging_lock import console_log, FileLogger
from config_models import UserConfiguration

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser

from queue_manager import UserQueue, Message, Sender, Group
from chat_providers.base import BaseChatProvider
from llm_providers.base import BaseLlmProvider

def _find_provider_class(module, base_class: Type) -> Optional[Type]:
    """
    Finds a class in the module that is a subclass of the base_class.
    """
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, base_class) and obj is not base_class:
            return obj
    return None

class ChatbotModel:
    """A wrapper for the LangChain conversation model for a single user."""
    def __init__(self, user_id: str, llm: Any, system_prompt: str):
        self.user_id = user_id
        self.llm = llm
        self.message_history = ChatMessageHistory()
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}"),
            ]
        )
        runnable = prompt | self.llm | StrOutputParser()
        self.conversation = RunnableWithMessageHistory(
            runnable,
            lambda session_id: self.message_history,
            input_messages_key="question",
            history_messages_key="history",
        )

    def get_response(self, message: str) -> str:
        return self.conversation.invoke({"question": message}, config={"configurable": {"session_id": self.user_id}})

from typing import Dict, Any, Optional, List

from typing import Dict, Any, Optional, List, Callable

class ChatbotInstance:
    """Manages all components for a single chatbot instance."""
    def __init__(self, config: UserConfiguration, on_session_end: Optional[Callable[[str], None]] = None):
        self.user_id = config.user_id
        self.config = config
        self.on_session_end = on_session_end
        self.user_queue: Optional[UserQueue] = None
        self.chatbot_model: Optional[ChatbotModel] = None
        self.provider_instance: Optional[Any] = None
        self.whitelist: list = []
        self.mode: str = "fully_functional"  # Default mode
        self.warnings: List[str] = []

        self._initialize_components()

    def _initialize_components(self):
        """
        Initializes all components for this instance based on the config.
        The chat provider is essential. The LLM provider is optional; if not
        provided, the instance will run in "collection only" mode.
        """
        console_log(f"INSTANCE ({self.user_id}): Initializing components...")

        # 1. Initialize Queue (Essential)
        self.whitelist = self.config.respond_to_whitelist
        chat_provider_config = self.config.chat_provider_config
        provider_name = chat_provider_config.provider_name
        self.user_queue = UserQueue(
            user_id=self.user_id,
            provider_name=provider_name,
            queue_config=self.config.queue_config
        )
        console_log(f"INSTANCE ({self.user_id}): Initialized queue.")

        # 2. Initialize Chat Provider (Essential)
        provider_module = importlib.import_module(f"chat_providers.{provider_name}")
        ProviderClass = _find_provider_class(provider_module, BaseChatProvider)
        if not ProviderClass:
            raise ImportError(f"Could not find a valid chat provider class in module 'chat_providers.{provider_name}'")

        file_logger = FileLogger(self.user_id, provider_name)

        self.provider_instance = ProviderClass(
            user_id=self.user_id,
            config=chat_provider_config,
            user_queues={self.user_id: self.user_queue},
            on_session_end=self.on_session_end,
            logger=file_logger
        )
        console_log(f"INSTANCE ({self.user_id}): Initialized chat provider '{provider_name}'.")

        # 3. Initialize Chatbot Model (Optional)
        if self.config.llm_provider_config:
            self.mode = "fully_functional"
            llm_provider_name = self.config.llm_provider_config.provider_name
            llm_provider_module = importlib.import_module(f"llm_providers.{llm_provider_name}")
            LlmProviderClass = _find_provider_class(llm_provider_module, BaseLlmProvider)
            if not LlmProviderClass:
                raise ImportError(f"Could not find a valid LLM provider class in module 'llm_providers.{llm_provider_name}'")

            llm_provider = LlmProviderClass(config=self.config.llm_provider_config, user_id=self.user_id)
            llm_instance = llm_provider.get_llm()
            system_prompt = llm_provider.get_system_prompt()
            self.chatbot_model = ChatbotModel(self.user_id, llm_instance, system_prompt)
            console_log(f"INSTANCE ({self.user_id}): Initialized chatbot model using LLM provider '{llm_provider_name}'.")
        else:
            self.mode = "collection_only"
            console_log(f"INSTANCE_WARNING ({self.user_id}): No 'llm_provider_config' found. Instance will run in collection-only mode.")

    def _message_callback(self, user_id: str, message: Message):
        """Processes a new message from the queue."""
        console_log(f"INSTANCE ({user_id}): Callback received for message {message.id}.")

        if message.source == 'bot':
            return

        if self.whitelist:
            sender_identifier = message.sender.identifier
            sender_display_name = message.sender.display_name

            # Check if any whitelisted string is a substring of either the identifier or display name
            if not any(
                whitelisted_sender in sender_identifier or whitelisted_sender in sender_display_name
                for whitelisted_sender in self.whitelist
            ):
                console_log(f"INSTANCE ({user_id}): Sender '{message.sender.identifier}' not in whitelist. Ignoring.")
                return

        if not self.chatbot_model or not self.provider_instance:
            console_log(f"INSTANCE_ERROR ({user_id}): Chatbot or provider not initialized.")
            return

        try:
            response_text = self.chatbot_model.get_response(message.content)

            # If the message is from a group, reply to the group. Otherwise, reply to the sender.
            recipient = message.group.identifier if message.group else message.sender.identifier
            self.provider_instance.sendMessage(recipient, response_text)

            bot_sender = Sender(identifier=f"bot_{user_id}", display_name=f"Bot ({user_id})")
            if self.user_queue:
                self.user_queue.add_message(
                    content=response_text,
                    sender=bot_sender,
                    source='bot',
                    originating_time=int(time.time() * 1000)
                )
        except Exception as e:
            console_log(f"Error in callback for user {user_id}: {e}")


    def start(self):
        """
        Wires up and starts the instance.
        Raises an exception if essential components like the queue or provider are not initialized.
        """
        if not self.user_queue or not self.provider_instance:
            # This is a critical error, as the instance cannot function at all without these.
            # This will be caught by the exception handler in main.py and reported to the user.
            raise RuntimeError(f"Instance {self.user_id} cannot start: queue or provider not initialized.")

        console_log(f"INSTANCE ({self.user_id}): Registering callback and starting provider listener...")
        self.user_queue.register_callback(self._message_callback)
        self.provider_instance.start_listening()
        console_log(f"INSTANCE ({self.user_id}): System is running.")

    def stop(self, cleanup_session: bool = False):
        """
        Stops the provider listener gracefully.

        Args:
            cleanup_session (bool): If True, instructs the provider to also clean up
                                    the session data (e.g., on user unlink).
        """
        if self.provider_instance:
            console_log(f"INSTANCE ({self.user_id}): Shutting down... (cleanup={cleanup_session})")
            self.provider_instance.stop_listening(cleanup_session=cleanup_session)
            console_log(f"INSTANCE ({self.user_id}): Shutdown complete.")

    def get_status(self):
        """Gets the connection status from the provider."""
        if self.provider_instance and hasattr(self.provider_instance, 'get_status'):
            return self.provider_instance.get_status()
        return {"status": "unknown", "message": "Provider does not support status checks."}
