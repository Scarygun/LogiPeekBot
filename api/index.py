import os
import asyncio
import logging
from flask import Flask, request
from telegram import Update
from bot import get_application

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global application instance
_application = None

async def get_app_instance():
    global _application
    if _application is None:
        _application = get_application()
        await _application.initialize()
        await _application.start()
    return _application

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Handle Telegram Webhook POST requests."""
    try:
        update_data = request.get_json(force=True)
        
        # We need a loop to initialize and process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        application = loop.run_until_complete(get_app_instance())
        update = Update.de_json(update_data, application.bot)
        loop.run_until_complete(application.process_update(update))
        
        return 'OK', 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return str(e), 500

@app.route('/')
def index():
    return "LogiPeekBot Webhook Handler is Active!"

# For Vercel, the entry point is the Flask app
# The file should be named api/index.py or similar
