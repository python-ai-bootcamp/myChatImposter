"""Quick diagnostic script to check config structure in MongoDB"""
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["chat_manager"]

# Check if 'tal' is findable with different query patterns
doc1 = db.configurations.find_one({"config_data.user_id": "tal"})
print(f"Found with config_data.user_id: {doc1 is not None}")

doc2 = db.configurations.find_one({"config_data.0.user_id": "tal"})
print(f"Found with config_data.0.user_id: {doc2 is not None}")

# List all configs
all_docs = list(db.configurations.find({}))
print(f"\nTotal docs: {len(all_docs)}")
for d in all_docs:
    config_data = d.get("config_data")
    config_type = type(config_data).__name__
    if isinstance(config_data, dict):
        user_id = config_data.get("user_id", "NO_USER_ID")
    elif isinstance(config_data, list) and config_data:
        user_id = config_data[0].get("user_id", "NO_USER_ID")
    else:
        user_id = "UNKNOWN"
    print(f"  - {user_id} (type: {config_type})")

client.close()
