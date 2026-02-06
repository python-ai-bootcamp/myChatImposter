
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
    configs = db["bot_configurations"]
    pattern = f"{TEST_USER}_bot_"
    await configs.delete_many({"config_data.bot_id": {"$regex": f"^{pattern}"}})
    
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
            create_url = f"{GATEWAY_URL}/api/external/ui/bots/{bot_id}"
            
            # Request Body
            payload = {
                "bot_id": bot_id,
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
                    
        # 5. Test Global Feature Limit (Limit 1)
        # We want to test that the limit is SHARED across bots.
        # User limits: max_bots=3, max_features=1
        
        # Bot 1: Enable 1 feature (1/1 Used) -> Should Pass
        target_bot_1 = f"{TEST_USER}_bot_1"
        print(f"\nTesting Global Feature Limit (Max 1)...")
        print(f"Enable 1 feature on {target_bot_1}...")
        
        payload_1 = {
             "bot_id": target_bot_1,
             "configurations": {"user_details": {}},
             "features": {
                 "automatic_bot_reply": {"enabled": True}, 
                 "periodic_group_tracking": {"enabled": False}
             }
        }
        resp = await client.patch(f"{GATEWAY_URL}/api/external/ui/bots/{target_bot_1}", json=payload_1, cookies=cookies)
        if resp.status_code == 200:
             print("SUCCESS: Bot 1 Feature enabled (Allowed)")
        else:
             print(f"FAILED: Bot 1 Feature blocked: {resp.status_code} {resp.text}")

        # Bot 2: Enable 1 feature (Total 2/1 Used) -> Should Fail
        target_bot_2 = f"{TEST_USER}_bot_2"
        print(f"Enable 1 feature on {target_bot_2} (should exceed global limit)...")
        
        payload_2 = {
             "bot_id": target_bot_2,
             "configurations": {"user_details": {}},
             "features": {
                 "automatic_bot_reply": {"enabled": True}, 
                 "periodic_group_tracking": {"enabled": False}
             }
        }
        resp = await client.patch(f"{GATEWAY_URL}/api/external/ui/bots/{target_bot_2}", json=payload_2, cookies=cookies)
        
        if resp.status_code == 400:
             print("SUCCESS: Bot 2 Feature blocked (Global Limit Reached)")
        else:
             print(f"FAILED: Bot 2 Feature NOT blocked! Status: {resp.status_code} (This confirms the bug if 200)")
             
        # 6. Test Over-Limit Maintenance (Delta Check)
        # Scenario: User has 2 bots * 1 feature = 2 total.
        # We lower limit to 1.
        # User tries to update Bot 1 (keeping 1 feature).
        # Should PASS (Count 2 -> 2, not increasing).
        
        print("\nTesting Over-Limit Update (Delta Check)...")
        
        # A. Set High Limit (10) and ensure Bot 1 & 2 have features enabled
        await credentials_collection.update_one(
            {"user_id": TEST_USER}, 
            {"$set": {"max_feature_limit": 10}}
        )
        
        # Ensure Bot 2 has 1 feature enabled
        
        # Ensure Bot 2 has 1 feature enabled
        payload_enable = {
             "bot_id": target_bot_2,
             "configurations": {"user_details": {}},
             "features": {
                 "automatic_bot_reply": {"enabled": True}, 
                 "periodic_group_tracking": {"enabled": False}
             }
        }
        res = await client.patch(f"{GATEWAY_URL}/api/external/ui/bots/{target_bot_2}", json=payload_enable, cookies=cookies)
        assert res.status_code == 200, f"Setup Failed: Could not enable feature on Bot 2. {res.text}"
        
        # Ensure Bot 1 has 1 feature enabled
        payload_enable_1 = {
             "bot_id": target_bot_1,
             "configurations": {"user_details": {}},
             "features": {
                 "automatic_bot_reply": {"enabled": True}, 
                 "periodic_group_tracking": {"enabled": False}
             }
        }
        res = await client.patch(f"{GATEWAY_URL}/api/external/ui/bots/{target_bot_1}", json=payload_enable_1, cookies=cookies)
        assert res.status_code == 200, f"Setup Failed: Could not enable feature on Bot 1. {res.text}"
        
        # Now Total Usage = 2.
        
        # B. Lower Limit to 1
        await credentials_collection.update_one(
            {"user_id": TEST_USER}, 
            {"$set": {"max_feature_limit": 1}}
        )
        
        # C. Update Bot 1 (Maintain 1 feature)
        
        # C. Update Bot 1 (Maintain 1 feature)
        # We send the SAME payload.
        # Old Total = 2. New Total = 2. 
        # Since New Total (2) > Limit (1), current logic blocks.
        # Correct logic: New (2) is NOT > Old (2), so allow.
        
        print(f"Attempting to update {target_bot_1} while over limit (Total 2 > Limit 1, but no increase)...")
        resp = await client.patch(f"{GATEWAY_URL}/api/external/ui/bots/{target_bot_1}", json=payload_enable_1, cookies=cookies)
        
        if resp.status_code == 200:
             print("SUCCESS: Update allowed (Delta check passed)")
        else:
             print(f"FAILED: Update blocked even without increase: {resp.status_code} {resp.text}")

        # D. Try to Increase (Should Block)
        # Enable 2nd feature on Bot 1 -> Total 3
        print(f"Attempting to INCREASE features on {target_bot_1} (Total 2 -> 3 > Limit 1)...")
        payload_increase = {
             "bot_id": target_bot_1,
             "configurations": {"user_details": {}},
             "features": {
                 "automatic_bot_reply": {"enabled": True}, 
                 "periodic_group_tracking": {"enabled": True}
             }
        }
        resp = await client.patch(f"{GATEWAY_URL}/api/external/ui/bots/{target_bot_1}", json=payload_increase, cookies=cookies)
        
        if resp.status_code == 400:
             print("SUCCESS: Increase blocked (Correct)")
        else:
             print(f"FAILED: Increase NOT blocked: {resp.status_code}")
             
        # Cleanup handled by next run or teardown if desired
        print("\nTest Complete.")
    
    mongo_client.close() # Close MongoDB client

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError: pass
    asyncio.run(run_test())
