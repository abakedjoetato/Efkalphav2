"""
Replit-specific Discord Bot Runner

This script is designed to run the Discord bot in a Replit environment.
It handles some Replit-specific configurations and environment setup.
"""

import os
import sys
import asyncio
import logging
import signal
import traceback
from typing import Optional
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/replit_bot.log")
    ]
)

logger = logging.getLogger("replit_runner")

# Global variables
bot = None

def setup_replit_environment():
    """
    Set up the environment specifically for Replit
    
    This function handles Replit-specific environment setup and configuration.
    """
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
    
    # MongoDB URI is required for Replit
    if not os.environ.get("MONGODB_URI"):
        logger.error("MONGODB_URI environment variable not set")
        sys.exit(1)
        
    # Set production mode for Replit
    os.environ["PRODUCTION"] = "True"
    
    # Replit-specific Discord configuration
    debug_guilds = os.environ.get("DEBUG_GUILDS", "")
    if debug_guilds:
        logger.info(f"Debug guilds: {debug_guilds}")
    
    logger.info("Replit environment set up successfully")

async def initialize_bot_for_replit():
    """Initialize the Discord bot for Replit"""
    global bot
    
    try:
        # Import the bot class
        from bot import Bot
        from config import config
        
        # Force production mode
        logger.info("Initializing bot in production mode...")
        
        # Get debug guilds
        debug_guilds_str = os.environ.get("DEBUG_GUILDS", "")
        debug_guilds = [int(guild_id.strip()) for guild_id in debug_guilds_str.split(",") if guild_id.strip()]
        
        # Initialize the Bot in production mode
        bot = Bot(production=True, debug_guilds=debug_guilds)
        
        # Initialize the database connection
        logger.info("Initializing database connection...")
        db_success = await bot.init_db(max_retries=5, retry_delay=5)
        
        if not db_success:
            logger.error("Failed to initialize database connection")
            return False
        
        # Load extensions/cogs from cogs directory
        cogs_loaded = 0
        for cog_name in os.listdir("cogs"):
            if cog_name.endswith(".py") and not cog_name.startswith("_"):
                cog_module = f"cogs.{cog_name[:-3]}"
                try:
                    logger.info(f"Loading extension: {cog_module}")
                    bot.load_extension(cog_module)
                    cogs_loaded += 1
                except Exception as e:
                    logger.error(f"Failed to load extension {cog_module}: {e}")
                    traceback.print_exc()
        
        logger.info(f"Loaded {cogs_loaded} extensions")
        
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
        traceback.print_exc()
        return False

async def start_bot_for_replit():
    """Start the Discord bot for Replit"""
    global bot
    
    if not bot:
        logger.error("Bot not initialized")
        return False
    
    try:
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            logger.error("DISCORD_TOKEN environment variable not set")
            return False
        
        logger.info("Starting bot in Replit environment...")
        await bot.start(token)
        return True
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        traceback.print_exc()
        return False

def cleanup_replit(signum, frame):
    """Clean up resources when the bot is stopped in Replit"""
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

async def main_replit():
    """Main entry point for Replit"""
    # Set up the environment
    setup_replit_environment()
    
    # Initialize the bot
    init_success = await initialize_bot_for_replit()
    
    if not init_success:
        logger.error("Failed to initialize bot for Replit")
        return
    
    # Start the bot
    await start_bot_for_replit()

def run_replit():
    """Run the bot using asyncio in Replit environment"""
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup_replit)
    signal.signal(signal.SIGTERM, cleanup_replit)
    
    # Run the bot
    try:
        asyncio.run(main_replit())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        cleanup_replit(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        traceback.print_exc()
        cleanup_replit(signal.SIGTERM, None)

if __name__ == "__main__":
    run_replit()