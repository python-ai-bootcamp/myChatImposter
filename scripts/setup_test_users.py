
import asyncio
import os
import sys
import bcrypt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from motor.motor_asyncio import AsyncIOMotorClient
from infrastructure import db_schema

async def setup_test_users():
    print("Setting up test users...")
    
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.get_database("chat_manager")
    credentials_collection = db.get_collection(db_schema.COLLECTION_CREDENTIALS)
    configurations_collection = db.get_collection(db_schema.COLLECTION_CONFIGURATIONS)

    # Create 'test_user'
    user_id = "test_user"
    password = "password123"
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    owned_list = ["test_user"] # Default self-ownership
    
    doc = {
        "user_id": user_id,
        "password_hash": hashed,
        "role": "user",
        "owned_user_configurations": owned_list,
        "max_user_configuration_limit": 5,
        "max_feature_limit": 5
    }
    
    await credentials_collection.update_one(
        {"user_id": user_id},
        {"$set": doc},
        upsert=True
    )
    
    # Create valid Configuration for test_user (Fixes 500 error)
    config_doc = {
        "config_data": {
            "user_id": user_id,
            "configurations": {
                "user_details": {},
                "chat_provider_config": {"provider_name": "whatsAppBaileys", "provider_config": {}},
                "llm_provider_config": {"provider_name": "openAi", "provider_config": {"api_key": "sk-dummy", "api_key_source": "explicit"}},
                "queue_config": {},
                "context_config": {}
            },
            "features": {}
        }
    }
    await configurations_collection.update_one(
        {"config_data.user_id": user_id},
        {"$set": config_doc},
        upsert=True
    )
    
    print(f"User '{user_id}' created/updated.")

    # Ensure 'admin' exists too
    admin_id = "admin"
    admin_doc = {
        "user_id": admin_id,
        "password_hash": hashed, # Same password for ease
        "role": "admin",
        "owned_user_configurations": ["admin"] # Admins usually don't rely on this list but good to have
    }
    await credentials_collection.update_one(
        {"user_id": admin_id},
        {"$set": admin_doc},
        upsert=True
    )
    print(f"User '{admin_id}' created/updated.")
    
    client.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass # Python 3.14+ might not have/need this
    asyncio.run(setup_test_users())
