import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from config import USER_API_ID, USER_API_HASH, USER_PHONE_NUMBER, TELETHON_STRING_SESSION
from database import load_groups_from_json
import re

logger = logging.getLogger(__name__)

class CustomTelethonClient:
    def __init__(self):
        is_vercel = os.getenv('VERCEL')
        
        if TELETHON_STRING_SESSION:
            logger.info("Telethon StringSession dan foydalanilmoqda...")
            self.client = TelegramClient(StringSession(TELETHON_STRING_SESSION), USER_API_ID, USER_API_HASH)
        elif is_vercel:
            # Vercel-da local session fayli ishlatib bo'lmaydi
            logger.error("XATO: Vercel-da TELETHON_STRING_SESSION bo'lishi shart!")
            raise RuntimeError(
                "Vercel-da 'user_session.session' faylini yaratib bo'lmaydi (Read-only filesystem). "
                "Iltimos, 'TELETHON_STRING_SESSION' environment variable-ni Vercel-ga qo'shing."
            )
        else:
            logger.info("Telethon local session faylidan foydalanilmoqda...")
            self.client = TelegramClient('user_session', USER_API_ID, USER_API_HASH)
        self.is_authorizing = False

    async def connect(self, send_code=False):
        if not self.client.is_connected():
            logger.info("Telethon client ulanmoqda...")
            await self.client.connect()
        
        is_auth = await self.client.is_user_authorized()
        if not is_auth:
            if send_code:
                logger.info("Telethon client avtorizatsiyadan o'tmagan. Kod yuborishga harakat qilinmoqda...")
                try:
                    # send_code_request is part of the manual flow
                    await self.client.send_code_request(USER_PHONE_NUMBER)
                    self.is_authorizing = True
                    logger.info(f"Avtorizatsiya kodi {USER_PHONE_NUMBER} raqamiga yuborildi.")
                except FloodWaitError as e:
                    logger.error(f"FloodWaitError: {e.seconds} soniya kutish kerak.")
                    raise
                except Exception as e:
                    logger.error(f"Kod yuborishda xato: {e}")
                    raise
            else:
                logger.info("Telethon client avtorizatsiyadan o'tmagan. 'python login.py' dan foydalaning.")
            return False
        
        logger.info("Telethon client muvaffaqiyatli ulandi va avtorizatsiyadan o'tdi.")
        return True

    async def disconnect(self):
        if self.is_connected():
            logger.info("Telethon client uzilmoqda...")
            await self.client.disconnect()
            logger.info("Telethon client uzildi.")

    def is_connected(self):
        return self.client.is_connected()

    async def verify_code(self, code):
        if not self.is_authorizing:
             # Agar connect(send_code=True) chaqirilgan bo'lsa is_authorizing True bo'ladi
             # Aks holda bu yerda xato beradi
             pass
        
        try:
            await self.client.sign_in(USER_PHONE_NUMBER, code)
            self.is_authorizing = False
            logger.info("Kod tasdiqlandi. Avtorizatsiya muvaffaqiyatli.")
            return True
        except SessionPasswordNeededError:
            logger.warning("Ikki bosqichli tekshiruv (2FA) yoqilgan. Parol talab qilinadi.")
            return "password_required"
        except Exception as e:
            logger.error(f"Kod tasdiqlashda xato: {e}")
            return False

    async def verify_password(self, password):
        try:
            await self.client.sign_in(password=password)
            self.is_authorizing = False
            logger.info("Parol tasdiqlandi. Avtorizatsiya muvaffaqiyatli.")
            return True
        except Exception as e:
            logger.error(f"Parol tasdiqlashda xato: {e}")
            return False

    def _extract_username(self, link):
        if not link:
            return None
        link = link.strip()
        match = re.search(r'(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]+)', link)
        if match:
            return match.group(1)
        if link.startswith('@'):
            return link[1:]
        if re.match(r'^[a-zA-Z0-9_]+$', link):
            return link
        return None

    async def search_messages(self, from_city, to_city, limit=20, progress_callback=None):
        if not self.is_connected():
            return []
        groups = await load_groups_from_json()
        if not groups:
            return []
        
        all_results = []
        query = f"{from_city} {to_city}"
        seen_texts = set()
        
        # Simplified search logic for brevity
        for group_link in groups:
            username = self._extract_username(group_link)
            if not username: continue
            try:
                entity = await self.client.get_entity(username)
                async for message in self.client.iter_messages(entity, search=query, limit=10):
                    if message.text and (from_city.lower() in message.text.lower() and to_city.lower() in message.text.lower()):
                        if message.text in seen_texts: continue
                        seen_texts.add(message.text)
                        all_results.append({
                            'group_title': entity.title,
                            'text': message.text,
                            'date': message.date.strftime("%Y-%m-%d %H:%M"),
                            'link': f"https://t.me/{username}/{message.id}"
                        })
            except:
                continue
        return all_results

telethon_client = CustomTelethonClient()
