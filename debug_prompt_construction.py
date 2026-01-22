import asyncio
import json
import logging
import sys
import io
from langchain_core.prompts import ChatPromptTemplate

# Force UTF-8 for stdout/stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Constants
LANGUAGE_CODE = "he"
USER_INPUT_JSON = json.dumps([
  {
    "when": "2026-01-21 20:35",
    "sender": "יהב",
    "content": "טוב יש מחר פגישת מועצת תלמידים. נא להתכונן למצגת."
  }
], indent=2, ensure_ascii=False)

# The template from group_tracker.py
SYSTEM_PROMPT_TEMPLATE = """You are a helpful assistant.
Language: {language_code}
Output structure:
[{{
"key": "value"
}}]
"""

async def simulate_logging():
    print("--- Simulating Production Logging ---")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_TEMPLATE),
        ("human", "{input}")
    ])
    
    # This is the exact code block inserted into group_tracker.py
    formatted_messages = await prompt.aformat_messages(input=USER_INPUT_JSON, language_code=LANGUAGE_CODE)
    logger.info("--- LLM PROMPT DEBUG ---")
    logger.info(f"System Message Content: {formatted_messages[0].content}")
    logger.info(f"Human Message Content: {formatted_messages[1].content}")
    logger.info("------------------------")

if __name__ == "__main__":
    asyncio.run(simulate_logging())
