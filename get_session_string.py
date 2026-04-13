from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('USER_API_ID', 0))
API_HASH = os.getenv('USER_API_HASH')

if not API_ID or not API_HASH:
    print("Xato: .env faylida USER_API_ID va USER_API_HASH bo'lishi shart!")
else:
    print("Telethon String Session yaratilmoqda...")
    with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        print("\nSIZNING STRING SESSION:\n")
        print(client.session.save())
        print("\nUshbu satrni nusxalab oling va Vercel-ga 'TELETHON_STRING_SESSION' nomi bilan qo'shing.")
