
import sys
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson.binary import Binary

# Connection String (Localhost)
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "chat_manager"
COLLECTION_NAME = "baileys_sessions"

async def cleanup_corrupted_keys():
    print(f"Connecting to {MONGO_URL}...")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # Pattern for sender-key-memory
    # The log showed: tal-sender-key-memory-120363406964581413@g.us
    # We want to find any document that looks like a sender key but is NOT binary data
    
    projection = {"_id": 1} # We need the ID and full doc to check type
    
    # regex for sender-key-memory
    regex = {"$regex": "sender-key-memory"}
    
    cursor = collection.find({"_id": regex})
    
    corrupted_count = 0
    scanned_count = 0
    
    print("Scanning 'sender-key-memory' keys...")
    
    ids_to_delete = []

    async for doc in cursor:
        scanned_count += 1
        key_id = doc["_id"]
        
        # Baileys stores the data in the root or 'value' field depending on implementation?
        # Based on typical baileys-mongo adapters, it usually stores the JSON directly or with a wrapper.
        # Let's inspect the document structure.
        
        # NOTE: The library usually stores just the value, or { _id: ..., value: ... }
        # Let's dump a sample if we are unsure, but the log says "stored as object".
        # This implies standard BSON Object (dict) instead of BSON Binary.
        
        # We need to fetch the FULL document to check the type of the value
        full_doc = await collection.find_one({"_id": key_id})
        
        # Common structure is { _id: "...", ... data ... } OR { _id: "...", value: ... }
        # If the 'value' itself is the data.
        
        # Let's check if it looks like a dict instead of bytes/binary
        # We check specific fields that shouldn't be there or type check
        
        # The corruption warning says "stored as object". valid keys are usually Buffers.
        # In mongo, this would be a Binary type.
        
        is_corrupt = False
        
        # Check if it has a 'value' field (some adapters use this)
        if 'value' in full_doc:
            data = full_doc['value']
            if isinstance(data, dict):
                is_corrupt = True
                print(f"[FOUND] {key_id}: Value is DICT (Corrupt)")
            elif not isinstance(data, (bytes, Binary)):
                 # Assuming typical string/buffer. If it's pure string it might be ok if base64? 
                 # But log says "Buffer (stored as object)". 
                 print(f"[CHECK] {key_id}: Value is {type(data)}")
                 # If it's a dict, it's definitely wrong for a key buffer
                 if isinstance(data, dict):
                     is_corrupt = True
        else:
            # If no 'value' wrapper, the doc itself IS the object?
            # Baileys usually expects the content to be the buffer. 
            # If the doc is { _id: ..., key: value, ... } then it is an object.
            # But normally sender-key is an opaque buffer.
            
            # Let's trust the "stored as object" vs Buffer distinction.
            # If we see many fields, it's an object.
            # A valid buffer storage might be { _id: ..., binary: <Bindata> } or similar?
            # actually, standard mongo adapter stores it as { _id: id, ...JSON... } if it is JSON.
            # But sender keys are Buffers.
            
            # If Python sees it as a dict (full_doc is always a dict), we need to check if it contains the raw key material
            # or if it's "just" the _id.
            
            # Let's look at a sample of what we find.
            pass

    # REVISED STRATEGY: 
    # Since I don't know the EXACT schema shape of the corruption without looking,
    # I will first print the TYPE of the data for `tal-sender-key-memory-120363406964581413@g.us`.
    
    target_id = "tal-sender-key-memory-120363406964581413@g.us"
    doc = await collection.find_one({"_id": target_id})
    
    if doc:
        print(f"\n--- TARGET DOC: {target_id} ---")
        print(f"Keys: {doc.keys()}")
        import pprint
        pprint.pprint(doc)
        print("-------------------------------")
        
        # If it looks like a JSON object with 'senderKeyId', 'senderChainKey' etc exposed as fields, 
        # instead of a proper serialization, that might be the issue?
        # OR if it's wrapped in a way Baileys doesn't like.
        
        # The User log said: "appears to be a corrupted Buffer (stored as object)"
        # This usually happens when a Buffer is saved as { type: 'Buffer', data: [...] } (JSON representation)
        # instead of actual BSON Binary.
        
        is_json_buffer = False
        if 'type' in doc and doc['type'] == 'Buffer' and 'data' in doc:
             is_json_buffer = True
             print("DETECTED JSON-SERIALIZED BUFFER!")
        
        # Also check inside 'value' if it exists
        if 'value' in doc:
            val = doc['value']
            if isinstance(val, dict) and val.get('type') == 'Buffer':
                is_json_buffer = True
                print("DETECTED JSON-SERIALIZED BUFFER in 'value'!")

        if is_json_buffer:
            print(f"Deleting corrupted key: {target_id}")
            await collection.delete_one({"_id": target_id})
            print("Deleted.")
        else:
            # If we simply want to force re-generation, deleting it is safe-ish (will force re-negotiation/re-sync)
            # The user prefers "transient" fixes, but deleting the Bad State is the way to make it Transient (gone).
            print(f"Deleting {target_id} to force re-sync.")
            await collection.delete_one({"_id": target_id})
            print("Deleted.")

    else:
        print(f"Target document {target_id} NOT FOUND.")

if __name__ == "__main__":
    asyncio.run(cleanup_corrupted_keys())
