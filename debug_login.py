import asyncio
import os
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from config import USER_API_ID, USER_API_HASH, USER_PHONE_NUMBER

async def main():
    print("="*50)
    print("TELEGRAM ADVANCED DEBUG LOGIN")
    print("="*50)
    
    session_name = 'debug_session' # Using a fresh session name
    client = TelegramClient(session_name, USER_API_ID, USER_API_HASH)
    
    try:
        await client.connect()
        print(f"Serverga ulandi. Raqam: {USER_PHONE_NUMBER}")
        
        # Checking if already authorized
        if await client.is_user_authorized():
            print("Siz allaqachon avtorizatsiyadan o'tgansiz!")
            me = await client.get_me()
            print(f"Foydalanuvchi: {me.first_name}")
            return

        print("Kod yuborish so'ralmoqda...")
        result = await client.send_code_request(USER_PHONE_NUMBER)
        print(f"Natija turi (Class): {type(result)}")
        print(f"Kodni yuborish usuli: {type(result.type).__name__}")
        print(f"Telefon kodi xeshi: {result.phone_code_hash}")
        
        if hasattr(result.type, 'length'):
            print(f"Kutilayotgan kod uzunligi: {result.type.length}")
        
        print("\n[!] Telegram API kod yuborilganini aytdi.")
        if "SentCodeTypeApp" in str(type(result.type)):
            print("[!] DIQQAT: Kod Telegram ilovangizga (akkaunt ichiga) yuborilgan!")
        elif "SentCodeTypeSms" in str(type(result.type)):
            print("[!] DIQQAT: Kod SMS orqali yuborilgan!")
        else:
            print(f"[!] Kod yuborilish holati: {type(result.type).__name__}")
        
        code = input("\nKodni kiriting: ")
        await client.sign_in(USER_PHONE_NUMBER, code, phone_code_hash=result.phone_code_hash)
        
        print("\nMUVAFFAQIYATLI!")
        # Copy debug session to main session
        if os.path.exists('user_session.session'):
            os.remove('user_session.session')
        os.rename('debug_session.session', 'user_session.session')
        print("Sessiya 'user_session.session' ga saqlandi.")

    except FloodWaitError as e:
        print(f"\nKUTISH KERAK: {e.seconds} soniya.")
    except Exception as e:
        print(f"\nXATOLIK TURI: {type(e).__name__}")
        print(f"XATOLIK XABARI: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
