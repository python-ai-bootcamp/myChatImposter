import json
import importlib
import inspect
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from config_models import LLMProviderConfig
from llm_providers.base import BaseLlmProvider
from resources import get_language_name

# Initialize logger
logger = logging.getLogger(__name__)

class ActionItemExtractor:
    def __init__(self):
        pass

    def __init__(self):
        pass

    def _build_llm_input_json(self, messages: list, timezone: ZoneInfo) -> str:
        """
        Builds a JSON array of messages formatted for LLM input.
        Each message has: when (timestamp in user's timezone), sender (display name), content.
        """
        formatted_messages = []
        for msg in messages:
            originating_time_ms = msg.get('originating_time', 0)
            originating_dt = datetime.fromtimestamp(originating_time_ms / 1000, tz=timezone)
            formatted_msg = {
                "when": originating_dt.strftime('%Y-%m-%d %H:%M'),
                "sender": msg.get('sender', {}).get('display_name', 'Unknown'),
                "content": msg.get('message', '')
            }
            formatted_messages.append(formatted_msg)
        return json.dumps(formatted_messages, indent=2, ensure_ascii=False)

    def _parse_llm_json(self, json_str: str) -> list:
        """
        Parses the LLM response which is expected to be a JSON array.
        Handles code blocks and other common LLM artifacts.
        """
        cleaned_response = json_str.strip()
        # Remove markdown code blocks if present
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        
        cleaned_response = cleaned_response.strip()

        try:
            parsed = json.loads(cleaned_response)
            if isinstance(parsed, list):
                return parsed
            else:
                logger.warning(f"LLM returned valid JSON but not a list: {type(parsed)}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON: {e}. Raw: {json_str[:200]}...")
            return []

    async def extract(self, messages: list, llm_config: LLMProviderConfig, user_id: str, timezone: ZoneInfo, group_id: str = "", language_code: str = "en") -> list:
        """
        Main entry point. Uses LLM to extract action items from group messages.
        
        Args:
            messages: List of raw message dicts
            llm_config: LLM provider configuration
            user_id: User identifier
            timezone: User's timezone
            group_id: Group identifier for recording purposes
            language_code: ISO 639-1 language code for response language
            
        Returns:
            List of action item dicts.
        """
        from llm_providers.recorder import LLMRecorder
        
        # Build Input JSON
        messages_json = self._build_llm_input_json(messages, timezone)
        logger.info(f"Built LLM input JSON with {len(messages)} messages for user {user_id}")

        # System prompt with language placeholder - uses LangChain template syntax
        # Curly braces for JSON are escaped with {{ and }}
        system_prompt_template = """You are a helpful assistant. For each chat group message thread you receive, extract all actionable items mentioned in the conversation and produce a structured summary.

General rules:

* task_title and task_description fields in output json must be written in language_code='{language_code}' ({language_name}).
* any important event must be included, even if no deadline is specified.
* if a task or event includes any form of date or deadline, it must appear verbatim in text_deadline and be parsed into timestamp_deadline as defined below.
* if a task or event is canceled it is also considered an actionable item, if new alternative date is suggested, wrap them both in a single actionable item. do not split into two actionable items.
* if no tasks are found return an empty array.

Output must be only a JSON array. Each object represents a single action item and has the following structure:
[{{
"relevant_task_messages": <array of RELEVANT_TASK_MESSAGE>,
"text_deadline": <sender-quoted deadline or event date string, or empty string if none exists>,
"timestamp_deadline": <absolute timestamp string derived from the sender-quoted deadline formatted yyyy-mm-dd hh:mm:ss, or empty string if none>,
"task_title": <short, concise task title>,
"task_description": <concise but complete task description>
}}]

Field rules:

* relevant_task_messages:
    - must include all messages directly related to the action item 
    - include only messages relevant to the actionable item, no needless commentary messages are needed.
    - all relevant task messages object should be copied without any alteration at all (do not modify in any way, not even a single letter, copy AS IS).
* text_deadline:
    - must contain the task deadline or event date exactly as written by the sender
    - if no deadline or event date is mentioned, set an empty string
* timestamp_deadline:
    - must be an absolute timestamp (not relative) in yyyy-mm-dd hh:mm:ss format (24h). 
    - relative deadlines (e.g. "next week", "next Wednesday") must be resolved relative to the time in which the message containing the deadline was sent. 
    - if no hour is specified in deadline, default to 12:00:00 noon. 
    - If no deadline exists, use an empty string.
* task_title:
    - must be a short, concise task title
    - must be written in {language_name} regardless of relevant_task_messages origin language
* task_description: 
    - must aggregate information from all related messages 
    - should includes relevant details: 
        -- needed preparations for task or event (keep it dry, do not improvise and add unneeded information)
        -- all people mentioned as relevant to the task's essence  
        -- a deadline or event date at the end of the task_description message (if one is available). 
    - deadline or event date format:    
       -- weekday name (in {language_name}, full weekday name, no shortname), date(formatted dd/mm/yyyy only), and time (24h formatted). If no hour was specified, neglect it.
       -- if the deadline was relative, include a resolved absolute deadline in following format: (weekday name (in {language_name}, full weekday name, no shortname), date(formatted dd/mm/yyyy only), and time (24h formatted). If no hour was specified, neglect it.
       -- double check weekday corresponds to the absolute date found in timestamp_deadline correctly
    - if relevant people are mentioned do not alter their name spelling in any way. copy it AS IS to the letter. no removal of any Matres lectionis (vowel indicators)!!!
    - double check that the quoted names appear identical (string compare) to the actual names appearing in message content or sender field inside relevant_task_messages correspondence    
    - must be written in {language_name} regardless of relevant_task_messages origin language
    
RELEVANT_TASK_MESSAGE format:
{{
"originating_time": <time the message was sent>,
"sender": <sender name>,
"content": <message content>
}}
"""
        
        # Setup recorder if enabled
        record_enabled = llm_config.provider_config.record_llm_interactions
        recorder = None
        epoch_ts = None
        if record_enabled:
            recorder = LLMRecorder(user_id, "periodic_group_tracking", group_id)
            epoch_ts = recorder.start_recording()
            # Format prompt for recording - substitute language_name variable
            language_name = get_language_name(language_code)
            formatted_prompt = system_prompt_template.replace("{language_name}", language_name)
            recorder.record_prompt(formatted_prompt, messages_json, epoch_ts=epoch_ts)
            # Record full LLM config (model, temperature, reasoning_effort, etc.)
            config_dict = llm_config.provider_config.model_dump()
            config_dict['provider_name'] = llm_config.provider_name
            config_dict['language_code'] = language_code
            recorder.record_config(config_dict, epoch_ts=epoch_ts)
        
        try:
            # Dynamically load the LLM provider
            llm_provider_name = llm_config.provider_name
            llm_provider_module = importlib.import_module(f"llm_providers.{llm_provider_name}")
            from utils.provider_utils import find_provider_class
            LlmProviderClass = find_provider_class(llm_provider_module, BaseLlmProvider)
            
            if not LlmProviderClass:
                logger.error(f"Could not find LLM provider class for {llm_provider_name}")
                return []
            
            llm_provider = LlmProviderClass(config=llm_config, user_id=f"action_items_{user_id}")
            llm = llm_provider.get_llm()
            
            # Create the prompt and chain - language_code passed as template variable
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt_template),
                ("human", "{input}")
            ])
            
            chain = prompt | llm | StrOutputParser()
            
            # Inspect and log the actual formatted messages
            language_name = get_language_name(language_code)
            formatted_messages = await prompt.aformat_messages(input=messages_json, language_code=language_code, language_name=language_name)
            print(f"--- LLM PROMPT DEBUG ---")
            print(f"System Message Content: {formatted_messages[0].content}")
            print(f"Human Message Content: {formatted_messages[1].content}")
            print(f"------------------------")

            # Invoke the chain with all template variables
            logger.info(f"Invoking LLM for action items extraction for user {user_id}")
            result = await chain.ainvoke({"input": messages_json, "language_code": language_code, "language_name": language_name})
            print(f"--- LLM RESULT DEBUG ---\n{result}\n-----------------------")
            
            # Sanitize LLM common error (escaped single quotes are invalid JSON)
            if isinstance(result, str):
                result = result.replace("\\'", "'")
            
            logger.info(f"LLM action items extraction completed for user {user_id}")
            
            # Record response if enabled
            if recorder and epoch_ts:
                recorder.record_response(result, epoch_ts=epoch_ts)
            
            # Parse the raw result string into a list of items
            if "[Error" in result:
                logger.error(f"LLM Error for {user_id}: {result}")
                return []

            action_items = self._parse_llm_json(result)
            return action_items
            
        except Exception as e:
            logger.error(f"Failed to extract action items for user {user_id}: {e}")
            error_msg = f"[Error extracting action items: {e}]"
            
            # Record error as response if enabled
            if recorder and epoch_ts:
                recorder.record_response(error_msg, epoch_ts=epoch_ts)
            
            return []
