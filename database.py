import sqlite3
from config import DATABASE_NAME
import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Optional, Union

logger = logging.getLogger(__name__)

# JSON fayl yo'li config.py dan olinadi
from config import USERS_JSON_FILE, GROUPS_JSON_FILE, CONTACTS_JSON_FILE

def init_db():
    with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
        conn.row_factory = sqlite3.Row # Natijalarni lug'at ko'rinishida olish uchun
        cursor = conn.cursor()
        
        # Guruhlar jadvali
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER UNIQUE,
            group_name TEXT,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Kontaktlar jadvali
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT,
            phone_number TEXT,
            balance REAL DEFAULT 0,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Admin operatsiyalari jadvali
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target_type TEXT,
            target_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Fikrlar jadvali
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            feedback_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()

def _load_users_from_json_sync() -> dict:
    try:
        with open(USERS_JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.warning(f"JSON fayl ({USERS_JSON_FILE}) buzilgan. Bo'sh lug'at qaytarilmoqda.")
        return {}

async def load_users_from_json() -> dict:
    return await asyncio.to_thread(_load_users_from_json_sync)

def _save_users_to_json_sync(users: dict):
    with open(USERS_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

async def save_users_to_json(users: dict):
    await asyncio.to_thread(_save_users_to_json_sync, users)

async def add_user_to_json(user_id: int, username: Optional[str]):
    users = await load_users_from_json()
    if str(user_id) not in users:
        link = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
        users[str(user_id)] = {
            'username': username,
            'profile_link': link,
            'added_date': datetime.now().isoformat()
        }
        await save_users_to_json(users)
        logger.info(f"User {user_id} JSON fayliga qo'shildi.")
    else:
        logger.info(f"User {user_id} allaqachon JSON faylida mavjud.")

async def get_user_count_from_json() -> int:
    users = await load_users_from_json()
    return len(users)

async def get_all_contacts():
    def _get_all_contacts_sync():
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contacts ORDER BY added_date DESC")
            contacts = cursor.fetchall()
            return contacts
    return await asyncio.to_thread(_get_all_contacts_sync)

async def get_group_count():
    def _get_group_count_sync():
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM groups")
            count = cursor.fetchone()[0]
            return count
    return await asyncio.to_thread(_get_group_count_sync)

async def get_contact_count():
    def _get_contact_count_sync():
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM contacts")
            count = cursor.fetchone()[0]
            return count
    return await asyncio.to_thread(_get_contact_count_sync)

async def add_contact(user_id, username, full_name, phone_number):
    def _add_contact_sync(user_id, username, full_name, phone_number):
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT OR IGNORE INTO contacts (user_id, username, full_name, phone_number) VALUES (?, ?, ?, ?)", 
                              (user_id, username, full_name, phone_number))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error adding contact: {e}")
                return False
    
    # SQLite ga qo'shish
    result = await asyncio.to_thread(_add_contact_sync, user_id, username, full_name, phone_number)
    
    # Agar muvaffaqiyatli bo'lsa, JSON ga ham qo'shish
    if result:
        await add_contact_to_json(user_id, username, full_name, phone_number)
    
    return result

async def log_admin_action(admin_id, action, target_type, target_id):
    def _log_admin_action_sync(admin_id, action, target_type, target_id):
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO admin_logs (admin_id, action, target_type, target_id) VALUES (?, ?, ?, ?)", 
                              (admin_id, action, target_type, target_id))
                conn.commit()
            except Exception as e:
                logger.error(f"Error logging admin action: {e}")
    return await asyncio.to_thread(_log_admin_action_sync, admin_id, action, target_type, target_id)

async def save_feedback(user_id, feedback_text):
    def _save_feedback_sync(user_id, feedback_text):
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO feedback (user_id, feedback_text) VALUES (?, ?)",
                              (user_id, feedback_text))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error saving feedback: {e}")
                return False
    return await asyncio.to_thread(_save_feedback_sync, user_id, feedback_text)

async def get_all_feedback():
    def _get_all_feedback_sync():
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, feedback_text, timestamp FROM feedback ORDER BY timestamp DESC")
            feedback = []
            for row in cursor.fetchall():
                feedback.append({'user_id': row[0], 'feedback_text': row[1], 'timestamp': row[2]})
            return feedback
    return await asyncio.to_thread(_get_all_feedback_sync)

async def add_group(chat_id: Union[int, str], title: Optional[str], group_link: Optional[str] = None, username: Optional[str] = None) -> bool:
    def _add_group_sync(chat_id: Union[int, str], title: Optional[str]) -> bool:
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            cursor = conn.cursor()
            try:
                # SQLite dynamically typed, shuning uchun int yoki str qabul qiladi
                cursor.execute("INSERT OR REPLACE INTO groups(group_id, group_name) VALUES (?, ?)", (chat_id, title))
                conn.commit()
                logger.info(f"Guruh {title} ({chat_id}) ma'lumotlar bazasiga qo'shildi.")
                return True
            except sqlite3.IntegrityError:
                logger.warning(f"Guruh {title} ({chat_id}) allaqachon mavjud.")
                return False
            except Exception as e:
                logger.error(f"DB add error for group {title} ({chat_id}): {e}")
                return False
    
    # SQLite ga qo'shish
    result = await asyncio.to_thread(_add_group_sync, chat_id, title)
    
    # Agar link berilgan bo'lsa, JSON ga ham qo'shish
    if result and group_link:
        await add_group_to_json(str(chat_id), group_link, title, username)
    
    return result

async def remove_group(chat_id: Union[int, str]):
    def _remove_group_sync(chat_id: Union[int, str]):
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM groups WHERE group_id=?", (chat_id,))
                conn.commit()
            except Exception as e:
                logger.error(f"DB remove error: {e}")
    
    # SQLite dan o'chirish
    await asyncio.to_thread(_remove_group_sync, chat_id)
    
    # JSON dan ham o'chirish
    await remove_group_from_json(str(chat_id))

async def get_all_groups() -> list:
    def _get_all_groups_sync():
        with sqlite3.connect(DATABASE_NAME, timeout=30.0) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT group_id, group_name, added_date FROM groups") # O'zgartirildi
            groups = cursor.fetchall()
            return groups
    return await asyncio.to_thread(_get_all_groups_sync)

# Guruhlarni JSON faylga saqlash funksiyalari
def _load_groups_from_json_sync():
    """
    groups.json faylini o'qiydi. Array formatida bo'lishi kerak (faqat linklar ro'yxati).
    Eski dict formatini ham qo'llab-quvvatlaydi (migratsiya uchun).
    Returns: list (array format - faqat linklar)
    """
    try:
        with open(GROUPS_JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Agar array bo'lsa, har bir linkni strip qilib qaytarish
            if isinstance(data, list):
                # Faqat string bo'lganlarini va bo'sh bo'lmaganlarini olamiz
                return [link.strip() for link in data if isinstance(link, str) and link.strip()]
            # Agar dict bo'lsa, eski formatdan yangi formatga o'tkazish
            if isinstance(data, dict):
                links = []
                for group_key, group_data in data.items():
                    if isinstance(group_data, dict) and 'group_link' in group_data:
                        link = group_data['group_link']
                        if link and isinstance(link, str):
                            links.append(link)
                    elif isinstance(group_data, str):
                        # Agar to'g'ridan-to'g'ri link bo'lsa
                        links.append(group_data)
                # Migratsiya: eski formatni yangi formatga o'tkazish
                if links:
                    _save_groups_to_json_sync(links)
                    logger.info(f"Groups.json eski formatdan yangi formatga o'tkazildi. {len(links)} ta link saqlandi.")
                return links
            # Boshqa format bo'lsa, bo'sh list qaytarish
            logger.warning(f"Groups.json noto'g'ri formatda. Array bo'lishi kerak.")
            return []
    except FileNotFoundError:
        logger.info(f"JSON fayl ({GROUPS_JSON_FILE}) topilmadi. Bo'sh ro'yxat qaytarilmoqda.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"JSON fayl ({GROUPS_JSON_FILE}) buzilgan. Xato: {e}")
        logger.warning(f"Bo'sh ro'yxat qaytarilmoqda.")
        return []
    except Exception as e:
        logger.error(f"JSON fayl ({GROUPS_JSON_FILE}) o'qishda xato: {e}")
        return []

async def load_groups_from_json():
    """
    groups.json faylini o'qiydi. Array formatida (faqat linklar ro'yxati).
    Returns: list (array format - faqat linklar)
    """
    return await asyncio.to_thread(_load_groups_from_json_sync)

async def get_group_count_from_json() -> int:
    """JSON fayldan guruhlar sonini olish"""
    groups = await load_groups_from_json()
    if isinstance(groups, list):
        return len(groups)
    return 0

def _save_groups_to_json_sync(groups: list):
    """Guruhlarni JSON faylga saqlash - faqat linklar massivi"""
    with open(GROUPS_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups, f, indent=4, ensure_ascii=False)

async def save_groups_to_json(groups: list):
    """Guruhlarni JSON faylga saqlash - faqat linklar massivi"""
    await asyncio.to_thread(_save_groups_to_json_sync, groups)

async def add_group_to_json(group_id: str, group_link: str, group_title: Optional[str], username: Optional[str] = None):
    """Guruhni JSON faylga qo'shish - faqat link saqlanadi"""
    if not group_link:
        logger.warning(f"Guruh linki berilmagan, JSON ga qo'shilmadi.")
        return
    
    groups = await load_groups_from_json()
    
    # Agar link allaqachon mavjud bo'lsa, qo'shmaslik
    if group_link not in groups:
        groups.append(group_link)
        await save_groups_to_json(groups)
        logger.info(f"Guruh qo'shildi - Link: {group_link}")
    else:
        logger.info(f"Guruh allaqachon mavjud - Link: {group_link}")

async def remove_group_from_json(group_id: str):
    """Guruhni JSON fayldan o'chirish - link orqali"""
    groups = await load_groups_from_json()
    
    # group_id dan linkni topish
    # group_id username yoki raqam bo'lishi mumkin
    # Link formatini tekshirish: https://t.me/username yoki https://t.me/+...
    link_to_remove = None
    
    # Agar group_id raqam bo'lsa, uni link formatiga o'tkazish mumkin emas
    # Shuning uchun barcha linklarni tekshirib, username yoki ID ga mos keladiganini topamiz
    if isinstance(groups, list):
        for link in groups:
            if isinstance(link, str):
                # Linkdan username yoki ID ni ajratib olish
                match = re.match(r'(?:https?://)?t\.me/([a-zA-Z0-9_+]+)', link)
                if match:
                    link_username = match.group(1)
                    # Agar group_id username ga mos kelsa
                    if str(group_id) == link_username:
                        link_to_remove = link
                        break
                    # Agar group_id raqam bo'lsa va linkda ID bo'lsa (invite link)
                    if str(group_id).isdigit() and link_username.startswith('+'):
                        # Invite linklarda ID ni tekshirish qiyin, shuning uchun to'liq linkni solishtiramiz
                        pass
    
    # Agar link topilgan bo'lsa, o'chirish
    if link_to_remove and link_to_remove in groups:
        groups.remove(link_to_remove)
        await save_groups_to_json(groups)
        logger.info(f"Guruh {group_id} (link: {link_to_remove}) JSON fayldan o'chirildi.")
        return True
    
    # Agar link topilmagan bo'lsa, group_id ni to'g'ridan-to'g'ri link sifatida qidirish
    # (agar u to'g'ridan-to'g'ri link bo'lsa)
    potential_link = str(group_id)
    if potential_link.startswith('https://t.me/') or potential_link.startswith('http://t.me/'):
        if potential_link in groups:
            groups.remove(potential_link)
            await save_groups_to_json(groups)
            logger.info(f"Guruh {potential_link} JSON fayldan o'chirildi.")
            return True
    
    logger.warning(f"Guruh {group_id} JSON faylda topilmadi.")
    return False

# ========== KONTAKTLAR JSON FUNKSIYALARI ==========

def _load_contacts_from_json_sync() -> dict:
    """Kontaktlarni JSON fayldan o'qish (sync)"""
    try:
        with open(CONTACTS_JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.warning(f"JSON fayl ({CONTACTS_JSON_FILE}) buzilgan. Bo'sh lug'at qaytarilmoqda.")
        return {}

async def load_contacts_from_json() -> dict:
    """Kontaktlarni JSON fayldan o'qish"""
    return await asyncio.to_thread(_load_contacts_from_json_sync)

def _save_contacts_to_json_sync(contacts: dict):
    """Kontaktlarni JSON faylga yozish (sync)"""
    with open(CONTACTS_JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(contacts, f, indent=4, ensure_ascii=False)

async def save_contacts_to_json(contacts: dict):
    """Kontaktlarni JSON faylga yozish"""
    await asyncio.to_thread(_save_contacts_to_json_sync, contacts)

async def add_contact_to_json(user_id: Union[int, str], username: Optional[str], full_name: Optional[str], phone_number: Optional[str]):
    """Kontaktni JSON faylga qo'shish - faqat phone_number saqlanadi"""
    contacts = await load_contacts_from_json()
    
    # phone_number ni key sifatida ishlatamiz (agar mavjud bo'lsa)
    # Agar phone_number bo'lmasa, user_id ni ishlatamiz
    if phone_number:
        contact_key = str(phone_number)
    else:
        contact_key = str(user_id)
    
    if contact_key not in contacts:
        contacts[contact_key] = {
            'phone_number': phone_number or str(user_id),
            'added_date': datetime.now().isoformat()
        }
        await save_contacts_to_json(contacts)
        logger.info(f"Kontakt {contact_key} JSON fayliga qo'shildi.")
    else:
        # Mavjud bo'lsa, yangilash
        contacts[contact_key]['phone_number'] = phone_number or str(user_id)
        contacts[contact_key]['updated_date'] = datetime.now().isoformat()
        await save_contacts_to_json(contacts)
        logger.info(f"Kontakt {contact_key} JSON faylida yangilandi.")

async def remove_contact_from_json(user_id: Union[int, str]):
    """Kontaktni JSON fayldan o'chirish"""
    contacts = await load_contacts_from_json()
    contact_key = str(user_id)
    
    if contact_key in contacts:
        del contacts[contact_key]
        await save_contacts_to_json(contacts)
        logger.info(f"Kontakt {user_id} JSON fayldan o'chirildi.")
        return True
    return False

async def get_contact_count_from_json() -> int:
    """JSON fayldan kontaktlar sonini olish"""
    contacts = await load_contacts_from_json()
    return len(contacts)