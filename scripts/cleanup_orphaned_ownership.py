"""
One-time cleanup script to fix orphaned entries in owned_user_configurations.
Removes any user_id from ownership lists that don't have a corresponding configuration.
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def cleanup_orphaned_ownership():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.get_database("chat_manager")
    
    creds_collection = db["user_auth_credentials"]
    configs_collection = db["configurations"]
    
    # Get all credentials with ownership lists
    async for cred in creds_collection.find({"owned_user_configurations": {"$exists": True, "$ne": []}}):
        user_id = cred["user_id"]
        owned = cred.get("owned_user_configurations", [])
        
        if not owned:
            continue
        
        # Find which owned configs actually exist
        existing_configs = await configs_collection.find(
            {"config_data.user_id": {"$in": owned}}
        ).to_list(length=100)
        
        existing_ids = {doc["config_data"]["user_id"] for doc in existing_configs}
        orphaned = [oid for oid in owned if oid not in existing_ids]
        
        if orphaned:
            print(f"User '{user_id}': Removing orphaned entries: {orphaned}")
            await creds_collection.update_one(
                {"user_id": user_id},
                {"$pull": {"owned_user_configurations": {"$in": orphaned}}}
            )
        else:
            print(f"User '{user_id}': All {len(owned)} ownership entries are valid.")
    
    print("\nCleanup complete.")
    client.close()

if __name__ == "__main__":
    if os.name == "nt":
        try: asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except: pass
    asyncio.run(cleanup_orphaned_ownership())
