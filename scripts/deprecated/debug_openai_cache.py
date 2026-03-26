
import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

# Mock a long system prompt
long_prompt = "You are a helpful assistant. " * 500  # ~2500 tokens
print(f"Prompt length: {len(long_prompt)} chars")

async def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set. Skipping execution.")
        return

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key
    )

    print("--- First Call (might not be cached) ---")
    msg1 = [
        SystemMessage(content=long_prompt),
        HumanMessage(content="Hello, how are you?")
    ]
    res1 = await llm.ainvoke(msg1)
    print("Response 1 Metadata:", res1.response_metadata)
    print("Response 1 Usage Metadata:", res1.usage_metadata)

    print("\n--- Second Call (should be cached) ---")
    msg2 = [
        SystemMessage(content=long_prompt),
        HumanMessage(content="Hello again!")
    ]
    res2 = await llm.ainvoke(msg2)
    print("Response 2 Metadata:", res2.response_metadata)
    print("Response 2 Usage Metadata:", res2.usage_metadata)

if __name__ == "__main__":
    asyncio.run(main())
