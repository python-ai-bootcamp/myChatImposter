import asyncio
import os
import sys

# Ensure paths work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import UpdateOne
from motor.motor_asyncio import AsyncIOMotorClient
from infrastructure import db_schema

async def migrate_model_provider_separation():
    db_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    if not os.environ.get("MONGODB_URL"):
        print("MONGODB_URL not set in environment. Using default localhost.")

    client = AsyncIOMotorClient(db_url)
    db = client.get_database("chat_manager")
    
    config_col = db.get_collection(db_schema.COLLECTION_BOT_CONFIGURATIONS)
    creds_col = db.get_collection(db_schema.COLLECTION_CREDENTIALS)

    print("Starting Model Provider Separation Migration...")

    # --- 1. Assign Ownerless Bots ---
    print("\nPhase 1: Assigning Ownerless Bots")
    all_bots_cursor = config_col.find({}, {"config_data.bot_id": 1})
    all_bot_ids = [doc["config_data"]["bot_id"] async for doc in all_bots_cursor if "bot_id" in doc.get("config_data", {})]
    
    ownerless_bots = []
    for bot_id in all_bot_ids:
        owner = await creds_col.find_one({"owned_bots": bot_id}, {"_id": 1})
        if not owner:
            ownerless_bots.append(bot_id)
            
    if ownerless_bots:
        print(f"Found {len(ownerless_bots)} ownerless bots. Assigning to 'system_admin'...")
        # Check if 'system_admin' exists, if not create it
        admin_doc = await creds_col.find_one({"user_id": "system_admin"})
        if not admin_doc:
            await creds_col.insert_one({"user_id": "system_admin", "owned_bots": [], "password_hash": "MIGRATION_PLACEHOLDER"})
            print("Created placeholder 'system_admin' user.")
            
        await creds_col.update_one(
            {"user_id": "system_admin"},
            {"$addToSet": {"owned_bots": {"$each": ownerless_bots}}}
        )
        print(f"Assigned bots {ownerless_bots} to 'system_admin'.")
    else:
        print("No ownerless bots found.")

    # --- 2, 3, 4. Update Bot Configurations ---
    print("\nPhase 2: Updating Provider Configurations & Stripping Stray Fields")
    bulk_updates = []
    
    # We define what fields belong to each provider settings type
    # BaseModelProviderSettings -> api_key_source, api_key, model
    base_fields = {"api_key_source", "api_key", "model"}
    # ChatCompletionProviderSettings -> BaseModel + temperature, reasoning_effort, seed, record_llm_interactions
    chat_fields = base_fields.union({"temperature", "reasoning_effort", "seed", "record_llm_interactions"})
    
    async for doc in config_col.find({}):
        llm_configs = doc.get("config_data", {}).get("configurations", {}).get("llm_configs", {})
        if not llm_configs:
            continue
            
        doc_id = doc["_id"]
        update_set = {}
        update_unset = {}
        
        # Process 'image_moderation' (BaseModelProviderSettings)
        if "image_moderation" in llm_configs:
            mod_data = llm_configs["image_moderation"]
            # 3. Update provider_name
            if mod_data.get("provider_name") == "openAi":
                update_set["config_data.configurations.llm_configs.image_moderation.provider_name"] = "openAiModeration"
                
            # 2. Strip chat-specific/stray fields
            prov_config = mod_data.get("provider_config", {})
            for key in prov_config.keys():
                if key not in base_fields:
                    update_unset[f"config_data.configurations.llm_configs.image_moderation.provider_config.{key}"] = ""
                    
        # Process 'high' and 'low' (ChatCompletionProviderSettings)
        for tier in ["high", "low"]:
            if tier in llm_configs:
                tier_data = llm_configs[tier]
                prov_config = tier_data.get("provider_config", {})
                
                # 4. Strip stray fields
                for key in prov_config.keys():
                    if key not in chat_fields:
                        update_unset[f"config_data.configurations.llm_configs.{tier}.provider_config.{key}"] = ""
                        
        if update_set or update_unset:
            current_update = {}
            if update_set:
                current_update["$set"] = update_set
            if update_unset:
                current_update["$unset"] = update_unset
            bulk_updates.append(UpdateOne({"_id": doc_id}, current_update))

    if bulk_updates:
        print(f"Applying {len(bulk_updates)} configuration updates...")
        result = await config_col.bulk_write(bulk_updates)
        print(f"Modified {result.modified_count} documents.")
    else:
        print("No configuration updates required.")

    print("\nMigration Complete.")
    client.close()

if __name__ == "__main__":
    asyncio.run(migrate_model_provider_separation())
