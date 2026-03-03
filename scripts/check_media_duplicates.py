import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_duplicates():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["chat_manager"]
    
    for collection_name in ["media_processing_jobs", "media_processing_jobs_holding", "media_processing_jobs_failed"]:
        collection = db[collection_name]
        pipeline = [
            {"$group": {"_id": "$guid", "count": {"$sum": 1}}},
            {"$match": {"count": {"$gt": 1}}}
        ]
        duplicates = await collection.aggregate(pipeline).to_list(length=100)
        print(f"Collection: {collection_name}")
        if duplicates:
            for d in duplicates:
                print(f"  Duplicate GUID: {d['_id']}, Count: {d['count']}")
        else:
            print("  No duplicates found.")

if __name__ == "__main__":
    asyncio.run(check_duplicates())
