
import requests
import time
import sys

URL = "http://localhost:8000/api/internal/bots/status"

print(f"Checking connectivity to {URL}...")
start = time.time()
try:
    response = requests.get(URL, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:100]}...")
    print(f"Time: {time.time() - start:.2f}s")
    if response.status_code == 200:
        print("Backend is RESPONSIVE.")
        sys.exit(0)
    else:
        print("Backend returned non-200 status.")
        sys.exit(1)
except Exception as e:
    print(f"Backend connectivity check FAILED: {e}")
    sys.exit(1)
