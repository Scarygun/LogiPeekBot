import asyncio
from config import TEXTUP_EMAIL, TEXTUP_PASSWORD
from textup_client import TextUpClient

async def main():
    client = TextUpClient(TEXTUP_EMAIL, TEXTUP_PASSWORD)
    templates = await client.get_templates()
    if templates and templates.get('templates'):
        template_id = templates['templates'][0]['id']
        print(f"Sending with template ID: {template_id}")
        sms_id = await client.send_sms(
            template_id=template_id,
            recipients=["+998901234567"]
        )
        print(f"Success! smsId: {sms_id}")

asyncio.run(main())
