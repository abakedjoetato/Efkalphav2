"""
Fixed Bot Runner

This script runs the Discord bot with our fixed py-cord environment.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fixed_bot.log")
    ]
)

logger = logging.getLogger("FixedRunner")

def main():
    # Load environment variables
    load_dotenv()
    
    # Import our fixed environment first
    logger.info("Setting up fixed py-cord environment...")
    try:
        import fixed_py_cord_env
        logger.info("Successfully set up fixed py-cord environment")
    except ImportError as e:
        logger.error(f"Failed to import fixed_py_cord_env: {e}")
        return 1
    
    # Check for Discord token
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN not found in environment variables")
        return 1
    
    # Now try to import our bot module
    logger.info("Importing bot module...")
    try:
        import utils.logging_setup
        utils.logging_setup.setup_logging()
        
        # Import bot module
        from bot import Bot
        logger.info("Successfully imported Bot class")
        
        # Create and run bot instance
        logger.info("Creating bot instance...")
        bot_instance = Bot(production=True)
        
        # Start the bot
        logger.info("Starting Discord bot...")
        bot_instance.run(token)
        
        return 0
    except Exception as e:
        logger.error(f"Error setting up bot: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())