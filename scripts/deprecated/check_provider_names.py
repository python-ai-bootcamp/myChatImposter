"""Check raw LLM provider config in database"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")

async def check():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client["chatbot_db"]
    
    count = 0
    async for doc in db["user_configurations"].find({}):
        count += 1
        user_id = doc.get("config_data", {}).get("user_id", "unknown")
        llm_config = doc.get("config_data", {}).get("configurations", {}).get("llm_provider_config", {})
        print(f"\n{user_id}:")
        print(f"  llm_provider_config: {json.dumps(llm_config, indent=4)}")
    
    print(f"\nTotal configs: {count}")
    client.close()

if __name__ == "__main__":
    asyncio.run(check())
