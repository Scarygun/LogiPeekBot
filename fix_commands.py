import asyncio
import logging
from telegram import Bot, BotCommand
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_commands():
    if not BOT_TOKEN:
        print("BOT_TOKEN topilmadi!")
        return

    bot = Bot(token=BOT_TOKEN)
    
    # 1. Delete existing commands
    print("Commands o'chirilmoqda...")
    await bot.delete_my_commands()
    print("Commands o'chirildi.")

    # 2. Set new commands
    commands = [
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("search", "Yuk qidirish"),
        BotCommand("add_group", "Guruh qo'shish"),
        BotCommand("add_contact", "Kontakt qo'shish"),
        BotCommand("balance", "Balansni tekshirish"),
        BotCommand("feedback", "Fikr bildirish"),
        BotCommand("language", "Tilni o'zgartirish"),
        BotCommand("help", "Yordam")
    ]
    
    print("Yangi commands o'rnatilmoqda...")
    await bot.set_my_commands(commands)
    print("Yangi commands o'rnatildi!")

    # 3. Verify
    current_commands = await bot.get_my_commands()
    print("Hozirgi commands:")
    for cmd in current_commands:
        print(f"/{cmd.command} - {cmd.description}")

if __name__ == "__main__":
    asyncio.run(fix_commands())
