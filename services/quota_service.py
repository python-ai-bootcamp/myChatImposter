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
                       config_tier: Literal["high", "low"]) -> float:
        """
        Calculates cost in dollars based on tokens and tier.
        Attributes usage to cached input tokens?? 
        NOTE: The spec distinguishes 'input_tokens' and 'cached_input_tokens'.
        However, the current tracking service only reports 'input_tokens'. 
        Assumption: treat all input tokens as standard 'input_tokens' for now unless tracking distinguishes them.
        """
        if config_tier not in self._token_menu:
             # Fallback or error?
             logger.warning(f"Unknown config_tier: {config_tier}")
             return 0.0
        
        menu = self._token_menu[config_tier]
        
        # Determine rates (per 1M tokens)
        rate_input = menu.get("input_tokens", 0)
        rate_output = menu.get("output_tokens", 0)
        
        cost = (input_tokens * rate_input / 1_000_000) + (output_tokens * rate_output / 1_000_000)
        return cost

    async def update_user_usage(self, user_id: str, cost: float):
        """
        Updates user's dollars_used and checks against limit.
        If limit exceeded, disables user and stops bots.
        """
        if cost <= 0:
            return

        # Fetch user's current quota
        user = await self.credentials_collection.find_one({"user_id": user_id}, {"llm_quota": 1})
        if not user or "llm_quota" not in user:
            # logger.warning(f"User {user_id} has no quota defined. Skipping enforcement.")
            return

        quota = user["llm_quota"]
        
        # Check if already disabled (to avoid redundant updates/stops)
        if not quota.get("enabled", True):
             return

        new_usage = quota.get("dollars_used", 0.0) + cost
        limit = quota.get("dollars_per_period", 1.0) # Default 1.0 if missing

        updates = {"llm_quota.dollars_used": new_usage}
        
        # Check limit
        if new_usage >= limit:
            logger.info(f"User {user_id} exceeded quota ({new_usage} >= {limit}). Disabling.")
            updates["llm_quota.enabled"] = False
            
            # Stop bots
            await self._stop_user_bots(user_id)

        await self.credentials_collection.update_one(
            {"user_id": user_id},
            {"$set": updates}
        )

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
                "config_data.bot_id": {"$in": owned_bots},
                "config_data.configurations.user_details.activated": True
            })
            
            async for doc in cursor:
                bot_id = doc.get("config_data", {}).get("bot_id")
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
        logger.info("QuotaService: Starting bots for all enabled users...")
        count = 0
        async for user in self.credentials_collection.find({"llm_quota.enabled": True}):
             await self.start_user_bots(user["user_id"])
             count += 1
        logger.info(f"QuotaService: Processed startup for {count} users.")

