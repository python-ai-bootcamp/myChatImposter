import httpx
import asyncio
import sys

BASE_URL = "http://127.0.0.1:8001"

async def verify_security():
    # Use a persistent client to handle cookies
    # Trust env means it will use proxy if set, but we are local.
    headers = {"Content-Type": "application/json"}
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0, headers=headers) as client:
        print("\n--- 0. Setup: Create Test User ---")
        # Login as Admin first
        try:
             res = await client.post("/api/external/auth/login", json={"user_id": "admin", "password": "Admin1234!"})
        except httpx.ConnectError:
             print("Failed to connect.")
             return
             
        if res.status_code == 200:
             print("Logged in as Admin.")
             data = res.json()
             print(f"Login Response Body: {data}")
             session_id = data.get("session_id")
             if session_id:
                 # Force cookie with domain/path
                 client.cookies.set("session_id", session_id, domain="127.0.0.1", path="/")
                 print(f"Set Admin Cookie manually: {session_id}")
             
             # Create user if not exists
             new_user = {
                "user_id": "test_security_user",
                "first_name": "Test",
                "last_name": "Security",
                "role": "user",
                "password": "User1234!",
                "country_value": "US",
                "language": "en"
            }
             res = await client.post("/api/external/users", json=new_user)
             if res.status_code in [200, 201]:
                  print("User 'test_security_user' created/exists.")
             elif res.status_code == 400:
                  print("User check/creation response: " + res.text)
             else:
                  print(f"Failed to create user: {res.text}")
        else:
             print(f"Failed to login as Admin (Critical for setup). Status: {res.status_code}, Body: {res.text}")

        # Logout Admin
        client.cookies.clear()
        
        print("\n--- 1. Login as 'test_security_user' ---")
        user_id = "test_security_user"
        password = "User1234!" 
        
        res = await client.post("/api/external/auth/login", json={"user_id": user_id, "password": password})

        if res.status_code != 200:
            print(f"Login failed: {res.text}")
            return
            
        print("Login successful.")
        data = res.json()
        session_id = data.get("session_id")
        if session_id:
             client.cookies.set("session_id", session_id, domain="127.0.0.1", path="/")
             print(f"Set User Cookie manually: {session_id}")
        
        print("\n--- 2. Attempt Self-Promotion via PUT (Should fail) ---")
        # PUT should now be 403 Forbidden (Blocked by Gateway or Backend)
        
        update_data = {
            "role": "admin",
            "first_name": "Hacked"
        }
        
        res = await client.put(f"/api/external/users/{user_id}", json=update_data)
        print(f"PUT Response: {res.status_code}")
        
        if res.status_code in [403, 401]:
             if res.status_code == 403:
                 print("SUCCESS: PUT blocked for User (403 Forbidden).")
             else:
                 print("WARNING: PUT blocked (401 Unauthorized) - Session might be lost?")
        else:
             print(f"FAILURE: PUT allowed! Status: {res.status_code}")

        print("\n--- 3. Attempt Self-Promotion via PATCH (Should fail to change role, succeed for name) ---")
        
        res = await client.patch(f"/api/external/users/{user_id}", json=update_data)
        print(f"PATCH Response: {res.status_code}")
        
        if res.status_code == 200:
             print("PATCH allowed (Expected). Checking if role changed...")
             
             res = await client.get(f"/api/external/users/{user_id}")
             data = res.json()
             role = data.get("role")
             name = data.get("first_name")
             
             print(f"Current Role: {role}")
             print(f"Current Name: {name}")
             
             if role == "user" and name == "Hacked":
                  print("SUCCESS: PATCH updated name but ignored role change!")
             elif role == "admin":
                  print("FAILURE: Role changed to Admin via PATCH!")
             else:
                  print(f"FAILURE: Unexpected state. Role: {role}, Name: {name}")
        else:
             print(f"FAILURE: PATCH blocked unexpectedly. Status: {res.status_code} Body: {res.text}")

        print("\n--- 4. Attempt Bot Creation via PATCH (Should succeed) ---")
        bot_id = "test_patch_bot_1"
        
        # We need to own it, or it needs to be new.
        # Since it is new, Gateway should allow PATCH.
        # Backend should create it.
        
        bot_patch = {
            "features": {"automatic_bot_reply": {"enabled": True}}
        }
        
        res = await client.patch(f"/api/external/bots/{bot_id}", json=bot_patch)
        print(f"Bot PATCH Response (Create): {res.status_code}")
        
        if res.status_code in [200, 201]:
             print("SUCCESS: Bot created via PATCH.")
             # Update same bot
             res = await client.patch(f"/api/external/bots/{bot_id}", json={"features": {"automatic_bot_reply": {"enabled": False}}})
             print(f"Bot PATCH Response (Update): {res.status_code}")
             if res.status_code == 200:
                 print("SUCCESS: Bot updated via PATCH.")
        else:
             print(f"FAILURE: Bot PATCH failed. Status: {res.status_code} Body: {res.text}")

        print("\n--- 5. Attempt Bot Creation via PUT (Should fail) ---")
        bot_id_fail = "test_put_bot_fail"
        res = await client.put(f"/api/external/bots/{bot_id_fail}", json={"bot_id": bot_id_fail})
        print(f"Bot PUT Response: {res.status_code}")
        
        if res.status_code in [403, 401]:
             if res.status_code == 403:
                  print("SUCCESS: Bot PUT blocked for User (403 Forbidden).")
             else:
                  print("WARNING: Bot PUT blocked (401 Unauthorized) - Session lost?")
        else:
             print(f"FAILURE: Bot PUT allowed! Status: {res.status_code}")

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass
    asyncio.run(verify_security())
