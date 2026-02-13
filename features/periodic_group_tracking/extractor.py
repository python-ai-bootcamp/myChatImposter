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

    async def extract(self, messages: list, llm_config: LLMProviderConfig, user_id: str, timezone: ZoneInfo, group_id: str = "", language_code: str = "en", llm_config_high: LLMProviderConfig = None, token_consumption_collection = None) -> list:
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
            # Dynamically load the LLM provider via Factory
            from services.llm_factory import create_tracked_llm
            
            llm = create_tracked_llm(
                llm_config=llm_config,
                user_id=f"action_items_{user_id}", # Context user_id for provider
                bot_id=list(messages[0].keys())[0] if messages else user_id, # Best effort bot_id or user_id
                feature_name="periodic_group_tracking",
                config_tier="low",
                token_consumption_collection=token_consumption_collection
            )
            
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
            # PHASE 1: Low Model Extraction
            # Invoke the chain with all template variables
            logger.info(f"Invoking LLM (Low) for action items extraction for user {user_id}")
            result_low = await chain.ainvoke({"input": messages_json, "language_code": language_code, "language_name": language_name})
            print(f"--- LLM RESULT (LOW) DEBUG ---\n{result_low}\n-----------------------")
            
            # Sanitize LLM common error (escaped single quotes are invalid JSON)
            if isinstance(result_low, str):
                result_low = result_low.replace("\\'", "'")
            
            # PHASE 2: High Model Refinement
            if llm_config_high:
                logger.info(f"Invoking LLM (High) for refinement for user {user_id}")
                try:
                    # 1. Load System Prompt
                    refine_prompt_path = Path("prompts/action_item_refinement_system.txt")
                    if refine_prompt_path.exists():
                        refine_system_prompt = refine_prompt_path.read_text(encoding="utf-8")
                    else:
                        logger.warning("Refinement prompt file not found, skipping Stage 2.")
                        refine_system_prompt = ""

                    # 2. Initialize High Model
                    # 2. Initialize High Model via Factory
                    high_llm = create_tracked_llm(
                        llm_config=llm_config_high,
                        user_id=user_id,
                        bot_id=list(messages[0].keys())[0] if messages else user_id,
                        feature_name="periodic_group_tracking",
                        config_tier="high",
                        token_consumption_collection=token_consumption_collection
                    )

                    # 3. Create Chain
                    # We pass the result_low as the USER message. System prompt is the file content.
                    refine_prompt = ChatPromptTemplate.from_messages([
                        ("system", "{system_content}"),
                        ("user", "{input_content}")
                    ])
                    refine_chain = refine_prompt | high_llm | StrOutputParser()
                    
                    # Format system prompt with language_code and language_name if present
                    try:
                        formatted_system_prompt = refine_system_prompt.format(
                            language_code=language_code,
                            language_name=language_name
                        )
                    except Exception as fmt_err:
                        logger.warning(f"Failed to format refinement system prompt: {fmt_err}. Using raw content.")
                        formatted_system_prompt = refine_system_prompt

                    # 4. Invoke
                    result_high = await refine_chain.ainvoke({
                        "system_content": formatted_system_prompt,
                        "input_content": result_low
                    })

                    print(f"--- LLM RESULT (HIGH) DEBUG ---\n{result_high}\n-----------------------")
                    
                    # Sanitize
                    if isinstance(result_high, str):
                        result_high = result_high.replace("\\'", "'")
                        
                    # Use High result as final
                    final_result = result_high

                except Exception as e:
                    logger.error(f"Stage 2 (High) Failed: {e}. Falling back to Low result.")
                    final_result = result_low
            else:
                 final_result = result_low

            logger.info(f"LLM action items extraction completed for user {user_id}")
            
            # Record response if enabled
            if recorder and epoch_ts:
                recorder.record_response(final_result, epoch_ts=epoch_ts)
            
            # Parse the raw result string into a list of items
            if "[Error" in final_result:
                logger.error(f"LLM Error for {user_id}: {final_result}")
                return []

            action_items = self._parse_llm_json(final_result)
            return action_items
            
        except Exception as e:
            logger.error(f"Failed to extract action items for user {user_id}: {e}")
            error_msg = f"[Error extracting action items: {e}]"
            
            # Record error as response if enabled
            if recorder and epoch_ts:
                recorder.record_response(error_msg, epoch_ts=epoch_ts)
            
            return []
