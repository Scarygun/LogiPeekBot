import asyncio
import logging
import json
import re
from datetime import datetime
from typing import Optional, Union, List, Dict
from pymongo import MongoClient
from config import MONGODB_URI, DATABASE_NAME_MONGO

logger = logging.getLogger(__name__)

# MongoDB Client Initialization
_client = None
_db = None

def get_db():
    global _client, _db
    if _db is None:
        _client = MongoClient(MONGODB_URI)
        _db = _client[DATABASE_NAME_MONGO]
    return _db

def init_db():
    """Initializes MongoDB indices for performance and uniqueness."""
    db = get_db()
    # Users collection
    db.users.create_index("user_id", unique=True)
    # Groups collection
    db.groups.create_index("group_link", unique=True, sparse=True)
    db.groups.create_index("group_id", unique=True, sparse=True)
    # Contacts collection
    db.contacts.create_index("user_id", unique=True, sparse=True)
    db.contacts.create_index("phone_number", unique=True, sparse=True)
    logger.info("MongoDB indices initialized.")

# ========== USER FUNCTIONS (formerly JSON based) ==========

def _add_user_sync(user_id: int, username: Optional[str]):
    db = get_db()
    link = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
    db.users.update_one(
        {"user_id": user_id},
        {"$set": {
            "username": username,
            "profile_link": link,
            "updated_at": datetime.now().isoformat()
        }, "$setOnInsert": {
            "added_date": datetime.now().isoformat()
        }},
        upsert=True
    )

async def add_user_to_json(user_id: int, username: Optional[str]):
    """Adds or updates a user in MongoDB (maintained alias for compatibility)."""
    await asyncio.to_thread(_add_user_sync, int(user_id), username)

async def get_user_count_from_json() -> int:
    def _count():
        return get_db().users.count_documents({})
    return await asyncio.to_thread(_count)

async def load_users_from_json() -> dict:
    """Returns users in the same dict format {str(user_id): data} for compatibility."""
    def _load():
        users = {}
        for doc in get_db().users.find():
            user_id = str(doc.get('user_id'))
            doc.pop('_id', None)
            users[user_id] = doc
        return users
    return await asyncio.to_thread(_load)

# ========== CONTACT FUNCTIONS ==========

async def add_contact(user_id: int, username: Optional[str], full_name: Optional[str], phone_number: Optional[str]):
    def _add():
        db = get_db()
        db.contacts.update_one(
            {"user_id": user_id},
            {"$set": {
                "username": username,
                "full_name": full_name,
                "phone_number": phone_number,
                "updated_at": datetime.now().isoformat()
            }, "$setOnInsert": {
                "added_date": datetime.now().isoformat(),
                "balance": 0.0
            }},
            upsert=True
        )
        return True
    return await asyncio.to_thread(_add)

async def get_all_contacts():
    def _get():
        docs = list(get_db().contacts.find().sort("added_date", -1))
        for d in docs: d.pop('_id', None)
        return docs
    return await asyncio.to_thread(_get)

async def get_contact_count():
    def _count():
        return get_db().contacts.count_documents({})
    return await asyncio.to_thread(_count)

# Aliases for contact functions that previously used JSON
async def add_contact_to_json(user_id, username, full_name, phone_number):
    await add_contact(user_id, username, full_name, phone_number)

async def load_contacts_from_json() -> dict:
    def _load():
        contacts = {}
        for doc in get_db().contacts.find():
            key = doc.get('phone_number') or str(doc.get('user_id'))
            doc.pop('_id', None)
            contacts[key] = doc
        return contacts
    return await asyncio.to_thread(_load)

async def get_contact_count_from_json() -> int:
    return await get_contact_count()

# ========== GROUP FUNCTIONS ==========

async def add_group(chat_id: Union[int, str], title: Optional[str], group_link: Optional[str] = None, username: Optional[str] = None) -> bool:
    def _add():
        db = get_db()
        # Ensure chat_id is int if it looks like one, or cleaned string
        try:
            chat_id_clean = int(chat_id)
        except (ValueError, TypeError):
            chat_id_clean = chat_id
            
        query = {"group_id": chat_id_clean}
        if group_link:
            query = {"$or": [{"group_id": chat_id_clean}, {"group_link": group_link}]}
        
        update = {
            "group_id": chat_id_clean,
            "group_name": title,
            "updated_at": datetime.now().isoformat()
        }
        if group_link: update["group_link"] = group_link
        if username: update["username"] = username

        db.groups.update_one(
            query,
            {"$set": update, "$setOnInsert": {"added_date": datetime.now().isoformat()}},
            upsert=True
        )
        return True
    return await asyncio.to_thread(_add)

async def remove_group(chat_id: Union[int, str]):
    def _remove():
        try:
            chat_id_clean = int(chat_id)
        except (ValueError, TypeError):
            chat_id_clean = chat_id
        get_db().groups.delete_one({"group_id": chat_id_clean})
    await asyncio.to_thread(_remove)

async def get_all_groups() -> list:
    def _get():
        docs = list(get_db().groups.find())
        for d in docs: d.pop('_id', None)
        return docs
    return await asyncio.to_thread(_get)

async def get_group_count():
    def _count():
        return get_db().groups.count_documents({})
    return await asyncio.to_thread(_count)

# Aliases for group functions that previously used JSON
async def load_groups_from_json() -> list:
    """Returns list of links for compatibility."""
    def _load():
        return [doc.get('group_link') for doc in get_db().groups.find() if doc.get('group_link')]
    return await asyncio.to_thread(_load)

async def get_group_count_from_json() -> int:
    def _count():
        return get_db().groups.count_documents({"group_link": {"$exists": True, "$ne": None}})
    return await asyncio.to_thread(_count)

async def add_group_to_json(group_id, group_link, group_title, username=None):
    await add_group(group_id, group_title, group_link, username)

# ========== ADMIN & FEEDBACK FUNCTIONS ==========

async def log_admin_action(admin_id, action, target_type, target_id):
    def _log():
        get_db().admin_logs.insert_one({
            "admin_id": admin_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "timestamp": datetime.now().isoformat()
        })
    await asyncio.to_thread(_log)

async def save_feedback(user_id, feedback_text):
    def _save():
        get_db().feedback.insert_one({
            "user_id": user_id,
            "feedback_text": feedback_text,
            "timestamp": datetime.now().isoformat()
        })
        return True
    return await asyncio.to_thread(_save)

async def get_all_feedback():
    def _get():
        docs = list(get_db().feedback.find().sort("timestamp", -1))
        for d in docs: d.pop('_id', None)
        return docs
    return await asyncio.to_thread(_get)

# Compatibility placeholders
async def save_users_to_json(users: dict): pass
async def save_groups_to_json(groups: list): pass
async def save_contacts_to_json(contacts: dict): pass

async def remove_group_from_json(group_id: str):
    def _remove():
        try:
            cid = int(group_id)
            get_db().groups.delete_one({"group_id": cid})
        except:
            get_db().groups.delete_one({"$or": [{"group_id": group_id}, {"group_link": {"$regex": group_id}}]})
    await asyncio.to_thread(_remove)