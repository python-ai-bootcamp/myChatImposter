
import asyncio
import os
import motor.motor_asyncio
import logging

# Config
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = "chat_manager"

async def inspect_creds():
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    collection = db["user_auth_credentials"]

    print("--- Inspecting Tal ---")
    doc = await collection.find_one({"user_id": "tal"})
    if doc:
        print(f"User: tal, Hash: {doc.get('password_hash')}")
    else:
        print("Tal not found.")




if __name__ == "__main__":
    asyncio.run(inspect_creds())
