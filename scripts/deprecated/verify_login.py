
import asyncio
import httpx

async def verify_login():
    url = "http://localhost:8001/api/external/auth/login"
    print(f"Testing login at {url}")
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json={"user_id": "admin", "password": "password123"})
            print(f"Status: {res.status_code}")
            print(f"Response: {res.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_login())
