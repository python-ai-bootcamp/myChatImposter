from pymongo import MongoClient

def migrate():
    # Assuming running from host with port forward or local access
    client = MongoClient("mongodb://localhost:27017")
    db = client["chat_manager"]
    collection = db["configurations"]
    
    print("Checking for baileys spelling updates...")
    
    # 1. Update 'whatsapp_baileys' (snake_case) to 'whatsAppBaileys'
    query1 = {"config_data.configurations.chat_provider_config.provider_name": "whatsapp_baileys"}
    res1 = collection.update_many(query1, {"$set": {"config_data.configurations.chat_provider_config.provider_name": "whatsAppBaileys"}})
    print(f"Updated {res1.modified_count} documents from 'whatsapp_baileys' to 'whatsAppBaileys'.")
    
    # 2. Update 'whatsAppBaileyes' (typo) to 'whatsAppBaileys'
    query2 = {"config_data.configurations.chat_provider_config.provider_name": "whatsAppBaileyes"}
    res2 = collection.update_many(query2, {"$set": {"config_data.configurations.chat_provider_config.provider_name": "whatsAppBaileys"}})
    print(f"Updated {res2.modified_count} documents from 'whatsAppBaileyes' to 'whatsAppBaileys'.")
    
    # Verify
    count_ok = collection.count_documents({"config_data.configurations.chat_provider_config.provider_name": "whatsAppBaileys"})
    print(f"Total documents with correct spelling: {count_ok}")
    
    client.close()

if __name__ == "__main__":
    migrate()
