"""
Discord Bot Entry Point Module

This is the main entry point to start the Discord bot.
It applies patches, initializes components, and runs the bot.
"""

import logging
import os
import asyncio
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot')

# Ensure that the utils modules are in the path
if os.path.exists('utils'):
    if 'utils' not in sys.path:
        sys.path.insert(0, '.')
        logger.info("Added current directory to sys.path")

# Apply the patch for discord.ext.commands before trying to import it
try:
    from utils.ext_commands_compat import setup_ext_commands_compat
    setup_ext_commands_compat()
    logger.info("Applied ext_commands_compat patches")
except ImportError:
    logger.warning("Could not import ext_commands_compat")

# Apply Discord patches
try:
    from utils.discord_patches import patch_all
    patch_all()
    logger.info("Applied discord_patches")
except ImportError:
    logger.warning("Could not import discord_patches")

# Import the actual bot
try:
    # First try the integrated bot
    try:
        from bot_integration import create_bot, setup_bot
        logger.info("Using integrated bot")
        async def main():
            bot = create_bot()
            await setup_bot(bot)
            await bot.start()
    except ImportError:
        # Fall back to the standard bot
        from bot import Bot
        logger.info("Using standard bot")
        async def main():
            # Get the token from environment variable
            token = os.environ.get('DISCORD_TOKEN')
            if not token:
                logger.error("No DISCORD_TOKEN found in environment variables")
                return
                
            # Create and start the bot
            bot = Bot(production=True)
            
            # Load extensions
            if os.path.exists('cogs'):
                logger.info("Loading cogs from 'cogs' directory")
                for filename in os.listdir('cogs'):
                    if filename.endswith('.py') and not filename.startswith('_'):
                        try:
                            extension_name = f'cogs.{filename[:-3]}'
                            bot.load_extension(extension_name)
                            logger.info(f"Loaded extension {extension_name}")
                        except Exception as e:
                            logger.error(f"Failed to load extension {filename}: {e}")
            
            # Run the bot
            await bot.init_db()  # Initialize database connection
            await bot.start(token)  # Start the bot with the token
except ImportError as e:
    logger.error(f"Failed to import bot modules: {e}")
    sys.exit(1)

# Run the bot
if __name__ == "__main__":
    try:
        logger.info("Starting Discord bot")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        sys.exit(1)