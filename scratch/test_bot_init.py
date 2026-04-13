import asyncio
import logging
from bot import get_application

logging.basicConfig(level=logging.INFO)

async def test_init():
    print("Testing bot initialization...")
    try:
        app = get_application(use_persistence=True)
        if app:
            print("✅ Application created successfully.")
            # We don't want to actually start it and poll
            # Just initialize and see if it fails
            await app.initialize()
            print("✅ Application initialized successfully.")
            await app.shutdown()
            print("✅ Application shutdown successfully.")
        else:
            print("❌ Failed to create application.")
    except Exception as e:
        print(f"❌ Error during initialization: {e}")

if __name__ == "__main__":
    asyncio.run(test_init())
