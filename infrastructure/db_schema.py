import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

# --- Collection Constants ---
COLLECTION_GLOBAL_CONFIGURATIONS = "configurations" # Repurposed for global settings (e.g. token_menu)
COLLECTION_BOT_CONFIGURATIONS = "bot_configurations" # New collection name
COLLECTION_QUEUES = "queues"
COLLECTION_BAILEYS_SESSIONS = "baileys_sessions"
COLLECTION_TRACKED_GROUPS = "tracked_groups"
COLLECTION_TRACKED_GROUP_PERIODS = "tracked_group_periods"
COLLECTION_GROUP_TRIALS = "group_trials"
COLLECTION_TOKEN_CONSUMPTION = "token_consumption_events"
COLLECTION_GROUP_TRACKING_STATE = "group_tracking_state"

# Authentication Collections
COLLECTION_SESSIONS = "authenticated_sessions"
COLLECTION_STALE_SESSIONS = "stale_authenticated_sessions"
COLLECTION_CREDENTIALS = "user_auth_credentials"
COLLECTION_AUDIT_LOGS = "audit_logs"
COLLECTION_ACCOUNT_LOCKOUTS = "account_lockouts"
COLLECTION_MEDIA_PROCESSING_JOBS = "media_processing_jobs"
COLLECTION_MEDIA_PROCESSING_JOBS_HOLDING = "media_processing_jobs_holding"
COLLECTION_MEDIA_PROCESSING_JOBS_FAILED = "media_processing_jobs_failed"

# --- Index Definitions ---

async def create_indexes(db: AsyncIOMotorDatabase):
    """
    Creates all required indexes for the application using Motor (Async).
    This should be called by the Backend on startup.
    Gateway should NOT call this, but rely on Backend to manage schema.
    """
    logger = logging.getLogger("api.schema")
    
    # 1. bot_configurations (Replaces deprecated 'configurations')
    try:
        # Unique index on bot_id
        await db[COLLECTION_BOT_CONFIGURATIONS].create_index([("config_data.bot_id", ASCENDING)], unique=True)
        logger.info(f"Ensured unique index for '{COLLECTION_BOT_CONFIGURATIONS}.config_data.bot_id'.")
    except Exception as e:
        logger.warning(f"Could not create index for {COLLECTION_BOT_CONFIGURATIONS}: {e}")

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
        await db[COLLECTION_QUEUES].create_index(
            [("bot_id", ASCENDING), ("provider_name", ASCENDING), ("correspondent_id", ASCENDING), ("id", ASCENDING)],
            unique=True,
            name="queues_bot_provider_correspondent_id_unique",
        )
        logger.info(f"Ensured unique queue index for {COLLECTION_QUEUES}.")

        for collection_name in [
            COLLECTION_MEDIA_PROCESSING_JOBS,
            COLLECTION_MEDIA_PROCESSING_JOBS_HOLDING,
            COLLECTION_MEDIA_PROCESSING_JOBS_FAILED,
        ]:
            collection = db[collection_name]
            await collection.create_index([("bot_id", ASCENDING)])
            await collection.create_index([("status", ASCENDING)])
            await collection.create_index([("mime_type", ASCENDING)])
            await collection.create_index([("guid", ASCENDING)])
            await collection.create_index([("created_at", ASCENDING)])
        logger.info("Ensured media processing job indexes.")

        # 5. Indexes for Tracked Group Periods
        await db[COLLECTION_TRACKED_GROUP_PERIODS].create_index([("bot_id", ASCENDING)], name="tracked_group_periods_bot_id_idx")
        await db[COLLECTION_TRACKED_GROUP_PERIODS].create_index([("tracked_group_unique_identifier", ASCENDING)], name="tracked_group_periods_unique_identifier_idx")
        await db[COLLECTION_TRACKED_GROUP_PERIODS].create_index([("periodEnd", DESCENDING)], name="tracked_group_periods_periodEnd_idx")
        logger.info(f"Created indexes for {COLLECTION_TRACKED_GROUP_PERIODS}.")

        # 6. Indexes for Group Tracking State
        await db[COLLECTION_GROUP_TRACKING_STATE].create_index(
            [("bot_id", ASCENDING), ("groupIdentifier", ASCENDING)],
            unique=True,
            name="group_tracking_state_bot_group_idx",
        )
        logger.info(f"Created indexes for {COLLECTION_GROUP_TRACKING_STATE}.")
        
    except Exception as e:
        logger.warning(f"Could not create feature indexes: {e}")
    # Token Consumption Events
    # 4. Token Consumption Events
    try:
        token_events = db[COLLECTION_TOKEN_CONSUMPTION]
        # TTL Index: Expire after 40 days (3456000 seconds)
        await token_events.create_index([("timestamp", ASCENDING)], expireAfterSeconds=3456000)
        # Compound Index for aggregation queries
        await token_events.create_index([
            ("user_id", ASCENDING),
            ("bot_id", ASCENDING),
            ("feature_name", ASCENDING),
            ("timestamp", ASCENDING)
        ])
        logger.info(f"Created indexes for {COLLECTION_TOKEN_CONSUMPTION}.")
    except Exception as e:
        logger.warning(f"Could not create token consumption indexes: {e}")
