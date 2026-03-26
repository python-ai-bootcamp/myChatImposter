"""
Migration: add_image_transcription_tier.py
Adds the image_transcription tier to all existing bot configurations 
and updates the token_menu with image_transcription pricing.

MUST be run BEFORE the Python code is deployed, to prevent Pydantic 
ValidationError on bot load (LLMConfigurations now requires image_transcription).
"""
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from infrastructure import db_schema
from config_models import DefaultConfigurations


async def migrate():
    print("Starting migration: Add Image Transcription Tier...")
    
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.get_database("chat_manager")
    
    bot_config_collection = db[db_schema.COLLECTION_BOT_CONFIGURATIONS]
    global_config_collection = db[db_schema.COLLECTION_GLOBAL_CONFIGURATIONS]
    
    # ──────────────────────────────────────────────────────────
    # 1. Add image_transcription tier to ALL existing bot configs
    # ──────────────────────────────────────────────────────────
    print("Adding image_transcription tier to bot configurations...")
    
    default_image_transcription = {
        "provider_name": DefaultConfigurations.model_provider_name_image_transcription,
        "provider_config": {
            "model": DefaultConfigurations.model_image_transcription,
            "api_key_source": DefaultConfigurations.model_api_key_source,
            "temperature": DefaultConfigurations.model_image_transcription_temperature,
            "reasoning_effort": DefaultConfigurations.model_image_transcription_reasoning_effort,
            "detail": "auto",
        }
    }
    
    # Only update configs that DON'T already have image_transcription
    result = await bot_config_collection.update_many(
        {"config_data.configurations.llm_configs.image_transcription": {"$exists": False}},
        {"$set": {"config_data.configurations.llm_configs.image_transcription": default_image_transcription}}
    )
    print(f"Updated {result.modified_count} bot configurations with image_transcription tier.")
    
    # ──────────────────────────────────────────────────────────
    # 2. Add image_transcription pricing to token_menu
    # ──────────────────────────────────────────────────────────
    print("Updating token_menu with image_transcription pricing...")
    
    image_transcription_pricing = {
        "input_tokens": 0.25,
        "cached_input_tokens": 0.025,
        "output_tokens": 2
    }
    
    existing_menu = await global_config_collection.find_one({"_id": "token_menu"})
    if existing_menu:
        if "image_transcription" not in existing_menu:
            await global_config_collection.update_one(
                {"_id": "token_menu"},
                {"$set": {"image_transcription": image_transcription_pricing}}
            )
            print("Added image_transcription pricing to token_menu.")
        else:
            print("image_transcription pricing already exists in token_menu. Skipping.")
    else:
        print("WARNING: token_menu not found! Create it first using initialize_quota_and_bots.py")
    
    # ──────────────────────────────────────────────────────────
    # 3. Delete _mediaProcessorDefinitions to force GIF re-seed
    # ──────────────────────────────────────────────────────────
    print("Deleting _mediaProcessorDefinitions for GIF pool re-seed...")
    result = await global_config_collection.delete_one({"_id": "_mediaProcessorDefinitions"})
    if result.deleted_count > 0:
        print("Deleted _mediaProcessorDefinitions — pools will re-seed from Python defaults on next startup.")
    else:
        print("_mediaProcessorDefinitions not found (already deleted or never existed). OK.")
    
    client.close()
    print("Migration complete.")


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass
    asyncio.run(migrate())
