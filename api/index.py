import os
import asyncio
import logging
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

async def get_app_instance():
    global _application
    if _application is None:
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN is missing from environment variables!")
            return None
        
        # Initialize the PTB application
        _application = get_application(use_persistence=True)
        await _application.initialize()
        await _application.start()
        logger.info("Bot application initialized and started.")
    return _application

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Handle Telegram Webhook POST requests."""
    try:
        update_data = request.get_json(force=True)
        
        # Create or use current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        application = loop.run_until_complete(get_app_instance())
        if not application:
            return 'Bot Not Initialized', 500
            
        update = Update.de_json(update_data, application.bot)
        loop.run_until_complete(application.process_update(update))
        
        return 'OK', 200
    except Exception as e:
        logger.error(f"Error in webhook: {e}", exc_info=True)
        return str(e), 500

@app.route('/')
def index():
    return "LogiPeekBot Webhook Handler is Active!"

# Entry point for Vercel
# The app object is picked up by Vercel's python builder
