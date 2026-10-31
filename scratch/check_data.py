import asyncio
import json
from database import load_users_from_json, load_contacts_from_json, load_groups_from_json

async def check():
    users = await load_users_from_json()
    contacts = await load_contacts_from_json()
    groups = await load_groups_from_json()
    
    with open('users.json', 'r') as f:
        raw_u = json.load(f)
    with open('contacts.json', 'r') as f:
        raw_c = json.load(f)
    with open('groups.json', 'r') as f:
        raw_g = json.load(f)
        
    print(f"Users JSON: {len(raw_u)} -> DB load: {len(users)}")
    print(f"Contacts JSON: {len(raw_c)} -> DB load: {len(contacts)}")
    print(f"Groups JSON: {len(raw_g)} -> DB load: {len(groups)}")

if __name__ == '__main__':
    asyncio.run(check())
