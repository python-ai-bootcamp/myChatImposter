import asyncio
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
DB_NAME = "chat_manager"
COLLECTION_NAME = "bot_configurations"

async def migrate_image_moderation():
    logging.info(f"Connecting to MongoDB at {MONGODB_URL}")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    default_moderation_config = {
        "provider_name": "openAi",
        "provider_config": {
            "api_key_source": "environment",
            "model": "omni-moderation-latest",
            "record_llm_interactions": False,
            "temperature": 0.7,  # Defaulting to standard for schema consistency
            "reasoning_effort": "minimal",
            "seed": None
        }
    }

    cursor = collection.find({})
    count = 0
    updated = 0

    async for doc in cursor:
        count += 1
        bot_id = doc.get("config_data", {}).get("bot_id", "unknown")
        llm_configs = doc.get("config_data", {}).get("configurations", {}).get("llm_configs", {})

        if "image_moderation" not in llm_configs:
            logging.info(f"Adding image_moderation to bot {bot_id}")
            result = await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"config_data.configurations.llm_configs.image_moderation": default_moderation_config}}
            )
            if result.modified_count > 0:
                updated += 1
        else:
            logging.info(f"Bot {bot_id} already has image_moderation. Skipping.")

    logging.info(f"Migration complete. Total bots: {count}, Updated: {updated}")
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_image_moderation())
