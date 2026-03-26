import asyncio
import pymongo
from pprint import pprint

async def main():
    client = pymongo.MongoClient("mongodb://localhost:27017")
    db = client["my_chat_imposter"]
    
    # Let's see the most recent jobs in media_processing_jobs_holding and _failed
    print("Holding collection:")
    for job in db["media_processing_jobs_holding"].find().sort("created_at", -1).limit(5):
        pprint(job)
        
    print("---------------------------------")
    print("Failed collection:")
    for job in db["media_processing_jobs_failed"].find().sort("created_at", -1).limit(5):
        pprint(job)

asyncio.run(main())
