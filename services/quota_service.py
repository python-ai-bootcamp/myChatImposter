import logging
from datetime import datetime
from typing import Optional, Dict, Literal
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from infrastructure import db_schema

logger = logging.getLogger(__name__)

class QuotaService:
    _instance = None
    _token_menu: Dict = {}

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.global_config_collection = db[db_schema.COLLECTION_GLOBAL_CONFIGURATIONS]
        self.credentials_collection = db[db_schema.COLLECTION_CREDENTIALS]
        self.bot_config_collection = db[db_schema.COLLECTION_BOT_CONFIGURATIONS]
        self.baileys_sessions_collection = db[db_schema.COLLECTION_BAILEYS_SESSIONS]

    @classmethod
    def get_instance(cls):
        return cls._instance

    @classmethod
    async def initialize(cls, db: AsyncIOMotorDatabase):
        if cls._instance is None:
            cls._instance = QuotaService(db)
            await cls._instance.load_token_menu()
        return cls._instance

    async def load_token_menu(self):
        """Loads token_menu from global configurations into memory."""
        doc = await self.global_config_collection.find_one({"_id": "token_menu"})
        if doc:
            self._token_menu = doc
            # logger.info(f"Loaded token_menu: {self._token_menu}")
        else:
            logger.error("token_menu not found in global configurations!")

    def calculate_cost(self, 
                       input_tokens: int, 
                       output_tokens: int, 
                       config_tier: Literal["high", "low"],
                       cached_input_tokens: int = 0) -> float:
        """
        Calculates cost in dollars based on tokens and tier.
        Subtracts cached tokens from total input tokens to apply correct rates.
        """
        if config_tier not in self._token_menu:
             # Fallback or error?
             logger.warning(f"Unknown config_tier: {config_tier}")
             return 0.0
        
        menu = self._token_menu[config_tier]
        
        # Determine rates (per 1M tokens)
        rate_input = menu.get("input_tokens", 0)
        rate_output = menu.get("output_tokens", 0)
        rate_cached = menu.get("cached_input_tokens", 0) # Assumes this key exists in menu
        
        # Calculate uncached input tokens
        # Ensure we don't have negative uncached tokens if something is wonky
        uncached_input = max(0, input_tokens - cached_input_tokens)
        
        cost = (uncached_input * rate_input / 1_000_000) + \
               (cached_input_tokens * rate_cached / 1_000_000) + \
               (output_tokens * rate_output / 1_000_000)
        
        return cost

    async def update_user_usage(self, user_id: str, cost: float):
        """
        Updates user's dollars_used atomically and checks against limit.
        """
        if cost <= 0:
            return

        # Atomic increment
        await self.credentials_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"llm_quota.dollars_used": cost}}
        )

        # Fetch updated user to check limit
        # Optimization: We could use find_one_and_update to get the doc in one go, 
        # but pure update_one is often faster if we don't *always* need the doc, 
        # though here we do need to check the limit.
        # Let's fetch after update to see current state.
        user = await self.credentials_collection.find_one({"user_id": user_id}, {"llm_quota": 1})
        
        if not user or "llm_quota" not in user:
            return

        quota = user["llm_quota"]
        
        # Check if already disabled
        if not quota.get("enabled", True):
             return

        usage = quota.get("dollars_used", 0.0)
        limit = quota.get("dollars_per_period", 1.0)

        # Check limit
        if usage >= limit:
            logger.info(f"User {user_id} exceeded quota ({usage} >= {limit}). Disabling.")
            
            # Disable user
            await self.credentials_collection.update_one(
                {"user_id": user_id},
                {"$set": {"llm_quota.enabled": False}}
            )
            
            # Stop bots
            await self._stop_user_bots(user_id)

    async def _stop_user_bots(self, user_id: str):
        """
        Gracefully stops all running bots for the user.
        """
        try:
            from dependencies import GlobalStateManager
            lifecycle = GlobalStateManager.get_instance().bot_lifecycle_service
            if not lifecycle:
                logger.error("QuotaService: BotLifecycleService not available to stop bots.")
                return

            # Get owned bots
            user_doc = await self.credentials_collection.find_one({"user_id": user_id}, {"owned_bots": 1})
            if not user_doc: return
            
            owned_bots = user_doc.get("owned_bots", [])
            
            # Stop each if active
            # We can iterate owned_bots and call stop_bot (it handles 'if active' check)
            for bot_id in owned_bots:
                 await lifecycle.stop_bot(bot_id)
                 
        except Exception as e:
            logger.error(f"QuotaService: Error stopping bots for {user_id}: {e}")

    async def _process_activation_queue(self, bot_ids: list[str]):
        """
        Activates bots sequentially with a random delay to prevent load spikes.
        Re-evaluates conditions before each activation.
        """
        import asyncio
        import random
        from dependencies import GlobalStateManager
        
        lifecycle = GlobalStateManager.get_instance().bot_lifecycle_service
        if not lifecycle:
            logger.error("QuotaService: BotLifecycleService not available.")
            return

        logger.info(f"QuotaService: Processing activation queue for {len(bot_ids)} bots...")
        
        for i, bot_id in enumerate(bot_ids):
            try:
                # 1. Re-evaluate conditions
                # We need to find the bot owner to check quota
                # This is a bit expensive to query for every bot, but necessary for strict correctness
                # Optimization: We could fetch the config and owner in one go.
                
                bot_config = await self.bot_config_collection.find_one({"config_data.bot_id": bot_id})
                if not bot_config:
                    logger.warning(f"QuotaService: Bot {bot_id} not found during activation. Skipping.")
                    continue
                
                config_data = bot_config.get("config_data", {})
                user_details = config_data.get("configurations", {}).get("user_details", {})
                
                # Check 1: Bot Activated
                if not user_details.get("activated", user_details.get("active", True)):
                    logger.info(f"QuotaService: Bot {bot_id} is disabled by user. Skipping.")
                    continue
                
                # Check 2: Owner Quota Enabled
                owner_phone = config_data.get("owner_phone_number") # This is actually the owner's ID in this system context? 
                # Wait, strictly speaking we need the User ID from the credentials that OWNS this bot.
                # In bot_management, owner is stored.
                # Let's rely on finding the user who has this bot in `owned_bots`
                
                owner_doc = await self.credentials_collection.find_one({"owned_bots": bot_id})
                if not owner_doc:
                     logger.warning(f"QuotaService: Owner for bot {bot_id} not found. Skipping.")
                     continue
                     
                llm_quota = owner_doc.get("llm_quota", {})
                if not llm_quota.get("enabled", True):
                     logger.info(f"QuotaService: User quota disabled for bot {bot_id}. Skipping.")
                     continue
                
                # Check 3: Authenticated
                auth_doc = await self.baileys_sessions_collection.find_one({"_id": f"{bot_id}-creds"})
                if not auth_doc:
                    logger.info(f"QuotaService: Bot {bot_id} not authenticated. Skipping.")
                    continue

                # All checks passed - Activate
                logger.info(f"QuotaService: Auto-activating bot {bot_id} ({i+1}/{len(bot_ids)})")
                await lifecycle.start_bot(bot_id)

                # Random Delay (10-20s) if not the last one
                if i < len(bot_ids) - 1:
                    delay = random.uniform(10, 20)
                    logger.info(f"QuotaService: Waiting {delay:.2f}s before next activation...")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"QuotaService: Error activating bot {bot_id}: {e}")
                # Continue to next bot even if this one fails

    async def check_and_reset_quotas(self):
        """
        Hourly job to reset quotas.
        """
        now_ms = datetime.utcnow().timestamp() * 1000
        bots_to_activate = []

        # Iterate users needing reset
        async for user in self.credentials_collection.find({"llm_quota.enabled": False}):
            try:
                user_id = user["user_id"]
                quota = user.get("llm_quota", {})
                last_reset = quota.get("last_reset", 0)
                reset_days = quota.get("reset_days", 7)
                
                next_reset = last_reset + (reset_days * 24 * 60 * 60 * 1000)
                
                if now_ms >= next_reset:
                    logger.info(f"QuotaService: Resetting quota for {user_id}")
                    
                    updates = {
                        "llm_quota.dollars_used": 0.0,
                        "llm_quota.last_reset": now_ms,
                        "llm_quota.enabled": True
                    }
                    await self.credentials_collection.update_one({"user_id": user_id}, {"$set": updates})
                    
                    # Collect bots for this user
                    user_bots = user.get("owned_bots", [])
                    bots_to_activate.extend(user_bots)
                         
            except Exception as e:
                logger.error(f"QuotaService: Error resetting quota for user {user.get('user_id')}: {e}")

        # Process activations
        if bots_to_activate:
             await self._process_activation_queue(bots_to_activate)

    async def start_all_active_users_bots(self):
        """
        Starts bots for all users with enabled quota.
        """
        import asyncio
        logger.info("QuotaService: Waiting 10s before auto-starting bots to ensure system stability...")
        await asyncio.sleep(10) 

        logger.info("QuotaService: Collecting bots for startup activation...")
        bots_to_activate = []
        
        async for user in self.credentials_collection.find({"llm_quota.enabled": True}):
             # Only add bots if they currently exist in owned_bots
             # We initiate the list here, validation happens in _process_activation_queue
             bots_to_activate.extend(user.get("owned_bots", []))
        
        if bots_to_activate:
            logger.info(f"QuotaService: Found {len(bots_to_activate)} potential bots to start.")
            await self._process_activation_queue(bots_to_activate)
        else:
            logger.info("QuotaService: No bots found to start.")

