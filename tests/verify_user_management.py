import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8001"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"  # Assuming this is the password for the admin user

async def verify_user_management():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        print("\n--- 1. Login as Admin ---")
        res = await client.post("/api/external/auth/login", json={"user_id": ADMIN_USER, "password": ADMIN_PASS})
        if res.status_code != 200:
            print(f"Failed to login as admin: {res.text}")
            return
        
        print("Login successful.")
        cookies = res.cookies
        
        print("\n--- 2. Create New User (test_user_1) ---")
        new_user = {
            "user_id": "test_user_1",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone_number": "+1234567890",
            "role": "user",
            "password": "password123",
            "confirm_password": "password123", # Frontend sends this, backend ignores
            "country_value": "US",
            "language": "en"
        }
        
        # Note: Backend expects 'password', frontend sends 'confirm_password' too but backend model ignores extra fields?
        # Let's check backend model. LoginRequest has user_id/password. 
        # CreateUserRequest has specific fields.
        # We need to make sure we match the schema.
        
        res = await client.post("/api/external/users", json=new_user, cookies=cookies)
        if res.status_code == 200:
            print("User created successfully.")
        elif res.status_code == 400 and "already exists" in res.text:
             print("User already exists (expected if re-running).")
        else:
            print(f"Failed to create user: {res.text}")
            
        print("\n--- 3. List Users ---")
        res = await client.get("/api/external/users", cookies=cookies)
        if res.status_code == 200:
            users = res.json()
            print(f"Found {len(users)} users.")
            found = any(u['user_id'] == 'test_user_1' for u in users)
            print(f"Test user found in list: {found}")
        else:
             print(f"Failed to list users: {res.text}")

        print("\n--- 4. Update User ---")
        update_data = {"first_name": "Updated Name"}
        res = await client.put("/api/external/users/test_user_1", json=update_data, cookies=cookies)
        # Wait, PUT replaces the whole resource usually. PATCH is for partial?
        # My backend implementation:
        # @router.put("/{user_id}") -> UpdateUserRequest (all optional?)
        # Let's check router implementation.
        # If I use PUT with partial data, Pydantic might complain if fields are required.
        # implementation_plan says PUT is "Full update". PATCH is "Partial update".
        
        # Let's try PATCH for partial update.
        res = await client.patch("/api/external/users/test_user_1", json=update_data, cookies=cookies)
        if res.status_code == 200:
             print("User updated successfully (PATCH).")
        else:
             print(f"Failed to update user: {res.text}")

        print("\n--- 5. Get User Details ---")
        res = await client.get("/api/external/users/test_user_1", cookies=cookies)
        if res.status_code == 200:
            details = res.json()
            print(f"User Name: {details.get('first_name')}")
            if details.get('first_name') == "Updated Name":
                print("Update verified.")
            else:
                print("Update validation failed.")
        else:
             print(f"Failed to get user: {res.text}")

        print("\n--- 6. Delete User ---")
        res = await client.delete("/api/external/users/test_user_1", cookies=cookies)
        if res.status_code == 200:
             print("User deleted successfully.")
        else:
             print(f"Failed to delete user: {res.text}")
             
        print("\n--- Verification Complete ---")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_user_management())
