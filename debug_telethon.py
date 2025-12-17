import asyncio
import logging
from telethon import TelegramClient
from config import USER_API_ID, USER_API_HASH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    client = TelegramClient('user_session', USER_API_ID, USER_API_HASH)
    
    logger.info("Connecting...")
    await client.connect()
    
    if not await client.is_user_authorized():
        logger.error("Client is NOT authorized. Session might be invalid.")
        return

    logger.info("Client is authorized. Attempting to get dialogs...")
    
    try:
        dialogs = await client.get_dialogs()
        logger.info(f"Successfully retrieved {len(dialogs)} dialogs.")
        for d in dialogs[:5]:
            logger.info(f" - {d.name} (ID: {d.id})")
    except Exception as e:
        logger.error(f"Failed to get dialogs: {e}")
        import traceback
        traceback.print_exc()

    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
