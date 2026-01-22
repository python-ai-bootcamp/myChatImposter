import asyncio
import json
import os
import logging
import sys
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# Setup logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Constants from the investigation
LANGUAGE_CODE = "he"
MODEL = "gpt-5"
TEMPERATURE = 0.7
REASONING_EFFORT = "minimal"

# The exact user input that failed
USER_INPUT_JSON = json.dumps([
  {
    "when": "2026-01-21 20:35",
    "sender": "יהב",
    "content": "טוב יש מחר פגישת מועצת תלמידים. נא להתכונן למצגת."
  }
], indent=2, ensure_ascii=False)

# The template from group_tracker.py (with {{ }})
SYSTEM_PROMPT_TEMPLATE = """You are a helpful assistant. For each chat group message thread you receive, extract all actionable items mentioned in the conversation and produce a structured summary.

General rules:

* task_title and task_description must be written in the defined language identified by language code = '{language_code}'.
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
* task_description: 
    - must aggregate information from all related messages 
    - should includes relevant details: 
        -- needed preparations for task or event (keep it dry, do not improvise and add unneeded information)
        -- all people mentioned as relevant to the task's essence  
        -- a deadline or event date at the end of the task_description message (if one is available). 
    - deadline or event date format:    
       -- weekday name (in defined language, full weekday name, no shortname), date(formatted dd/mm/yyyy only), and time (24h formatted). If no hour was specified, neglect it.
       -- if the deadline was relative, include a resolved absolute deadline in following format: (weekday name (in defined language, full weekday name, no shortname), date(formatted dd/mm/yyyy only), and time (24h formatted). If no hour was specified, neglect it.
       -- double check weekday corresponds to the absolute date found in timestamp_deadline correctly
    - if relevant people are mentioned do not alter their name spelling in any way. copy it AS IS to the letter. no removal of any Matres lectionis (vowel indicators)!!!
    - double check that the quoted names appear identical (string compare) to the actual names appearing in message content or sender field inside relevant_task_messages correspondence    
    
RELEVANT_TASK_MESSAGE format:
{{
"originating_time": <time the message was sent>,
"sender": <sender name>,
"content": <message content>
}}
"""

# The recorded string (simulated) - has {{ }} and replaced language_code
RECORDED_PROMPT_STRING = SYSTEM_PROMPT_TEMPLATE.replace("{language_code}", LANGUAGE_CODE)

async def run_reproduction():
    logger.info("Initializing reproduction script...")
    
    # Check API Key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment variables.")
        # Try to read from config if possible
        try:
            with open("llm_providers/openAi.key", "r") as f: # Hypothetical
                pass
        except:
             pass
        # Proceeding might fail but let's try
        
    # Initialize LLM
    try:
        llm = ChatOpenAI(
            model=MODEL,
            temperature=TEMPERATURE,
            reasoning_effort=REASONING_EFFORT,
            api_key=api_key
        )
    except TypeError:
         logger.warning("reasoning_effort might not be supported. Trying without.")
         llm = ChatOpenAI(
            model=MODEL,
            temperature=TEMPERATURE,
            api_key=api_key
        )

    # --- Test 1: ChatPromptTemplate (group_tracker.py behavior) ---
    logger.info("\n--- Test 1: ChatPromptTemplate (Production Code) ---")
    prompt_prod = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_TEMPLATE),
        ("human", "{input}")
    ])
    
    # Inspect the formatted messages
    formatted_prod = await prompt_prod.aformat_messages(input=USER_INPUT_JSON, language_code=LANGUAGE_CODE)
    logger.info(f"Prod System Message Content (snippet): ...{formatted_prod[0].content[300:500]}...")
    
    # Check if {{ became {
    if "[{" in formatted_prod[0].content and "[{{" not in formatted_prod[0].content:
        logger.info("Prod prompt converted '{{' to '{'. This is expected for ChatPromptTemplate.")
    else:
        logger.info("Prod prompt preserved '{{' or behaved unexpectedly.")

    chain_prod = prompt_prod | llm | StrOutputParser()
    
    try:
        result_prod = await chain_prod.ainvoke({"input": USER_INPUT_JSON, "language_code": LANGUAGE_CODE})
        logger.info(f"Prod Result: {result_prod}")
    except Exception as e:
        logger.error(f"Prod Error: {e}")


    # --- Test 2: SystemMessage + Recorded String (Eval behavior) ---
    logger.info("\n--- Test 2: SystemMessage with Recorded String (Eval Code) ---")
    
    # Eval runner uses SystemMessage(content=recorded_string)
    # The recorded string naturally has {{ because it was just a string replace on the template
    
    messages_eval = [
        SystemMessage(content=RECORDED_PROMPT_STRING),
        HumanMessage(content=USER_INPUT_JSON)
    ]
    
    logger.info(f"Eval System Message Content (snippet): ...{messages_eval[0].content[300:500]}...")
    
    # Check if {{ is present
    if "[{{" in messages_eval[0].content:
        logger.info("Eval prompt has '[{{'. This is expected for direct string usage.")
    else:
        logger.info("Eval prompt does NOT have '[{{'. Unexpected.")
        
    try:
        result_eval = await llm.ainvoke(messages_eval)
        logger.info(f"Eval Result: {result_eval.content}")
    except Exception as e:
        logger.error(f"Eval Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_reproduction())
