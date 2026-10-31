import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

from database import _read_json
from config import USERS_JSON_FILE

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
        """Backend dan yuklarni izlash"""
        token = await self._get_valid_token(user_id)
        if not token:
            logger.error(f"Token yo'qligi sababli yuk izlab bo'lmadi (User: {user_id}).")
            return "NOT_LOGGED_IN"

        search_url = f"{self.base_url}/api/v1/cargo/marketplace/listings/"
        
        params = {
            "origin": from_city,
            "destination": to_city
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Backenddan kelgan ma'lumotni bot formatiga o'tkazish
                        # Bu qism backend qanday JSON qaytarishiga qarab o'zgartirilishi kerak!
                        
                        results = []
                        loads = data if isinstance(data, list) else data.get('results', [])
                        
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
                                'group_title': title,
                                'text': desc,
                                'date': pickup_date,
                                'sender': sender_name,
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
