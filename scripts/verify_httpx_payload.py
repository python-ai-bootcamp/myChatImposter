
import sys
import os
import asyncio
import httpx
import base64
import json

# Add project root to path
sys.path.append(os.getcwd())

from actionable_item_formatter import ActionableItemFormatter

BASE_URL = "http://localhost:9000"
USER_ID = "tal"
RECIPIENT = "972543231017@s.whatsapp.net" 

def generate_test_ics():
    item = {
        "task_title": "Test Task via HTTPX",
        "task_description": "Testing ICS sending capability with HTTPX library.",
        "timestamp_deadline": "2026-02-20 12:00:00",
        "group_display_name": "Test Group"
    }
    return ActionableItemFormatter.generate_ics(item)

async def send_file_httpx(ics_bytes, mimetype):
    url = f"{BASE_URL}/sessions/{USER_ID}/send"
    
    content_b64 = base64.b64encode(ics_bytes).decode('utf-8')
    filename = "test_task_httpx.ics"
    
    payload = {
        "recipient": RECIPIENT,
        "type": "document",
        "content": content_b64,
        "fileName": filename,
        "mimetype": mimetype,
        "caption": f"Test ICS via HTTPX ({mimetype})"
    }
    
    print(f"Sending file {filename} ({mimetype}) to {RECIPIENT} using httpx...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    ics_bytes = generate_test_ics()
    print(f"ICS Bytes Length: {len(ics_bytes)}")
    asyncio.run(send_file_httpx(ics_bytes, "text/calendar"))
