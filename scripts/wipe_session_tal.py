
import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Connection String (Localhost)
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "chat_manager"
COLLECTION_NAME = "baileys_sessions"

async def wipe_tal():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    print(f"Wiping ALL session data for 'tal'...")
    
    # regex for anything starting with "tal-"
    regex = {"$regex": "^tal-"}
    
    # Count first
    count = await collection.count_documents({"_id": regex})
    print(f"Found {count} documents for 'tal'.")
    
    if count > 0:
        result = await collection.delete_many({"_id": regex})
        print(f"Deleted {result.deleted_count} documents.")
        print("Session 'tal' is now CLEAN. Please restart logic/scan QR.")
    else:
        print("No documents found for 'tal'. Already clean?")

if __name__ == "__main__":
    asyncio.run(wipe_tal())
