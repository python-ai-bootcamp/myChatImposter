import asyncio
import os
import sys
import logging
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure import db_schema
from infrastructure import db_schema

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def migrate_group_tracking_bot_id():
    """
    Migrates the group tracking collections from using 'user_id' to 'bot_id'.
    """
    logger.info("Starting database migration: Group Tracking user_id -> bot_id")
    
    # 1. Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.get_database("chat_manager")
    logger.info(f"Connected to database: {db.name}")
    
    collections_to_migrate = [
        db_schema.COLLECTION_TRACKED_GROUPS,
        db_schema.COLLECTION_TRACKED_GROUP_PERIODS,
        db_schema.COLLECTION_GROUP_TRACKING_STATE
    ]
    
    total_modified = 0
    
    # 2. Rename fields
    for collection_name in collections_to_migrate:
        collection = db[collection_name]
        logger.info(f"Processing collection: {collection_name}")
        
        # 3. Drop old indexes that contain 'user_id' so db_schema can recreate new ones smoothly and to prevent E11000 dup key errors on $rename
        try:
            indexes = await collection.index_information()
            for index_name, index_info in indexes.items():
                keys = [k[0] for k in index_info.get('key', [])]
                if 'user_id' in keys:
                    logger.info(f"Dropping old index '{index_name}' in {collection_name} because it contains 'user_id'.")
                    await collection.drop_index(index_name)
        except Exception as e:
            logger.warning(f"Error checking/dropping indexes in {collection_name}: {e}")
            
        # Check if there are any documents with 'user_id'
        count = await collection.count_documents({"user_id": {"$exists": True}})
        if count == 0:
            logger.info(f"No documents with 'user_id' found in {collection_name}. Skipping rename.")
        else:
            logger.info(f"Found {count} documents with 'user_id'. Renaming to 'bot_id'...")
            # Use $rename operator to efficiently rename the field
            result = await collection.update_many(
                {"user_id": {"$exists": True}},
                {"$rename": {"user_id": "bot_id"}}
            )
            logger.info(f"Successfully renamed 'user_id' to 'bot_id' in {result.modified_count} documents in {collection_name}.")
            total_modified += result.modified_count

    logger.info(f"Migration completed cleanly. Total documents modified across all collections: {total_modified}")
    
    # Close connection
    client.close()

if __name__ == "__main__":
    # Ensure asyncio event loop handles the async function
    try:
        if sys.platform == 'win32':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(migrate_group_tracking_bot_id())
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
