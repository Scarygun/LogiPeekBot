import asyncio
from telethon import TelegramClient
from telethon.tl.types import Message
from config import USER_API_ID, USER_API_HASH, USER_PHONE_NUMBER # Yangilangan import
from database import get_all_groups
import logging
import re # Added for regex

# Log konfiguratsiyasi
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telethon klienti
class CustomTelethonClient:
    def __init__(self):
        self.client = None
        self.api_id = USER_API_ID # Use user API ID for search
        self.api_hash = USER_API_HASH # Use user API hash for search
        self.phone_number = USER_PHONE_NUMBER # Telefon raqamini konfiguratsiyadan olish
        self.session_name = 'logi_peek_bot_session' # Sessiya nomini belgilash
        self.is_authorized = False
    
    async def connect(self):
        if not self.api_id or not self.api_hash:
            raise ValueError("USER_API_ID yoki USER_API_HASH topilmadi. .env faylini tekshiring.")
        if not self.phone_number:
            raise ValueError("USER_PHONE_NUMBER topilmadi. .env faylini tekshiring.")
        
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.start(phone=self.phone_number)
        self.is_authorized = True
        print("Telethon client (foydalanuvchi rejimida) muvaffaqiyatli ulandi")
        return True
    
    def authorized(self):
        return self.is_authorized and self.client and self.client.is_connected()
    
    def is_connected(self):
        return self.client and self.client.is_connected()
    
    async def search_messages(self, from_city, to_city):
        results = []
        if not self.is_connected():
            logger.error("Telethon client (foydalanuvchi rejimida) ulanmagan.")
            return []
        
        try:
            groups = await get_all_groups()
            logger.info(f"Qidirilmoqda: From '{from_city}', To '{to_city}' ")
            
            # Qidiruv so'rovlari ro'yxati
            search_queries = [
                f"{from_city}-{to_city}",
                f"{to_city}-{from_city}",
                f"{from_city} {to_city}", # Oldingi variantni ham qoldiramiz
                f"{to_city} {from_city}"  # Oldingi variantni ham qoldiramiz
            ]
            found_first_match = False

            for group_entry in groups:
                if found_first_match: # Birinchi topilgan yukni olgach, boshqa guruhlarni tekshirmaymiz
                    break

                group_id_raw = group_entry['group_id'] # row_factory tufayli lug'at sifatida olinadi
                
                match = re.match(r'(?:https?://)?t.me/([a-zA-Z0-9_]+)', group_id_raw)
                if match:
                    group_id = match.group(1)
                else:
                    group_id = group_id_raw

                logger.info(f"Guruh qidirilmoqda: {group_id}")
                try:
                    entity = await self.client.get_entity(group_id)
                    logger.info(f"Guruh obyekti olindi: {entity.title if hasattr(entity, 'title') else group_id}")
                    
                    for query_text in search_queries:
                        logger.info(f"Guruh '{group_id}' ichida '{query_text}' so'rovi bo'yicha qidirilmoqda (limit: 1)...")
                        async for message in self.client.iter_messages(entity, search=query_text, limit=1):
                            if isinstance(message, Message) and message.text:
                                logger.info(f"Xabar topildi ({group_id}, so'rov: '{query_text}'): {message.text[:100]}...")
                                
                                if message.peer_id and hasattr(message.peer_id, 'channel_id'):
                                    channel_username = (await self.client.get_entity(message.peer_id.channel_id)).username
                                    if channel_username:
                                        link = f"https://t.me/{channel_username}/{message.id}"
                                    else:
                                        link = "#"
                                else:
                                    link = "#"

                                results.append({
                                    'group_title': entity.title if entity.title else 'Noma’lum guruh',
                                    'date': message.date.strftime('%Y-%m-%d'),
                                    'sender': message.sender.first_name if message.sender else 'Noma’lum',
                                    'text': message.text,
                                    'link': link
                                })
                                found_first_match = True # Birinchi topilgan yukni belgilaymiz
                                break # Faqat bitta yukni olamiz
                        if found_first_match:
                            break
                    
                    if not found_first_match: # Agar bu guruhda topilmasa, keyingi guruhga o'tamiz
                        logger.info(f"Guruhda hech qanday so'rov bo'yicha xabar topilmadi: {group_id}")
                except Exception as e:
                    logger.error(f"Guruh ({group_id}) ichida qidirishda xatolik: {e}")
            return results
        except Exception as e:
            logger.error(f"Telethon qidiruv xatosi: {e}")
            return []
    
    async def disconnect(self):
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            self.is_authorized = False

# Global telethon klienti
telethon_client = CustomTelethonClient()
