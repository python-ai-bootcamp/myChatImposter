from langchain_community.llms.fake import FakeListLLM
from langchain_core.callbacks import BaseCallbackHandler
# from langchain_openai import ChatOpenAI # Avoid dependency if possible, or use if available
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

import os

class MyHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs):
        print("CALLBACK: on_llm_start triggered")
    def on_llm_end(self, response, **kwargs):
        print("CALLBACK: on_llm_end triggered")

print("--- Test 1: FakeListLLM ---")
llm = FakeListLLM(responses=["foo"])
# The mechanism in question: post-init assignment
llm.callbacks = [MyHandler()]
print(f"Callbacks assigned. Invoking...")
llm.invoke("hi")

print("\n--- Test 2: ChatOpenAI Attribute Check ---")
if ChatOpenAI:
    os.environ["OPENAI_API_KEY"] = "sk-proj-fake-key-for-test"
    try:
        llm2 = ChatOpenAI()
        llm2.callbacks = [MyHandler()]
        print(f"ChatOpenAI callbacks attribute set. Count: {len(llm2.callbacks)}")
        print("Mechanism confirmed valid for ChatOpenAI.")
    except Exception as e:
        print(f"Error initializing ChatOpenAI: {e}")
else:
    print("ChatOpenAI not available, skipping.")
