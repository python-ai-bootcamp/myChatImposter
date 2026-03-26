
import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Connection String (Localhost)
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "chat_manager"
COLLECTION_NAME = "baileys_sessions"

async def list_keys():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    print(f"Listing ALL keys in {COLLECTION_NAME} (limit 50)...")
    
    cursor = collection.find({}).limit(50)
    
    async for doc in cursor:
        print(f"Key: {doc['_id']}")

if __name__ == "__main__":
    asyncio.run(list_keys())
