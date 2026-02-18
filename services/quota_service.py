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

    async def start_user_bots(self, user_id: str):
        """
        Start all activated bots for a user.
        """
        try:
            from dependencies import GlobalStateManager
            lifecycle = GlobalStateManager.get_instance().bot_lifecycle_service
            if not lifecycle:
                 logger.error("QuotaService: BotLifecycleService not available to start bots.")
                 return

            # Get owned bots
            user_doc = await self.credentials_collection.find_one({"user_id": user_id}, {"owned_bots": 1})
            if not user_doc: return
            
            owned_bots = user_doc.get("owned_bots", [])
            
            # Filter by activated flag in bot_configurations
            cursor = self.bot_config_collection.find({
                "config_data.bot_id": {"$in": owned_bots}
            })
            
            async for doc in cursor:
                config_data = doc.get("config_data", {})
                bot_id = config_data.get("bot_id")
                
                # Check 1: Activated
                user_details = config_data.get("configurations", {}).get("user_details", {})
                activated = user_details.get("activated", user_details.get("active", True))
                
                if not activated:
                    continue

                # Check 2: Authenticated (Has Credentials)
                # Only start if credentials exist
                auth_doc = await self.baileys_sessions_collection.find_one({"_id": f"{bot_id}-creds"})
                if not auth_doc:
                     logger.info(f"QuotaService: Skipping auto-start for {bot_id} (Activated but Not Authenticated)")
                     continue

                if bot_id:
                    await lifecycle.start_bot(bot_id)
                    
        except Exception as e:
             logger.error(f"QuotaService: Error starting bots for {user_id}: {e}")

    async def check_and_reset_quotas(self):
        """
        Midnight job to reset quotas.
        """
        now_ms = datetime.utcnow().timestamp() * 1000
        
        # Iterate all users with quota
        # Optimization: Add index on last_reset if this becomes slow.
        async for user in self.credentials_collection.find({"llm_quota": {"$exists": True}}):
            try:
                user_id = user["user_id"]
                quota = user.get("llm_quota", {})
                last_reset = quota.get("last_reset", 0)
                reset_days = quota.get("reset_days", 7)
                
                # Check if due for reset
                # (last_reset + reset_days_in_ms) < now
                next_reset = last_reset + (reset_days * 24 * 60 * 60 * 1000)
                
                if now_ms >= next_reset:
                    logger.info(f"QuotaService: Resetting quota for {user_id}")
                    
                    updates = {
                        "llm_quota.dollars_used": 0.0,
                        "llm_quota.last_reset": now_ms,
                        "llm_quota.enabled": True
                    }
                    await self.credentials_collection.update_one({"user_id": user_id}, {"$set": updates})
                    
                    # If it was disabled, restart bots
                    if not quota.get("enabled", True):
                         await self.start_user_bots(user_id)
                         
            except Exception as e:
                logger.error(f"QuotaService: Error resetting quota for user {user.get('user_id')}: {e}")

    async def start_all_active_users_bots(self):
        """
        Starts bots for all users with enabled quota.
        """
        import asyncio
        logger.info("QuotaService: Waiting 60s before auto-starting bots to ensure system stability...")
        await asyncio.sleep(60) 

        logger.info("QuotaService: Starting bots for all enabled users...")
        count = 0
        async for user in self.credentials_collection.find({"llm_quota.enabled": True}):
             await self.start_user_bots(user["user_id"])
             count += 1
        logger.info(f"QuotaService: Processed startup for {count} users.")

