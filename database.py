import asyncio
import logging
import json
import os
import time
from datetime import datetime
from typing import Optional, Union, List
from config import USERS_JSON_FILE, GROUPS_JSON_FILE, CONTACTS_JSON_FILE

logger = logging.getLogger(__name__)

# Constants for extra files
FEEDBACK_JSON_FILE = "feedback.json"
ADMIN_LOGS_JSON_FILE = "admin_logs.json"

_GROUPS_CACHE_TTL_SECONDS = 60
_groups_cache: List[str] = []
_groups_cache_expires_at = 0.0

def _read_json(filepath: str, default_data: Union[dict, list]) -> Union[dict, list]:
    if not os.path.exists(filepath):
        return default_data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading {filepath}: {e}")
        return default_data

def _write_json(filepath: str, data: Union[dict, list]):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Error writing to {filepath}: {e}")

def _invalidate_groups_cache():
    global _groups_cache, _groups_cache_expires_at
    _groups_cache = []
    _groups_cache_expires_at = 0.0

def _load_group_links_sync() -> List[str]:
    groups = _read_json(GROUPS_JSON_FILE, [])
    if isinstance(groups, list):
        return [g.get("group_link") if isinstance(g, dict) else g for g in groups]
    elif isinstance(groups, dict):
        return [g.get("group_link") for g in groups.values() if isinstance(g, dict) and g.get("group_link")]
    return []

def init_db():
    logger.info("JSON Database initialized.")

# ========== USER FUNCTIONS ==========

def _add_user_sync(user_id: int, username: Optional[str]):
    users = _read_json(USERS_JSON_FILE, [])
    if isinstance(users, dict):
        str_id = str(user_id)
        if str_id not in users:
            users[str_id] = {
                "user_id": user_id,
                "added_date": datetime.now().isoformat(),
                "balance": 0.0,
                "subscription_end": None
            }
        users[str_id]["username"] = username
        users[str_id]["profile_link"] = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
        users[str_id]["updated_at"] = datetime.now().isoformat()
        _write_json(USERS_JSON_FILE, users)
        return
        
    user = next((u for u in users if u.get("user_id") == user_id), None)
    if not user:
        user = {
            "user_id": user_id,
            "added_date": datetime.now().isoformat(),
            "balance": 0.0,
            "subscription_end": None
        }
        users.append(user)
        
    user["username"] = username
    user["profile_link"] = f"https://t.me/{username}" if username else f"tg://user?id={user_id}"
    user["updated_at"] = datetime.now().isoformat()
    _write_json(USERS_JSON_FILE, users)

async def add_user_to_json(user_id: int, username: Optional[str]):
    await asyncio.to_thread(_add_user_sync, int(user_id), username)

async def get_user_count_from_json() -> int:
    def _count():
        users = _read_json(USERS_JSON_FILE, [])
        return len(users) if isinstance(users, (list, dict)) else 0
    return await asyncio.to_thread(_count)

async def load_users_from_json() -> dict:
    def _load():
        users_data = _read_json(USERS_JSON_FILE, [])
        if isinstance(users_data, dict):
            return users_data
        
        users_dict = {}
        for idx, u in enumerate(users_data):
            if "user_id" in u:
                users_dict[str(u["user_id"])] = u
            elif "username" in u:
                users_dict[u["username"]] = u
            else:
                users_dict[f"unknown_{idx}"] = u
        return users_dict
    return await asyncio.to_thread(_load)

async def get_balance(user_id: Union[int, str]) -> float:
    def _get():
        try:
            uid = int(user_id)
        except:
            uid = user_id
        
        users = _read_json(USERS_JSON_FILE, [])
        if isinstance(users, dict):
            user = users.get(str(uid), {})
        else:
            user = next((u for u in users if u.get("user_id") == uid), {})
            
        return float(user.get("balance", 0.0))
    return await asyncio.to_thread(_get)

async def update_balance(user_id: Union[int, str], amount: float) -> bool:
    def _update():
        try:
            uid = int(user_id)
        except:
            uid = user_id
        
        users = _read_json(USERS_JSON_FILE, [])
        modified = False
        
        if isinstance(users, dict):
            str_id = str(uid)
            if str_id not in users:
                users[str_id] = {"user_id": uid, "balance": 0.0, "added_date": datetime.now().isoformat()}
            users[str_id]["balance"] = float(users[str_id].get("balance", 0.0)) + amount
            users[str_id]["updated_at"] = datetime.now().isoformat()
            modified = True
        else:
            user = next((u for u in users if u.get("user_id") == uid), None)
            if not user:
                user = {"user_id": uid, "balance": 0.0, "added_date": datetime.now().isoformat()}
                users.append(user)
            user["balance"] = float(user.get("balance", 0.0)) + amount
            user["updated_at"] = datetime.now().isoformat()
            modified = True
            
        if modified:
            _write_json(USERS_JSON_FILE, users)
        return modified
    return await asyncio.to_thread(_update)

async def check_user_subscription(user_id: Union[int, str]) -> bool:
    """Returns True if user has an active subscription"""
    def _check():
        try:
            uid = int(user_id)
        except:
            uid = user_id
            
        users = _read_json(USERS_JSON_FILE, [])
        if isinstance(users, dict):
            user = users.get(str(uid), {})
        else:
            user = next((u for u in users if u.get("user_id") == uid), {})
            
        sub_end = user.get("subscription_end")
        if not sub_end:
            return False
            
        try:
            end_date = datetime.fromisoformat(sub_end)
            return datetime.now() < end_date
        except ValueError:
            return False
    return await asyncio.to_thread(_check)

async def get_user_subscription_end(user_id: Union[int, str]) -> Optional[str]:
    """Returns the subscription end date as ISO string or None"""
    def _get():
        try:
            uid = int(user_id)
        except:
            uid = user_id
            
        users = _read_json(USERS_JSON_FILE, [])
        if isinstance(users, dict):
            user = users.get(str(uid), {})
        else:
            user = next((u for u in users if u.get("user_id") == uid), {})
            
        return user.get("subscription_end")
    return await asyncio.to_thread(_get)

async def add_subscription_days(user_id: Union[int, str], days: int) -> Optional[str]:
    """Adds days to user's subscription and returns the new end date"""
    from datetime import timedelta
    def _add():
        try:
            uid = int(user_id)
        except:
            uid = user_id
            
        users = _read_json(USERS_JSON_FILE, [])
        modified = False
        new_end_date = None
        
        if isinstance(users, dict):
            str_id = str(uid)
            if str_id not in users:
                users[str_id] = {"user_id": uid, "added_date": datetime.now().isoformat(), "balance": 0.0, "subscription_end": None}
            user = users[str_id]
        else:
            user = next((u for u in users if u.get("user_id") == uid), None)
            if not user:
                user = {"user_id": uid, "added_date": datetime.now().isoformat(), "balance": 0.0, "subscription_end": None}
                users.append(user)
        
        current_end_str = user.get("subscription_end")
        if current_end_str:
            try:
                current_end = datetime.fromisoformat(current_end_str)
                # If already expired, start from today
                if current_end < datetime.now():
                    current_end = datetime.now()
            except ValueError:
                current_end = datetime.now()
        else:
            current_end = datetime.now()
            
        new_end = current_end + timedelta(days=days)
        new_end_date = new_end.isoformat()
        user["subscription_end"] = new_end_date
        user["updated_at"] = datetime.now().isoformat()
        modified = True
        
        if modified:
            _write_json(USERS_JSON_FILE, users)
            
        return new_end_date
    return await asyncio.to_thread(_add)

# ========== CONTACT FUNCTIONS ==========

async def add_contact(user_id: Union[int, str], username: Optional[str], full_name: Optional[str], phone_number: Optional[str]):
    def _add():
        contacts = _read_json(CONTACTS_JSON_FILE, [])
        
        if isinstance(contacts, dict):
            key = str(phone_number) if phone_number else str(user_id)
            if key not in contacts:
                contacts[key] = {"added_date": datetime.now().isoformat(), "balance": 0.0}
            contacts[key].update({
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "phone_number": phone_number,
                "updated_at": datetime.now().isoformat()
            })
            _write_json(CONTACTS_JSON_FILE, contacts)
            return True
            
        contact = next((c for c in contacts if c.get("user_id") == user_id or (phone_number and c.get("phone_number") == phone_number)), None)
        if not contact:
            contact = {"added_date": datetime.now().isoformat(), "balance": 0.0}
            contacts.append(contact)
            
        contact.update({
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "phone_number": phone_number,
            "updated_at": datetime.now().isoformat()
        })
        _write_json(CONTACTS_JSON_FILE, contacts)
        return True
    return await asyncio.to_thread(_add)

async def get_all_contacts():
    def _get():
        contacts = _read_json(CONTACTS_JSON_FILE, [])
        if isinstance(contacts, dict):
            return list(contacts.values())
        return contacts
    return await asyncio.to_thread(_get)

async def get_contact_count():
    def _count():
        contacts = _read_json(CONTACTS_JSON_FILE, [])
        return len(contacts) if isinstance(contacts, (list, dict)) else 0
    return await asyncio.to_thread(_count)

async def add_contact_to_json(user_id, username, full_name, phone_number):
    await add_contact(user_id, username, full_name, phone_number)

async def load_contacts_from_json() -> dict:
    def _load():
        contacts_data = _read_json(CONTACTS_JSON_FILE, [])
        if isinstance(contacts_data, dict):
            return contacts_data
        
        contacts_dict = {}
        for c in contacts_data:
            key = c.get('phone_number') or str(c.get('user_id'))
            contacts_dict[key] = c
        return contacts_dict
    return await asyncio.to_thread(_load)

async def get_contact_count_from_json() -> int:
    return await get_contact_count()

# ========== GROUP FUNCTIONS ==========

async def add_group(chat_id: Union[int, str], title: Optional[str], group_link: Optional[str] = None, username: Optional[str] = None) -> bool:
    def _add():
        try:
            chat_id_clean = int(chat_id)
        except (ValueError, TypeError):
            chat_id_clean = chat_id
            
        groups = _read_json(GROUPS_JSON_FILE, [])
        
        if isinstance(groups, dict):
            str_id = str(chat_id_clean)
            if str_id not in groups:
                groups[str_id] = {"added_date": datetime.now().isoformat()}
            groups[str_id]["group_id"] = chat_id_clean
            groups[str_id]["group_name"] = title
            groups[str_id]["updated_at"] = datetime.now().isoformat()
            if group_link: groups[str_id]["group_link"] = group_link
            if username: groups[str_id]["username"] = username
            _write_json(GROUPS_JSON_FILE, groups)
            _invalidate_groups_cache()
            return True
            
        group = next((g for g in groups if g.get("group_id") == chat_id_clean or (group_link and g.get("group_link") == group_link)), None)
        if not group:
            group = {"added_date": datetime.now().isoformat()}
            groups.append(group)
            
        group["group_id"] = chat_id_clean
        group["group_name"] = title
        group["updated_at"] = datetime.now().isoformat()
        if group_link: group["group_link"] = group_link
        if username: group["username"] = username
        _write_json(GROUPS_JSON_FILE, groups)
        _invalidate_groups_cache()
        return True
    return await asyncio.to_thread(_add)

async def remove_group(chat_id: Union[int, str]):
    def _remove():
        try:
            chat_id_clean = int(chat_id)
        except (ValueError, TypeError):
            chat_id_clean = chat_id
            
        groups = _read_json(GROUPS_JSON_FILE, [])
        if isinstance(groups, dict):
            if str(chat_id_clean) in groups:
                del groups[str(chat_id_clean)]
                _write_json(GROUPS_JSON_FILE, groups)
        else:
            filtered_groups = [g for g in groups if g.get("group_id") != chat_id_clean]
            if len(filtered_groups) != len(groups):
                _write_json(GROUPS_JSON_FILE, filtered_groups)
        _invalidate_groups_cache()
    await asyncio.to_thread(_remove)

async def get_all_groups() -> list:
    def _get():
        groups = _read_json(GROUPS_JSON_FILE, [])
        if isinstance(groups, dict):
            return list(groups.values())
        return groups
    return await asyncio.to_thread(_get)

async def get_group_count():
    def _count():
        groups = _read_json(GROUPS_JSON_FILE, [])
        return len(groups) if isinstance(groups, (list, dict)) else 0
    return await asyncio.to_thread(_count)

async def load_groups_from_json() -> list:
    global _groups_cache, _groups_cache_expires_at
    now = time.monotonic()
    if _groups_cache_expires_at > now:
        return list(_groups_cache)

    group_links = await asyncio.to_thread(_load_group_links_sync)
    _groups_cache = group_links
    _groups_cache_expires_at = now + _GROUPS_CACHE_TTL_SECONDS
    return list(group_links)

async def get_group_count_from_json() -> int:
    def _count():
        groups = _read_json(GROUPS_JSON_FILE, [])
        return len(groups) if isinstance(groups, (list, dict)) else 0
    return await asyncio.to_thread(_count)

async def add_group_to_json(group_id, group_link, group_title, username=None):
    await add_group(group_id, group_title, group_link, username)

async def remove_group_from_json(group_id: str):
    await remove_group(group_id)

# ========== ADMIN & FEEDBACK FUNCTIONS ==========

async def log_admin_action(admin_id, action, target_type, target_id):
    def _log():
        logs = _read_json(ADMIN_LOGS_JSON_FILE, [])
        log_entry = {
            "admin_id": admin_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "timestamp": datetime.now().isoformat()
        }
        if isinstance(logs, list):
            logs.append(log_entry)
        _write_json(ADMIN_LOGS_JSON_FILE, logs)
    await asyncio.to_thread(_log)

async def save_feedback(user_id, feedback_text):
    def _save():
        feedbacks = _read_json(FEEDBACK_JSON_FILE, [])
        feedback = {
            "user_id": user_id,
            "feedback_text": feedback_text,
            "timestamp": datetime.now().isoformat()
        }
        if isinstance(feedbacks, list):
            feedbacks.append(feedback)
        _write_json(FEEDBACK_JSON_FILE, feedbacks)
        return True
    return await asyncio.to_thread(_save)

async def get_all_feedback():
    def _get():
        feedbacks = _read_json(FEEDBACK_JSON_FILE, [])
        if isinstance(feedbacks, list):
            return sorted(feedbacks, key=lambda x: x.get("timestamp", ""), reverse=True)
        return []
    return await asyncio.to_thread(_get)

# Compatibility placeholders
async def save_users_to_json(users: dict): pass
async def save_groups_to_json(groups: list): pass
async def save_contacts_to_json(contacts: dict): pass
