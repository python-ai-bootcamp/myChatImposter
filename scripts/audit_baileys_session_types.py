
import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson.binary import Binary

# Connection String (Localhost)
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "chat_manager"
COLLECTION_NAME = "baileys_sessions"

async def audit_session_keys():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Find all docs for user 'tal'
    # The IDs start with 'tal-'
    cursor = collection.find({"_id": {"$regex": "^tal-"}})
    
    print(f"Scanning keys for 'tal'...")
    
    counts = {}
    corruptions = []

    async for doc in cursor:
        key_type = "unknown"
        key_id = doc["_id"]
        
        # Classify key category
        if "sender-key-memory" in key_id:
            cat = "sender-key-memory"
        elif "session-" in key_id:
            cat = "session"
        elif "app-state-sync-" in key_id:
            cat = "app-state-sync"
        elif "pre-key-" in key_id:
            cat = "pre-key"
        else:
            cat = "other"
            
        # Check value type
        val = doc.get('value')
        val_type = type(val)
        
        # Track stats
        if cat not in counts: counts[cat] = {}
        if str(val_type) not in counts[cat]: counts[cat][str(val_type)] = 0
        counts[cat][str(val_type)] += 1
        
        # Check for corruption (String or Dict where Binary expected)
        # Pre-keys are usually Buffers.
        # Sessions are usually Buffers (Protobuf).
        # Sender Keys are Buffers.
        # Creds (tal-creds) is JSON (dict).
        
        if cat in ["sender-key-memory", "session", "app-state-sync", "pre-key"]:
            if isinstance(val, (str, dict)):
                corruptions.append({"id": key_id, "type": str(val_type), "val_preview": str(val)[:50]})

    print("\n--- Summary Check ---")
    import pprint
    pprint.pprint(counts)
    
    print("\n--- Potential Corruptions ---")
    if corruptions:
        for c in corruptions:
            print(f"[CORRUPT?] {c['id']} => {c['type']} : {c['val_preview']}")
            
        print(f"\nFound {len(corruptions)} potential corruptions.")
    else:
        print("No obvious corruptions found (all expected keys are not strings/dicts).")

if __name__ == "__main__":
    asyncio.run(audit_session_keys())
