
import asyncio
import httpx
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Config
GATEWAY_URL = "http://localhost:8001"
# We need to test the user who reported the issue 'dudu', but for reproduction
# I will use a fresh user 'calc_bug_user' to replicate the state.
TEST_USER = "calc_bug_user"
TEST_PASS = "password123"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

async def setup_bug_user():
    # Setup 2 bots with known features
    # Bot 1: 3 features
    # Bot 2: 2 features
    
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.get_database("chat_manager")
    creds = db["user_auth_credentials"]
    
    await creds.delete_one({"user_id": TEST_USER})
    # Reset bots
    configs = db["configurations"]
    pattern = f"{TEST_USER}_bot_"
    await configs.delete_many({"config_data.user_id": {"$regex": f"^{pattern}"}})
    
    # Create Owner
    import bcrypt
    hashed = bcrypt.hashpw(TEST_PASS.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    await creds.insert_one({
        "user_id": TEST_USER,
        "password_hash": hashed,
        "role": "user",
        "owned_user_configurations": [],
        "max_user_configuration_limit": 5,
        "max_feature_limit": 10 # High limit to start
    })
    client.close()

async def create_bot_with_features(client, cookies, bot_id, features_enabled):
    create_url = f"{GATEWAY_URL}/api/external/ui/users/{bot_id}"
    features = {
        "automatic_bot_reply": {"enabled": False},
        "periodic_group_tracking": {"enabled": False},
        "kid_phone_safety_tracking": {"enabled": False}
    }
    
    count = 0
    for i, enabled in enumerate(features_enabled):
        keys = list(features.keys())
        if i < len(keys):
             features[keys[i]]["enabled"] = enabled
             if enabled: count += 1
             
    payload = {
        "user_id": bot_id,
        "configurations": {"user_details": {}},
        "features": features
    }
    resp = await client.put(create_url, json=payload, cookies=cookies)
    return resp

async def run_test():
    await setup_bug_user()
    
    async with httpx.AsyncClient(timeout=10.0, base_url=GATEWAY_URL) as client:
        # Login
        login_url = f"{GATEWAY_URL}/api/external/auth/login"
        resp = await client.post(login_url, json={"user_id": TEST_USER, "password": TEST_PASS})
        cookies = resp.cookies
        
        # Bot 1: Enable 3 features
        await create_bot_with_features(client, cookies, f"{TEST_USER}_bot_1", [True, True, True])
        
        # Bot 2: Enable 2 features
        await create_bot_with_features(client, cookies, f"{TEST_USER}_bot_2", [True, True, False]) # 2 features
        
        # Total Features: 3 + 2 = 5.
        
        # Set Limit to 5 (At Limit)
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        mongo_client = AsyncIOMotorClient(mongodb_url)
        db = mongo_client.get_database("chat_manager")
        await db.user_auth_credentials.update_one({"user_id": TEST_USER}, {"$set": {"max_feature_limit": 5}})
        
        # Now try to ADD 1 feature to Bot 2.
        # Expected:
        # Old Global Total = 5 (3 from Bot1 + 2 from Bot2)
        # New Count for Bot 2 = 3.
        # Others (Bot 1) = 3.
        # New Global Total = 3 (Others) + 3 (New) = 6.
        # Limit = 5.
        # Should Block.
        # Error Msg should say: "Used 6 features (New: 3, Others: 3)".
        
        print("\n--- Triggering Calculation ---")
        payload = {
            "user_id": f"{TEST_USER}_bot_2",
            "configurations": {"user_details": {}},
            "features": {
                "automatic_bot_reply": {"enabled": True},
                "periodic_group_tracking": {"enabled": True},
                "kid_phone_safety_tracking": {"enabled": True} # 3 features (increase from 2)
            }
        }
        resp = await client.patch(f"{GATEWAY_URL}/api/external/ui/users/{TEST_USER}_bot_2", json=payload, cookies=cookies)
        
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        
    mongo_client.close()

if __name__ == "__main__":
    if os.name == "nt":
        try: asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except: pass
    asyncio.run(run_test())
