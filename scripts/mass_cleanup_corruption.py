
import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson.binary import Binary

# Connection String (Localhost)
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "chat_manager"
COLLECTION_NAME = "baileys_sessions"

async def mass_cleanup():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Find all docs for user 'tal'
    cursor = collection.find({"_id": {"$regex": "^tal-"}})
    
    print(f"Scanning keys for 'tal'...")
    
    ids_to_delete = []

    async for doc in cursor:
        key_id = doc["_id"]
        val = doc.get('value')
        
        # Check for corruption: Value is String or Dict (when it should be Buffer for these types)
        # Note: 'creds' is usually a dict, but 'session-', 'pre-key-', 'feature-', 'app-state-' are Buffers.
        # Actually 'tal-creds' is likely fine as JSON.
        
        # We will be aggressive but exclude 'creds' if it looks like checking
        if "creds" in key_id:
             # Creds are usually JSON. Let's inspect type.
             # If it's a dict, it's fine. If it's a string, maybe fine if JSON?
             continue

        # For everything else (sessions, keys, state), Baileys uses Buffer.
        # If it is stored as 'str' or 'dict' (JSON representation of buffer), it is the corruption we saw.
        if isinstance(val, (str, dict)):
            # Double check it's not a valid dict structure for some keys?
            # The log explicitly said "corrupted Buffer (stored as object)".
            # All the examples in audit were <class 'str'>.
            ids_to_delete.append(key_id)

    print(f"Found {len(ids_to_delete)} corrupted keys to delete.")
    
    if ids_to_delete:
        result = await collection.delete_many({"_id": {"$in": ids_to_delete}})
        print(f"Deleted {result.deleted_count} documents.")
        print("Run complete.")
    else:
        print("No corruption found.")

if __name__ == "__main__":
    asyncio.run(mass_cleanup())
