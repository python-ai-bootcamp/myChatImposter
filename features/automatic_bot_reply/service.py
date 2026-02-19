import importlib
import inspect
import time
import logging
import asyncio
from typing import Dict, Any, Optional, Type, List

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from pydantic import Field

from config_models import ContextConfig
from queue_manager import Message
from llm_providers.base import BaseLlmProvider
from services.session_manager import SessionManager
from .whitelist import WhitelistPolicy

from utils.provider_utils import find_provider_class

class TimestampedAndPrefixedChatMessageHistory(ChatMessageHistory):
    """
    A ChatMessageHistory that stores messages with timestamps, prefixes, and handles truncation.
    """
    message_timestamps: List[float] = Field(default_factory=list)
    context_config: ContextConfig = Field(default_factory=ContextConfig)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pop context_config from kwargs to prevent it from being passed to Pydantic's ChatMessageHistory
        self.context_config = kwargs.pop('context_config', ContextConfig())

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the history with a timestamp and apply truncation."""
        limit = self.context_config.max_characters_single_message

        # Truncate content if necessary
        truncated_content = message.content
        if limit and limit > 0 and len(truncated_content) > limit:
            truncated_content = truncated_content[:limit]

        # Create a new message with the potentially truncated content
        if isinstance(message, AIMessage):
            new_message = AIMessage(content=f"Bot: {truncated_content}")
        elif isinstance(message, HumanMessage):
            # Human messages are already formatted with the sender's name at this point.
            # We need to find the content part and truncate it.
            parts = message.content.split(": ", 1)
            if len(parts) == 2:
                sender, original_content = parts
                if limit and limit > 0 and len(original_content) > limit:
                    original_content = original_content[:limit]
                new_content = f"{sender}: {original_content}"
                new_message = HumanMessage(content=new_content)
            else: # Fallback for unexpected format
                 new_message = HumanMessage(content=truncated_content)
        else:
            new_message = message.__class__(content=truncated_content)

        super().add_message(new_message)
        self.message_timestamps.append(time.time())

    def clear(self) -> None:
        """Clear messages and their timestamps."""
        super().clear()
        self.message_timestamps = []

class ChatbotModel:
    """A wrapper for the LangChain conversation model for a single bot user (bot_id)."""
    def __init__(self, bot_id: str, llm: Any, system_prompt: str, context_config: ContextConfig):
        self.bot_id = bot_id
        self.llm = llm
        self.context_config = context_config
        self.system_prompt = system_prompt
        self.histories: Dict[str, TimestampedAndPrefixedChatMessageHistory] = {}
        self.shared_history = TimestampedAndPrefixedChatMessageHistory(context_config=self.context_config)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{question}"),
            ]
        )

        self.runnable = prompt | self.llm | StrOutputParser()
        self.conversation = RunnableWithMessageHistory(
            self.runnable,
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
            self.histories[session_id] = TimestampedAndPrefixedChatMessageHistory(context_config=self.context_config)
        return self.histories[session_id]

    def _trim_history(self, history: TimestampedAndPrefixedChatMessageHistory):
        """
        Trims the message history based on the context_config settings.
        """
        now = time.time()
        max_age_seconds = self.context_config.max_days * 24 * 60 * 60
        total_chars = sum(len(msg.content) for msg in history.messages)

        # 1. Evict by age
        while history.messages and (now - history.message_timestamps[0]) > max_age_seconds:
            evicted_msg = history.messages.pop(0)
            history.message_timestamps.pop(0)
            total_chars -= len(evicted_msg.content)

        # 2. Evict by total characters
        while history.messages and total_chars > self.context_config.max_characters:
            evicted_msg = history.messages.pop(0)
            history.message_timestamps.pop(0)
            total_chars -= len(evicted_msg.content)

        # 3. Evict by total message count
        while history.messages and len(history.messages) + 2 > self.context_config.max_messages:
            evicted_msg = history.messages.pop(0)
            history.message_timestamps.pop(0)
            total_chars -= len(evicted_msg.content)

    async def get_response_async(self, content: str, sender_name: str, correspondent_id: str) -> str:
        """
        Gets a response from the model, using the context for the given correspondent.
        """
        session_id = self.bot_id if self.context_config.shared_context else correspondent_id
        history = self._get_session_history(session_id)

        # Before getting a response, trim the history
        self._trim_history(history)

        # Format the message for the model
        formatted_message = f"{sender_name}: {content}"

        # Capture current history state *before* adding the new message
        # This prevents the message from being duplicated in the prompt (once in history, once as 'question')
        current_history_messages = list(history.messages)

        # Invoke the underlying runnable directly
        logging.info(f"INVOKING LANCHAIN CHAIN for session {session_id}")
        response = await self.runnable.ainvoke(
            {"question": formatted_message, "history": current_history_messages},
            config={"configurable": {"session_id": session_id}}
        )
        logging.info(f"LANCHAIN CHAIN RETURNED for session {session_id}")

        # Manually add the user message to history *after* generation (or just updates the store)
        history.add_message(HumanMessage(content=formatted_message))

        # Manually add the AI response to history
        history.add_message(AIMessage(content=response))

        return response

    def get_all_histories(self) -> Dict[str, TimestampedAndPrefixedChatMessageHistory]:
        """
        Returns all active histories.
        """
        if self.context_config.shared_context:
            return {"SHARED_CONTEXT": self.shared_history}
        return self.histories


class AutomaticBotReplyService:
    """
    Service that subscribers to incoming messages and generates LLM replies 
    if the sender is whitelisted.
    """
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.config = session_manager.config
        self.bot_id = self.config.bot_id
        
        self.whitelist = self.config.features.automatic_bot_reply.respond_to_whitelist
        self.whitelist_group = self.config.features.automatic_bot_reply.respond_to_whitelist_group
        self.chatbot_model: Optional[ChatbotModel] = None
        self.llm: Any = None # Initialize self.llm here
        
        self._initialize_llm()

    def _initialize_llm(self):
        try:
            from services.llm_factory import create_tracked_llm
            
            # Use the new factory with token tracking
            # user_id should be the OWNER of the bot
            owner_user_id = self.session_manager.owner_user_id if self.session_manager.owner_user_id else self.bot_id
            
            llm_instance = create_tracked_llm(
                llm_config=self.config.configurations.llm_configs.high,
                user_id=owner_user_id, 
                bot_id=self.bot_id,
                feature_name="automatic_bot_reply",
                config_tier="high",
                token_consumption_collection=self.session_manager.token_consumption_collection
            )
            
            self.llm = llm_instance
            logging.info(f"Initialized LLM provider '{self.config.configurations.llm_configs.high.provider_name}' with token tracking.")
            system_prompt = self.config.features.automatic_bot_reply.chat_system_prompt.format(user_id=self.bot_id)
            
            self.chatbot_model = ChatbotModel(
                self.bot_id,
                llm_instance,
                system_prompt,
                self.config.configurations.context_config
            )
            logging.info(f"AUTO_REPLY ({self.bot_id}): Initialized chatbot model using LLM provider '{self.config.configurations.llm_configs.high.provider_name}'.")
        except Exception as e:
            logging.error(f"AUTO_REPLY ({self.bot_id}): Failed to initialize LLM: {e}")
            raise

    async def handle_message(self, correspondent_id: str, message: Message):
        """
        Handler for incoming messages. Checks whitelist and replies.
        """
        if message.group:
            if not self.whitelist_group:
                # No group whitelist configured, skip
                return
            
            group = message.group
            identifiers = [group.identifier, group.display_name]
            logging.info(f"AUTO_REPLY ({self.bot_id}): Evaluating group '{group.display_name}' against group whitelist. Identifiers: {identifiers}, Whitelist: {self.whitelist_group}")
            
            result = WhitelistPolicy.check(identifiers, self.whitelist_group)
            
            if result.is_allowed:
                logging.info(f"AUTO_REPLY ({self.bot_id}): Group whitelist check passed for group '{group.display_name}'. Identifier '{result.matched_identifier}' matched whitelist entry '{result.matched_whitelist_entry}'.")
            else:
                logging.info(f"AUTO_REPLY ({self.bot_id}): Group '{group.display_name}' not in group whitelist. Ignoring.")
                return
        else:
            if not self.whitelist:
                # No whitelist configured for direct messages, skip
                return
            
            sender = message.sender
            identifiers = [sender.identifier] + getattr(sender, 'alternate_identifiers', [])
            logging.info(f"AUTO_REPLY ({self.bot_id}): Evaluating sender '{sender.display_name}' against direct message whitelist. Identifiers: {identifiers}, Whitelist: {self.whitelist}")
            
            result = WhitelistPolicy.check(identifiers, self.whitelist)
            
            if result.is_allowed:
                logging.info(f"AUTO_REPLY ({self.bot_id}): Whitelist check passed for sender '{sender.display_name}'. Identifier '{result.matched_identifier}' matched whitelist entry '{result.matched_whitelist_entry}'.")
            else:
                logging.info(f"AUTO_REPLY ({self.bot_id}): Sender '{sender.display_name}' not in whitelist. Ignoring.")
                return

        if not self.chatbot_model or not self.session_manager.provider_instance:
            logging.error(f"AUTO_REPLY ({self.bot_id}): Chatbot or provider not initialized.")
            return

        try:
            response_text = await self.chatbot_model.get_response_async(
                content=message.content,
                sender_name=message.sender.display_name,
                correspondent_id=correspondent_id
            )

            # If the message is from a group, reply to the group. Otherwise, reply to the sender.
            # Note: message.group.identifier IS the correspondent_id for groups.
            # And for DMs, correspondent_id IS the sender identity.
            # So we can just use correspondent_id.
            recipient = correspondent_id
            await self.session_manager.provider_instance.sendMessage(recipient, response_text)

        except Exception as e:
            logging.error(f"AUTO_REPLY ({self.bot_id}): Error in bot reply handler: {e}")
