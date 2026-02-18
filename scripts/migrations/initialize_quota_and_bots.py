import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from infrastructure import db_schema

async def migrate():
    print("Starting migration: Initialize Quota and Bots...")
    
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.get_database("chat_manager")
    
    credentials_collection = db[db_schema.COLLECTION_CREDENTIALS]
    bot_config_collection = db[db_schema.COLLECTION_BOT_CONFIGURATIONS]
    global_config_collection = db[db_schema.COLLECTION_GLOBAL_CONFIGURATIONS]
    
    # 1. Update Users with Default Quota
    print("Updating users with default llm_quota...")
    default_quota = {
        "reset_days": 7,
        "dollars_per_period": 1.0,
        "dollars_used": 0.0,
        "last_reset": 0,
        "enabled": True
    }
    # Update all users who don't have llm_quota
    result = await credentials_collection.update_many(
        {"llm_quota": {"$exists": False}},
        {"$set": {"llm_quota": default_quota}}
    )
    print(f"Updated {result.modified_count} users with default quota.")

    # 2. Update Bot Configurations (Deactivate all)
    print("Deactivating all bot configurations...")
    # The spec says: "all existing bot confugurations will be added with ... activated: false"
    # Logic: Set config_data.configurations.user_details.activated = False
    result = await bot_config_collection.update_many(
        {},
        {"$set": {"config_data.configurations.user_details.activated": False}}
    )
    print(f"Deactivated {result.modified_count} bot configurations.")

    # 3. Initialize Token Menu
    print("Initializing token_menu...")
    token_menu = {
        "high": {
            "input_tokens": 1.25,
            "cached_input_tokens": 0.125,
            "output_tokens": 10
        },
        "low": {
            "input_tokens": 0.25,
            "cached_input_tokens": 0.025,
            "output_tokens": 2
        }
    }
    
    # Check if token_menu exists
    existing_menu = await global_config_collection.find_one({"_id": "token_menu"})
    if not existing_menu:
        await global_config_collection.insert_one({"_id": "token_menu", **token_menu})
        print("Created token_menu.")
    else:
        print("token_menu already exists. Skipping.")
        
    client.close()
    print("Migration complete.")

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass
    asyncio.run(migrate())
