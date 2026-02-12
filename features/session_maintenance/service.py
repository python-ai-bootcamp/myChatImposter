import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

logger = logging.getLogger(__name__)

class SessionMaintenanceService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = self.db["baileys_sessions"]

    async def run_maintenance_job(self, user_id: str):
        """
        Scans for and deletes corrupted session keys for a specific user.
        """
        logger.info(f"SESSION_MAINTENANCE: Starting cleanup for user {user_id}")
        
        # Define key patterns to check
        # These keys should ALWAYS be Binary buffers. If they are String/Dict, they are corrupt.
        target_prefixes = [
            f"{user_id}-sender-key-memory-",
            f"{user_id}-session-",
            f"{user_id}-app-state-sync-",
            f"{user_id}-pre-key-"
        ]
        
        # We also check for keys that utilize the user_id as a prefix but might not match exactly the above generic patterns 
        # but fall relatively into the same bucket.
        # Actually, simpler to regex scan all keys for the user and check types for known "Buffer-only" categories.
        
        cursor = self.collection.find({"_id": {"$regex": f"^{user_id}-"}})
        
        ids_to_delete = []
        scanned_count = 0
        
        async for doc in cursor:
            scanned_count += 1
            key_id = doc["_id"]
            val = doc.get('value')
            
            # Skip valid JSON types (like creds)
            if f"{user_id}-creds" in key_id:
                continue
                
            # Check for corruption: Value is String or Dict (when it should be Buffer/Binary)
            # Valid keys in Mongo for Baileys are stored as BinData.
            # Corrupted ones appeared as String (JSON string) or Dict (JSON object).
            if isinstance(val, (str, dict)):
                # Double check specific categories to be safe
                if any(x in key_id for x in ["sender-key-memory", "session-", "app-state-sync", "pre-key"]):
                    # logging.debug(f"SESSION_MAINTENANCE: Found potential corruption: {key_id} type={type(val)}")
                    ids_to_delete.append(key_id)

        if ids_to_delete:
            logger.warning(f"SESSION_MAINTENANCE: Found {len(ids_to_delete)} corrupted keys for {user_id}. Deleting...")
            result = await self.collection.delete_many({"_id": {"$in": ids_to_delete}})
            logger.info(f"SESSION_MAINTENANCE: Cleanup complete. Deleted {result.deleted_count} corrupted keys.")
        else:
            logger.info(f"SESSION_MAINTENANCE: No corrupted keys found for {user_id} (Scanned {scanned_count} items).")

    async def run_global_maintenance(self):
        """
        Iterates over all users with sessions and runs maintenance.
        """
        # Find all unique user IDs from credentials or sessions?
        # Better to query valid users from user_auth or just look at unique prefixes in sessions.
        # For safety/simplicity, let's look at authenticated_sessions or user_auth_credentials if available.
        # Or we can just deduce users from the session keys themselves (regex distinct).
        
        # However, to avoid heavy aggregation, let's rely on the concept that we know active users.
        # If we don't have a list of active users readily available here without circular deps,
        # we can do a regex distinct on the _id prefix.
        
        # Efficient approach: Use the "creds" keys to find users.
        # Every valid user has a 'userid-creds' entry.
        
        logger.info("SESSION_MAINTENANCE: Starting global maintenance run.")
        
        try:
            creds_cursor = self.collection.find({"_id": {"$regex": "-creds$"}})
            
            async for doc in creds_cursor:
                # doc['_id'] is like "tal-creds"
                user_id = doc["_id"].replace("-creds", "")
                if user_id:
                    await self.run_maintenance_job(user_id)
                    
        except Exception as e:
            logger.error(f"SESSION_MAINTENANCE: Global maintenance failed: {e}")
