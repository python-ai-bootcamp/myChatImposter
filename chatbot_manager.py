import json
import importlib
import time
import threading
import sys
import inspect
import asyncio
from typing import Dict, Any, Optional, Type, List

from logging_lock import console_log, FileLogger
from config_models import UserConfiguration, ContextConfig

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableLambda
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import Field

from queue_manager import UserQueuesManager, Message, Sender, Group
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

class TimestampedAndPrefixedChatMessageHistory(ChatMessageHistory):
    """
    A ChatMessageHistory that stores messages with timestamps and prefixes AI messages.
    """
    message_timestamps: List[float] = Field(default_factory=list)

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the history with a timestamp."""
        if isinstance(message, AIMessage):
            # Create a new AIMessage with the prefixed content
            prefixed_message = AIMessage(content=f"Bot: {message.content}")
            super().add_message(prefixed_message)
        else:
            super().add_message(message)
        self.message_timestamps.append(time.time())

    def clear(self) -> None:
        """Clear messages and their timestamps."""
        super().clear()
        self.message_timestamps = []

class ChatbotModel:
    """A wrapper for the LangChain conversation model for a single user."""
    def __init__(self, user_id: str, llm: Any, system_prompt: str, context_config: ContextConfig):
        self.user_id = user_id
        self.llm = llm
        self.context_config = context_config
        self.histories: Dict[str, TimestampedAndPrefixedChatMessageHistory] = {}
        self.shared_history = TimestampedAndPrefixedChatMessageHistory()

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}"),
            ]
        )

        def _truncate_output(text: str) -> str:
            limit = self.context_config.max_characters_single_message
            if limit and limit > 0 and len(text) > limit:
                return text[:limit]
            return text

        runnable = prompt | self.llm | StrOutputParser() | RunnableLambda(_truncate_output)
        self.conversation = RunnableWithMessageHistory(
            runnable,
            self._get_session_history,
            input_messages_key="question",
            history_messages_key="history",
        )

    def _get_session_history(self, session_id: str) -> TimestampedAndPrefixedChatMessageHistory:
        """
        Returns the appropriate message history based on the shared_context flag.
        """
        if self.context_config.shared_context:
            return self.shared_history
        if session_id not in self.histories:
            self.histories[session_id] = TimestampedAndPrefixedChatMessageHistory()
        return self.histories[session_id]

    def _trim_history(self, history: TimestampedAndPrefixedChatMessageHistory):
        """
        Trims the message history based on the context_config settings.
        This is analogous to the _enforce_limits method in CorrespondentQueue.
        """
        now = time.time()
        max_age_seconds = self.context_config.max_days * 24 * 60 * 60
        total_chars = sum(len(msg.content) for msg in history.messages)

        # 1. Evict by age
        while history.messages and (now - history.message_timestamps[0]) > max_age_seconds:
            evicted_msg = history.messages.pop(0)
            history.message_timestamps.pop(0)
            total_chars -= len(evicted_msg.content)

        # 2. Evict by total characters (if new message would exceed)
        # In this context, we trim *before* adding the new message, so we check against the current limit.
        while history.messages and total_chars > self.context_config.max_characters:
            evicted_msg = history.messages.pop(0)
            history.message_timestamps.pop(0)
            total_chars -= len(evicted_msg.content)

        # 3. Evict by total message count
        while len(history.messages) > self.context_config.max_messages:
            evicted_msg = history.messages.pop(0)
            history.message_timestamps.pop(0)
            total_chars -= len(evicted_msg.content)

    async def get_response_async(self, content: str, sender_name: str, correspondent_id: str) -> str:
        """
        Gets a response from the model, using the context for the given correspondent.
        """
        session_id = self.user_id if self.context_config.shared_context else correspondent_id
        history = self._get_session_history(session_id)

        # Before getting a response, trim the history
        self._trim_history(history)

        # Truncate the incoming message content if it's too long
        limit = self.context_config.max_characters_single_message
        if limit and limit > 0 and len(content) > limit:
            content = content[:limit]

        # Format the message for the model
        formatted_message = f"{sender_name}: {content}"

        response = await self.conversation.ainvoke(
            {"question": formatted_message},
            config={"configurable": {"session_id": session_id}}
        )
        return response

    def get_all_histories(self) -> Dict[str, TimestampedAndPrefixedChatMessageHistory]:
        """Returns all message histories, shared or per-correspondent."""
        if self.context_config.shared_context:
            return {"shared_context": self.shared_history}
        return self.histories

from typing import Dict, Any, Optional, List

from typing import Dict, Any, Optional, List, Callable
from pymongo.collection import Collection
from dataclasses import asdict

class CorrespondenceIngester:
    """
    An asynchronous worker that pulls messages from queues and persists them to the database.
    """
    def __init__(self, user_id: str, provider_name: str, user_queues_manager: UserQueuesManager, queues_collection: Collection, main_loop):
        self.user_id = user_id
        self.provider_name = provider_name
        self.user_queues_manager = user_queues_manager
        self.queues_collection = queues_collection
        self.main_loop = main_loop
        self._stop_event = asyncio.Event()
        self._task = None

    def _normalize_to_text(self, message: Message) -> str:
        return message.content

    async def _run(self):
        """The main async loop for the ingester."""
        console_log(f"INGESTER ({self.user_id}): Starting up.")
        while not self._stop_event.is_set():
            any_message_processed = False
            all_queues = self.user_queues_manager.get_all_queues()

            for queue in all_queues:
                while True:
                    message = queue.pop_message()
                    if not message:
                        break

                    any_message_processed = True
                    try:
                        message_doc = asdict(message)
                        message_doc['user_id'] = self.user_id
                        message_doc['provider_name'] = self.provider_name
                        message_doc['correspondent_id'] = queue.correspondent_id

                        # Run the blocking DB call in a separate thread to not block the event loop
                        await asyncio.to_thread(self.queues_collection.insert_one, message_doc)

                        console_log(f"INGESTER ({self.user_id}/{queue.correspondent_id}): Successfully persisted message {message.id}.")
                    except Exception as e:
                        console_log(f"INGESTER_ERROR ({self.user_id}/{queue.correspondent_id}): Failed to process or save message {message.id}: {e}")

            if not any_message_processed:
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    pass

        console_log(f"INGESTER ({self.user_id}): Shutting down.")

    def start(self):
        """Starts the ingester task."""
        if not self._task:
            self._task = self.main_loop.create_task(self._run())

    async def stop(self):
        """Signals the ingester task to stop and waits for it to finish."""
        if self._task:
            self._stop_event.set()
            await self._task
            self._task = None

class ChatbotInstance:
    """Manages all components for a single chatbot instance."""
    def __init__(self, config: UserConfiguration, on_session_end: Optional[Callable[[str], None]] = None, queues_collection: Optional[Collection] = None, main_loop = None):
        self.user_id = config.user_id
        self.config = config
        self.on_session_end = on_session_end
        self.main_loop = main_loop
        self.user_queues_manager: Optional[UserQueuesManager] = None
        self.chatbot_model: Optional[ChatbotModel] = None
        self.provider_instance: Optional[Any] = None
        self.ingester: Optional[CorrespondenceIngester] = None
        self.whitelist: list = []
        self.whitelist_group: list = []
        self.mode: str = "fully_functional"  # Default mode
        self.warnings: List[str] = []
        self._queues_collection = queues_collection

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
        self.whitelist_group = self.config.respond_to_whitelist_group
        chat_provider_config = self.config.chat_provider_config
        provider_name = chat_provider_config.provider_name
        self.user_queues_manager = UserQueuesManager(
            user_id=self.user_id,
            provider_name=provider_name,
            queue_config=self.config.queue_config,
            queues_collection=self._queues_collection,
            main_loop=self.main_loop
        )
        console_log(f"INSTANCE ({self.user_id}): Initialized queue manager.")

        # 2. Initialize Ingester (if DB is available)
        if self._queues_collection is not None:
            self.ingester = CorrespondenceIngester(
                user_id=self.user_id,
                provider_name=provider_name,
                user_queues_manager=self.user_queues_manager,
                queues_collection=self._queues_collection,
                main_loop=self.main_loop
            )
            console_log(f"INSTANCE ({self.user_id}): Initialized correspondence ingester.")
        else:
            console_log(f"INSTANCE_WARNING ({self.user_id}): No database collection provided. Ingester will not run.")

        # 3. Initialize Chat Provider (Essential)
        provider_module = importlib.import_module(f"chat_providers.{provider_name}")
        ProviderClass = _find_provider_class(provider_module, BaseChatProvider)
        if not ProviderClass:
            raise ImportError(f"Could not find a valid chat provider class in module 'chat_providers.{provider_name}'")

        file_logger = FileLogger(self.user_id, provider_name)

        provider_init_params = {
            "user_id": self.user_id,
            "config": chat_provider_config,
            "user_queues": {self.user_id: self.user_queues_manager},
            "on_session_end": self.on_session_end,
            "logger": file_logger,
        }
        if provider_name == "whatsAppBaileyes":
            provider_init_params["main_loop"] = self.main_loop

        self.provider_instance = ProviderClass(**provider_init_params)
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
            self.chatbot_model = ChatbotModel(
                self.user_id,
                llm_instance,
                system_prompt,
                self.config.context_config
            )
            console_log(f"INSTANCE ({self.user_id}): Initialized chatbot model using LLM provider '{llm_provider_name}'.")
        else:
            self.mode = "collection_only"
            console_log(f"INSTANCE_WARNING ({self.user_id}): No 'llm_provider_config' found. Instance will run in collection-only mode.")

    async def _message_callback(self, user_id: str, correspondent_id: str, message: Message):
        """Processes a new message from a correspondent's queue."""
        console_log(f"INSTANCE ({user_id}/{correspondent_id}): Callback received for message {message.id}.")

        if message.source == 'bot':
            return

        if message.group:
            if self.whitelist_group:
                group = message.group
                all_identifiers = [group.identifier, group.display_name]
                console_log(f"INSTANCE ({user_id}): Evaluating group '{group.display_name}' against group whitelist. Identifiers: {all_identifiers}, Whitelist: {self.whitelist_group}")


                matching_identifier = None
                matching_whitelist_entry = None
                is_whitelisted = False

                for whitelisted_group in self.whitelist_group:
                    if not whitelisted_group:
                        continue
                    for identifier in all_identifiers:
                        if identifier and whitelisted_group in identifier:
                            is_whitelisted = True
                            matching_identifier = identifier
                            matching_whitelist_entry = whitelisted_group
                            break
                    if is_whitelisted:
                        break

                if is_whitelisted:
                    console_log(f"INSTANCE ({user_id}): Group whitelist check passed for group '{group.display_name}'. Identifier '{matching_identifier}' matched whitelist entry '{matching_whitelist_entry}'.")
                else:
                    console_log(f"INSTANCE ({user_id}): Group '{group.display_name}' not in group whitelist. Ignoring.")
                    return
        elif self.whitelist:
            sender = message.sender
            all_identifiers = [sender.identifier] + getattr(sender, 'alternate_identifiers', [])
            console_log(f"INSTANCE ({user_id}): Evaluating sender '{sender.display_name}' against direct message whitelist. Identifiers: {all_identifiers}, Whitelist: {self.whitelist}")

            matching_identifier = None
            matching_whitelist_entry = None
            is_whitelisted = False

            for whitelisted_sender in self.whitelist:
                if not whitelisted_sender:
                    continue
                for identifier in all_identifiers:
                    if identifier and whitelisted_sender in identifier:
                        is_whitelisted = True
                        matching_identifier = identifier
                        matching_whitelist_entry = whitelisted_sender
                        break
                if is_whitelisted:
                    break

            if is_whitelisted:
                console_log(f"INSTANCE ({user_id}): Whitelist check passed for sender '{sender.display_name}'. Identifier '{matching_identifier}' matched whitelist entry '{matching_whitelist_entry}'.")
            else:
                console_log(f"INSTANCE ({user_id}): Sender '{sender.display_name}' not in whitelist. Ignoring.")
                return

        if not self.chatbot_model or not self.provider_instance:
            console_log(f"INSTANCE_ERROR ({user_id}): Chatbot or provider not initialized.")
            return

        try:
            response_text = await self.chatbot_model.get_response_async(
                content=message.content,
                sender_name=message.sender.display_name,
                correspondent_id=correspondent_id
            )

            # If the message is from a group, reply to the group. Otherwise, reply to the sender.
            recipient = message.group.identifier if message.group else message.sender.identifier
            await self.provider_instance.sendMessage(recipient, response_text)

            # The bot's response is no longer added directly to the queue.
            # It will be processed when it comes back from the WebSocket as an outgoing message.
        except Exception as e:
            console_log(f"Error in callback for user {user_id}: {e}")


    async def start(self):
        """
        Wires up and starts the instance.
        Raises an exception if essential components like the queue or provider are not initialized.
        """
        if not self.user_queues_manager or not self.provider_instance:
            # This is a critical error, as the instance cannot function at all without these.
            # This will be caught by the exception handler in main.py and reported to the user.
            raise RuntimeError(f"Instance {self.user_id} cannot start: queue manager or provider not initialized.")

        console_log(f"INSTANCE ({self.user_id}): Registering callback and starting provider listener...")
        self.user_queues_manager.register_callback(self._message_callback)

        if self.ingester:
            self.ingester.start()

        await self.provider_instance.start_listening()
        console_log(f"INSTANCE ({self.user_id}): System is running.")

    async def stop(self, cleanup_session: bool = False):
        """
        Stops the provider listener gracefully.

        Args:
            cleanup_session (bool): If True, instructs the provider to also clean up
                                    the session data (e.g., on user unlink).
        """
        if self.ingester:
            await self.ingester.stop()

        if self.provider_instance:
            console_log(f"INSTANCE ({self.user_id}): Shutting down... (cleanup={cleanup_session})")
            await self.provider_instance.stop_listening(cleanup_session=cleanup_session)
            console_log(f"INSTANCE ({self.user_id}): Shutdown complete.")

    async def get_status(self):
        """Gets the connection status from the provider."""
        if self.provider_instance and hasattr(self.provider_instance, 'get_status'):
            return await self.provider_instance.get_status()
        return {"status": "unknown", "message": "Provider does not support status checks."}
