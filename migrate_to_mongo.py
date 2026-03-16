import sqlite3
import json
import os
import re
from pymongo import MongoClient
from datetime import datetime
from config import (
    DATABASE_NAME, USERS_JSON_FILE, GROUPS_JSON_FILE, 
    CONTACTS_JSON_FILE, MONGODB_URI, DATABASE_NAME_MONGO
)

def migrate():
    print("Starting migration to MongoDB...")
    
    # Connect to MongoDB
    client = MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME_MONGO]
    
    # --- Migrate Users (from JSON) ---
    print("Migrating users...")
    if os.path.exists(USERS_JSON_FILE):
        with open(USERS_JSON_FILE, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
            users_list = []
            for user_id, info in users_data.items():
                info['user_id'] = int(user_id)
                users_list.append(info)
            if users_list:
                db.users.delete_many({}) # Clear existing
                db.users.insert_many(users_list)
                print(f"✅ Migrated {len(users_list)} users.")
    
    # --- Migrate Groups (from JSON and SQLite) ---
    print("Migrating groups...")
    groups_to_insert = {} # Use dict to avoid duplicates by link or ID
    
    # From JSON
    if os.path.exists(GROUPS_JSON_FILE):
        with open(GROUPS_JSON_FILE, 'r', encoding='utf-8') as f:
            links = json.load(f)
            if isinstance(links, list):
                for link in links:
                    groups_to_insert[link] = {'group_link': link, 'added_date': datetime.now().isoformat()}
    
    # From SQLite
    if os.path.exists(DATABASE_NAME):
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT group_id, group_name, added_date FROM groups")
            for row in cursor.fetchall():
                group_id = row['group_id']
                group_name = row['group_name']
                # Create a key that is either the link or the ID
                key = str(group_id)
                if key not in groups_to_insert:
                    groups_to_insert[key] = {
                        'group_id': group_id,
                        'group_name': group_name,
                        'added_date': row['added_date']
                    }
                else:
                    groups_to_insert[key]['group_id'] = group_id
                    groups_to_insert[key]['group_name'] = group_name
        except sqlite3.OperationalError:
            print("Groups table not found in SQLite.")
        conn.close()
    
    if groups_to_insert:
        db.groups.delete_many({})
        db.groups.insert_many(list(groups_to_insert.values()))
        print(f"✅ Migrated {len(groups_to_insert)} groups.")

    # --- Migrate Contacts (from JSON and SQLite) ---
    print("Migrating contacts...")
    contacts_to_insert = {}
    
    # From JSON
    if os.path.exists(CONTACTS_JSON_FILE):
        with open(CONTACTS_JSON_FILE, 'r', encoding='utf-8') as f:
            contacts_data = json.load(f)
            for key, info in contacts_data.items():
                contacts_to_insert[key] = info
    
    # From SQLite
    if os.path.exists(DATABASE_NAME):
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM contacts")
            for row in cursor.fetchall():
                user_id = row['user_id']
                phone = row['phone_number']
                key = phone if phone else str(user_id)
                data = dict(row)
                if key in contacts_to_insert:
                    contacts_to_insert[key].update(data)
                else:
                    contacts_to_insert[key] = data
        except sqlite3.OperationalError:
            print("Contacts table not found in SQLite.")
        conn.close()
    
    if contacts_to_insert:
        db.contacts.delete_many({})
        db.contacts.insert_many(list(contacts_to_insert.values()))
        print(f"✅ Migrated {len(contacts_to_insert)} contacts.")

    # --- Migrate Admin Logs (from SQLite) ---
    print("Migrating admin logs...")
    if os.path.exists(DATABASE_NAME):
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM admin_logs")
            logs = [dict(row) for row in cursor.fetchall()]
            if logs:
                db.admin_logs.delete_many({})
                db.admin_logs.insert_many(logs)
                print(f"✅ Migrated {len(logs)} admin logs.")
        except sqlite3.OperationalError:
             print("Admin logs table not found in SQLite.")
        conn.close()

    # --- Migrate Feedback (from SQLite) ---
    print("Migrating feedback...")
    if os.path.exists(DATABASE_NAME):
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM feedback")
            feedbacks = [dict(row) for row in cursor.fetchall()]
            if feedbacks:
                db.feedback.delete_many({})
                db.feedback.insert_many(feedbacks)
                print(f"✅ Migrated {len(feedbacks)} feedback entries.")
        except sqlite3.OperationalError:
            print("Feedback table not found in SQLite.")
        conn.close()

    print("\nMigration completed successfully!")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
