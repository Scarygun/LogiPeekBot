import asyncio
import os
import sys

# Add project root to path
sys.path.append('/Users/scarygun/Loyihalar/LogiPeekBot')

from backend_client import backend_client

async def test_api():
    print("Loging in...")
    token = await backend_client._get_valid_token()
    print(f"Token: {token[:20]}..." if token else "Failed to login")
    
    if token:
        print("\nSearching loads from Toshkent to Samarqand...")
        import aiohttp
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token}"}
            params = {"origin": "Nókis", "destination": "Toshkent"}
            async with session.get(f"{backend_client.base_url}/api/v1/cargo/marketplace/listings/", params=params, headers=headers) as resp:
                print(f"Status: {resp.status}")
                raw_data = await resp.json()
                print(f"Raw response (type {type(raw_data)}):")
                import json
                print(json.dumps(raw_data, indent=2, ensure_ascii=False)[:1000])


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # ensure env vars are set if not loaded properly by dotenv
    backend_client.base_url = os.getenv('BACKEND_API_URL', 'https://api.vigo.uz')
    backend_client.username = os.getenv('BACKEND_USER', '')
    backend_client.password = os.getenv('BACKEND_PASS', '')
    
    asyncio.run(test_api())
