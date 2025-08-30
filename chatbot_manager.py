import json
import importlib
import time
import threading
import sys
import inspect
from typing import Dict, Any, Optional, Type, List

from logging_lock import lock

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

class ChatbotInstance:
    """Manages all components for a single chatbot instance."""
    def __init__(self, config: Dict[str, Any]):
        self.user_id = config['user_id']
        self.config = config
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
        with lock:
            sys.stdout.buffer.write(f"INSTANCE ({self.user_id}): Initializing components...\n".encode('utf-8'))
            sys.stdout.flush()

        # 1. Initialize Queue (Essential)
        self.whitelist = self.config.get('respond_to_whitelist', [])
        chat_provider_config = self.config['chat_provider_config']
        provider_name = chat_provider_config['provider_name']
        q_config = self.config['queue_config']
        self.user_queue = UserQueue(
            user_id=self.user_id,
            provider_name=provider_name,
            max_messages=q_config['max_messages'],
            max_characters=q_config['max_characters'],
            max_days=q_config['max_days'],
            max_characters_single_message=q_config.get('max_characters_single_message', q_config['max_characters'])
        )
        with lock:
            sys.stdout.buffer.write(f"INSTANCE ({self.user_id}): Initialized queue.\n".encode('utf-8'))
            sys.stdout.flush()

        # 2. Initialize Chat Provider (Essential)
        provider_config = chat_provider_config.get('provider_config')
        if provider_config is None:
            self.warnings.append("No 'provider_config' section found for chat provider; reverting to default settings.")
            provider_config = {}

        provider_module = importlib.import_module(f"chat_providers.{provider_name}")
        ProviderClass = _find_provider_class(provider_module, BaseChatProvider)
        if not ProviderClass:
            raise ImportError(f"Could not find a valid chat provider class in module 'chat_providers.{provider_name}'")

        self.provider_instance = ProviderClass(
            user_id=self.user_id,
            config=provider_config,
            user_queues={self.user_id: self.user_queue}
        )
        with lock:
            sys.stdout.buffer.write(f"INSTANCE ({self.user_id}): Initialized chat provider '{provider_name}'.\n".encode('utf-8'))
            sys.stdout.flush()

        # 3. Initialize Chatbot Model (Optional)
        llm_provider_config = self.config.get('llm_provider_config')
        if llm_provider_config:
            self.mode = "fully_functional"
            llm_provider_name = llm_provider_config['provider_name']
            llm_provider_module = importlib.import_module(f"llm_providers.{llm_provider_name}")
            LlmProviderClass = _find_provider_class(llm_provider_module, BaseLlmProvider)
            if not LlmProviderClass:
                raise ImportError(f"Could not find a valid LLM provider class in module 'llm_providers.{llm_provider_name}'")

            llm_provider = LlmProviderClass(config=llm_provider_config.get('provider_config', {}), user_id=self.user_id)
            llm_instance = llm_provider.get_llm()
            system_prompt = llm_provider.get_system_prompt()
            self.chatbot_model = ChatbotModel(self.user_id, llm_instance, system_prompt)
            with lock:
                sys.stdout.buffer.write(f"INSTANCE ({self.user_id}): Initialized chatbot model using LLM provider '{llm_provider_name}'.\n".encode('utf-8'))
                sys.stdout.flush()
        else:
            self.mode = "collection_only"
            with lock:
                sys.stdout.buffer.write(f"INSTANCE_WARNING ({self.user_id}): No 'llm_provider_config' found. Instance will run in collection-only mode.\n".encode('utf-8'))
                sys.stdout.flush()

    def _message_callback(self, user_id: str, message: Message):
        """Processes a new message from the queue."""
        with lock:
            sys.stdout.buffer.write(f"INSTANCE ({user_id}): Callback received for message {message.id}.\n".encode('utf-8'))
            sys.stdout.flush()

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
                with lock:
                    log_message = f"INSTANCE ({user_id}): Sender '{sender_identifier}' ('{sender_display_name}') not in whitelist. Ignoring.\n"
                    sys.stdout.buffer.write(log_message.encode('utf-8', 'backslashreplace'))
                    sys.stdout.flush()
                return

        if not self.chatbot_model or not self.provider_instance:
            with lock:
                sys.stdout.buffer.write(f"INSTANCE_ERROR ({user_id}): Chatbot or provider not initialized.\n".encode('utf-8'))
                sys.stdout.flush()
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
            with lock:
                # Using backslashreplace to handle any weird characters in the error message itself
                error_str = f"Error in callback for user {user_id}: {e}\n"
                sys.stdout.buffer.write(error_str.encode('utf-8', 'backslashreplace'))
                sys.stdout.flush()


    def start(self):
        """
        Wires up and starts the instance.
        Raises an exception if essential components like the queue or provider are not initialized.
        """
        if not self.user_queue or not self.provider_instance:
            # This is a critical error, as the instance cannot function at all without these.
            # This will be caught by the exception handler in main.py and reported to the user.
            raise RuntimeError(f"Instance {self.user_id} cannot start: queue or provider not initialized.")

        with lock:
            sys.stdout.buffer.write(f"INSTANCE ({self.user_id}): Registering callback and starting provider listener...\n".encode('utf-8'))
            sys.stdout.flush()
        self.user_queue.register_callback(self._message_callback)
        self.provider_instance.start_listening()
        with lock:
            sys.stdout.buffer.write(f"INSTANCE ({self.user_id}): System is running.\n".encode('utf-8'))
            sys.stdout.flush()

    def stop(self):
        """Stops the provider listener gracefully."""
        if self.provider_instance:
            with lock:
                sys.stdout.buffer.write(f"INSTANCE ({self.user_id}): Shutting down...\n".encode('utf-8'))
                sys.stdout.flush()
            self.provider_instance.stop_listening()
            with lock:
                sys.stdout.buffer.write(f"INSTANCE ({self.user_id}): Shutdown complete.\n".encode('utf-8'))
                sys.stdout.flush()

    def get_status(self):
        """Gets the connection status from the provider."""
        if self.provider_instance and hasattr(self.provider_instance, 'get_status'):
            return self.provider_instance.get_status()
        return {"status": "unknown", "message": "Provider does not support status checks."}
