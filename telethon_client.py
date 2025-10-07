import asyncio
from telethon import TelegramClient
from telethon.tl.types import Message
from config import USER_API_ID, USER_API_HASH, USER_PHONE_NUMBER
from database import get_all_groups
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomTelethonClient:
    def __init__(self):
        self.client = None
        self.api_id = USER_API_ID
        self.api_hash = USER_API_HASH
        self.phone_number = USER_PHONE_NUMBER
        self.session_name = 'logi_peek_bot_session'
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
            
            search_queries = [
                f"{from_city}-{to_city}",
                f"{to_city}-{from_city}",
                f"{from_city} {to_city}",
                f"{to_city} {from_city}"
            ]
            found_first_match = False

            for group_entry in groups:
                if found_first_match:
                    break

                group_id_raw = group_entry['group_id'] # O'zgartirildi: group_entry['group_id'] orqali group_id ni olamiz
                
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
                                found_first_match = True
                                break
                        if found_first_match:
                            break
                    
                    if not found_first_match:
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

telethon_client = CustomTelethonClient()
