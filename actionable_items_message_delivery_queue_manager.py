import asyncio
import random
import uuid
import json
from datetime import datetime
from pymongo import MongoClient
from chatbot_manager import ChatbotInstance
from chat_providers.whatsAppBaileyes import WhatsAppBaileysProvider
from logging_lock import console_log

# logger = logging.getLogger(__name__) # Removed in favor of console_log consistency
class ActionableItemsDeliveryQueueManager:
    def __init__(self, mongo_url: str, chatbot_instances: dict[str, ChatbotInstance]):
        self.mongo_client = MongoClient(mongo_url)
        self.db = self.mongo_client['chat_manager']
        
        # Collections
        self.queue_collection = self.db['actionable_items_message_delivery_queue']
        self.failed_collection = self.db['actionable_items_message_delivery_queue_failed']
        self.unconnected_collection = self.db['actionable_items_message_delivery_queue_unconnected_users_messages']
        
        self.chatbot_instances = chatbot_instances
        self.running = False
        self.consumer_task = None
        
        # Ensure indexes
        self.queue_collection.create_index("message_metadata.send_attempts")
        self.queue_collection.create_index("message_metadata.message_destination.user_id")
        self.unconnected_collection.create_index("message_metadata.message_destination.user_id")

    async def start_consumer(self):
        if self.running:
            return
        self.running = True
        self.consumer_task = asyncio.create_task(self._consumer_loop())
        console_log("ACTIONABLE_QUEUE: ActionableItemsDeliveryQueueManager consumer started.")

    async def stop_consumer(self):
        self.running = False
        if self.consumer_task:
            self.consumer_task.cancel()
            try:
                await self.consumer_task
            except asyncio.CancelledError:
                pass
        console_log("ACTIONABLE_QUEUE: ActionableItemsDeliveryQueueManager consumer stopped.")

    def add_item(self, actionable_item: dict, user_id: str, provider_name: str):
        """
        Adds an actionable item to the main delivery queue.
        """
        message_id = str(uuid.uuid4())
        doc = {
            "actionable_item": actionable_item,
            "message_metadata": {
                "message_id": message_id,
                "message_destination": {
                    "user_id": user_id,
                    "provider_name": provider_name
                },
                "send_attempts": 0
            },
            "created_at": datetime.utcnow()
        }
        
        try:
            self.queue_collection.insert_one(doc)
            console_log(f"ACTIONABLE_QUEUE: Added item to delivery queue: {message_id} for user {user_id}")
        except Exception as e:
            console_log(f"ACTIONABLE_QUEUE_ERROR: Failed to add item to delivery queue: {e}")

    def move_user_to_holding(self, user_id: str):
        """
        Moves all items for a specific user from the active queue to the unconnected holding queue.
        """
        try:
            # Find items
            query = {"message_metadata.message_destination.user_id": user_id}
            items = list(self.queue_collection.find(query))
            
            if items:
                # Insert to unconnected
                self.unconnected_collection.insert_many(items)
                # Delete from active
                self.queue_collection.delete_many(query)
                console_log(f"ACTIONABLE_QUEUE: Moved {len(items)} items for user {user_id} to UNCONNECTED holding queue.")
            else:
                pass # console_log(f"ACTIONABLE_QUEUE_DEBUG: No items to move to holding for user {user_id}.")
        except Exception as e:
            console_log(f"ACTIONABLE_QUEUE_ERROR: Failed to move items to holding for user {user_id}: {e}")

    def move_user_to_active(self, user_id: str):
        """
        Moves all items for a specific user from the unconnected holding queue to the active queue.
        """
        try:
            # Find items
            query = {"message_metadata.message_destination.user_id": user_id}
            items = list(self.unconnected_collection.find(query))
            
            if items:
                # Insert to active
                self.queue_collection.insert_many(items)
                # Delete from unconnected
                self.unconnected_collection.delete_many(query)
                console_log(f"ACTIONABLE_QUEUE: Moved {len(items)} items for user {user_id} to ACTIVE delivery queue.")
            else:
                pass # console_log(f"ACTIONABLE_QUEUE_DEBUG: No items to move to active for user {user_id}.")
        except Exception as e:
            console_log(f"ACTIONABLE_QUEUE_ERROR: Failed to move items to active for user {user_id}: {e}")

    def move_all_to_holding(self):
        """
        Moves ALL items from the active queue to the unconnected holding queue.
        Used on startup.
        """
        try:
            items = list(self.queue_collection.find({}))
            if items:
                self.unconnected_collection.insert_many(items)
                self.queue_collection.delete_many({})
                console_log(f"ACTIONABLE_QUEUE: Startup: Moved {len(items)} items to UNCONNECTED holding queue.")
            else:
                console_log("ACTIONABLE_QUEUE: Startup: No pending items to move to holding.")
        except Exception as e:
            console_log(f"ACTIONABLE_QUEUE_ERROR: Failed to move all items to holding: {e}")

    async def _consumer_loop(self):
        console_log("ACTIONABLE_QUEUE: ActionableItemsDeliveryQueueManager loop running.")
        while self.running:
            try:
                # Jitter: Sleep random time between 1 and 12 seconds
                sleep_time = random.uniform(1, 12)
                await asyncio.sleep(sleep_time)

                # Random Selection Pipeline (Size 1)
                pipeline = [{"$sample": {"size": 1}}]
                cursor = self.queue_collection.aggregate(pipeline)
                candidate_list = list(cursor)
                
                if not candidate_list:
                    continue 

                candidate = candidate_list[0]
                message_id = candidate["message_metadata"]["message_id"]
                user_id = candidate["message_metadata"]["message_destination"]["user_id"]
                attempts = candidate["message_metadata"]["send_attempts"]

                # 1. Check Attempts Limit
                if attempts >= 3:
                    console_log(f"ACTIONABLE_QUEUE_WARN: Item {message_id} reached max attempts (3). Moving to FAILED queue.")
                    try:
                        self.failed_collection.insert_one(candidate)
                        self.queue_collection.delete_one({"_id": candidate["_id"]})
                    except Exception as e:
                        console_log(f"ACTIONABLE_QUEUE_ERROR: Failed to move item {message_id} to failed queue: {e}")
                    continue

                # 2. Check User Connection (Presend Check)
                # Find Chatbot Instance
                target_instance = None
                for instance in self.chatbot_instances.values():
                    if instance.user_id == user_id:
                        target_instance = instance
                        break
                
                # Logic: If instance missing OR (instance exists but provider not ready/connected)
                # Note: `get_status` or direct attribute check. 
                # For Baileys, user_jid being present usually implies connection/auth.
                is_connected = False
                if target_instance and target_instance.provider_instance:
                    if isinstance(target_instance.provider_instance, WhatsAppBaileysProvider):
                         if target_instance.provider_instance.user_jid:
                             is_connected = True
                
                if not is_connected:
                    # Just skip this iteration. Do NOT move to holding automatically.
                    # Let external lifecycle events handle the queue movement.
                    # console_log(f"ACTIONABLE_QUEUE_DEBUG: User {user_id} momentarily not connected/ready. Skipping item {message_id}.")
                    continue

                # 3. Increment Attempts (in DB)
                updated_doc = self.queue_collection.find_one_and_update(
                    {"_id": candidate["_id"]},
                    {"$inc": {"message_metadata.send_attempts": 1}},
                    return_document=True
                )

                if not updated_doc:
                    # Race condition, item gone
                    continue

                # 4. Attempt Send
                # Using updated attempts count for logging
                current_attempt = updated_doc["message_metadata"]["send_attempts"]
                console_log(f"ACTIONABLE_QUEUE: Sending item {message_id} to {user_id} (Attempt {current_attempt}/3)")
                
                try:
                    actionable_item = updated_doc["actionable_item"]
                    item_json_str = json.dumps(actionable_item, indent=2, ensure_ascii=False)
                    recipient_jid = target_instance.provider_instance.user_jid # Already checked above
                    
                    await target_instance.provider_instance.sendMessage(recipient_jid, item_json_str)
                    
                    # 5. Success -> Delete
                    self.queue_collection.delete_one({"_id": candidate["_id"]})
                    console_log(f"ACTIONABLE_QUEUE: Sent item {message_id} successfully. Removed from queue.")
                    
                except Exception as e:
                    console_log(f"ACTIONABLE_QUEUE_ERROR: Failed to send item {message_id}: {e}")
                    # CRITICAL FIX: Do NOT delete the item.
                    # The item remains in the queue with incremented 'send_attempts'.
                    # It will be picked up again by the consumer loop (subject to jitter).
                    # If it reaches max attempts (3), it will be moved to failed queue.
                    
                    # Optional: Check for disconnection error specifically to move to unconnected immediately?
                    # For now, we rely on the retry limit or external lifecycle events to move it.
                    pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                console_log(f"ACTIONABLE_QUEUE_ERROR: Error in consumer loop: {e}")
                await asyncio.sleep(5)

    def get_queue_items(self, queue_type: str, user_id: str = None) -> list:
        """
        Retrieves items from the specified queue, optionally filtered by user_id.
        queue_type: 'active', 'failed', 'unconnected'
        """
        collection = None
        if queue_type == "active":
            collection = self.queue_collection
        elif queue_type == "failed":
            collection = self.failed_collection
        elif queue_type == "unconnected":
            collection = self.unconnected_collection
        else:
            raise ValueError(f"Invalid queue_type: {queue_type}")

        query = {}
        if user_id:
            query["message_metadata.message_destination.user_id"] = user_id

        # Return list of items, converting ObjectId to str for JSON serialization if needed elsewhere
        items = list(collection.find(query))
        for item in items:
            item["_id"] = str(item["_id"])
        return items

    def delete_queue_item(self, queue_type: str, message_id: str) -> bool:
        """
        Deletes a specific item by message_id from the specified queue.
        Returns True if deleted, False if not found.
        """
        collection = None
        if queue_type == "active":
            collection = self.queue_collection
        elif queue_type == "failed":
            collection = self.failed_collection
        elif queue_type == "unconnected":
            collection = self.unconnected_collection
        else:
            raise ValueError(f"Invalid queue_type: {queue_type}")

        result = collection.delete_one({"message_metadata.message_id": message_id})
        if result.deleted_count > 0:
            console_log(f"ACTIONABLE_QUEUE: Deleted item {message_id} from {queue_type} queue.")
            return True
        else:
            console_log(f"ACTIONABLE_QUEUE_WARN: Item {message_id} not found in {queue_type} queue for deletion.")
            return False

