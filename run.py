"""
Discord Bot Entry Point

This script is the main entry point for the Discord bot.
It initializes and starts the bot with all necessary configurations.
"""

import os
import sys
import asyncio
import logging
import signal
from typing import Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log")
    ]
)

logger = logging.getLogger("bot_runner")

# Global variables
bot = None

def setup_environment():
    """Set up the environment for the Discord bot"""
    # Load environment variables from .env file
    load_dotenv()
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Set up Python path
    sys.path.insert(0, os.path.abspath("."))
    
    # Check for required environment variables
    if not os.environ.get("DISCORD_TOKEN"):
        logger.error("DISCORD_TOKEN environment variable not set")
        sys.exit(1)
    
    # Set up MongoDB URI if not set
    if not os.environ.get("MONGODB_URI"):
        logger.warning("MONGODB_URI environment variable not set, using default")
        os.environ["MONGODB_URI"] = "mongodb://localhost:27017/discordbot"
    
    logger.info("Environment set up successfully")

async def initialize_bot():
    """Initialize the Discord bot"""
    global bot
    
    try:
        # Import the bot class
        from bot import Bot
        from config import config
        
        # Initialize the Bot
        logger.info("Initializing bot...")
        discord_config = config.get("discord", {})
        
        production = discord_config.get("production", False)
        debug_guilds = discord_config.get("debug_guilds", [])
        
        bot = Bot(production=production, debug_guilds=debug_guilds)
        
        # Initialize the database connection
        logger.info("Initializing database connection...")
        db_success = await bot.init_db()
        
        if not db_success:
            logger.error("Failed to initialize database connection")
        
        # Load extensions/cogs
        for cog_name in os.listdir("cogs"):
            if cog_name.endswith(".py") and not cog_name.startswith("_"):
                cog_module = f"cogs.{cog_name[:-3]}"
                try:
                    logger.info(f"Loading extension: {cog_module}")
                    bot.load_extension(cog_module)
                except Exception as e:
                    logger.error(f"Failed to load extension {cog_module}: {e}")
        
        # Initialize premium manager
        try:
            from utils.premium_manager import PremiumManager
            
            pm = PremiumManager(bot.db)
            await pm.initialize()
            bot.premium_manager = pm
            logger.info("Premium manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize premium manager: {e}")
            bot.premium_manager = None
            
        return True
    except Exception as e:
        logger.error(f"Error initializing bot: {e}")
        return False

async def start_bot():
    """Start the Discord bot"""
    global bot
    
    if not bot:
        logger.error("Bot not initialized")
        return False
    
    try:
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            logger.error("DISCORD_TOKEN environment variable not set")
            return False
        
        logger.info("Starting bot...")
        await bot.start(token)
        return True
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return False

def cleanup(signum, frame):
    """Clean up resources when the bot is stopped"""
    global bot
    
    logger.info(f"Received signal {signum}, shutting down")
    
    if bot:
        # Create an event loop for cleanup
        loop = asyncio.get_event_loop()
        
        # Close the bot
        try:
            loop.run_until_complete(bot.close())
        except Exception as e:
            logger.error(f"Error closing bot: {e}")
    
    logger.info("Cleanup complete")
    sys.exit(0)

async def main():
    """Main entry point"""
    # Set up the environment
    setup_environment()
    
    # Initialize the bot
    init_success = await initialize_bot()
    
    if not init_success:
        logger.error("Failed to initialize bot")
        return
    
    # Start the bot
    await start_bot()

def run():
    """Run the bot using asyncio"""
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        cleanup(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        cleanup(signal.SIGTERM, None)

if __name__ == "__main__":
    run()