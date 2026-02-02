import json
import importlib
import inspect
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
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

        # System prompt with language placeholder - loaded from external file
        try:
            prompt_path = Path("prompts/action_item_extractor_system.txt")
            if not prompt_path.exists():
                logger.error(f"Prompt file not found: {prompt_path.absolute()}")
                return []
            
            system_prompt_template = prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read prompt file: {e}")
            return []
        
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
