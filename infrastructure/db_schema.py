import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

# --- Collection Constants ---
COLLECTION_CONFIGURATIONS = "configurations"
COLLECTION_QUEUES = "queues"
COLLECTION_BAILEYS_SESSIONS = "baileys_sessions"
COLLECTION_TRACKED_GROUPS = "tracked_groups"
COLLECTION_TRACKED_GROUP_PERIODS = "tracked_group_periods"
COLLECTION_GROUP_TRACKING_STATE = "group_tracking_state"

# Authentication Collections
COLLECTION_SESSIONS = "authenticated_sessions"
COLLECTION_STALE_SESSIONS = "stale_authenticated_sessions"
COLLECTION_CREDENTIALS = "user_auth_credentials"
COLLECTION_AUDIT_LOGS = "audit_logs"
COLLECTION_ACCOUNT_LOCKOUTS = "account_lockouts"

# --- Index Definitions ---

async def create_indexes(db: AsyncIOMotorDatabase):
    """
    Creates all required indexes for the application using Motor (Async).
    This should be called by the Backend on startup.
    Gateway should NOT call this, but rely on Backend to manage schema.
    """
    logger = logging.getLogger("api.schema")
    
    # 1. configurations
    try:
        await db[COLLECTION_CONFIGURATIONS].create_index([("config_data.user_id", ASCENDING)], unique=True)
        logger.info(f"Ensured unique index for '{COLLECTION_CONFIGURATIONS}.config_data.user_id'.")
    except Exception as e:
        logger.warning(f"Could not create index for {COLLECTION_CONFIGURATIONS}: {e}")

    # 2. Authentication Collections
    try:
        # Sessions
        sessions = db[COLLECTION_SESSIONS]
        await sessions.create_index([("session_id", ASCENDING)], unique=True)
        await sessions.create_index([("user_id", ASCENDING)])
        await sessions.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
        logger.info(f"Created indexes for {COLLECTION_SESSIONS}.")

        # Credentials
        creds = db[COLLECTION_CREDENTIALS]
        await creds.create_index([("user_id", ASCENDING)], unique=True)
        logger.info(f"Created indexes for {COLLECTION_CREDENTIALS}.")

        # Audit Logs
        logs = db[COLLECTION_AUDIT_LOGS]
        await logs.create_index([("timestamp", ASCENDING)], expireAfterSeconds=2592000) # 30 days
        await logs.create_index([("user_id", ASCENDING)])
        await logs.create_index([("event_type", ASCENDING)])
        logger.info(f"Created indexes for {COLLECTION_AUDIT_LOGS}.")

        # Account Lockouts
        lockouts = db[COLLECTION_ACCOUNT_LOCKOUTS]
        await lockouts.create_index([("user_id", ASCENDING)], unique=True, sparse=True)
        await lockouts.create_index([("ip_address", ASCENDING)], sparse=True)
        await lockouts.create_index([("locked_until", ASCENDING)], expireAfterSeconds=0, sparse=True)
        logger.info(f"Created indexes for {COLLECTION_ACCOUNT_LOCKOUTS}.")

    except Exception as e:
        logger.warning(f"Could not create authentication indexes: {e}")

    # 3. Features
    try:
        # Tracked Group Periods (Group Tracking)
        periods = db[COLLECTION_TRACKED_GROUP_PERIODS]
        # Common q: user_id + group_id + periodEnd (for sorting)
        await periods.create_index([("user_id", ASCENDING), ("tracked_group_unique_identifier", ASCENDING), ("periodEnd", DESCENDING)])
        logger.info(f"Created indexes for {COLLECTION_TRACKED_GROUP_PERIODS}.")
        
        # Tracking State
        state = db[COLLECTION_GROUP_TRACKING_STATE]
        await state.create_index([("user_id", ASCENDING), ("group_id", ASCENDING)], unique=True)
        logger.info(f"Created indexes for {COLLECTION_GROUP_TRACKING_STATE}.")
        
    except Exception as e:
        logger.warning(f"Could not create feature indexes: {e}")
