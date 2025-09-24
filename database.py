import sqlite3
from config import DATABASE_NAME
import asyncio

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Natijalarni lug'at ko'rinishida olish uchun
    cursor = conn.cursor()
    
    # Guruhlar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id TEXT UNIQUE,
        group_name TEXT,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Kontaktlar jadvali
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE,
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
    conn.close()

async def get_all_groups():
    def _get_all_groups_sync():
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM groups ORDER BY added_date DESC")
        groups = cursor.fetchall()
        conn.close()
        return groups
    return await asyncio.to_thread(_get_all_groups_sync)

async def get_all_contacts():
    def _get_all_contacts_sync():
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contacts ORDER BY added_date DESC")
        contacts = cursor.fetchall()
        conn.close()
        return contacts
    return await asyncio.to_thread(_get_all_contacts_sync)

async def get_group_count():
    def _get_group_count_sync():
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM groups")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    return await asyncio.to_thread(_get_group_count_sync)

async def get_contact_count():
    def _get_contact_count_sync():
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contacts")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    return await asyncio.to_thread(_get_contact_count_sync)

async def add_group(group_id, group_name):
    def _add_group_sync():
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO groups (group_id, group_name) VALUES (?, ?)", 
                          (group_id, group_name))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding group: {e}")
            return False
        finally:
            conn.close()
    return await asyncio.to_thread(_add_group_sync)

async def add_contact(user_id, username, full_name, phone_number):
    def _add_contact_sync():
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO contacts (user_id, username, full_name, phone_number) VALUES (?, ?, ?, ?)", 
                          (user_id, username, full_name, phone_number))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding contact: {e}")
            return False
        finally:
            conn.close()
    return await asyncio.to_thread(_add_contact_sync)

async def log_admin_action(admin_id, action, target_type, target_id):
    def _log_admin_action_sync():
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO admin_logs (admin_id, action, target_type, target_id) VALUES (?, ?, ?, ?)", 
                          (admin_id, action, target_type, target_id))
            conn.commit()
        except Exception as e:
            print(f"Error logging admin action: {e}")
        finally:
            conn.close()
    return await asyncio.to_thread(_log_admin_action_sync)

async def save_feedback(user_id, feedback_text):
    def _save_feedback_sync():
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO feedback (user_id, feedback_text) VALUES (?, ?)",
                          (user_id, feedback_text))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving feedback: {e}")
            return False
        finally:
            conn.close()
    return await asyncio.to_thread(_save_feedback_sync)

async def get_all_feedback():
    def _get_all_feedback_sync():
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, feedback_text, timestamp FROM feedback ORDER BY timestamp DESC")
        feedback = []
        for row in cursor.fetchall():
            feedback.append({'user_id': row[0], 'feedback_text': row[1], 'timestamp': row[2]})
        conn.close()
        return feedback
    return await asyncio.to_thread(_get_all_feedback_sync)