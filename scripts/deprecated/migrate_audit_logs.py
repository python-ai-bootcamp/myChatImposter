import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

async def migrate_audit_logs():
    """Migrates details.extracted_user_id to details.extracted_bot_id in audit_logs collection."""
    mongo_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongo_url)
    db = client.get_default_database("chat_manager")
    audit_collection = db["audit_logs"]
    
    print("Starting migration for audit logs collection...")
    
    count_to_update = await audit_collection.count_documents({"details.extracted_user_id": {"$exists": True}})
    print(f"Found {count_to_update} documents to migrate in audit_logs collection.")
    
    if count_to_update > 0:
        result = await audit_collection.update_many(
            {"details.extracted_user_id": {"$exists": True}},
            {"$rename": {"details.extracted_user_id": "details.extracted_bot_id"}}
        )
        print(f"Update completed. Modified {result.modified_count} documents.")
    else:
        print("No documents required migration.")

    print("Migration finished.")

if __name__ == "__main__":
    asyncio.run(migrate_audit_logs())
