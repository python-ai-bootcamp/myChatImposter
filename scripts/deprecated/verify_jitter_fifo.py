
import asyncio
import random
import uuid
import time
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from async_message_delivery_queue_manager import AsyncMessageDeliveryQueueManager, QueueMessageType

async def verify():
    print("Starting Jitter and FIFO Verification...")
    
    # 1. Setup
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client['test_jitter_db']
    # Use separate collections for testing
    queue_col = db['test_queue_active']
    failed_col = db['test_queue_failed']
    holding_col = db['test_queue_holding']
    
    await queue_col.delete_many({})
    
    # Mock bot instances
    chatbot_instances = {
        "test_bot": type('obj', (object,), {
            "bot_id": "ron",
            "provider_instance": type('obj', (object,), {
                "is_connected": True
            })
        })
    }
    
    manager = AsyncMessageDeliveryQueueManager(db, chatbot_instances)
    # Override collections to test ones
    manager.queue_collection = queue_col
    manager.failed_collection = failed_col 
    manager.unconnected_collection = holding_col
    
    # Mock Processor Factory
    from message_processors.factory import MessageProcessorFactory
    class MockProcessor:
        async def process(self, doc, instance):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing {doc['message_metadata']['message_id']}")
            # Simulate a 1s send time
            await asyncio.sleep(1)
            # Delete from queue (standard behavior after success)
            await queue_col.delete_one({"_id": doc["_id"]})

    MessageProcessorFactory.get_processor = lambda t: MockProcessor()
    
    # 2. Add items in FIFO order
    print("Adding 3 items to queue...")
    for i in range(3):
        await manager.add_item(
            content=f"Test message {i}",
            message_type=QueueMessageType.ICS_ACTIONABLE_ITEM,
            bot_id="ron",
            provider_name="whatsAppBaileys"
        )
        # Ensure distinct created_at
        await asyncio.sleep(0.1)
    
    # 3. Start Consumer
    sent_times = []
    original_logging_info = manager._consumer_loop # Save reference
    
    # Start the manager
    await manager.start_consumer()
    print("Consumer started. Waiting for delivery...")
    
    # Monitor the queue
    start_time = time.time()
    while await queue_col.count_documents({}) > 0 and time.time() - start_time < 60:
        count = await queue_col.count_documents({})
        # We track sent times via logs (simulated here)
        await asyncio.sleep(1)
        
    await manager.stop_consumer()
    print("Verification complete.")

if __name__ == "__main__":
    asyncio.run(verify())
