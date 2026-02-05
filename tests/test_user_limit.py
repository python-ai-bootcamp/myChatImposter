
import asyncio
import sys
import httpx
import logging
import uuid

# Config
GATEWAY_URL = "http://localhost:8001"
# Assuming 'test_user' exists from previous tests or setup
TEST_USER = "test_user_limit"
TEST_PASS = "password123"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

async def get_cookies_and_create_user_if_needed(client: httpx.AsyncClient, user_id, password):
    # Try login
    res = await client.post("/api/external/auth/login", json={"user_id": user_id, "password": password})
    if res.status_code == 200:
        return res.cookies
    elif res.status_code == 401:
        # Create user via direct backend/db access? No, let's assume setup_test_users.py is run.
        # But wait, we need a clean user with 0 owned configs to test the full range 0-5.
        # It's better to create a new user directly in DB if possible, or use a known one.
        # Since I can't easily register a user via API (no register endpoint), I will rely on existing 'test_user'
        # But 'test_user' might already have owned configs.
        # I'll create a new function to setup a fresh user directly in Mongo.
        pass
    return None

from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import os

async def setup_limit_user():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.get_database("chat_manager")
    creds = db["user_auth_credentials"]
    
    # Reset test_user_limit
    await creds.delete_one({"user_id": TEST_USER})
    # Also clean up old bots if any (backend reset)
    configs = db["configurations"]
    pattern = f"{TEST_USER}_bot_"
    await configs.delete_many({"config_data.user_id": {"$regex": f"^{pattern}"}})
    
    hashed = bcrypt.hashpw(TEST_PASS.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    await creds.insert_one({
        "user_id": TEST_USER,
        "password_hash": hashed,
        "role": "user",
        "owned_user_configurations": [] # Start Empty
    })
    
    logger.info(f"Reset {TEST_USER} with 0 owned configurations.")
    client.close()

async def run_test():
    await setup_limit_user()
    
    # Setup MongoDB client for updating limits
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongo_client = AsyncIOMotorClient(mongodb_url)
    db = mongo_client.get_database("chat_manager")
    credentials_collection = db["user_auth_credentials"]

    async with httpx.AsyncClient(timeout=10.0, base_url=GATEWAY_URL) as client:
        # 3. Authenticate to get session (and ensure limits are loaded)
        login_url = f"{GATEWAY_URL}/api/external/auth/login"
        resp = await client.post(login_url, json={"user_id": TEST_USER, "password": TEST_PASS})
        if resp.status_code != 200:
             print(f"FAILED: Login failed: {resp.text}")
             mongo_client.close()
             return

        cookies = resp.cookies
        session_id = str(cookies.get("session_id"))
        print(f"Logged in. Session ID: {session_id}")

        # UPDATE: Set custom limits in DB for this test user to verify dynamic logic
        # Limit: 3 bots, 1 feature
        await credentials_collection.update_one(
            {"user_id": TEST_USER},
            {"$set": {"max_user_configuration_limit": 3, "max_feature_limit": 1}}
        )
        print("Updated test user limits: max_bots=3, max_features=1")
        
        # We need to re-login to force session refresh with new limits? 
        # Yes, because session is cached. Or wait 24h. Easiest is to login again or clear cache.
        # Actually session manager creates new ID on login.
        
        resp = await client.post(login_url, json={"user_id": TEST_USER, "password": TEST_PASS})
        cookies = resp.cookies
        print("Re-logged in to refresh limits.")

        # 4. Create Bots (Limit 3)
        # We expect 3 successes, 4th failure
        for i in range(1, 6):
            bot_id = f"{TEST_USER}_bot_{i}"
            create_url = f"{GATEWAY_URL}/api/external/ui/users/{bot_id}"
            
            # Request Body
            payload = {
                "user_id": bot_id,
                "configurations": {
                     "user_details": {}
                },
                "features": {
                     "automatic_bot_reply": {"enabled": False},
                     "periodic_group_tracking": {"enabled": False},
                     "kid_phone_safety_tracking": {"enabled": False}
                }
            }
            
            print(f"Attempting to create bot {i}: {bot_id}")
            resp = await client.put(create_url, json=payload, cookies=cookies)
            
            if i <= 3:
                if resp.status_code == 200:
                    print(f"SUCCESS: Created {bot_id}")
                else:
                    print(f"FAILED: Expected success for {bot_id}, got {resp.status_code} {resp.text}")
            else:
                if resp.status_code == 403:
                    print(f"SUCCESS: Blocked {bot_id} (Limit reached)")
                else:
                    print(f"FAILED: {bot_id} NOT blocked! Status: {resp.status_code}")
                    
        # 5. Test Feature Limit (Limit 1)
        # Use existing bot 1
        target_bot = f"{TEST_USER}_bot_1"
        patch_url = f"{GATEWAY_URL}/api/external/ui/users/{target_bot}"
        
        print("\nTesting Feature Limit (Max 1)...")
        
        # Test A: Enable 1 feature (Should Pass)
        payload_1 = {
             "user_id": target_bot,
             "configurations": {"user_details": {}},
             "features": {
                 "automatic_bot_reply": {"enabled": True}, 
                 "periodic_group_tracking": {"enabled": False}
             }
        }
        resp = await client.patch(patch_url, json=payload_1, cookies=cookies)
        if resp.status_code == 200:
             print("SUCCESS: 1 Feature enabled (Allowed)")
        else:
             print(f"FAILED: 1 Feature blocked: {resp.status_code} {resp.text}")

        # Test B: Enable 2 features (Should Fail)
        payload_2 = {
             "user_id": target_bot,
             "configurations": {"user_details": {}},
             "features": {
                 "automatic_bot_reply": {"enabled": True}, 
                 "periodic_group_tracking": {"enabled": True}
             }
        }
        resp = await client.patch(patch_url, json=payload_2, cookies=cookies)
        if resp.status_code == 400:
             print("SUCCESS: 2 Features blocked (Limit Reached)")
        else:
             print(f"FAILED: 2 Features NOT blocked: {resp.status_code} {resp.text}")
             
        # Cleanup handled by next run or teardown if desired
        print("\nTest Complete.")
    
    mongo_client.close() # Close MongoDB client

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError: pass
    asyncio.run(run_test())
