import asyncio
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Configuration from logs
MODEL = "gpt-5"
TEMPERATURE = 0.7
REASONING_EFFORT = "minimal"
API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Exact Prompt Template from logs (double braces for Python formatting)
SYSTEM_PROMPT = """You are a helpful assistant. For each chat group message thread you receive, extract all actionable items mentioned in the conversation and produce a structured summary.

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

# Exact Input from failure log
INPUT_JSON = """[
  {
    "when": "2026-01-21 22:10",
    "sender": "יהב",
    "content": "טוב יש מחר פגישת מועצת תלמידים. נא להתכונן למצגת."
  }
]"""

LANGUAGE_CODE = "he"

async def run_test():
    print("Initializing LLM...")
    try:
        # Note: reasoning_effort is only for o1 models. If gpt-5 supports it, good. 
        # If not, it might be ignored or cause error. The logs showed it being passed.
        llm = ChatOpenAI(
            model=MODEL,
            temperature=TEMPERATURE,
            reasoning_effort=REASONING_EFFORT, 
            api_key=API_KEY
        )
    except Exception as e:
        print(f"Error init LLM: {e}")
        return

    print("Building Prompt...")
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}")
    ])

    chain = prompt | llm | StrOutputParser()

    print("------------------------------------------")
    print(f"Running Chain with Input:\n{INPUT_JSON}")
    print("------------------------------------------")

    try:
        result = await chain.ainvoke({"input": INPUT_JSON, "language_code": LANGUAGE_CODE})
        print(f"RESULT:\n{result}")
    except Exception as e:
        print(f"EXECUTION ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())
