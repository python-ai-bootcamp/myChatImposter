import asyncio
import httpx
import sys

BASE_URL = "http://127.0.0.1:8001"
ADMIN_USER = "admin"
ADMIN_PASS = "Admin1234!"

async def reproduce_issue():
    # Use a persistent client with a cookie jar
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        print(f"\n--- 1. Login as Admin at {BASE_URL} ---")
        try:
            res = await client.post("/api/external/auth/login", json={"user_id": ADMIN_USER, "password": ADMIN_PASS})
        except httpx.ConnectError as e:
            print(f"Failed to connect: {e}")
            return
            
        if res.status_code != 200:
            print(f"Failed to login as admin: {res.text}")
            return
        
        print(f"Login successful. Status: {res.status_code}")
        print(f"Cookies received: {res.cookies}")
        
        # httpx client stores cookies automatically in client.cookies if we use the same client
        # BUT we must make sure we are not creating a new client or losing context.
        # We are inside the with block, so it should be fine.
        
        print("\n--- 2. Ensure Test User Exists ---")
        user_id = "test_user_repro"
        
        # Test if auth works
        res = await client.get("/api/external/auth/validate")
        print(f"Auth check: {res.status_code} {res.text}")
        if res.status_code != 200:
             print("Auth check failed. Cookies in client:")
             print(client.cookies)

        res = await client.get(f"/api/external/users/{user_id}")
        if res.status_code == 404:
            print(f"Creating user {user_id}...")
            new_user = {
                "user_id": user_id,
                "first_name": "Test",
                "last_name": "Repro",
                "role": "user",
                "password": "User1234!",
                "country_value": "US",
                "language": "en"
            }
            res = await client.post("/api/external/users", json=new_user)
            if res.status_code != 201 and res.status_code != 200:
                 print(f"Failed to create user: {res.text}")
                 return
            print("User created.")
        elif res.status_code == 200:
             print("User already exists.")
        else:
             print(f"Failed to check user: {res.text}")
             return

        print("\n--- 3. Update User Role (Trigger 500) ---")
        # Trying to update role to 'admin' or toggle it
        # We need to make sure we change the role to trigger invalidation logic
        
        # Get current role
        res = await client.get(f"/api/external/users/{user_id}")
        current_role = res.json().get("role")
        new_role = "admin" if current_role == "user" else "user"
        
        print(f"Switching role from {current_role} to {new_role}")
        
        update_data = {"role": new_role}
        res = await client.put(f"/api/external/users/{user_id}", json=update_data)
        
        if res.status_code == 200:
             print("SUCCESS: User updated successfully. Issue NOT reproduced.")
        elif res.status_code == 500:
             print("FAILURE: Verified 500 Internal Server Error. Issue reproduced.")
        else:
             print(f"Unexpected status code: {res.status_code}")
             print(f"Response: {res.text}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reproduce_issue())
