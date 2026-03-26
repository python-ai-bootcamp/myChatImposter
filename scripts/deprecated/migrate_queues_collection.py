import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

async def migrate_queues():
    """Migrates user_id to bot_id in queues_collection."""
    mongo_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client.get_default_database("chat_manager")
    queues_collection = db["queues"]
    
    print("Starting migration for queues collection...")
    
    # Check how many documents actually matched
    count_to_update = await queues_collection.count_documents({"user_id": {"$exists": True}})
    print(f"Found {count_to_update} documents to migrate in queues collection.")
    
    if count_to_update > 0:
        result = await queues_collection.update_many(
            {"user_id": {"$exists": True}},
            {"$rename": {"user_id": "bot_id"}}
        )
        print(f"Update completed. Modified {result.modified_count} documents.")
    else:
        print("No documents required migration.")

    print("Migration finished.")

if __name__ == "__main__":
    asyncio.run(migrate_queues())
