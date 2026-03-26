#!/usr/bin/env python3
"""
Migration Script: Backfill User Schema
Adds missing fields to existing user documents in MongoDB.
"""

import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def migrate_users():
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    print(f"Connecting to MongoDB: {mongo_url}")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client["chat_manager"]
    collection = db["user_auth_credentials"]
    
    print("Checking for users needing migration...")
    
    # Define defaults
    defaults = {
        "first_name": "Unknown",
        "last_name": "User",
        "phone_number": "",
        "email": "",
        "gov_id": "",
        "country_value": "US",
        "language": "en"
    }
    
    # Bulk write would be better for massive datasets, but loop is fine here
    cursor = collection.find({})
    count = 0
    updated = 0
    
    async for user in cursor:
        count += 1
        user_id = user.get("user_id")
        updates = {}
        
        for field, default_val in defaults.items():
            if field not in user:
                updates[field] = default_val
                
        if updates:
            await collection.update_one({"_id": user["_id"]}, {"$set": updates})
            print(f"Migrated user: {user_id} -> Added {list(updates.keys())}")
            updated += 1
            
    print(f"\nMigration Complete.")
    print(f"Total Users Scanned: {count}")
    print(f"Users Updated: {updated}")
    
    client.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate_users())
