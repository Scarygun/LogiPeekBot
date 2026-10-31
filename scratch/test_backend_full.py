import os
import asyncio
import aiohttp
import json
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BACKEND_API_URL", "https://api.vigo.uz")
USER = os.getenv("BACKEND_USER", "+998915555390")
PASS = os.getenv("BACKEND_PASS", "LogiPeekBot.0813261102")

async def test_endpoint(session, name, method, url, headers=None, json_data=None, params=None):
    print(f"\n--- [TEST] {name} ---")
    print(f"Request: {method} {url}")
    try:
        if method == "GET":
            async with session.get(url, headers=headers, params=params) as resp:
                status = resp.status
                try:
                    data = await resp.json()
                    print(f"Status: {status} | Response: {json.dumps(data, ensure_ascii=False)[:300]}...")
                    return status, data
                except:
                    text = await resp.text()
                    print(f"Status: {status} | Text: {text[:200]}")
                    return status, text
        elif method == "POST":
            async with session.post(url, headers=headers, json=json_data) as resp:
                status = resp.status
                try:
                    data = await resp.json()
                    print(f"Status: {status} | Response: {json.dumps(data, ensure_ascii=False)[:300]}...")
                    return status, data
                except:
                    text = await resp.text()
                    print(f"Status: {status} | Text: {text[:200]}")
                    return status, text
    except Exception as e:
        print(f"Error: {e}")
        return 0, str(e)

async def main():
    print(f"Testing Vigo.uz Backend API at: {BASE_URL}")
    print(f"Using credentials: phone={USER}")
    
    async with aiohttp.ClientSession() as session:
        # 1. Login
        status, data = await test_endpoint(
            session, "1. Auth Login", "POST",
            f"{BASE_URL}/api/v1/auth/login/",
            json_data={"phone": USER, "password": PASS}
        )
        if status != 200:
            print("❌ Login failed! Cannot test authenticated endpoints.")
            return

        token = data.get("tokens", {}).get("access")
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
        print(f"✅ Login OK. Access token: {token[:20]}...")

        # 2. Auth Me (Profile)
        await test_endpoint(
            session, "2. Auth Me (User Profile)", "GET",
            f"{BASE_URL}/api/v1/auth/me/", headers=headers
        )

        # 3. Cargo Marketplace Listings (Search)
        await test_endpoint(
            session, "3. Cargo Marketplace Listings", "GET",
            f"{BASE_URL}/api/v1/cargo/marketplace/listings/",
            headers=headers, params={"origin": "Toshkent", "destination": "Samarqand"}
        )

        # 4. Billing Payment Card
        await test_endpoint(
            session, "4. Billing Payment Card", "GET",
            f"{BASE_URL}/api/v1/billing/payment-card/", headers=headers
        )

        # 5. Billing Subscription Plans
        await test_endpoint(
            session, "5. Billing Subscription Plans", "GET",
            f"{BASE_URL}/api/v1/billing/subscription-plans/", headers=headers
        )

        # 6. Billing User Subscription
        await test_endpoint(
            session, "6. User Subscription Status", "GET",
            f"{BASE_URL}/api/v1/billing/subscription/", headers=headers
        )

        # 7. Notifications
        await test_endpoint(
            session, "7. Notifications", "GET",
            f"{BASE_URL}/api/v1/notifications/", headers=headers
        )

        # 8. Support Conversation
        await test_endpoint(
            session, "8. Support Conversation", "GET",
            f"{BASE_URL}/api/v1/support/conversation/", headers=headers
        )

        # 9. Register Start (dry run check endpoint availability)
        await test_endpoint(
            session, "9. Register Start Endpoint Check", "POST",
            f"{BASE_URL}/api/v1/auth/register/start/",
            json_data={"phone": "+998900000000"}
        )

if __name__ == "__main__":
    asyncio.run(main())

