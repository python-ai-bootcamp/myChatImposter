import requests
import urllib.parse
import sys

BASE_URL = "http://localhost:8001" 

def test_validation(bot_id):
    encoded_id = urllib.parse.quote(bot_id)
    url = f"{BASE_URL}/api/external/ui/bots/validate/{encoded_id}"
    
    print(f"Testing bot_id: '{bot_id}'", flush=True)
    print(f"URL: {url}", flush=True)
    
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}", flush=True)
        print(f"Response: {response.text}", flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)

if __name__ == "__main__":
    print("--- Test 1: Standard Valid ---", flush=True)
    test_validation("valid_user")
    
    print("\n--- Test 2: With Encoded # (valid_user#injection) ---", flush=True)
    test_validation("valid_user#injection")
    
    print("\n--- Test 3: Just the part before # (valid_user) ---", flush=True)
    test_validation("valid_user")

if __name__ == "__main__":
    print("--- Test 1: Standard Valid ---")
    test_validation("valid_user")
    
    print("\n--- Test 2: With Encoded # (valid_user#injection) ---")
    test_validation("valid_user#injection")
    
    print("\n--- Test 3: Just the part before # (valid_user) ---")
    test_validation("valid_user")
