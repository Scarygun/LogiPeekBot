import asyncio
import os
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from config import USER_API_ID, USER_API_HASH, USER_PHONE_NUMBER

async def main():
    print("="*50)
    print("TELEGRAM LOGIN SCRIPT")
    print("="*50)
    
    # Session name 'user_session' is used by the main bot as well
    client = TelegramClient('user_session', USER_API_ID, USER_API_HASH)
    
    print(f"\nUlanmoqda: {USER_PHONE_NUMBER}")
    
    try:
        await client.start(phone=USER_PHONE_NUMBER)
    except FloodWaitError as e:
        wait_hours = e.seconds // 3600
        wait_minutes = (e.seconds % 3600) // 60
        print("\n" + "!"*50)
        print("TELEGRAM CHEKLOVI (FLOOD WAIT)")
        print(f"Siz juda ko'p urinish qildingiz.")
        print(f"Kutish vaqti: {e.seconds} soniya (~{wait_hours} soat {wait_minutes} daqiqa).")
        print("Iltimos, ushbu vaqtdan keyin qayta urinib ko'ring.")
        print("!"*50 + "\n")
        await client.disconnect()
        return
    except Exception as e:
        print(f"\nKutulmagan xatolik: {e}")
        await client.disconnect()
        return
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print("\n" + "="*50)
        print("MUVAFFAQIYATLI!")
        print(f"Siz {me.first_name} (ID: {me.id}) sifatida kirdingiz.")
        print("Sessiya 'user_session.session' fayliga saqlandi.")
        print("Endi botni ishga tushirishingiz mumkin.")
        print("="*50)
    else:
        print("\nXato: Avtorizatsiyadan o'tib bo'lmadi.")

    await client.disconnect()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nJarayon to'xtatildi.")
    except Exception as e:
        print(f"\nXatolik yuz berdi: {e}")
