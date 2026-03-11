import asyncio
import logging
import uuid
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from config_models import ChatCompletionProviderConfig, ChatCompletionProviderSettings
from services.model_factory import create_model_provider
from unittest.mock import patch, MagicMock, AsyncMock
from infrastructure import db_schema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_integration_test():
    """
    Component Integration Test for Token Flow.
    
    1. Connects to local MongoDB.
    2. Creates a tracked LLM using FakeLlmProvider.
    3. Invokes the LLM.
    4. Verifies the token consumption event is stored in MongoDB.
    """
    
    # 1. Setup MongoDB Connection
    mongo_url = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(mongo_url)
    db = client.get_database("chat_manager") # Use the real DB name
    
    try:
        # Verify connection
        await client.admin.command('ismaster')
        logger.info("Connected to MongoDB.")
        
        collection = db[db_schema.COLLECTION_TOKEN_CONSUMPTION]
        
        # 2. Setup Context
        test_run_id = str(uuid.uuid4())
        user_id = f"test_user_{test_run_id}"
        bot_id = f"test_bot_{test_run_id}"
        feature_name = "integration_test"
        
        # 3. Create Tracked LLM (Fake Provider)
        llm_config = ChatCompletionProviderConfig(
            provider_name="fakeLlm", 
            provider_config=ChatCompletionProviderSettings(
                model="fake-gpt", 
                api_key="fake",
            )
        )
        setattr(llm_config.provider_config, "response_array", ["Hello Integration Test"])

        # Patch dependencies for the factory
        with patch('services.model_factory.resolve_model_config', new_callable=AsyncMock) as mock_config, \
             patch('services.model_factory.resolve_user', new_callable=AsyncMock) as mock_user, \
             patch('services.model_factory.get_global_state') as mock_state:
            mock_config.return_value = llm_config
            mock_user.return_value = user_id
            
            mock_global = MagicMock()
            mock_global.token_consumption_collection = collection
            mock_state.return_value = mock_global

            llm = await create_model_provider(
                bot_id=bot_id,
                feature_name=feature_name,
                config_tier="low"
            )
        
        # 4. Invoke LLM
        logger.info("Invoking LLM...")
        response = await llm.ainvoke("Hi")
        logger.info(f"LLM Response: {response.content}")
        
        # 5. Verify MongoDB
        # Give a small buffer for async write (though usually awaited in callback, but callback is async)
        # LangChain callbacks are awaited if methods are async.
        
        logger.info("Verifying MongoDB...")
        # Query by unique user_id/bot_id
        event = await collection.find_one({
            "user_id": user_id,
            "bot_id": bot_id,
            "feature_name": feature_name
        })
        
        if event:
            logger.info("SUCCESS: Event found in MongoDB!")
            logger.info(f"Event: {event}")
            
            # Verify fields
            assert event["input_tokens"] == 10
            assert event["output_tokens"] == 5
            assert isinstance(event["timestamp"], datetime)
            print("TEST PASSED")
        else:
            logger.error("FAILURE: Event not found in MongoDB.")
            # Debug: list all events
            # async for doc in collection.find().limit(5):
            #    print(doc)
            raise AssertionError("Event was not saved to MongoDB")
            
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(run_integration_test())
