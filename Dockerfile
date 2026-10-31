# Python bazaviy obrazi (Debian Bookworm - barqaror va tez)
FROM python:3.10-slim-bookworm

# Python kesh va buferlash sozlamalari (loglar terminalda darhol ko'rinishi uchun)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Tashkent

# Ishchi katalogni belgilash
WORKDIR /app

# Talablar faylini nusxalash va o'rnatish (barcha paketlar uchun binary wheel mavjud)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini nusxalash
COPY . /app/

# Botni ishga tushirish
CMD ["python", "bot.py"]
