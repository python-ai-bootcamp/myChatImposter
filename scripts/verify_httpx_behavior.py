import httpx
import asyncio
import urllib.parse

async def test():
    base = "http://backend:8000/api/internal/bots"
    
    # Scene 1: Current Vulnerable Behavior
    path_decoded = "ui/bots/validate/bot#injection"
    url_vulnerable = f"{base}/{path_decoded}"
    print(f"Vulnerable Construction: {url_vulnerable}")
    # httpx Request object to see what it Would send
    req_vuln = httpx.Request("GET", url_vulnerable)
    print(f"httpx parsed path: {req_vuln.url.path}") 
    print(f"httpx parsed fragment: {req_vuln.url.fragment}")
    print(f"Actual sent path (vulnerable): {req_vuln.url.raw_path.decode()}") # Should be .../bot
    
    print("-" * 20)
    
    # Scene 2: Fixed Behavior
    path_encoded = urllib.parse.quote(path_decoded, safe="/")
    url_fixed = f"{base}/{path_encoded}"
    print(f"Fixed Construction: {url_fixed}")
    req_fixed = httpx.Request("GET", url_fixed)
    print(f"httpx parsed path: {req_fixed.url.path}")
    print(f"httpx parsed fragment: {req_fixed.url.fragment}")
    print(f"Actual sent path (fixed): {req_fixed.url.raw_path.decode()}") # Should be .../bot%23injection

if __name__ == "__main__":
    asyncio.run(test())
