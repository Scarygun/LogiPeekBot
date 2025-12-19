# config.py
import os

# Adminlar ro'yxati
ADMINS = [API]

# Bot egasining ID raqami (xabar tarqatish uchun)
OWNER_ID = API # O'zingizning Telegram ID'ingizni qo'ying

# Ma'lumotlar bazasi nomi
DATABASE_NAME = 'bot_data.db'
USERS_JSON_FILE = 'users.json' # Yangi qo'shildi: Foydalanuvchi ma'lumotlarini saqlash uchun JSON fayli
GROUPS_JSON_FILE = 'groups.json' # Guruhlarni saqlash uchun JSON fayli
CONTACTS_JSON_FILE = 'contacts.json' # Kontaktlarni saqlash uchun JSON fayli
ACTIVE_GROUPS_JSON_FILE = 'active_groups.json' # Muvaffaqiyatli guruhlar ro'yxati

# Bot tokeni (to‘g‘ridan-to‘g‘ri yozilgan)
BOT_TOKEN = 'TOKEN'

# Foydalanuvchi Telethon sozlamalari
USER_API_ID = 
USER_API_HASH = '----'
USER_PHONE_NUMBER = 'Nomer' # Telethon foydalanuvchi hisobi uchun telefon raqami

# Log fayli sozlamalari
LOG_FILE_NAME = 'bot_activity.log' # Bot loglarini saqlash uchun fayl nomi
