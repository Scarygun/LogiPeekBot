import logging
import asyncio
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from config import USER_API_ID, USER_API_HASH, USER_PHONE_NUMBER
from database import load_groups_from_json
import re

logger = logging.getLogger(__name__)

class CustomTelethonClient:
    def __init__(self):
        self.client = TelegramClient('user_session', USER_API_ID, USER_API_HASH)
        self.is_authorizing = False

    async def connect(self):
        if not self.is_connected():
            logger.info("Telethon client ulanmoqda...")
            try:
                await self.client.connect()
                if not await self.client.is_user_authorized():
                    logger.info("Telethon client avtorizatsiyadan o'tmagan. Kod yuborilmoqda...")
                    await self.client.send_code_request(USER_PHONE_NUMBER)
                    self.is_authorizing = True
                    logger.info(f"Avtorizatsiya kodi {USER_PHONE_NUMBER} raqamiga yuborildi.")
                    return False
                else:
                    logger.info("Telethon client muvaffaqiyatli ulandi va avtorizatsiyadan o'tdi.")
                    return True
            except Exception as e:
                logger.error(f"Telethon client ulanishida yoki avtorizatsiyada xato: {e}")
                self.is_authorizing = False
                raise
        return await self.client.is_user_authorized()

    async def disconnect(self):
        if self.is_connected():
            logger.info("Telethon client uzilmoqda...")
            await self.client.disconnect()
            logger.info("Telethon client uzildi.")

    def is_connected(self):
        return self.client.is_connected()

    async def verify_code(self, code):
        if not self.is_authorizing:
            logger.warning("Avtorizatsiya jarayoni boshlanmagan.")
            return False
        
        try:
            await self.client.sign_in(USER_PHONE_NUMBER, code)
            self.is_authorizing = False
            logger.info("Kod tasdiqlandi. Avtorizatsiya muvaffaqiyatli.")
            return True
        except Exception as e:
            logger.error(f"Kod tasdiqlashda xato: {e}")
            return False

    def _extract_username(self, link):
        """Linkdan username ni ajratib olish"""
        if not link:
            return None
        
        link = link.strip()
        
        # https://t.me/username
        match = re.search(r'(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]+)', link)
        if match:
            return match.group(1)
            
        # @username
        if link.startswith('@'):
            return link[1:]
            
        # username (faqat harflar, raqamlar va pastki chiziq)
        if re.match(r'^[a-zA-Z0-9_]+$', link):
            return link
            
        return None

    async def search_messages(self, from_city, to_city, limit=20, progress_callback=None):
        if not self.is_connected():
            logger.error("Telethon client ulanmagan. Qidiruv amalga oshirilmaydi.")
            return []

        logger.info(f"Qidiruv boshlandi: From '{from_city}', To '{to_city}'")
        
        # Guruhlarni olish (groups.json dan)
        groups = await load_groups_from_json()
        total_groups = len(groups)
        logger.info(f"groups.json dan {total_groups} ta guruh topildi.")
        
        if total_groups == 0:
            logger.warning("Hech qanday guruh topilmadi!")
            return []

        # Dialoglarni oldindan yuklab olish va map yaratish
        username_map = {}
        try:
            logger.info("Dialoglar yuklanmoqda...")
            dialogs = await self.client.get_dialogs()
            for d in dialogs:
                if hasattr(d.entity, 'username') and d.entity.username:
                    username_map[d.entity.username.lower()] = d.entity
            logger.info(f"Dialoglar yuklandi. {len(username_map)} ta guruh/kanal xotiraga olindi.")
        except Exception as e:
            logger.warning(f"Dialoglarni yuklashda xatolik: {e}")
            # Dialoglarsiz ham davom etamiz, lekin har bir guruh uchun API call bo'ladi

        all_results = []
        searched_groups = 0
        
        # Asosiy qidiruv so'zi
        query = f"{from_city} {to_city}"

        for group_link in groups:
            searched_groups += 1
            
            # Linkdan username ni olish
            username = self._extract_username(group_link)
            if not username:
                logger.warning(f"Linkdan username aniqlanmadi: {group_link}")
                continue
                
            # Har 5 ta guruhdan keyin log chiqarish
            if searched_groups % 5 == 0:
                logger.info(f"[{searched_groups}/{total_groups}] Guruhlar tekshirildi...")

            entity = None
            actual_group_name = username

            try:
                # 1. Lokal map dan qidirish (Eng tez va xavfsiz)
                if username.lower() in username_map:
                    entity = username_map[username.lower()]
                    actual_group_name = entity.title if hasattr(entity, 'title') else username
                    # logger.info(f"✅ Guruh keshdan topildi: {username}")
                
                # 2. Agar lokalda yo'q bo'lsa, API orqali olish (Ehtiyotkorlik bilan)
                else:
                    logger.info(f"⚠️ Guruh keshda yo'q, API orqali so'ralmoqda: {username}")
                    try:
                        entity = await self.client.get_entity(username)
                        actual_group_name = entity.title if hasattr(entity, 'title') else username
                        # Muvaffaqiyatli topilsa, keyingi safar uchun map ga qo'shib qo'yamiz
                        username_map[username.lower()] = entity
                        # Rate limit uchun kutish
                        await asyncio.sleep(1) 
                    except FloodWaitError as e:
                        logger.warning(f"❌ FloodWaitError ({username}): {e.seconds} soniya kutish kerak. O'tkazib yuboriladi.")
                        continue
                    except ValueError:
                        logger.warning(f"❌ Guruh topilmadi yoki kirish imkoni yo'q: {username}")
                        continue
                    except Exception as e:
                        logger.warning(f"❌ Guruhni olishda xatolik ({username}): {e}")
                        continue

                # Guruhda xabarlarni qidirish
                if entity:
                    try:
                        messages = self.client.iter_messages(entity, search=query, limit=5)
                        
                        async for message in messages:
                            if message.text:
                                result = {
                                    'group_title': actual_group_name,
                                    'text': message.text,
                                    'date': message.date.strftime("%Y-%m-%d %H:%M"),
                                    'sender': 'Noma\'lum',
                                    'link': f"https://t.me/{entity.username}/{message.id}" if hasattr(entity, 'username') and entity.username else '#'
                                }
                                
                                try:
                                    sender = await message.get_sender()
                                    if sender:
                                        result['sender'] = f"{sender.first_name} {sender.last_name if sender.last_name else ''}".strip()
                                except:
                                    pass
                                    
                                all_results.append(result)
                    except Exception as e:
                        logger.warning(f"Xabarlarni qidirishda xatolik ({username}): {e}")

                # Progress callback
                if progress_callback and (searched_groups % 20 == 0 or searched_groups == total_groups):
                    await progress_callback(searched_groups, total_groups, all_results)
                    
            except Exception as e:
                logger.warning(f"Umumiy xatolik ({username}): {e}")
                continue
        
        logger.info(f"Qidiruv yakunlandi. Jami {len(all_results)} ta natija topildi.")
        return all_results

# Global client obyekti
telethon_client = CustomTelethonClient()
