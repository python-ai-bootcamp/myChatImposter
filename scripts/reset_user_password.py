
import asyncio
import os
import sys
import argparse
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient

async def reset_password(user_id, new_password):
    # Connect
    mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    
    print(f"Connecting to MongoDB: {mongo_url}")
    
    client = AsyncIOMotorClient(mongo_url)
    db = client["chat_manager"]
    collection = db["user_auth_credentials"]
    
    # Initialize Service
    # Note: UserAuthService expects collection
    from services.user_auth_service import UserAuthService
    auth_service = UserAuthService(collection)
    
    # Update
    try:
        success, message = await auth_service.update_password(user_id, new_password)
        
        if success:
            print(f"Success: {message}")
        else:
            print(f"Error: {message}")
            if "not found" in message:
                 print(f"User '{user_id}' does not exist.")
                 
    except Exception as e:
        print(f"Error during update: {e}")

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
