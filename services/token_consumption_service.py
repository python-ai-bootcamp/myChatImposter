from datetime import datetime
from typing import Literal
from motor.motor_asyncio import AsyncIOMotorCollection
import logging

logger = logging.getLogger(__name__)

class TokenConsumptionService:
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    async def record_event(self, 
                           user_id: str, 
                           bot_id: str, 
                           feature_name: str, 
                           input_tokens: int, 
                           output_tokens: int, 
                           config_tier: Literal["high", "low"]):
        """
        Record a token consumption event to MongoDB.
        
        Args:
            user_id: The ID of the user interacting with the bot.
            bot_id: The ID of the bot.
            feature_name: The name of the feature using the LLM.
            input_tokens: Number of prompt tokens.
            output_tokens: Number of completion tokens.
            config_tier: The LLM configuration tier used ("high" or "low").
        """
        if self.collection is None:
            logger.error("TokenConsumptionService: No collection configured. Dropping event.")
            return

        try:
            doc = {
                "timestamp": datetime.utcnow(), # stored as ISODate (BSON Date) for TTL and logic
                "user_id": user_id,
                "bot_id": bot_id,
                "feature_name": feature_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "reporting_llm_config": config_tier
            }
            await self.collection.insert_one(doc)
            # logger.debug(f"Recorded token usage for {feature_name}: {input_tokens} in, {output_tokens} out.")
            
            # --- Quota Enforcement ---
            try:
                from services.quota_service import QuotaService
                quota_service = QuotaService.get_instance()
                if quota_service:
                    cost = quota_service.calculate_cost(input_tokens, output_tokens, config_tier)
                    await quota_service.update_user_usage(user_id, cost)
                else:
                    logger.warning("TokenConsumptionService: QuotaService not initialized. Cost not tracked.")
            except Exception as qe:
                logger.error(f"TokenConsumptionService: Failed to update quota: {qe}")
                
        except Exception as e:
            logger.error(f"Failed to record token consumption event: {e}")
