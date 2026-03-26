import os

files = [
    'tests/test_queue_manager.py',
    'tests/test_refactored_services.py',
    'tests/chat_providers/test_whatsapp_baileys_provider.py',
    'tests/test_session_manager.py'
]

for f in files:
    if not os.path.exists(f): 
        continue
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    content = content.replace("user_id=", "bot_id=")
    content = content.replace("'user_id':", "'bot_id':")
    content = content.replace('"user_id":', '"bot_id":')
    content = content.replace(".user_id", ".bot_id")
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print("Tests updated")
