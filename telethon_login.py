import asyncio
from telethon import TelegramClient

from config import USER_API_ID, USER_API_HASH

async def login_telethon_user():
    api_id = USER_API_ID
    api_hash = USER_API_HASH
    session_name = 'user_session'

    client = TelegramClient(session_name, api_id, api_hash)
    print("Telethon klientini foydalanuvchi sifatida ulashga harakat qilmoqda...")
    try:
        await client.start()
        print("Signed in successfully as", (await client.get_me()).first_name)
    except Exception as e:
        print(f"Telethon klientini ulashda xatolik: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(login_telethon_user())
