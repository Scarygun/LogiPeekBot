import sqlite3
from config import DATABASE_NAME
import asyncio
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# JSON fayl yo'li config.py dan olinadi
from config import USERS_JSON_FILE

def init_db():
    with sqlite3.connect(DATABASE_NAME) as conn:
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

async def add_user_to_json(user_id: int, username: str | None):
    users = await load_users_from_json()
    if str(user_id) not in users:
        users[str(user_id)] = {
            'username': username,
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
        with sqlite3.connect(DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contacts ORDER BY added_date DESC")
            contacts = cursor.fetchall()
            return contacts
    return await asyncio.to_thread(_get_all_contacts_sync)

async def get_group_count():
    def _get_group_count_sync():
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM groups")
            count = cursor.fetchone()[0]
            return count
    return await asyncio.to_thread(_get_group_count_sync)

async def get_contact_count():
    def _get_contact_count_sync():
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM contacts")
            count = cursor.fetchone()[0]
            return count
    return await asyncio.to_thread(_get_contact_count_sync)

async def add_contact(user_id, username, full_name, phone_number):
    def _add_contact_sync(user_id, username, full_name, phone_number):
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT OR IGNORE INTO contacts (user_id, username, full_name, phone_number) VALUES (?, ?, ?, ?)", 
                              (user_id, username, full_name, phone_number))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error adding contact: {e}")
                return False
    return await asyncio.to_thread(_add_contact_sync, user_id, username, full_name, phone_number)

async def log_admin_action(admin_id, action, target_type, target_id):
    def _log_admin_action_sync(admin_id, action, target_type, target_id):
        with sqlite3.connect(DATABASE_NAME) as conn:
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
        with sqlite3.connect(DATABASE_NAME) as conn:
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
        with sqlite3.connect(DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, feedback_text, timestamp FROM feedback ORDER BY timestamp DESC")
            feedback = []
            for row in cursor.fetchall():
                feedback.append({'user_id': row[0], 'feedback_text': row[1], 'timestamp': row[2]})
            return feedback
    return await asyncio.to_thread(_get_all_feedback_sync)

async def add_group(chat_id: int, title: str | None):
    def _add_group_sync(chat_id: int, title: str | None):
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT OR REPLACE INTO groups(group_id, group_name) VALUES (?, ?)", (chat_id, title))
                conn.commit()
            except Exception as e:
                logger.error(f"DB add error: {e}")
    return await asyncio.to_thread(_add_group_sync, chat_id, title)

async def remove_group(chat_id: int):
    def _remove_group_sync(chat_id: int):
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM groups WHERE group_id=?", (chat_id,))
                conn.commit()
            except Exception as e:
                logger.error(f"DB remove error: {e}")
    return await asyncio.to_thread(_remove_group_sync, chat_id)

async def get_all_groups() -> list:
    def _get_all_groups_sync():
        with sqlite3.connect(DATABASE_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT group_id, group_name, added_date FROM groups") # O'zgartirildi
            groups = cursor.fetchall()
            return groups
    return await asyncio.to_thread(_get_all_groups_sync)