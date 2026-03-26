
import asyncio
import sys
import os
import requests

# Adjust path to include project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

def create_user(user_id_header, user_data):
    url = f"{BASE_URL}/api/internal/users"
    headers = {"X-User-Id": user_id_header}
    response = requests.post(url, json=user_data, headers=headers)
    return response

def update_user_patch(user_id_header, user_id, update_data):
    url = f"{BASE_URL}/api/internal/users/{user_id}"
    headers = {"X-User-Id": user_id_header}
    response = requests.patch(url, json=update_data, headers=headers)
    return response

def run_tests():
    print("--- Starting Backend Validation Verification ---")
    
    # 1. Create Admin directly (if needed) to ensure user 'admin' exists for the header lookup
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    from services.user_auth_service import UserAuthService
    
    async def ensure_admin():
        mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        print(f"Connecting to MongoDB at {mongo_url}")
        client = AsyncIOMotorClient(mongo_url)
        db = client["chat_manager"]
        creds = db["user_auth_credentials"]
        
        existing = await creds.find_one({"user_id": ADMIN_USER})
        if not existing:
             print(f"Creating admin user '{ADMIN_USER}' directly in DB...")
             service = UserAuthService(creds)
             # Hash password manually or use service helper if available? 
             # Service has create_credentials which hashes.
             await service.create_credentials(
                 user_id=ADMIN_USER,
                 password=ADMIN_PASS,
                 role="admin",
                 first_name="Admin",
                 last_name="Super",
                 email="admin@example.com",
                 phone_number="+1234567890",
                 gov_id="ADMIN1",
                 country_value="US",
                 language="en"
             )
        client.close()

    # Run the async setup
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ensure_admin())
    loop.close()

    admin_header = ADMIN_USER

    # 2. Test Invalid Country (should be 2 chars uppercase)
    print("\n[TEST] Invalid Country (USA)")
    bad_user = {
        "user_id": "test_bad_country",
        "password": "Password1!",
        "role": "user",
        "first_name": "Bad",
        "last_name": "Country",
        "email": "badcountry@example.com",
        "phone_number": "+1234567890",
        "gov_id": "123",
        "country_value": "USA", # Invalid
        "language": "en"
    }
    res = create_user(admin_header, bad_user)
    if res.status_code == 422:
        print("PASS: Rejected invalid country.")
    else:
        print(f"FAIL: Accepted invalid country? Status: {res.status_code} {res.text}")

    # 3. Test Invalid Language (should be 2 chars lowercase)
    print("\n[TEST] Invalid Language (ENG)")
    bad_user["country_value"] = "US" # Fix country
    bad_user["user_id"] = "test_bad_lang"
    bad_user["language"] = "ENG" # Invalid
    res = create_user(admin_header, bad_user)
    if res.status_code == 422:
        print("PASS: Rejected invalid language.")
    else:
         print(f"FAIL: Accepted invalid language? Status: {res.status_code} {res.text}")

    # 4. Test Invalid Phone (Must start with +)
    print("\n[TEST] Invalid Phone (No +)")
    bad_user["language"] = "en" # Fix lang
    bad_user["user_id"] = "test_bad_phone"
    bad_user["phone_number"] = "1234567890" # Invalid
    res = create_user(admin_header, bad_user)
    if res.status_code == 422:
        print("PASS: Rejected invalid phone.")
    else:
         print(f"FAIL: Accepted invalid phone? Status: {res.status_code} {res.text}")

    # 5. Create Valid Users for Duplicate Email Test
    print("\n[TEST] Duplicate Email on Update")
    user1 = {
        "user_id": "user_email_1",
        "password": "Password1!",
        "role": "user",
        "first_name": "User",
        "last_name": "One",
        "email": "unique1@example.com",
        "phone_number": "+1234567890",
        "gov_id": "111",
        "country_value": "US",
        "language": "en"
    }
    user2 = {
        "user_id": "user_email_2",
        "password": "Password1!",
        "role": "user",
        "first_name": "User",
        "last_name": "Two",
        "email": "unique2@example.com",
        "phone_number": "+1234567890",
        "gov_id": "222",
        "country_value": "US",
        "language": "en"
    }
    
    # Clean up first if they exist (optional, but good practice)
    # login as admin -> delete? For now just try create, ignore 400
    create_user(admin_header, user1)
    create_user(admin_header, user2)

    # Imitate User 2 via header
    user2_header = "user_email_2"
    
    # Try to update email to user1's email
    res = update_user_patch(user2_header, "user_email_2", {"email": "unique1@example.com"})
    if res.status_code == 400 and "in use" in res.text:
         print("PASS: Rejected duplicate email update.")
    else:
         print(f"FAIL: Allowed duplicate email? Status: {res.status_code} {res.text}")

    # 6. Test Role Escalation (User trying to become Admin)
    print("\n[TEST] User Privilege Escalation Check")
    # Try to update role to admin as user_email_2
    res = update_user_patch(user2_header, "user_email_2", {"role": "admin"})
    if res.status_code == 200:
        # Check if role actually changed
        # Need a get_user function or just trust the logic? 
        # Let's try to get user details AS ADMIN to see the role
        get_url = f"{BASE_URL}/api/internal/users/user_email_2"
        # Accessing as Admin
        headers_admin_check = {"X-User-Id": ADMIN_USER, "X-User-Role": "admin"}
        get_res = requests.get(get_url, headers=headers_admin_check)
        if get_res.status_code == 200:
            user_data = get_res.json()
            if user_data.get("role") == "user":
                print("PASS: Role remained 'user' after attempted escalation.")
            else:
                 print(f"FAIL: Role changed to {user_data.get('role')}!")
        else:
             print(f"WARN: Could not fetch user profile to verify role. Status: {get_res.status_code}")
    else:
         print(f"PASS: Update rejected (Optional behavior, currently silent ignore preferred but error is fine). Status: {res.status_code}")

    # 7. Test Restricted Response check
    print("\n[TEST] Restricted Response Privacy Check")
    # Admin fetching User 2 (Should retrieve Role)
    url_user2 = f"{BASE_URL}/api/internal/users/user_email_2"
    headers_admin = {"X-User-Id": ADMIN_USER, "X-User-Role": "admin"}
    res_as_admin = requests.get(url_user2, headers=headers_admin)
    if res_as_admin.status_code == 200:
        data = res_as_admin.json()
        if "role" in data:
            print("PASS: Admin can see 'role'.")
        else:
            print("FAIL: Admin CANNOT see 'role'.")
    else:
        print(f"FAIL: Admin fetch failed. {res_as_admin.status_code}")

    # User 2 fetching Self (Should NOT retrieve Role)
    headers_user = {"X-User-Id": "user_email_2", "X-User-Role": "user"}
    res_as_user = requests.get(url_user2, headers=headers_user)
    if res_as_user.status_code == 200:
        data = res_as_user.json()
        if "role" not in data:
            print("PASS: User CANNOT see 'role' (Restricted Model Applied).")
        else:
            print(f"FAIL: User CAN see 'role'! Leaked info.")
    else:
        print(f"FAIL: User fetch failed. {res_as_user.status_code}")

    # 8. Test Empty Name Validation
    print("\n[TEST] Empty Name Validation")
    empty_name_payload = {"first_name": ""}
    res = requests.patch(url_user2, json=empty_name_payload, headers=headers_user)
    if res.status_code == 422:
        print("PASS: Rejected empty first_name.")
    else:
        print(f"FAIL: Accepted empty first_name! Status: {res.status_code}")

if __name__ == "__main__":
    run_tests()
