import asyncio
import logging
from database import init_db, get_db, add_user_to_json, get_user_count_from_json

logging.basicConfig(level=logging.INFO)

async def verify():
    print("--- MongoDB Verification ---")
    try:
        # Check connection
        db = get_db()
        print(f"✅ Connected to MongoDB: {db.name}")
        
        # Test init
        init_db()
        print("✅ Indices initialized.")
        
        # Test user addition
        test_user_id = 9999999
        await add_user_to_json(test_user_id, "test_user_mongo")
        print(f"✅ Test user added/updated.")
        
        # Test count
        count = await get_user_count_from_json()
        print(f"✅ Total users in MongoDB: {count}")
        
        print("\n🎉 Verification successful!")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        print("\nMake sure you have installed the requirements: pip install pymongo dnspython")

if __name__ == "__main__":
    asyncio.run(verify())
