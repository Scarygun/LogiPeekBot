import asyncio
from config import TEXTUP_EMAIL, TEXTUP_PASSWORD
from textup_client import TextUpClient

async def main():
    client = TextUpClient(TEXTUP_EMAIL, TEXTUP_PASSWORD)
    templates = await client.get_templates()
    template_id = templates['templates'][0]['id']
    content = templates['templates'][0]['content']
    print(f"Sending with template ID: {template_id}")
    try:
        sms_id = await client.send_sms(
            template_id=template_id,
            message=content,
            recipients=["+998942177939"]
        )
        print(f"Success! smsId: {sms_id}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
