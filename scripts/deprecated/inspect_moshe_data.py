
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def inspect_moshe():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.get_database("chat_manager")
    
    # 1. Find 'moshe' credentials
    cred = await db.user_auth_credentials.find_one({"user_id": "moshe"})
    if not cred:
        print("ERROR: User 'moshe' not found in credentials.")
        return
    
    print("=== MOSHE CREDENTIALS ===")
    print(f"  user_id: {cred.get('user_id')}")
    print(f"  role: {cred.get('role')}")
    print(f"  max_feature_limit: {cred.get('max_feature_limit')}")
    print(f"  owned_user_configurations: {cred.get('owned_user_configurations')}")
    
    owned_bots = cred.get("owned_user_configurations", [])
    
    # Check for duplicates
    if len(owned_bots) != len(set(owned_bots)):
        print("\n!!! WARNING: DUPLICATE ENTRIES IN owned_user_configurations !!!")
        from collections import Counter
        counts = Counter(owned_bots)
        for bot, count in counts.items():
            if count > 1:
                print(f"  {bot}: appears {count} times")
    
    # 2. Find all configs for owned bots
    print("\n=== CONFIGURATIONS FOR OWNED BOTS ===")
    total_features = 0
    for bot_id in owned_bots:
        # Find config
        configs = await db.configurations.find({"config_data.user_id": bot_id}).to_list(length=10)
        if not configs:
            print(f"  {bot_id}: NO CONFIG FOUND")
        elif len(configs) > 1:
            print(f"\n!!! WARNING: MULTIPLE CONFIGS FOR {bot_id} !!!")
            for i, cfg in enumerate(configs):
                print(f"  Config {i}: _id={cfg.get('_id')}")
        else:
            cfg = configs[0]
            features = cfg.get("config_data", {}).get("features", {})
            count = sum(1 for f in features.values() if isinstance(f, dict) and f.get("enabled", False))
            total_features += count
            print(f"  {bot_id}: {count} features enabled")
    
    print(f"\n=== TOTAL FEATURES ACROSS ALL OWNED BOTS: {total_features} ===")
    
    client.close()

if __name__ == "__main__":
    if os.name == "nt":
        try: asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except: pass
    asyncio.run(inspect_moshe())
