import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Configuration
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = "chat_manager"

async def debug_lockouts():
    print(f"Connecting to {MONGO_URL}, DB: {DB_NAME}...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    print("Listing collections:")
    cols = await db.list_collection_names()
    print(cols)

    print("\nListing Admin User:")
    admin = await db.credentials.find_one({"user_id": "admin"})
    if admin:
        print(f"Admin found: role={admin.get('role')}")

    print("\nListing Test User:")
    test = await db.credentials.find_one({"user_id": "test_security_user"})
    if test:
        print(f"Test User found: role={test.get('role')}")

    print("\nListing lockouts in 'account_lockouts':")
    cursor = db.account_lockouts.find({})
    async for doc in cursor:
        print(doc)
    
    print("\nDeleting ALL lockouts...")
    await db.account_lockouts.delete_many({})
    print("All lockouts deleted.")

if __name__ == "__main__":
    if os.name == 'nt':
         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(debug_lockouts())
