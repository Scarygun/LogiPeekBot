import asyncio
from pymongo import MongoClient
import json

URI = "mongodb+srv://ozodbeksalimov456_db_user:Ozodbek_5317@cluster0.mpwdr4x.mongodb.net/?appName=Cluster0"
DB_NAME = "logipeek_db"

def dump_data():
    client = MongoClient(URI)
    db = client[DB_NAME]
    
    # 1. Users
    users = list(db.users.find())
    for u in users:
        u.pop('_id', None)
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)
    print(f"Users dumped: {len(users)}")
    
    # 2. Contacts
    contacts = list(db.contacts.find())
    for c in contacts:
        c.pop('_id', None)
    with open('contacts.json', 'w', encoding='utf-8') as f:
        json.dump(contacts, f, indent=4, ensure_ascii=False)
    print(f"Contacts dumped: {len(contacts)}")
    
    # 3. Groups (in MongoDB they are dicts)
    groups = list(db.groups.find())
    for g in groups:
        g.pop('_id', None)
    with open('groups.json', 'w', encoding='utf-8') as f:
        json.dump(groups, f, indent=4, ensure_ascii=False)
    print(f"Groups dumped: {len(groups)}")

if __name__ == '__main__':
    dump_data()
