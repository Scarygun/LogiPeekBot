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
            total_groups = len(groups)
            logger.info(f"Qidiruv boshlandi: From '{from_city}', To '{to_city}'")
            logger.info(f"Jami {total_groups} ta guruhda qidirilmoqda...")
            
            if total_groups == 0:
                logger.warning("Ma'lumotlar bazasida guruhlar topilmadi!")
                return []
            
            # Qaysi guruhlarda qidirilayotganini ko'rsatish
            group_names = []
            for group_entry in groups:
                # sqlite3.Row obyekti .get() metodiga ega emas
                try:
                    group_name = str(group_entry['group_name']) if group_entry['group_name'] is not None else "Noma'lum"
                except (KeyError, IndexError):
                    group_name = "Noma'lum"
                group_names.append(group_name)
            logger.info(f"Qidirilayotgan guruhlar: {', '.join(group_names[:10])}{'...' if len(group_names) > 10 else ''}")
            
            # Manzil variantlarini yaratish (katta-kichik harf, variantlar)
            from_city_variants = [
                from_city.lower(),
                from_city.upper(),
                from_city.capitalize(),
                from_city.title()
            ]
            to_city_variants = [
                to_city.lower(),
                to_city.upper(),
                to_city.capitalize(),
                to_city.title()
            ]
            
            # Qidiruv so'rovlari - turli formatlarda
            search_queries = [
                f"{from_city}-{to_city}",
                f"{to_city}-{from_city}",
                f"{from_city} {to_city}",
                f"{to_city} {from_city}",
                f"{from_city} -> {to_city}",
                f"{to_city} <- {from_city}",
                f"{from_city} → {to_city}",
                f"{to_city} ← {from_city}"
            ]
            
            # Manzil variantlarini qo'shish
            for from_var in from_city_variants:
                for to_var in to_city_variants:
                    if f"{from_var}-{to_var}" not in search_queries:
                        search_queries.append(f"{from_var}-{to_var}")
                    if f"{from_var} {to_var}" not in search_queries:
                        search_queries.append(f"{from_var} {to_var}")

            searched_groups = 0
            for group_entry in groups:
                group_id_raw = group_entry['group_id']
                # sqlite3.Row obyekti .get() metodiga ega emas
                try:
                    group_name = str(group_entry['group_name']) if group_entry['group_name'] is not None else "Noma'lum"
                except (KeyError, IndexError):
                    group_name = "Noma'lum"
                
                # group_id ni to'g'ri formatga o'tkazish
                group_id_str = str(group_id_raw)
                match = re.match(r'(?:https?://)?t\.me/([a-zA-Z0-9_]+)', group_id_str)
                if match:
                    group_id = match.group(1)
                else:
                    group_id = group_id_raw

                searched_groups += 1
                logger.info(f"[{searched_groups}/{total_groups}] Guruh qidirilmoqda: {group_name} (@{group_id})")
                
                try:
                    entity = await self.client.get_entity(group_id)
                    logger.info(f"Guruh obyekti olindi: {entity.title if hasattr(entity, 'title') else group_id}")
                    
                    # Xabarlarni olish va matnida manzilni tekshirish
                    found_messages = set()  # Takrorlanishni oldini olish uchun
                    found_in_group = False
                    
                    # Avval Telegram search dan foydalanish
                    for query_text in search_queries[:8]:  # Faqat asosiy so'rovlarni
                        try:
                            async for message in self.client.iter_messages(entity, search=query_text, limit=5):
                                if isinstance(message, Message) and message.text and message.id not in found_messages:
                                    found_messages.add(message.id)
                                    found_in_group = True
                                    
                                    # Link yaratish
                                    try:
                                        if hasattr(message, 'peer_id') and message.peer_id:
                                            if hasattr(message.peer_id, 'channel_id'):
                                                channel_username = entity.username if hasattr(entity, 'username') else None
                                                if channel_username:
                                                    link = f"https://t.me/{channel_username}/{message.id}"
                                                else:
                                                    link = f"https://t.me/c/{abs(message.peer_id.channel_id)}/{message.id}"
                                            else:
                                                # Guruh bo'lsa
                                                link = "#"
                                        else:
                                            link = "#"
                                    except Exception as link_error:
                                        logger.debug(f"Link yaratishda xatolik: {link_error}")
                                        link = "#"

                                    results.append({
                                        'group_title': entity.title if hasattr(entity, 'title') else group_name,
                                        'group_id': group_id,
                                        'date': message.date.strftime('%Y-%m-%d %H:%M'),
                                        'sender': message.sender.first_name if message.sender and hasattr(message.sender, 'first_name') else "Noma'lum",
                                        'text': message.text,
                                        'link': link,
                                        'query': query_text
                                    })
                        except Exception as search_error:
                            logger.debug(f"Qidiruv so'rovida xatolik ({query_text}): {search_error}")
                            continue
                    
                    # Agar Telegram search natija bermasa, so'nggi xabarlarni tekshirish
                    if not found_in_group:
                        try:
                            # So'nggi 50 ta xabarni olish va matnida manzilni tekshirish
                            async for message in self.client.iter_messages(entity, limit=50):
                                if isinstance(message, Message) and message.text and message.id not in found_messages:
                                    message_text_lower = message.text.lower()
                                    
                                    # Manzil variantlarini tekshirish
                                    from_found = any(var.lower() in message_text_lower for var in from_city_variants)
                                    to_found = any(var.lower() in message_text_lower for var in to_city_variants)
                                    
                                    if from_found and to_found:
                                        found_messages.add(message.id)
                                        found_in_group = True
                                        
                                        # Link yaratish
                                        try:
                                            if hasattr(message, 'peer_id') and message.peer_id:
                                                if hasattr(message.peer_id, 'channel_id'):
                                                    channel_username = entity.username if hasattr(entity, 'username') else None
                                                    if channel_username:
                                                        link = f"https://t.me/{channel_username}/{message.id}"
                                                    else:
                                                        link = f"https://t.me/c/{abs(message.peer_id.channel_id)}/{message.id}"
                                                else:
                                                    link = "#"
                                            else:
                                                link = "#"
                                        except Exception as link_error:
                                            logger.debug(f"Link yaratishda xatolik: {link_error}")
                                            link = "#"

                                        results.append({
                                            'group_title': entity.title if hasattr(entity, 'title') else group_name,
                                            'group_id': group_id,
                                            'date': message.date.strftime('%Y-%m-%d %H:%M'),
                                            'sender': message.sender.first_name if message.sender and hasattr(message.sender, 'first_name') else "Noma'lum",
                                            'text': message.text,
                                            'link': link,
                                            'query': f"{from_city} -> {to_city} (matn qidiruv)"
                                        })
                        except Exception as msg_error:
                            logger.debug(f"Xabarlarni olishda xatolik: {msg_error}")
                            continue
                    
                    if found_in_group:
                        logger.info(f"✅ {group_name} guruhida {len([r for r in results if r.get('group_id') == group_id])} ta natija topildi")
                    else:
                        logger.info(f"❌ {group_name} guruhida natija topilmadi")
                        
                except Exception as e:
                    logger.error(f"❌ Guruh ({group_name} - {group_id}) ichida qidirishda xatolik: {e}")
                    continue
            
            logger.info(f"Qidiruv yakunlandi. Jami {len(results)} ta natija topildi.")
            return results
        except Exception as e:
            logger.error(f"Telethon qidiruv xatosi: {e}")
            return []
    
    async def disconnect(self):
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            self.is_authorized = False

telethon_client = CustomTelethonClient()
