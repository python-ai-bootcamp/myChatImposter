
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from motor.motor_asyncio import AsyncIOMotorClient
from infrastructure import db_schema

async def backfill_owned_configurations():
    print("Starting backfill of owned_user_configurations...")
    
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.get_database("chat_manager")
    credentials_collection = db.get_collection(db_schema.COLLECTION_CREDENTIALS)

    cursor = credentials_collection.find({})
    count = 0
    updated_count = 0
    
    async for doc in cursor:
        count += 1
        user_id = doc.get("user_id")
        
        # Check if already has the field
        if "owned_user_configurations" in doc:
           print(f"Skipping {user_id} - already has field")
           continue

        # Migration Logic: Initial 1:1 mapping
        # Each user owns the configuration matching their own user_id
        owned_list = [user_id]
        
        await credentials_collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"owned_user_configurations": owned_list}}
        )
        updated_count += 1
        print(f"Updated {user_id} with owned_configurations: {owned_list}")

    print(f"Backfill complete. Processed {count} users, Updated {updated_count}.")
    client.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(backfill_owned_configurations())
