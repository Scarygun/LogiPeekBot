import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta

import difflib
import re

logger = logging.getLogger(__name__)

from database import _read_json
from config import USERS_JSON_FILE

# O'zbekiston viloyatlari, asosiy shaharlari va tumanlari sinonim / variantlari
LOCATION_ALIASES = {
    'toshkent': {'toshkent', 'tashkent', 'tosh', 'tash'},
    'samarqand': {'samarqand', 'samarkand', 'samarkant'},
    'buxoro': {'buxoro', 'buxara', 'bukhara', 'buhoro'},
    'andijon': {'andijon', 'andijan'},
    'namangan': {'namangan'},
    'fargona': {'fargona', "farg'ona", "farg‘ona", 'fergana', 'fergona'},
    'qashqadaryo': {'qashqadaryo', 'kashkadarya', 'qarshi', 'karshi', 'koson', 'kason', 'kasan', 'shahrisabz', 'shaxrisabz'},
    'surxondaryo': {'surxondaryo', 'surxandarya', 'termiz', 'termez'},
    'xorazm': {'xorazm', 'khorezm', 'horazm', 'urganch', 'urgench', 'xiva'},
    'navoiy': {'navoiy', 'navoi'},
    'jizzax': {'jizzax', 'djizak', 'jizak'},
    'sirdaryo': {'sirdaryo', 'sirdarya', 'guliston', 'gulistan'},
    'qoraqalpogiston': {'qoraqalpogiston', 'karakalpakstan', 'nukus', 'nókis', 'nokis'},
    'koson': {'koson', 'kason', 'kasan', 'kassan'},
    'nukus': {'nukus', 'nókis', 'nokis'},
    'qarshi': {'qarshi', 'karshi'},
}

STOPWORDS = {
    'tumani', 'tuman', 'viloyati', 'viloyat', 'shahri', 'shahar', 
    'vil', 'sh', 't', 'rayon', 'oblast', 'gorod', 'oʻzbekiston', 
    'ozbekiston', 'uzbekistan', 'respublikasi', 'resp'
}

WILDCARD_TERMS = {
    'barchasi', 'barcha', 'farqiyoq', 'farqi yoq', "farqi yo'q", "farqi yo‘q",
    'ixtiyoriy', 'hamma', 'hammasi', 'all', 'har qanday', '-', '*', 'lyuboy', 'lyubaya', 'har joyga'
}

def clean_and_tokenize(text: str):
    """Joy nomidan ortiqcha so'zlarni olib tashlab, asosiy kalit so'zlarni ajratish"""
    if not text:
        return []
    cleaned = re.sub(r'[^a-zA-Z0-9\u0400-\u04FF\u02BB\u02BC\'`\u00F3\u00D3]', ' ', text.lower())
    words = cleaned.split()
    tokens = [w for w in words if w not in STOPWORDS and len(w) > 1]
    return tokens

def phonetic_key(word: str) -> str:
    """Imloviy xatolarni qoplash uchun fonetik kalit yaratish"""
    w = word.lower()
    w = w.replace('ó', 'o').replace('oʻ', 'o').replace("o'", 'o').replace('o`', 'o')
    w = w.replace('gʻ', 'g').replace("g'", 'g').replace('g`', 'g')
    w = w.replace('kh', 'x').replace('h', 'x')
    w = w.replace('q', 'k')
    w = w.replace('c', 's')
    w = w.replace('dj', 'j')
    w = re.sub(r'[aou]', '*', w)
    w = re.sub(r'[ei]', '#', w)
    w = re.sub(r'(.)\1+', r'\1', w)
    return w

def is_word_match(w1: str, w2: str) -> bool:
    """Ikki so'z o'rtasidagi to'g'ri, qisman yoki noaniq (fuzzy) moslikni aniqlash"""
    w1_l = w1.lower()
    w2_l = w2.lower()
    if w1_l == w2_l:
        return True
    if w1_l in w2_l or w2_l in w1_l:
        return True
        
    for key, group in LOCATION_ALIASES.items():
        if (w1_l in group or key == w1_l) and (w2_l in group or key == w2_l):
            return True

    if phonetic_key(w1) == phonetic_key(w2):
        return True

    if len(w1) >= 4 and len(w2) >= 4:
        sim = difflib.SequenceMatcher(None, w1_l, w2_l).ratio()
        if sim >= 0.70:
            return True
            
    return False

def location_matches(query: str, target: str) -> bool:
    """Foydalanuvchi qidiruvi bazadagi joy nomiga mos kelishini tekshirish"""
    if not query:
        return True
    q_clean = query.strip().lower()
    if q_clean in WILDCARD_TERMS:
        return True

    q_tokens = clean_and_tokenize(query)
    t_tokens = clean_and_tokenize(target)
    
    if not q_tokens:
        return True
    if not t_tokens:
        return False
        
    for qw in q_tokens:
        for tw in t_tokens:
            if is_word_match(qw, tw):
                return True
    return False

class BackendClient:
    def __init__(self):
        self.base_url = os.getenv('BACKEND_API_URL', 'https://api.vigo.uz')
        self.user_tokens = {}
        self._lock = asyncio.Lock()

    async def _login_user(self, user_id: str):
        """Foydalanuvchi ma'lumotlari bilan login qilish va tokenni olish"""
        users = _read_json(USERS_JSON_FILE, [])
        phone = None
        password = None
        
        if isinstance(users, list):
            for u in users:
                if str(u.get("user_id")) == str(user_id):
                    phone = u.get("vigo_phone")
                    password = u.get("vigo_password")
                    break
        elif isinstance(users, dict):
            if str(user_id) in users:
                phone = users[str(user_id)].get("vigo_phone")
                password = users[str(user_id)].get("vigo_password")
                
        if not phone or not password:
            # Fallback to system service account
            phone = os.getenv("BACKEND_USER", "+998915555390")
            password = os.getenv("BACKEND_PASS", "LogiPeekBot.0813261102")
            
        login_url = f"{self.base_url}/api/v1/auth/login/"
        payload = {
            "phone": phone,
            "password": password
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(login_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        token = data.get('tokens', {}).get('access')
                        expires_in = data.get('expires_in', 23 * 3600)
                        expires_at = datetime.now() + timedelta(seconds=expires_in)
                        
                        self.user_tokens[str(user_id)] = {
                            "token": token,
                            "expires_at": expires_at
                        }
                        logger.info(f"Foydalanuvchi {user_id} muvaffaqiyatli login qildi.")
                        return token
                    else:
                        logger.error(f"Foydalanuvchi {user_id} uchun login xatosi: {response.status}")
                        # If user's personal credentials failed, try system account as fallback
                        sys_phone = os.getenv("BACKEND_USER", "+998915555390")
                        sys_pass = os.getenv("BACKEND_PASS", "LogiPeekBot.0813261102")
                        if phone != sys_phone:
                            async with session.post(login_url, json={"phone": sys_phone, "password": sys_pass}) as sys_resp:
                                if sys_resp.status == 200:
                                    s_data = await sys_resp.json()
                                    s_token = s_data.get('tokens', {}).get('access')
                                    s_expires = s_data.get('expires_in', 23 * 3600)
                                    self.user_tokens[str(user_id)] = {
                                        "token": s_token,
                                        "expires_at": datetime.now() + timedelta(seconds=s_expires)
                                    }
                                    return s_token
                        return None
        except Exception as e:
            logger.error(f"Backend bilan bog'lanishda xatolik ({user_id}): {e}")
            return None

    async def _get_valid_token(self, user_id: str):
        """Yaroqli tokenni qaytaradi, kerak bo'lsa yangilaydi"""
        async with self._lock:
            user_data = self.user_tokens.get(str(user_id))
            if not user_data or not user_data.get("token") or datetime.now() >= user_data.get("expires_at"):
                token = await self._login_user(str(user_id))
                return token
            return user_data.get("token")

    async def search_loads(self, from_city: str, to_city: str, user_id: str):
        """Backend dan yuklarni izlash (imloviy xatolar va tuman/viloyat so'zlariga chidamli qidiruv)"""
        token = await self._get_valid_token(user_id)
        if not token:
            logger.error(f"Token yo'qligi sababli yuk izlab bo'lmadi (User: {user_id}).")
            return "NOT_LOGGED_IN"

        search_url = f"{self.base_url}/api/v1/cargo/marketplace/listings/"
        
        orig_clean = from_city.strip().lower()
        dest_clean = to_city.strip().lower()
        
        is_orig_wildcard = orig_clean in WILDCARD_TERMS
        is_dest_wildcard = dest_clean in WILDCARD_TERMS
        
        orig_tokens = clean_and_tokenize(from_city)
        dest_tokens = clean_and_tokenize(to_city)
        
        params = {}
        if not is_orig_wildcard and orig_tokens:
            params["origin"] = orig_tokens[0]
        if not is_dest_wildcard and dest_tokens:
            params["destination"] = dest_tokens[0]
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        loads = data if isinstance(data, list) else data.get('results', [])
                        
                        # Agar to'g'ridan-to'g'ri qidiruvda natija topilmasa (imloviy xato, o'zgargan nomlar),
                        # umumiy ro'yxatdan fuzzy va fonetik algoritm orqali qidiramiz
                        if not loads:
                            logger.info(f"Aniq qidiruv natija bermadi ({from_city} -> {to_city}). Noaniq (fuzzy) qidiruv ishga tushirilmoqda...")
                            async with session.get(search_url, headers=headers) as all_resp:
                                if all_resp.status == 200:
                                    all_data = await all_resp.json()
                                    all_loads = all_data if isinstance(all_data, list) else all_data.get('results', [])
                                    loads = [
                                        l for l in all_loads
                                        if location_matches(from_city, l.get('origin', '')) and location_matches(to_city, l.get('destination', ''))
                                    ]
                        
                        results = []
                        for load in loads:
                            title = load.get('title')
                            if not title:
                                title = f"{load.get('origin') or from_city} - {load.get('destination') or to_city}"
                            
                            desc = load.get('description')
                            if not desc:
                                desc = 'Yuk haqida to\'liq ma\'lumot yo\'q.'
                                
                            weight = load.get('weight_kg')
                            if weight:
                                desc += f"\n⚖️ Vazni: {weight} kg"
                            
                            price = load.get('price')
                            if price:
                                desc += f"\n💰 Narxi: {price} {load.get('currency') or ''}"
                                
                            sender_name = load.get('owner_name')
                            if not sender_name:
                                sender_name = 'Vigo Tizimi'
                                
                            pickup_date = load.get('pickup_date')
                            if not pickup_date:
                                pickup_date = datetime.now().strftime("%Y-%m-%d")
                                
                            link = load.get('id')
                            if link:
                                link = f"https://vigo.uz/listing/{link}"
                            else:
                                link = "#"
                                
                            results.append({
                                'id': load.get('id'),
                                'group_title': title,
                                'title': title,
                                'origin': load.get('origin', ''),
                                'destination': load.get('destination', ''),
                                'cargo_type': load.get('cargo_type', ''),
                                'food_subtype': load.get('food_subtype', ''),
                                'weight_kg': weight or load.get('weight'),
                                'price': price,
                                'currency': load.get('currency') or 'UZS',
                                'price_negotiable': load.get('price_negotiable'),
                                'pickup_date': pickup_date,
                                'required_delivery_date': load.get('required_delivery_date'),
                                'sender': sender_name,
                                'owner_name': sender_name,
                                'description': load.get('description', ''),
                                'required_doc_types': load.get('required_doc_types') or [],
                                'required_driver_document_types': load.get('required_driver_document_types') or [],
                                'required_listing_document_types': load.get('required_listing_document_types') or [],
                                'text': desc,
                                'date': pickup_date,
                                'link': link
                            })
                        
                        return results
                    elif response.status == 401:
                        logger.warning("Token yaroqsiz (401), qayta login qilinadi...")
                        if str(user_id) in self.user_tokens:
                            del self.user_tokens[str(user_id)]
                        return await self.search_loads(from_city, to_city, user_id)
                    else:
                        logger.error(f"Yuk izlashda xatolik: {response.status} - {await response.text()}")
                        return []
        except Exception as e:
            logger.error(f"Yuk izlash so'rovida xatolik: {e}")
            return []

    async def get_payment_card(self, user_id: str):
        """Admin tomonidan sozlangan to'lov kartasini olish"""
        token = await self._get_valid_token(user_id)
        if not token:
            return None
        url = f"{self.base_url}/api/v1/billing/payment-card/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 409:
                        logger.warning("To'lov kartasi sozlanmagan (409)")
                        return None
                    elif response.status == 401:
                        if str(user_id) in self.user_tokens:
                            del self.user_tokens[str(user_id)]
                        return None
        except Exception as e:
            logger.error(f"get_payment_card xatolik: {e}")
        return None

    async def get_subscription_plans(self, user_id: str):
        """Mavjud obuna rejalarini (tariflar) olish"""
        token = await self._get_valid_token(user_id)
        if not token:
            return []
        url = f"{self.base_url}/api/v1/billing/subscription-plans/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data if isinstance(data, list) else data.get("results", [])
                    elif response.status == 401:
                        if str(user_id) in self.user_tokens:
                            del self.user_tokens[str(user_id)]
                        return []
        except Exception as e:
            logger.error(f"get_subscription_plans xatolik: {e}")
        return []

    async def get_subscription(self, user_id: str):
        """Foydalanuvchining joriy obuna holatini olish"""
        token = await self._get_valid_token(user_id)
        if not token:
            return None
        url = f"{self.base_url}/api/v1/billing/subscription/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        if str(user_id) in self.user_tokens:
                            del self.user_tokens[str(user_id)]
                        return None
        except Exception as e:
            logger.error(f"get_subscription xatolik: {e}")
        return None

    async def purchase_subscription(self, plan_id: str, user_id: str):
        """Obuna sotib olish so'rovini yuborish va payment yaratish"""
        token = await self._get_valid_token(user_id)
        if not token:
            return None
        url = f"{self.base_url}/api/v1/billing/subscriptions/purchase/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
        payload = {"plan_id": plan_id, "provider": "card_transfer"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status in (200, 201):
                        return await response.json()
                    else:
                        err_text = await response.text()
                        logger.error(f"purchase_subscription xatosi: {response.status} - {err_text}")
                        return None
        except Exception as e:
            logger.error(f"purchase_subscription request error: {e}")
        return None

    async def upload_payment_receipt(self, payment_id: str, file_bytes: bytes, filename: str, user_id: str):
        """To'lov chekini yuklash (multipart/form-data)"""
        token = await self._get_valid_token(user_id)
        if not token:
            return False, "Avtorizatsiyadan o'tilmagan"
        url = f"{self.base_url}/api/v1/billing/payments/{payment_id}/receipt/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
        
        # Backend 'image' maydonini kutadi
        for field_name in ["image", "file", "receipt"]:
            try:
                data = aiohttp.FormData()
                data.add_field(field_name, file_bytes, filename=filename, content_type="image/jpeg")
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=data, headers=headers) as response:
                        if response.status in (200, 201):
                            res_json = await response.json()
                            return True, res_json
                        elif response.status == 400:
                            err_text = await response.text()
                            logger.warning(f"upload receipt with field '{field_name}' returned 400: {err_text}")
                            if field_name not in err_text and "image" in err_text:
                                continue
                            return False, err_text
                        else:
                            err_text = await response.text()
                            logger.error(f"upload receipt error: {response.status} - {err_text}")
                            return False, err_text
            except Exception as e:
                logger.error(f"upload_payment_receipt error with {field_name}: {e}")
        return False, "Server xatosi"

    async def get_payment_details(self, payment_id: str, user_id: str = "system"):
        """To'lov tafsilotlari va uning so'nggi statusini olish"""
        token = await self._get_valid_token(user_id)
        if not token:
            return None
        url = f"{self.base_url}/api/v1/billing/payments/{payment_id}/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.error(f"get_payment_details xatolik: {e}")
        return None

    async def get_notifications(self, user_id: str = "system"):
        """Foydalanuvchi yoki tizim xabarnomalarini olish"""
        token = await self._get_valid_token(user_id)
        if not token:
            return []
        url = f"{self.base_url}/api/v1/notifications/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data if isinstance(data, list) else data.get("results", [])
        except Exception as e:
            logger.error(f"get_notifications xatolik: {e}")
        return []

    async def get_support_conversation(self, user_id: str):
        """Foydalanuvchining qo'llab-quvvatlash suhbati va xabarlar tarixini olish"""
        token = await self._get_valid_token(user_id)
        if not token:
            return None
        url = f"{self.base_url}/api/v1/support/conversation/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.error(f"get_support_conversation xatolik: {e}")
        return None

    async def send_support_message(self, message: str, user_id: str):
        """Qo'llab-quvvatlash xizmatiga yangi xabar yuborish"""
        token = await self._get_valid_token(user_id)
        if not token:
            return None
        url = f"{self.base_url}/api/v1/support/conversation/messages/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
        payload = {"message": message}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status in (200, 201):
                        return await response.json()
                    else:
                        err = await response.text()
                        logger.error(f"send_support_message error: {response.status} - {err}")
        except Exception as e:
            logger.error(f"send_support_message xatolik: {e}")
        return None

    async def request_support_callback(self, phone: str, message: str = "", user_id: str = "system"):
        """Qayta qo'ng'iroq qilish so'rovini yuborish"""
        token = await self._get_valid_token(user_id)
        if not token:
            return None
        url = f"{self.base_url}/api/v1/support/callback-request/"
        headers = {"Authorization": f"Bearer {token}", "User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
        payload = {"phone": phone}
        if message:
            payload["message"] = message
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status in (200, 201):
                        return await response.json()
        except Exception as e:
            logger.error(f"request_support_callback xatolik: {e}")
        return None

    async def forgot_password(self, phone: str):
        """Parolni tiklash uchun OTP kod so'rash"""
        url = f"{self.base_url}/api/v1/auth/forgot-password/"
        headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"phone": phone}, headers=headers) as resp:
                    if resp.status == 200:
                        return True, await resp.json()
                    else:
                        err = await resp.text()
                        logger.error(f"forgot_password xatosi: {resp.status} - {err}")
                        return False, err
        except Exception as e:
            logger.error(f"forgot_password request error: {e}")
            return False, str(e)

    async def reset_password(self, phone: str, otp: str, password: str, confirm_password: str):
        """Yangi parol va OTP orqali parolni qayta o'rnatish"""
        url = f"{self.base_url}/api/v1/auth/reset-password/"
        headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
        payload = {
            "phone": phone,
            "otp": otp,
            "password": password,
            "confirm_password": confirm_password
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return True, await resp.json()
                    else:
                        err = await resp.text()
                        logger.error(f"reset_password xatosi: {resp.status} - {err}")
                        return False, err
        except Exception as e:
            logger.error(f"reset_password request error: {e}")
            return False, str(e)

backend_client = BackendClient()
