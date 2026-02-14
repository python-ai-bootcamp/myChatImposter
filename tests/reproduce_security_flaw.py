import httpx
import asyncio
import sys

BASE_URL = "http://127.0.0.1:8001"

async def reproduce_security_flaw():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        print("\n--- 1. Login as User ---")
        user_id = "test_user_repro"
        password = "User1234!" # Assumed from previous task
        
        # Ensure user exists (admin creation)
        # We assume the user exists from previous run, or we might need to create it.
        # Let's try to login.
        
        try:
            res = await client.post("/api/external/auth/login", json={"user_id": user_id, "password": password})
        except httpx.ConnectError:
            print("Failed to connect.")
            return

        if res.status_code != 200:
            print(f"Login failed: {res.text}. Trying to create user first...")
            # We can't create user as 'user'. We need admin. 
            # Assuming user exists from previous task.
            return

        print(f"Login successful as {user_id}.")
        print(f"Cookies: {client.cookies}")

        print("\n--- 2. Attempt Self-Promotion to Admin ---")
        # The user manually edited local storage to enable the UI.
        # The UI then sends a PUT request with role="admin".
        
        update_data = {
            "role": "admin",
             # Backend might require other fields?
             "first_name": "Hacked",
             "last_name": "Admin"
        }
        
        res = await client.put(f"/api/external/users/{user_id}", json=update_data)
        
        print(f"Update response: {res.status_code}")
        print(f"Response body: {res.text}")
        
        if res.status_code == 200 and "admin" in res.text:
            print("\n!!! SECURITY FLAW CONFIRMED: User successfully promoted themselves to Admin! !!!")
        else:
            print("\nUser failed to promote themselves (Good).")

        print("\n--- 3. Attempt to Overwrite Admin Bot (Bot Takeover) ---")
        # Attempt to PUT to a bot ID we don't own
        bot_id = "admin_bot_takeover" 
        res = await client.put(f"/api/external/bots/{bot_id}", json={"name": "Hacked Bot", "context": "I own you now"})
        
        print(f"Bot PUT response: {res.status_code}")
        if res.status_code == 200:
             print("\n!!! SECURITY FLAW CONFIRMED: User successfully wrote to unowned bot ID! !!!")
        else:
             print(f"Bot PUT blocked: {res.status_code}")

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass
    asyncio.run(reproduce_security_flaw())
