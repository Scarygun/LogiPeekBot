#!/bin/bash

# Script joylashgan papkaga o'tish
cd "$(dirname "$0")"

# Virtual muhitni tekshirish va faollashtirish
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "🚀 Bot ishga tushirilmoqda..."
python bot.py
