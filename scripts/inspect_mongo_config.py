
import asyncio
import os
import motor.motor_asyncio
from pprint import pprint

async def inspect_config():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    db = client["chat_manager"]
    collection = db["bot_configurations"]

    print("--- Inspecting Bot Configuration ---")
    doc = await collection.find_one({})
    if doc:
        config_data = doc.get("config_data", {})
        print("KEYS:", config_data.keys())
        if "configurations" in config_data:
            print("CONFIGURATIONS KEYS:", config_data["configurations"].keys())
            if "user_details" in config_data["configurations"]:
                print("USER DETAILS:", config_data["configurations"]["user_details"])
            else:
                 print("user_details NOT FOUND in configurations")
        else:
            print("configurations NOT FOUND in config_data")
            
        pprint(config_data)
    else:
        print("No bot configurations found.")

if __name__ == "__main__":
    asyncio.run(inspect_config())
