"""
Migration Script: Convert Legacy List-Format Configs to Dict-Format
Run this once before removing list-handling code from user_management.py
"""
from pymongo import MongoClient

def migrate():
    client = MongoClient("mongodb://localhost:27017")
    db = client["chat_manager"]
    collection = db["configurations"]

    # Find all list-format documents
    cursor = collection.find({"config_data": {"$type": "array"}})
    migrated = 0
    
    for doc in cursor:
        config_list = doc["config_data"]
        if config_list:
            config_dict = config_list[0]  # Extract first element
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"config_data": config_dict}}
            )
            print(f"Migrated: {config_dict.get('user_id')}")
            migrated += 1

    print(f"\nMigration complete. {migrated} documents migrated.")
    
    # Verify
    remaining = collection.count_documents({"config_data": {"$type": "array"}})
    print(f"Remaining legacy list-format docs: {remaining}")
    
    client.close()

if __name__ == "__main__":
    migrate()
