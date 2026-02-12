
import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson.binary import Binary
import logging

# Set up simple logging
logging.basicConfig(level=logging.INFO)

# Add project root to path
sys.path.append(os.getcwd())

from features.session_maintenance.service import SessionMaintenanceService

# Mock DB class to avoid full app startup complexity?
# Or just connect to real local mongo for integration test.
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "chat_manager"

async def test_maintenance():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    service = SessionMaintenanceService(db)
    
    user_id = "test_user_maintenance"
    
    # 1. Setup Test Data
    print("Setting up test data...")
    # Corrupted Key (String)
    await db["baileys_sessions"].update_one(
        {"_id": f"{user_id}-sender-key-memory-corrupt@g.us"},
        {"$set": {"value": '{"json": "string"}'}}, # Corrupt: String
        upsert=True
    )
    
    # Corrupt Key (Dict / JSON Object)
    await db["baileys_sessions"].update_one(
        {"_id": f"{user_id}-session-corrupt-session"},
        {"$set": {"value": {"some": "dict"}} }, # Corrupt: Dict
        upsert=True
    )
    
    # Valid Key (Binary)
    await db["baileys_sessions"].update_one(
        {"_id": f"{user_id}-pre-key-1"},
        {"$set": {"value": Binary(b'\x00\x01\x02')}}, # Valid: Binary
        upsert=True
    )
    
    # 2. Run Maintenance
    print("Running maintenance...")
    await service.run_maintenance_job(user_id)
    
    # 3. Verify Results
    print("Verifying results...")
    
    doc_str = await db["baileys_sessions"].find_one({"_id": f"{user_id}-sender-key-memory-corrupt@g.us"})
    if doc_str:
        print("[FAIL] Corrupted String Key was NOT deleted.")
    else:
        print("[PASS] Corrupted String Key was deleted.")

    doc_dict = await db["baileys_sessions"].find_one({"_id": f"{user_id}-session-corrupt-session"})
    if doc_dict:
        print("[FAIL] Corrupted Dict Key was NOT deleted.")
    else:
        print("[PASS] Corrupted Dict Key was deleted.")
        
    doc_bin = await db["baileys_sessions"].find_one({"_id": f"{user_id}-pre-key-1"})
    if doc_bin:
        print("[PASS] Valid Binary Key was PRESERVED.")
    else:
        print("[FAIL] Valid Binary Key was DELETED incorrectly.")

    # Cleanup
    await db["baileys_sessions"].delete_many({"_id": {"$regex": f"^{user_id}-"}})

if __name__ == "__main__":
    asyncio.run(test_maintenance())
