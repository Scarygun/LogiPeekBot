import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

def get_env_list(key, default=None):
    val = os.getenv(key)
    if val:
        try:
            return [int(x.strip()) for x in val.split(',')]
        except ValueError:
            return [x.strip() for x in val.split(',')]
    return default

# Adminlar ro'yxati
ADMINS = get_env_list('ADMINS', [])

# Bot egasining ID raqami
OWNER_ID = int(os.getenv('OWNER_ID', 0))

# Ma'lumotlar bazasi va fayl nomlari
DATABASE_NAME = os.getenv('DATABASE_NAME', 'bot_data.db')
USERS_JSON_FILE = 'users.json'
GROUPS_JSON_FILE = 'groups.json'
CONTACTS_JSON_FILE = 'contacts.json'
ACTIVE_GROUPS_JSON_FILE = 'active_groups.json'

# MongoDB sozlamalari
MONGODB_URI = os.getenv('MONGODB_URI')
DATABASE_NAME_MONGO = os.getenv('DATABASE_NAME_MONGO', 'logipeek_db')

# Bot tokeni
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Foydalanuvchi Telethon sozlamalari
USER_API_ID = int(os.getenv('USER_API_ID', 0))
USER_API_HASH = os.getenv('USER_API_HASH')
USER_PHONE_NUMBER = os.getenv('USER_PHONE_NUMBER')
TELETHON_STRING_SESSION = os.getenv('TELETHON_STRING_SESSION') # Vercel uchun

# TextUP SMS API sozlamalari
TEXTUP_EMAIL = os.getenv('TEXTUP_EMAIL', os.getenv('TEXTUP_API_KEY', ''))
TEXTUP_PASSWORD = os.getenv('TEXTUP_PASSWORD', os.getenv('TEXTUP_API_SECRET', ''))

# Webhook sozlamalari (Vercel uchun)
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Log fayli sozlamalari
LOG_FILE_NAME = os.getenv('LOG_FILE_NAME', 'bot_activity.log')

# Yordam so'rovlari uchun guruh IDsi
SUPPORT_GROUP_ID = int(os.getenv('SUPPORT_GROUP_ID', 0))
