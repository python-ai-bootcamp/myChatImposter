import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from motor.motor_asyncio import AsyncIOMotorClient
from services.user_auth_service import UserAuthService
from infrastructure import db_schema

# Configuration
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = "chat_manager"
ADMIN_USER = "admin"
ADMIN_PASS = "Admin1234!"

async def reset_admin():
    print(f"Connecting to {MONGO_URL}...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Initialize Service
    auth_service = UserAuthService(db[db_schema.COLLECTION_CREDENTIALS])
    
    # Create/Update Admin
    print(f"Creating/Updating admin user '{ADMIN_USER}'...")
    
    # Check if exists
    existing = await auth_service.get_credentials(ADMIN_USER)
    
    if existing:
        print("Admin exists. Updating password...")
        success, msg = await auth_service.update_password(ADMIN_USER, ADMIN_PASS)
        # Ensure role is admin
        await db[db_schema.COLLECTION_CREDENTIALS].update_one(
             {"user_id": ADMIN_USER}, 
             {"$set": {"role": "admin"}}
        )
    else:
        print("Creating new admin...")
        success, msg = await auth_service.create_credentials(
            user_id=ADMIN_USER,
            password=ADMIN_PASS,
            role="admin",
            first_name="Admin",
            last_name="User"
        )
        
    print(f"Admin Update Result: {success} - {msg}")
    
    # Create Test User as well
    TEST_USER = "test_security_user"
    TEST_PASS = "User1234!"
    print(f"Creating/Updating test user '{TEST_USER}'...")
    
    existing_test = await auth_service.get_credentials(TEST_USER)
    if existing_test:
        print("Test user exists. Updating password...")
        await auth_service.update_password(TEST_USER, TEST_PASS)
        # Ensure role is user
        await db[db_schema.COLLECTION_CREDENTIALS].update_one(
             {"user_id": TEST_USER}, 
             {"$set": {"role": "user"}}
        )
    else:
        print("Creating new test user...")
        await auth_service.create_credentials(
            user_id=TEST_USER,
            password=TEST_PASS,
            role="user"
        )
    
    
    # ---------------------------------------------------------
    # Legacy code removed. Auth Service alrady handled updates.
    # ---------------------------------------------------------
        
    # Clear lockouts
    print("Clearing lockouts...")
    await db.account_lockouts.delete_many({"user_id": {"$in": [ADMIN_USER, "test_security_user"]}})
        
    print("Admin password reset and lockouts cleared.")

if __name__ == "__main__":
    if os.name == 'nt':
         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_admin())
