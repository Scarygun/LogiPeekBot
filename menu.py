from telegram import BotCommand

async def set_bot_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("search", "Yuk qidirish"),
        BotCommand("add_group", "Guruh qo'shish"),
        BotCommand("add_contact", "Kontakt qo'shish"),
        BotCommand("balance", "Balansni tekshirish"),
        BotCommand("feedback", "Fikr bildirish"),
        BotCommand("language", "Tilni o'zgartirish"),
        BotCommand("help", "Yordam")
    ])
