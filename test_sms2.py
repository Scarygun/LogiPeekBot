import asyncio
from config import TEXTUP_EMAIL, TEXTUP_PASSWORD
from textup_client import TextUpClient

async def main():
    client = TextUpClient(TEXTUP_EMAIL, TEXTUP_PASSWORD)
    uid = await client.get_textup_user_id()
    print(f"User ID: {uid}")
    
    print("Getting templates...")
    templates = await client.get_templates()
    print(f"Templates: {templates}")
    
    if templates and templates.get('data'):
        template_id = templates['data'][0]['id']
        print(f"Sending with template ID: {template_id}")
        sms_id = await client.send_sms(
            template_id=template_id,
            recipients=["+998901234567"]
        )
        print(f"Success! smsId: {sms_id}")

asyncio.run(main())
