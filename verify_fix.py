import asyncio
import json
import logging
import sys
import io
from langchain_core.messages import SystemMessage, HumanMessage

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

# The template from group_tracker.py (with {{ }})
SYSTEM_PROMPT_TEMPLATE = """You are a helpful assistant.
Language: {language_code}
Output structure:
[{{
"key": "value"
}}]
"""

async def verify_fix():
    print("--- Verifying Fix (UTF-8) ---")
    
    # Simulate the NEW logic in group_tracker.py
    print("\n1. New Logic (Manual Replacement + SystemMessage)...")
    try:
        # Code from the fix:
        formatted_system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{language_code}", LANGUAGE_CODE)
        messages = [
            SystemMessage(content=formatted_system_prompt),
            HumanMessage(content=USER_INPUT_JSON)
        ]
        
        system_content = messages[0].content
        
        print(f"New System Content:\n{system_content}")
        
        if "{{" in system_content:
             print("\nSUCCESS: New logic preserves '{{' braces (matches Eval behavior).")
        else:
             print("\nFAILURE: New logic lost '{{' braces.")

    except Exception as e:
        print(f"Verification Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_fix())
