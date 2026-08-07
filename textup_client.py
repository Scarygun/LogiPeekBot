"""
TextUP SMS API klienti.
Hujjat: https://api-auth.textup.uz va https://sms-api.textup.uz

Xususiyatlar:
- JWT token avtomatik cache va yangilash
- Login, alpha names, templates, groups, SMS yuborish
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List

import aiohttp

logger = logging.getLogger(__name__)

AUTH_BASE = "https://api-auth.textup.uz/v1"
SMS_BASE = "https://sms-api.textup.uz/v1"


class TextUpAuthError(Exception):
    """Login yoki token muammosi."""


class TextUpAPIError(Exception):
    """API javob xatosi."""
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


class TextUpClient:
    """
    TextUP SMS API bilan ishlovchi async client.

    Foydalanish:
        client = TextUpClient(email, password)
        await client.send_sms(user_id, recipients=["+998901234567"], message="Salom!")
    """

    def __init__(self, email: str, password: str):
        self._email = email
        self._password = password

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

        # TextUP user.id — bir marta login qilganda olinadi
        self._textup_user_id: Optional[str] = None

        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    #  Token boshqaruvi
    # ------------------------------------------------------------------ #

    def _is_token_valid(self) -> bool:
        if not self._access_token or not self._token_expires:
            return False
        # 60 sekundlik xavfsizlik chegarasi
        return datetime.utcnow() < self._token_expires - timedelta(seconds=60)

    async def _login(self) -> None:
        """TextUP API ga login qilib JWT token olish."""
        url = f"{AUTH_BASE}/login"
        payload = {"email": self._email, "password": self._password}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                body = await resp.text()
                if resp.status != 200:
                    raise TextUpAuthError(f"Login failed ({resp.status}): {body}")
                data = await resp.json(content_type=None)

        self._access_token = data.get("accessToken")
        self._refresh_token = data.get("refreshToken")
        self._textup_user_id = data.get("user", {}).get("id")

        if not self._access_token:
            raise TextUpAuthError("Login javobida accessToken yo'q.")

        # JWT token odatda 1 soat amal qiladi; biz 55 daqiqa saqlaymiz
        self._token_expires = datetime.utcnow() + timedelta(minutes=55)
        logger.info(
            "TextUP login muvaffaqiyatli. user_id=%s", self._textup_user_id
        )

    async def _ensure_token(self) -> str:
        """Token haqiqiyligini tekshiradi; kerak bo'lsa yangilaydi."""
        async with self._lock:
            if not self._is_token_valid():
                await self._login()
        return self._access_token  # type: ignore[return-value]

    def _auth_headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ #
    #  Yordamchi so'rov yuboruvchi
    # ------------------------------------------------------------------ #

    async def _get(self, base: str, path: str, params: Optional[dict] = None) -> dict:
        token = await self._ensure_token()
        url = f"{base}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=self._auth_headers(token), params=params
            ) as resp:
                body = await resp.text()
                if resp.status not in (200, 201):
                    raise TextUpAPIError(resp.status, body)
                return await resp.json(content_type=None)

    async def _post(self, base: str, path: str, payload: dict) -> dict:
        token = await self._ensure_token()
        url = f"{base}{path}"
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=self._auth_headers(token), json=payload
            ) as resp:
                body = await resp.text()
                if resp.status not in (200, 201):
                    raise TextUpAPIError(resp.status, body)
                return await resp.json(content_type=None)

    # ------------------------------------------------------------------ #
    #  Public API metodlari
    # ------------------------------------------------------------------ #

    async def get_textup_user_id(self) -> str:
        """TextUP user ID sini qaytaradi (kerak bo'lsa login qiladi)."""
        await self._ensure_token()
        if not self._textup_user_id:
            raise TextUpAuthError("TextUP user ID topilmadi.")
        return self._textup_user_id

    async def get_alpha_names(self, page: int = 1, limit: int = 50) -> dict:
        """
        Mavjud alpha name (jo'natuvchi nomlari) ro'yxatini olish.
        GET /v1/nick-names
        """
        uid = await self.get_textup_user_id()
        params = {"page": page, "limit": limit, "userId": uid}
        return await self._get(AUTH_BASE, "/nick-names", params=params)

    async def get_templates(self, page: int = 1, limit: int = 50) -> dict:
        """
        SMS shablonlar ro'yxatini olish.
        GET /v1/templates
        """
        uid = await self.get_textup_user_id()
        params = {"page": page, "limit": limit, "userId": uid}
        return await self._get(AUTH_BASE, "/templates", params=params)

    async def get_groups(self) -> dict:
        """
        TextUP SMS guruhlar ro'yxatini olish.
        GET /v1/groups
        """
        return await self._get(AUTH_BASE, "/groups")

    async def get_sms_list(self, page: int = 1, limit: int = 20) -> dict:
        """
        Yuborilgan SMSlar ro'yxatini olish.
        GET /v1/sms
        """
        uid = await self.get_textup_user_id()
        params = {"page": page, "limit": limit, "userId": uid}
        return await self._get(SMS_BASE, "/sms", params=params)

    async def get_sms_by_id(self, sms_id: str) -> dict:
        """
        SMS holatini ID bo'yicha olish.
        GET /v1/sms/<smsId>
        """
        return await self._get(SMS_BASE, f"/sms/{sms_id}")

    async def send_sms(
        self,
        *,
        message: Optional[str] = None,
        template_id: Optional[str] = None,
        group_id: Optional[str] = None,
        recipients: Optional[List[str]] = None,
        nickname_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> str:
        """
        SMS yuborish.
        POST /v1/send

        Qaytadi: smsId (str)

        Qoidalar:
        - message YOKI template_id (yoki ikkalasi) bo'lishi kerak
        - group_id YOKI recipients (yoki ikkalasi) bo'lishi kerak
        """
        uid = await self.get_textup_user_id()
        payload: dict = {"userId": uid}

        if message:
            payload["message"] = message
        if template_id:
            payload["templateId"] = template_id
        if group_id:
            payload["groupId"] = group_id
        if recipients:
            payload["recipients"] = recipients
        if nickname_id:
            payload["nicknameId"] = nickname_id
        if name:
            payload["name"] = name

        data = await self._post(SMS_BASE, "/send", payload)
        sms_id = data.get("smsId")
        if not sms_id:
            raise TextUpAPIError(0, f"smsId javobda yo'q: {data}")
        logger.info("SMS yuborildi. smsId=%s", sms_id)
        return sms_id
