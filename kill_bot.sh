#!/bin/bash

echo "Bot jarayonlarini tozalash boshlandi..."

# 1. Barcha python bot jarayonlarini o'chirish (majburiy)
pkill -9 -f "bot.py"
pkill -9 -f "python3 bot.py"
pkill -9 -f "python bot.py"
pkill -9 -f "venv/bin/python bot.py"
ps aux | grep "bot.py" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null

# 1 soniya kutish
sleep 1

# 2. Tozalanganini tekshirish
PIDS=$(pgrep -f "bot.py")

if [ -n "$PIDS" ]; then
    echo "⚠️ Ba'zi jarayonlar hali ham o'chmadi ($PIDS). Iltimos, kompyuterni qayta ishga tushiring yoki qo'lda kill qiling."
else
    # 3. Loglarni tozalash (ixtiyoriy, muammolarni aniq ko'rish uchun)
    # rm -f bot_output.log bot_activity.log
    echo "✅ MacBook bot jarayonlaridan to'liq tozalandi."
    echo "Endi 'python bot.py' komandasi bilan botni xavfsiz ishga tushirishingiz mumkin."
fi
