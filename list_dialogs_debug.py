import asyncio
from telethon import TelegramClient
from config import USER_API_ID, USER_API_HASH

async def main():
    client = TelegramClient('user_session', USER_API_ID, USER_API_HASH)
    await client.connect()
    if not await client.is_user_authorized():
        print("Telethon client authorized emas!")
        return

    print("--- Dialoglar ro'yxati ---")
    bot_id = 8468044431
    found_any_bot_group = False

    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            bot_api_id = dialog.id
            if dialog.is_channel:
                if not str(bot_api_id).startswith("-100"):
                    if bot_api_id > 0:
                        bot_api_id = int(f"-100{bot_api_id}")
            
            try:
                is_bot_here = False
                async for user in client.iter_participants(dialog.id):
                    if user.id == bot_id:
                        is_bot_here = True
                        break
                
                if is_bot_here:
                    print(f"✅ [BOT BOR] Title: {dialog.name} | ID: {bot_api_id} | Type: {'Supergroup/Channel' if dialog.is_channel else 'Group'}")
                    found_any_bot_group = True
                else:
                    # Faqat guruhlarni chiqaramiz, kanallarni kamaytiramiz agar bot yo'q bo'lsa
                    if not dialog.is_channel:
                         print(f"❌ [BOT YO'Q] Title: {dialog.name} | ID: {bot_api_id}")
            except Exception:
                # Ehtimol adminlik huquqi yo'q ishtirokchilarni ko'rishga
                pass

    if not found_any_bot_group:
        print("\n--- Xulosa: Bot hech qanday guruhda topilmadi! ---")

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
