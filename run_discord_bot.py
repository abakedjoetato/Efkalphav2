"""
Discord Bot Launcher - Replit Compatible Version

This script ensures compatibility with py-cord and properly initializes the bot
"""

import os
import sys
import logging
import importlib
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger("DiscordBotLauncher")

def ensure_discord_setup():
    """
    Ensure py-cord is properly set up and handling discord imports
    """
    # First import our compatibility layer
    try:
        import discord_compat
        logger.info("Loaded discord compatibility layer")
        
        # Now try to import discord and confirm it works correctly
        try:
            import discord
            if hasattr(discord, 'ext') and hasattr(discord.ext, 'commands'):
                logger.info(f"Using discord library version: {discord.__version__}")
                # Successfully loaded discord with compatibility layer
                return True
            else:
                logger.error("Even with compatibility layer, discord library is missing expected attributes")
                return False
        except ImportError as e:
            logger.error(f"Failed to import discord after compatibility layer: {e}")
            return False
    except ImportError:
        logger.warning("Could not import discord_compat module")
        
        # Fall back to standard method
        try:
            import discord
            if hasattr(discord, 'ext') and hasattr(discord.ext, 'commands'):
                logger.info(f"Using discord library version: {discord.__version__}")
                return True
            else:
                logger.error("Discord library is missing expected attributes")
                return False
        except ImportError as e:
            logger.error(f"Failed to import discord: {e}")
            return False
    
    return False

def setup_bot():
    """
    Import the bot module and initialize the bot
    """
    if not ensure_discord_setup():
        logger.error("Failed to set up discord properly")
        return None
        
    # Import main bot module
    try:
        import bot
        return bot.Bot(production=True)
    except ImportError as e:
        logger.error(f"Failed to import bot module: {e}")
        return None
    except Exception as e:
        logger.error(f"Error initializing bot: {e}", exc_info=True)
        return None

def run_bot():
    """
    Run the Discord bot
    """
    # Get the token
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable is not set")
        return
    
    # Set up and run the bot
    bot = setup_bot()
    if bot:
        try:
            logger.info("Starting bot...")
            bot.run(token)
        except Exception as e:
            logger.error(f"Error running bot: {e}", exc_info=True)
    else:
        logger.error("Failed to initialize bot")

if __name__ == "__main__":
    try:
        run_bot()
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)