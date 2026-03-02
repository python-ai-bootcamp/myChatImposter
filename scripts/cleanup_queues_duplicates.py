import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

async def find_and_fix_duplicates():
    mongo_url = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017/")
    client = AsyncIOMotorClient(mongo_url)
    db = client["chat_manager"]
    queues_collection = db["queues"]

    print("Checking for duplicate messages in 'queues' collection...")

    pipeline = [
        {
            "$group": {
                "_id": {
                    "bot_id": "$bot_id",
                    "provider_name": "$provider_name",
                    "correspondent_id": "$correspondent_id",
                    "id": "$id"
                },
                "count": {"$sum": 1},
                "ids": {"$push": "$_id"}
            }
        },
        {"$match": {"count": {"$gt": 1}}}
    ]

    duplicates = await queues_collection.aggregate(pipeline).to_list(None)

    if not duplicates:
        print("No duplicates found.")
        return

    print(f"Found {len(duplicates)} sets of duplicates.")

    for dupe in duplicates:
        # Keep the first ID, delete the rest
        to_keep = dupe["ids"][0]
        to_delete = dupe["ids"][1:]
        
        print(f"Dupe group: {dupe['_id']} - Keeping {to_keep}, Deleting {len(to_delete)} documents.")
        
        result = await queues_collection.delete_many({"_id": {"$in": to_delete}})
        print(f"Deleted {result.deleted_count} documents.")

    print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(find_and_fix_duplicates())
