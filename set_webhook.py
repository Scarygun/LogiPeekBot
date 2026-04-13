import asyncio
import os
import sys
import logging
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def set_webhook(url: str):
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN topilmadi!")
        return

    bot = Bot(token=token)
    
    # URL ni to'g'rilash (admin so'rovi bo'lmasa, api/webhook qo'shish)
    if not url.endswith('/api/webhook'):
        if url.endswith('/'):
            url = url + 'api/webhook'
        else:
            url = url + '/api/webhook'
            
    logger.info(f"Webhook o'rnatilmoqda: {url}")
    
    try:
        success = await bot.set_webhook(url=url)
        if success:
            logger.info("Webhook muvaffaqiyatli o'rnatildi!")
            info = await bot.get_webhook_info()
            logger.info(f"Webhook ma'lumotlari: {info}")
        else:
            logger.error("Webhook o'rnatib bo'lmadi.")
    except Exception as e:
        logger.error(f"Xatolik: {e}")

async def delete_webhook():
    token = os.getenv('BOT_TOKEN')
    if not token:
        logger.error("BOT_TOKEN topilmadi!")
        return

    bot = Bot(token=token)
    logger.info("Webhook o'chirilmoqda...")
    
    try:
        success = await bot.delete_webhook()
        if success:
            logger.info("Webhook muvaffaqiyatli o'chirildi!")
        else:
            logger.error("Webhook o'chirib bo'lmadi.")
    except Exception as e:
        logger.error(f"Xatolik: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Foydalanish: ")
        print("  python set_webhook.py set https://your-app.vercel.app")
        print("  python set_webhook.py delete")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "set":
        if len(sys.argv) < 3:
            print("Xato: URL ko'rsatilmadi!")
            sys.exit(1)
        asyncio.run(set_webhook(sys.argv[2]))
    elif cmd == "delete":
        asyncio.run(delete_webhook())
    elif cmd == "info":
        async def get_info():
            token = os.getenv('BOT_TOKEN')
            if not token:
                logger.error("BOT_TOKEN topilmadi!")
                return
            bot = Bot(token=token)
            info = await bot.get_webhook_info()
            logger.info(f"Hozirgi Webhook ma'lumotlari: {info}")
        asyncio.run(get_info())
    else:
        print(f"Noma'lum buyruq: {cmd}")
