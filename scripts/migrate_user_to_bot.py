
import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration")

MONGODB_URL = os.environ.get("MONGODB_URL", "mongodb://mongodb:27017/")
DB_NAME = "chat_manager" # Corrected from 'chat_imposter'

async def migrate():
    logger.info("Starting migration from 'User' to 'Bot' terminology...")
    
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    
    # 1. Migrate configurations -> bot_configurations
    config_collection = db["configurations"]
    bot_config_collection = db["bot_configurations"]
    
    # Iterate over old configurations and migrate them
    async for doc in config_collection.find({}):
        # Prepare new document structure
        new_doc = doc.copy()
        needs_save = False
        
        # Check config_data.user_id -> bot_id
        config_data = new_doc.get("config_data", {})
        if "user_id" in config_data:
            logger.info(f"Migrating config for {config_data['user_id']}...")
            config_data["bot_id"] = config_data.pop("user_id")
            new_doc["config_data"] = config_data
            needs_save = True
        
        # Check root level user_id (legacy)
        if "user_id" in new_doc:
            new_doc["bot_id"] = new_doc.pop("user_id")
            needs_save = True

        # If data was migrated or if we are moving it to the new collection
        # We try to insert/update in bot_configurations
        
        # Ensure we have a bot_id to key off
        bot_id = new_doc.get("config_data", {}).get("bot_id") or new_doc.get("bot_id")
        
        if bot_id:
             # Check if already exists to avoid overwriting newer data if any
             existing = await bot_config_collection.find_one({"_id": new_doc["_id"]})
             if not existing:
                 await bot_config_collection.insert_one(new_doc)
                 logger.info(f"Moved config {new_doc['_id']} to bot_configurations")
             else:
                 # Optional: Update if needed, but safe to skip if ID collision implies same data
                 logger.info(f"Config {new_doc['_id']} already in bot_configurations. Skipping.")
        else:
            logger.warning(f"Skipping document {new_doc['_id']} - could not determine bot_id")

    # 3. Update credentials collection
    # Note: Correct collection name found in DB inspection is 'user_auth_credentials'
    credentials = db["user_auth_credentials"]
    async for doc in credentials.find({}):
        if "owned_user_configurations" in doc:
            logger.info(f"Migrating credentials for user {doc.get('user_id')}...")
            owned_bots = doc.pop("owned_user_configurations")
            await credentials.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {"owned_bots": owned_bots},
                    "$unset": {"owned_user_configurations": ""}
                }
            )
            logger.info(f"Updated credentials for {doc.get('user_id')}")

    logger.info("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
