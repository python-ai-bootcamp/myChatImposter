
import asyncio
import os
import sys
import argparse
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient

async def reset_password(user_id, new_password):
    # Connect
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "chat_manager")
    
    print(f"Connecting to MongoDB: {mongo_url} (DB: {db_name})")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    collection = db["user_auth_credentials"]
    
    # Check user
    user = await collection.find_one({"user_id": user_id})
    if not user:
        print(f"Error: User '{user_id}' not found in database '{db_name}'.")
        client.close()
        return

    # Hash
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    
    # Update
    result = await collection.update_one(
        {"user_id": user_id},
        {"$set": {"password_hash": hashed}}
    )
    
    if result.modified_count > 0:
        print(f"Success: Password for '{user_id}' has been reset.")
    else:
        print(f"Warning: Password for '{user_id}' was not changed (maybe it was the same?).")

    client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset user password.")
    parser.add_argument("user_id", help="User ID to reset")
    parser.add_argument("password", help="New password")
    
    args = parser.parse_args()
    
    # Windows loop policy fix
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            pass
        
    asyncio.run(reset_password(args.user_id, args.password))
