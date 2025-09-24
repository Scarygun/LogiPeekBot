from telegram import BotCommand

async def set_bot_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("help", "Yordam")
    ])
