"""Fix LLM provider_name from 'openai' to 'openAi' in chat_manager.configurations"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Use the internal docker service name if running inside container, or localhost if outside
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")

async def fix():
    print(f"Connecting to {MONGODB_URL}...")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client['chat_manager']
    collection = db['configurations']
    
    # Check count before
    query = {'config_data.configurations.llm_provider_config.provider_name': 'openai'}
    count_before = await collection.count_documents(query)
    print(f"Found {count_before} documents requiring fix.")
    
    if count_before > 0:
        result = await collection.update_many(
            query,
            {'$set': {'config_data.configurations.llm_provider_config.provider_name': 'openAi'}}
        )
        print(f'Fixed {result.modified_count} users')
    else:
        print("No users needed fixing.")
        
    client.close()

if __name__ == "__main__":
    asyncio.run(fix())
