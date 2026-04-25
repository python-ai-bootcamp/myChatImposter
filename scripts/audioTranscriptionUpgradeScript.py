"""
Audio Transcription Upgrade Script
====================================

OPERATIONAL DEPLOYMENT REQUIREMENT:
This migration script MUST be executed against the database BEFORE deploying
and restarting the backend code, to prevent unbilled usage resulting from the
QuotaService loading a stale 3-tier menu at startup.

This script accomplishes:
1. Updates existing bot configs in MongoDB — adds config_data.configurations.llm_configs.audio_transcription
   where missing.
2. Replaces the existing token_menu (3 tiers) with a new 4-tier menu: high, low, image_transcription,
   audio_transcription. (image_moderation is intentionally excluded from token_menu because moderation
   providers currently bypass the token tracking pipeline.)

SONIOX_API_KEY:
Ensure the SONIOX_API_KEY environment variable is provisioned in the deployment environment.
The Soniox SDK does not fail gracefully if it is missing and api_key_source is set to "environment".
"""

import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default audio transcription config that matches DefaultConfigurations
DEFAULT_AUDIO_TRANSCRIPTION_CONFIG = {
    "provider_name": "sonioxAudioTranscription",
    "provider_config": {
        "api_key_source": "environment",
        "api_key": None,
        "model": "stt-async-v4",
        "temperature": 0.0
    }
}


async def run_migration(mongo_uri: str = "mongodb://localhost:27017", db_name: str = "myChatImposter"):
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]
    bot_configurations_collection = db["bot_configurations"]
    global_configurations_collection = db["configurations"]

    # --- Step 1: Upsert audio_transcription into all bot configs ---
    logger.info("Step 1: Upserting audio_transcription config into existing bots...")
    
    cursor = bot_configurations_collection.find(
        {"config_data.bot_id": {"$exists": True}},
        {"config_data.bot_id": 1, "config_data.configurations.llm_configs.audio_transcription": 1}
    )
    
    updated_count = 0
    async for doc in cursor:
        config_data = doc.get("config_data", {})
        llm_configs = config_data.get("configurations", {}).get("llm_configs", {})
        
        if "audio_transcription" not in llm_configs:
            result = await bot_configurations_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {
                    "config_data.configurations.llm_configs.audio_transcription": DEFAULT_AUDIO_TRANSCRIPTION_CONFIG
                }}
            )
            if result.modified_count > 0:
                updated_count += 1
                logger.info(f"  Updated bot: {config_data.get('bot_id', 'unknown')}")
    
    logger.info(f"Step 1 complete: {updated_count} bot(s) updated with audio_transcription config.")

    # --- Step 2: Replace token_menu with full 4-tier menu ---
    logger.info("Step 2: Replacing token_menu with 4-tier menu...")
    
    new_token_menu = {
        "_id": "token_menu",
        "high": {"input_tokens": 2.5, "output_tokens": 10.0, "cached_input_tokens": 1.25},
        "low": {"input_tokens": 0.15, "output_tokens": 0.6, "cached_input_tokens": 0.075},
        "image_transcription": {"input_tokens": 2.5, "output_tokens": 10.0, "cached_input_tokens": 1.25},
        "audio_transcription": {"input_tokens": 1.5, "output_tokens": 3.5, "cached_input_tokens": 0}
    }
    
    await global_configurations_collection.update_one(
        {"_id": "token_menu"},
        {"$set": new_token_menu},
        upsert=True
    )
    
    logger.info("Step 2 complete: token_menu updated with 4 tiers (high, low, image_transcription, audio_transcription).")

    # --- Verification ---
    logger.info("Verifying migration...")
    
    token_menu = await global_configurations_collection.find_one({"_id": "token_menu"})
    if token_menu:
        assert "audio_transcription" in token_menu, "audio_transcription tier missing from token_menu!"
        assert token_menu["audio_transcription"]["input_tokens"] == 1.5
        assert token_menu["audio_transcription"]["output_tokens"] == 3.5
        assert token_menu["audio_transcription"]["cached_input_tokens"] == 0
        logger.info("  token_menu verified: audio_transcription tier present with correct pricing.")
    else:
        logger.error("  VERIFICATION FAILED: token_menu not found!")

    # Verify a sample bot
    sample_bot = await bot_configurations_collection.find_one({"config_data.bot_id": {"$exists": True}})
    if sample_bot:
        at_config = (
            sample_bot.get("config_data", {})
            .get("configurations", {})
            .get("llm_configs", {})
            .get("audio_transcription")
        )
        if at_config:
            logger.info(f"  Sample bot verified: audio_transcription config present.")
        else:
            logger.warning("  Sample bot missing audio_transcription config.")
    
    logger.info("Migration complete.")
    client.close()


if __name__ == "__main__":
    import sys
    mongo_uri = sys.argv[1] if len(sys.argv) > 1 else "mongodb://localhost:27017"
    db_name = sys.argv[2] if len(sys.argv) > 2 else "myChatImposter"
    asyncio.run(run_migration(mongo_uri, db_name))
