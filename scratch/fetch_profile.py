import asyncio
import aiohttp
import json

async def main():
    login_url = "https://api.vigo.uz/api/v1/auth/login/"
    payload = {"phone": "+998933199952", "password": "Ozodbek5317!"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(login_url, json=payload) as resp:
            data = await resp.json()
            token = data.get('tokens', {}).get('access')
            if not token:
                print("Login failed:", data)
                return
            
            headers = {"Authorization": f"Bearer {token}"}
            me_url = "https://api.vigo.uz/api/v1/auth/me/"
            
            async with session.get(me_url, headers=headers) as r:
                if r.status in [200, 201]:
                    profile = await r.json()
                    print(json.dumps(profile, indent=2))
                else:
                    print(f"Error fetching profile: {r.status} {await r.text()}")

asyncio.run(main())
