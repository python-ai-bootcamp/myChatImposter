import requests
import json
import time

BASE_URL = "http://localhost:8001/api/external"
ADMIN_ID = "admin_user"
ADMIN_PASS = "admin123"

def get_admin_session():
    # Bootstrap Admin User directly in DB to ensure it exists
    import subprocess
    # Password hash for 'admin123' (bcrypt) - generic hash
    # actually, let's just use a known hash or let the auth service handle it?
    # Auth service uses bcrypt. I can't generate a hash easily without bcrypt lib.
    # BUT, I can use the existing 'admin' if it exists.
    # If I can't generate a hash, I should try to use the 'setup' endpoint if one exists?
    # No setup endpoint.
    
    # Alternative: Use python to generate hash if bcrypt is installed.
    # If not, I can't insert a valid user.
    
    # Wait! The dev environment usually has an admin. 
    # Maybe I should try the default credentials from `mongo-init.js` if functionality exists?
    # Or just `admin` / `admin`.
    
    # Let's try `admin` / `admin` first?
    # Or, let's look at `services/user_auth_service.py` to see how verify_password works.
    # It uses passlib.hash.bcrypt.
    
    # I'll try to use a pre-calculated hash for 'admin123'.
    # $2b$12$EixZaYVK1fsbw1ZfbX3OXePaW/N/gA3z.9X9B.M0x6y... (example)
    
    # Let's assume 'admin_user' doesn't exist.
    # I can try to find an existing user in the DB via docker exec and use that?
    # `db.credentials.findOne({})`
    
    # Always bootstrap admin user to ensure known state
    
    # I'll use python inside the GATEWAY container to generate the hash using the SAME library (bcrypt).
    # Verification happens in Gateway, so hash should be generated there to be safe.
    
    cmd_hash = [
        "docker", "exec", "gateway", "python", "-c", 
        "import bcrypt; print(bcrypt.hashpw(b'admin123', bcrypt.gensalt(12)).decode('utf-8'))"
    ]
    res_hash = subprocess.run(cmd_hash, capture_output=True, text=True)
    if res_hash.returncode != 0:
            print(f"[ERROR] Hashing failed: {res_hash.stderr}")
            exit(1)
            
    password_hash = res_hash.stdout.strip()
    print(f"[DEBUG] Generated Hash: {password_hash}")
    
    if not password_hash:
            print("[ERROR] Generated hash is empty.")
            exit(1)
            
    # Insert/Update admin_user
    update_js = f"""
    print(JSON.stringify(db.user_auth_credentials.updateOne(
        {{ user_id: '{ADMIN_ID}' }},
        {{ $set: {{ 
            password_hash: '{password_hash}',
            role: 'admin',
            first_name: 'Admin',
            last_name: 'User',
            email: 'admin@example.com',
            phone_number: '+1234567890',
            gov_id: 'ADMIN123',
            country_value: 'US',
            language: 'en'
        }} }},
        {{ upsert: true }}
    )));
    """
    cmd_update = [
        "docker", "exec", "mongodb", "mongosh", "chat_manager", "--quiet", "--eval", update_js
    ]
    res_update = subprocess.run(cmd_update, capture_output=True, text=True)
    print(f"[DEBUG] Update Result: {res_update.stdout.strip()}")
    if res_update.returncode != 0:
        print(f"[ERROR] Update failed: {res_update.stderr}")

    s = requests.Session()
    # Login to get token/session
    login_data = {"user_id": ADMIN_ID, "password": ADMIN_PASS}
    # Gateway login endpoint
    resp = s.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if resp.status_code != 200 or not resp.json().get("success"):
        print(f"Login failed: {resp.text}")
        exit(1)
        
    return s

def run_tests():
    s = get_admin_session()
    
    # 1. Create a valid user
    test_user_id = f"test_valid_{int(time.time())}"
    print(f"\n[TEST] Creating User {test_user_id}...")
    user_data = {
        "user_id": test_user_id,
        "password": "TestPass123!",
        "role": "user",
        "first_name": "Test",
        "last_name": "User",
        "email": f"{test_user_id}@example.com",
        "phone_number": "+15550001111",
        "gov_id": "ID12345",
        "country_value": "US",
        "language": "en"
    }
    resp = s.post(f"{BASE_URL}/users", json=user_data)
    if resp.status_code != 201:
        print(f"Failed to create user: {resp.text}")
        return

    print("User created successfully.")

    # 2. Corrupt the user in DB (Simulate Legacy Data)
    print("[SETUP] Corrupting user data (clearing first_name) via Docker...")
    import subprocess
    cmd = [
        "docker", "exec", "mongodb", "mongosh", "chat_manager", "--eval",
        f"db.user_auth_credentials.updateOne({{user_id: '{test_user_id}'}}, {{$set: {{first_name: ''}}}})"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to corrupt data: {result.stderr}")
        return
    print("User data corrupted.")

    # 3. Attempt PATCH with VALID field (e.g. phone), but INVALID merged state
    print("[TEST] PATCH phone_number (valid) on corrupted user (empty name)...")
    patch_data = {"phone_number": "+15550002222"}
    resp = s.patch(f"{BASE_URL}/users/{test_user_id}", json=patch_data)
    
    if resp.status_code == 422:
        print("PASS: Request rejected as expected (Validation failed on merged state).")
        print(f"Response: {resp.text}")
    else:
        print(f"FAIL: Request unexpectedly succeeded or failed with wrong code: {resp.status_code}")
        print(resp.text)

    # 4. Attempt PATCH to FIX the invalid field
    print("[TEST] PATCH first_name (fix) on corrupted user...")
    patch_data_fix = {"first_name": "FixedName"}
    resp = s.patch(f"{BASE_URL}/users/{test_user_id}", json=patch_data_fix)
    
    if resp.status_code == 200:
        print("PASS: Fix applied successfully.")
    else:
        print(f"FAIL: Fix failed: {resp.status_code}")
        print(resp.text)

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"Error: {e}")
