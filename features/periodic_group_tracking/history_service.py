
import logging
from datetime import datetime
from pymongo import MongoClient
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class GroupHistoryService:
    def __init__(self, mongo_url: str):
        self.mongo_client = MongoClient(mongo_url)
        self.db = self.mongo_client['chat_manager']
        self.tracked_groups_collection = self.db['tracked_groups']
        self.tracked_group_periods_collection = self.db['tracked_group_periods']
        self.tracking_state_collection = self.db['group_tracking_state']

    def _build_period_query(self, user_id, group_id, time_from=None, time_until=None):
        query = {
            "user_id": user_id,
            "tracked_group_unique_identifier": group_id
        }

        if time_from is not None:
            query["periodStart"] = {"$gt": time_from}
        if time_until is not None:
            query["periodEnd"] = {"$lt": time_until}

        return query

    def _build_group_response(self, group_meta, last_periods: int, time_from=None, time_until=None):
        user_id = group_meta['user_id']
        group_id = group_meta['group_id']

        query = self._build_period_query(user_id, group_id, time_from, time_until)
        cursor = self.tracked_group_periods_collection.find(query).sort("periodEnd", -1)

        if last_periods > 0:
            cursor = cursor.limit(last_periods)

        periods = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            if isinstance(doc.get('createdAt'), datetime):
                doc['createdAt'] = doc['createdAt'].isoformat()
            
            # Enrich with display_name from metadata if missing (Normalization on Read support)
            # Although API router does this, doing it here is also robust.
            # But wait, original code passed `group_meta` to this function, so we have it!
            if 'display_name' not in doc:
                 doc['display_name'] = group_meta.get('display_name', 'Unknown')

            periods.append(doc)

        return {
            "group": {
                "identifier": group_id,
                "display_name": group_meta.get('display_name', 'Unknown'),
                "alternate_identifiers": group_meta.get('alternate_identifiers', [])
            },
            "periods": periods
        }

    def get_tracked_periods(self, user_id: str, group_id: str = None) -> List[Dict]:
        """
        Fetch raw tracked period documents (Flat List).
        Enriches them with 'display_name' from the group metadata.
        Used by API endpoints expecting a flat list of periods.
        """
        # 1. Build Map
        groups_cursor = self.tracked_groups_collection.find({"user_id": user_id})
        group_map = {g['group_id']: g.get('display_name', 'Unknown') for g in groups_cursor}
        
        # 2. Build Query
        query = {"user_id": user_id}
        if group_id:
            query["tracked_group_unique_identifier"] = group_id
            
        cursor = self.tracked_group_periods_collection.find(query).sort("periodEnd", -1)
        
        results = []
        for doc in cursor:
            # Serialization
            doc['_id'] = str(doc['_id'])
            if isinstance(doc.get('createdAt'), datetime):
                doc['createdAt'] = doc['createdAt'].isoformat()
            
            # Enrichment
            gid = doc.get('tracked_group_unique_identifier')
            # Use stored display_name if available, else lookup
            if 'display_name' not in doc:
                 doc['display_name'] = group_map.get(gid, 'Unknown Group')
                 
            results.append(doc)
            
        return results

    def get_group_messages(self, user_id: str, group_id: str, last_periods: int = 0, time_from: int = None, time_until: int = None) -> Optional[Dict]:
        """Fetch tracked periods for a specific group."""
        group_meta = self.tracked_groups_collection.find_one({"user_id": user_id, "group_id": group_id})
        if not group_meta:
            return None
        return self._build_group_response(group_meta, last_periods, time_from, time_until)

    def get_all_user_messages(self, user_id: str, last_periods: int = 0, time_from: int = None, time_until: int = None) -> List[Dict]:
        """Fetch tracked periods for ALL groups of a user."""
        groups_cursor = self.tracked_groups_collection.find({"user_id": user_id})

        results = []
        for group_meta in groups_cursor:
            results.append(self._build_group_response(group_meta, last_periods, time_from, time_until))

        return results

    def delete_group_messages(self, user_id: str, group_id: str, last_periods: int = 0, time_from: int = None, time_until: int = None) -> int:
        """Delete tracked periods for a specific group."""
        query = self._build_period_query(user_id, group_id, time_from, time_until)

        if last_periods > 0:
            # Fetch IDs to delete (most recent N matching filters)
            cursor = self.tracked_group_periods_collection.find(query, {"_id": 1}).sort("periodEnd", -1).limit(last_periods)
            ids = [doc["_id"] for doc in cursor]
            if not ids:
                return 0
            result = self.tracked_group_periods_collection.delete_many({"_id": {"$in": ids}})
            return result.deleted_count
        else:
            result = self.tracked_group_periods_collection.delete_many(query)
            return result.deleted_count

    def delete_all_user_messages(self, user_id: str, last_periods: int = 0, time_from: int = None, time_until: int = None) -> int:
        """Delete all tracked periods for a user."""
        total_deleted = 0
        groups_cursor = self.tracked_groups_collection.find({"user_id": user_id})
        for group_meta in groups_cursor:
            deleted = self.delete_group_messages(user_id, group_meta['group_id'], last_periods, time_from, time_until)
            total_deleted += deleted

        return total_deleted
    
    def save_tracking_result(self, user_id: str, config_group_id: str, config_display_name: str, config_schedule: str, 
                           messages: List[Dict], start_ts: int, end_ts: int, alternate_identifiers_set: set):
        """
        Saves the result of a tracking run:
        1. Upserts Group Metadata.
        2. Inserts Period Document.
        3. Updates Last Run State.
        """
        
        # 1. Upsert Group Metadata
        # Ensure we have the latest metadata
        alternate_identifiers_set.add(config_group_id)
        alternate_identifiers_set.add(config_display_name)

        self.tracked_groups_collection.update_one(
            {"user_id": user_id, "group_id": config_group_id},
            {"$set": {
                "user_id": user_id,
                "group_id": config_group_id,
                "display_name": config_display_name,
                "alternate_identifiers": list(alternate_identifiers_set),
                "crontab_triggering_expression": config_schedule
            }},
            upsert=True
        )

        # 2. Insert Period Document
        period_doc = {
            "user_id": user_id,
            "tracked_group_unique_identifier": config_group_id,
            "periodStart": start_ts,
            "periodEnd": end_ts,
            "messageCount": len(messages),
            "createdAt": datetime.utcnow(),
            "messages": messages,
            # Store display name for creating independent record
            "display_name": config_display_name 
        }
        self.tracked_group_periods_collection.insert_one(period_doc)

        # 3. Update last run state
        state_key = {"user_id": user_id, "group_id": config_group_id}
        self.tracking_state_collection.update_one(
            state_key,
            {"$set": {"last_run_ts": end_ts}},
            upsert=True
        )
        
    def get_last_run(self, user_id: str, group_id: str) -> Optional[int]:
        state_key = {'user_id': user_id, 'group_id': group_id}
        state_doc = self.tracking_state_collection.find_one(state_key)
        if state_doc:
            return state_doc.get('last_run_ts')
        return None

    def get_recent_message_ids(self, user_id: str, group_id: str, limit: int = 500) -> set:
        """
        Fetch a set of provider_message_ids from the most recent tracked periods.
        Used to prevent duplication across periods (e.g. if a message timestamp updates).
        """
        # Fetch last few periods
        cursor = self.tracked_group_periods_collection.find(
            {"user_id": user_id, "tracked_group_unique_identifier": group_id},
            {"messages.provider_message_id": 1}
        ).sort("periodEnd", -1).limit(5) # Look back 5 periods
        
        existing_ids = set()
        for doc in cursor:
            for msg in doc.get('messages', []):
                pid = msg.get('provider_message_id')
                if pid:
                    existing_ids.add(pid)
                    
        return existing_ids
