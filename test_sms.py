import asyncio
from config import TEXTUP_EMAIL, TEXTUP_PASSWORD
from textup_client import TextUpClient

async def main():
    try:
        client = TextUpClient(TEXTUP_EMAIL, TEXTUP_PASSWORD)
        print("Logging in...")
        uid = await client.get_textup_user_id()
        print(f"User ID: {uid}")
        
        print("Sending SMS...")
        # try to send an SMS to myself
        sms_id = await client.send_sms(
            message="Test SMS",
            recipients=["+998901234567"]
        )
        print(f"Success! smsId: {sms_id}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(main())
