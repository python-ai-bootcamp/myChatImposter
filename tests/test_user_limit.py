
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
    
    async with httpx.AsyncClient(timeout=10.0, base_url=GATEWAY_URL) as client:
        # Login
        res_login = await client.post("/api/external/auth/login", json={"user_id": TEST_USER, "password": TEST_PASS})
        if res_login.status_code != 200:
             logger.error("Login failed")
             return
        cookies = res_login.cookies
        
        # Test Loop: Create 6 users
        for i in range(1, 7):
            bot_id = f"{TEST_USER}_bot_{i}"
            logger.info(f"Attempting to create bot {i}: {bot_id}")
            
            payload = {
                "user_id": bot_id,
                "configurations": {"user_details": {}},
                "features": {}
            }
            
            # Create (PUT)
            res = await client.put(f"/api/external/ui/users/{bot_id}", json=payload, cookies=cookies)
            
            if i <= 5:
                if res.status_code == 200:
                    logger.info(f"SUCCESS: Created {bot_id}")
                else:
                    logger.error(f"FAILED: Could not create {bot_id}. Status: {res.status_code} - {res.text}")
                    return
            else:
                # 6th attempt should fail
                if res.status_code == 403:
                    logger.info(f"SUCCESS: 6th creation blocked with 403. Message: {res.text}")
                else:
                    logger.error(f"FAILED: 6th creation NOT blocked! Status: {res.status_code}")

        # Check Updates (PATCH) still work for existing
        last_success_bot = f"{TEST_USER}_bot_5"
        logger.info(f"Testing Update on existing {last_success_bot}...")
        res_update = await client.patch(f"/api/external/ui/users/{last_success_bot}", json={"user_id": last_success_bot, "configurations": {"user_details": {"name": "Updated"}}}, cookies=cookies)
        
        if res_update.status_code == 200:
             logger.info("SUCCESS: Update allowed even at limit.")
        else:
             logger.error(f"FAILED: Update blocked! Status: {res_update.status_code}")

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError: pass
    asyncio.run(run_test())
