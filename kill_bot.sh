#!/bin/bash

echo "Bot jarayonlari qidirilmoqda..."

# 1. Yumshoq to'xtatish (SIGTERM)
pkill -f "bot.py"

# Biroz kutish
sleep 1

# 2. Agar hali ham ishlab turgan bo'lsa, majburiy to'xtatish (SIGKILL)
# pgrep -f "bot.py" jarayon IDlarini qaytaradi
PIDS=$(pgrep -f "bot.py")

if [ -n "$PIDS" ]; then
    echo "⚠️ Ba'zi jarayonlar to'xtamadi. Majburiy o'chirilmoqda (kill -9)..."
    echo "$PIDS" | xargs kill -9
    echo "✅ Bot majburiy to'xtatildi."
else
    echo "✅ Bot muvaffaqiyatli to'xtatildi."
fi
