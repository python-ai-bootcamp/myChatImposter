
import asyncio
import sys
import httpx
import logging
from typing import Dict, Any

# Config
GATEWAY_URL = "http://localhost:8001"
TEST_USER = "test_user"
TEST_PASS = "password123"
ADMIN_USER = "admin"
ADMIN_PASS = "password123"

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

async def get_cookies(client: httpx.AsyncClient, user_id: str, password: str) -> httpx.Cookies:
    res = await client.post("/api/external/auth/login", json={"user_id": user_id, "password": password})
    if res.status_code != 200:
        raise Exception(f"Login failed for {user_id}: {res.text}")
    return res.cookies

async def run_tests():
    async with httpx.AsyncClient(timeout=10.0, base_url=GATEWAY_URL) as client:
        
        try:
            # 1. Setup Sessions
            logger.info("--- 1. Login ---")
            user_cookies = await get_cookies(client, TEST_USER, TEST_PASS)
            admin_cookies = await get_cookies(client, ADMIN_USER, ADMIN_PASS)
            logger.info("Sessions created.")

            # 2. Test Legacy Restriction (User accessing Legacy)
            logger.info("\n--- 2. Security Check: Block Legacy Route ---")
            legacy_url = f"/api/external/bots/{TEST_USER}"
            res = await client.get(legacy_url, cookies=user_cookies)
            if res.status_code == 403:
                logger.info("SUCCESS: Legacy route blocked for Regular User (403).")
            elif res.status_code == 404:
                # Gateway block usually returns 403, but let's see permission validator logic
                # It returns False -> Middleware returns 403 Forbidden
                logger.error(f"FAILED: Expected 403, got 404. Did permission allow pass?")
            else:
                logger.error(f"FAILED: Legacy route accessible! Status: {res.status_code}")

            # 3. Test Legacy Access (Admin accessing Legacy)
            logger.info("\n--- 3. Admin Access: Legacy Route ---")
            res_admin = await client.get(legacy_url, cookies=admin_cookies)
            if res_admin.status_code == 200:
                data = res_admin.json()
                if "llm_provider_config" in data.get("configurations", {}):
                    logger.info("SUCCESS: Admin sees full config (including secrets).")
                else:
                    logger.error("FAILED: Admin config missing expected fields.")
            else:
                logger.error(f"FAILED: Admin denied access to legacy route: {res_admin.status_code}")

            # 4. Test UI Endpoint (User Access)
            logger.info("\n--- 4. UI Access: Restricted GET ---")
            ui_url = f"/api/external/ui/bots/{TEST_USER}"
            res_ui = await client.get(ui_url, cookies=user_cookies)
            
            if res_ui.status_code == 200:
                data = res_ui.json()
                # Verify SANITIZATION
                configs = data.get("configurations", {})
                if "llm_provider_config" not in configs and "queue_config" not in configs:
                     if "user_details" in configs:
                         logger.info("SUCCESS: UI Config is sanitized (Secrets hidden, Details present).")
                     else:
                         logger.error("FAILED: UI Config missing allowed fields.")
                else:
                     logger.error(f"CRITICAL FAILURE: UI Config LEAKED secrets! Keys: {list(configs.keys())}")
            else:
                 logger.error(f"FAILED: User denied access to UI route: {res_ui.status_code}")

            # 5. Test UI Patch (User Update)
            logger.info("\n--- 5. UI Access: PATCH Update ---")
            patch_data = {
                "bot_id": TEST_USER,
                "configurations": {
                    "user_details": {"first_name": "Test", "last_name": "Patched"}
                },
                "features": {
                    "automatic_bot_reply": {"enabled": True, "chat_system_prompt": "You are a test bot."}
                }
            }
            # Attempt malicious injection (should be ignored/rejected)
            malicious_data = patch_data.copy()
            malicious_data["configurations"]["queue_config"] = {"max_messages": 99999}
            
            res_patch = await client.patch(ui_url, json=malicious_data, cookies=user_cookies)
            
            if res_patch.status_code == 200:
                logger.info("PATCH successful.")
                
                # Check persistence
                res_verify = await client.get(ui_url, cookies=user_cookies)
                new_data = res_verify.json()
                
                fname = new_data["configurations"]["user_details"].get("first_name")
                if fname == "Test":
                    logger.info("SUCCESS: PATCH applied correct fields.")
                else:
                    logger.error(f"FAILED: PATCH did not apply fields. Got: {fname}")
                
                # Verify NO INJECTION
                # We need Admin to check the queue config
                res_check_admin = await client.get(legacy_url, cookies=admin_cookies)
                full_config = res_check_admin.json()
                q_config = full_config["configurations"].get("queue_config", {})
                
                if q_config.get("max_messages") != 99999:
                    logger.info("SUCCESS: Malicious injection ignored.")
                else:
                    logger.error("CRITICAL FAILURE: Malicious injection SUCCEEDED!")

            else:
                 logger.error(f"FAILED: PATCH failed: {res_patch.status_code} - {res_patch.text}")

        except Exception as e:
            logger.error(f"TEST EXCEPTION: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError: pass
    asyncio.run(run_tests())
