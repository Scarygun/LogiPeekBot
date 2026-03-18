import asyncio
import os
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from config import USER_API_ID, USER_API_HASH, USER_PHONE_NUMBER

async def main():
    print("="*50)
    print("TELEGRAM LOGIN SCRIPT (ROBUST MODE)")
    print("="*50)
    
    session_file = 'user_session.session'
    if os.path.exists(session_file):
        print(f"Eski sessiya fayli topildi. Uni tozalash tavsiya etiladi.")
        ans = input("Eski sessiyani o'chirib, yangidan boshlaymizmi? (y/n): ")
        if ans.lower() == 'y':
            os.remove(session_file)
            print("Sessiya fayli o'chirildi.")

    client = TelegramClient('user_session', USER_API_ID, USER_API_HASH)
    
    print(f"\nUlanmoqda: {USER_PHONE_NUMBER}")
    print("Eslatma: Kod odatda Telegram ilovangizga (SMS emas) xabar bo'lib boradi.")
    
    try:
        await client.start(phone=USER_PHONE_NUMBER)
    except FloodWaitError as e:
        wait_hours = e.seconds // 3600
        wait_minutes = (e.seconds % 3600) // 60
        print("\n" + "!"*50)
        print("TELEGRAM CHEKLOVI (FLOOD WAIT)")
        print(f"Kutish vaqti: {e.seconds} soniya (~{wait_hours} soat {wait_minutes} daqiqa).")
        print("!"*50 + "\n")
        await client.disconnect()
        return
    except Exception as e:
        print(f"\nXatolik: {e}")
        await client.disconnect()
        return
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print("\n" + "="*50)
        print("MUVAFFAQIYATLI!")
        print(f"Siz {me.first_name} sifatida kirdingiz.")
        print("="*50)
    else:
        print("\nXato: Avtorizatsiya yakunlanmadi.")

    await client.disconnect()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nJarayon to'xtatildi.")
    except Exception as e:
        print(f"\nXatolik yuz berdi: {e}")
