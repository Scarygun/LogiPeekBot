import os
import asyncio
import logging
import traceback
from threading import Lock
from flask import Flask, request
from telegram import Update
from bot import get_application
from config import BOT_TOKEN

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global application instance
_application = None
_loop = asyncio.new_event_loop()
_loop_lock = Lock()

async def get_app_instance():
    global _application
    if _application is None:
        try:
            if not BOT_TOKEN:
                logger.error("BOT_TOKEN is missing from environment variables!")
                return None
            
            logger.info("Initializing Bot Application...")
            # Initialize the PTB application
            _application = get_application(use_persistence=True)
            await _application.initialize()
            if _application.post_init:
                logger.info("Running PTB post_init hook for webhook mode...")
                await _application.post_init(_application)
            await _application.start()
            logger.info("Bot application initialized and started successfully.")
        except Exception as e:
            logger.error(f"CRITICAL: Failed to initialize bot: {e}")
            logger.error(traceback.format_exc())
            _application = None
            raise e
    return _application

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Handle Telegram Webhook POST requests."""
    try:
        update_data = request.get_json(force=True)
        logger.info(f"Received update: {update_data.get('update_id')}")

        with _loop_lock:
            asyncio.set_event_loop(_loop)
            application = _loop.run_until_complete(get_app_instance())
            if not application:
                return 'Bot Not Initialized', 500

            update = Update.de_json(update_data, application.bot)
            _loop.run_until_complete(application.process_update(update))
        
        return 'OK', 200
    except Exception as e:
        error_msg = f"Error in webhook: {e}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg, 500

@app.route('/')
def index():
    return "LogiPeekBot Webhook Handler is Active!"

@app.route('/health')
def health():
    return "OK", 200
