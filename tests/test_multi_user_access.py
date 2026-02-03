
import asyncio
import httpx
import sys
import logging

# Config
GATEWAY_URL = "http://localhost:8001"
TEST_USER = "test_user"
TEST_PASS = "password123"
ADMIN_USER = "admin"
ADMIN_PASS = "password123"

logging.basicConfig(level=logging.INFO, format="%(message)s")

async def run_verification():
    print(f"Starting Verification against {GATEWAY_URL}")
    
    async with httpx.AsyncClient(timeout=10.0, base_url=GATEWAY_URL) as client:
        
        # 1. Login as Regular User
        print("\n--- Step 1: Login as Regular User ---")
        login_res = await client.post("/api/external/auth/login", json={
            "user_id": TEST_USER,
            "password": TEST_PASS
        })
        if login_res.status_code != 200:
            print(f"FAILED: Login failed: {login_res.text}")
            return
        
        print("Login Successful.")
        print(f"Cookies from MultiUser Test: {client.cookies}")

        # 2. List Users (Should show only own)
        print("\n--- Step 2: List Users (Expect Filtering) ---")
        list_res = await client.get("/api/external/users")
        print(f"Status: {list_res.status_code}")
        users = list_res.json().get("user_ids", [])
        print(f"Users found: {users}")
        
        if TEST_USER in users and ADMIN_USER not in users:
             print("SUCCESS: Filtering working (Shows self, hides admin).")
        else:
             print("FAILED: Filtering incorrect.")

        # 3. Access Own Resource
        print(f"\n--- Step 3: Access Own Resource ({TEST_USER}) ---")
        # NOTE: Frontend uses /info suffix for structure. We should verify THAT endpoint for Owner field.
        own_res = await client.get(f"/api/external/users/{TEST_USER}/info")
        if own_res.status_code in [200, 404]: # 404 is fine if config doesn't exist yet, but permission granted to check
            print(f"SUCCESS: Access granted (Status {own_res.status_code})")
            if own_res.status_code == 200:
                data = own_res.json()
                # Verify Owner Field (Phase 5 Requirement)
                configs = data.get("configurations", [])
                if configs:
                    owner_val = configs[0].get("owner")
                    print(f"Owner Check: {owner_val}")
                    if owner_val == TEST_USER:
                        print("SUCCESS: Owner field correct.")
                    else:
                        print(f"FAILED: Owner field incorrect. Expected {TEST_USER}, got {owner_val}")
                else:
                     print("FAILED: No configuratons returned in /info")
        else:
            print(f"FAILED: Access denied or error (Status {own_res.status_code})")

        # 4. Access Admin Resource (Forbidden)
        print(f"\n--- Step 4: Access Admin Resource ({ADMIN_USER}) ---")
        other_res = await client.get(f"/api/external/users/{ADMIN_USER}")
        if other_res.status_code == 403: # Should be 403 Forbidden? 
             # Wait, PermissionValidator returns "False" for unowned.
             # Middleware returns 403 if check_permission returns False.
             print("SUCCESS: Access correctly denied (403).")
        else:
             print(f"FAILED: Expected 403, got {other_res.status_code}")

        # 5. Create NEW Resource (Ownership Claim)
        new_bot_id = f"{TEST_USER}_bot_1"
        print(f"\n--- Step 5: Create New Resource ({new_bot_id}) ---")
        
        # We need a valid body for PUT
        config_body = {
            "user_id": new_bot_id,
            "configurations": {
                "user_details": {},
                "chat_provider_config": {"provider_name": "whatsapp_baileys", "provider_config": {}},
                 "llm_provider_config": {"provider_name": "openai", "provider_config": {"api_key": "sk-dummy", "api_key_source": "explicit", "model": "gpt-4"}}
            },
            "features": {}
        }
        
        put_res = await client.put(f"/api/external/users/{new_bot_id}", json=config_body)
        print(f"PUT Status: {put_res.status_code}")
        
        if put_res.status_code == 200:
             print("Create Successful.")
        else:
             print(f"FAILED: Create failed: {put_res.text}")
             # If backend issues (not running?), we stop.
             pass

        # 6. Verify Ownership Claimed (List again)
        print("\n--- Step 6: Verify Ownership Claimed (List Users) ---")
        list_res_2 = await client.get("/api/external/users")
        users_2 = list_res_2.json().get("user_ids", [])
        print(f"Users found: {users_2}")
        
        if new_bot_id in users_2:
             print("SUCCESS: New bot appeared in list immediately (Cache updated).")
        else:
             print("FAILED: New bot NOT in list (Cache update failed?)")

    print("\nVerification Complete.")

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass
    asyncio.run(run_verification())
