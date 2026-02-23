import asyncio
import httpx
import sys

async def test_connection():
    url = "https://api.telegram.org"
    print(f"Testing connection to {url}...")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            print(f"✅ Success! Status code: {response.status_code}")
            return True
    except httpx.ConnectError as e:
        print(f"❌ Connection Error (ConnectError): {e}")
        print("This usually means the site is blocked or there is no internet connection.")
    except httpx.TimeoutException as e:
        print(f"❌ Connection Timed Out: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {type(e).__name__}: {e}")
    return False

async def test_google():
    url = "https://www.google.com"
    print(f"\nTesting connection to {url} (Internet check)...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            print(f"✅ Internet is OK. Status code: {response.status_code}")
            return True
    except Exception as e:
        print(f"❌ Internet check failed: {e}")
        return False

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    print("--- Network Diagnostic Tool ---")
    
    async def main():
        google_ok = await test_google()
        telegram_ok = await test_connection()
        
        print("\n--- Summary ---")
        if not google_ok:
            print("❌ No internet connection detected.")
        elif not telegram_ok:
            print("⚠️ Internet is present, but Telegram API is unreachable.")
            print("   You likely need a VPN or Proxy.")
        else:
            print("✅ Connection seems fine.")
            
    asyncio.run(main())
