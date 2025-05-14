"""
Replit Discord Bot Runner

This script serves as the Replit entry point to start the Discord bot.
It handles all initialization and sets up the necessary configurations.
"""

import logging
import os
import sys
import asyncio

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord_bot')

# Ensure current directory is in path
if '.' not in sys.path:
    sys.path.insert(0, '.')
    logger.info("Added current directory to Python path")

# Verify environment variables
if not os.environ.get('DISCORD_TOKEN'):
    logger.error("DISCORD_TOKEN not found in environment variables")
    print("Please add your Discord token in the Secrets tab")
    sys.exit(1)

if not os.environ.get('MONGODB_URI'):
    logger.warning("MONGODB_URI not found in environment variables")
    print("Please add your MongoDB URI in the Secrets tab for database functionality")

# Import late to allow patch system to work first
try:
    # Import the compatibility layers first to ensure proper patching
    try:
        logger.info("Initializing compatibility layers...")
        from utils.ext_commands_compat import setup_ext_commands_compat
        setup_ext_commands_compat()
        
        from utils.discord_patches import patch_all
        patch_all()
        logger.info("Applied compatibility patches")
    except ImportError as e:
        logger.warning(f"Error importing compatibility modules: {e}")
        
    # Now import the main function to run the bot
    try:
        from main import main as run_main
        
        async def main():
            logger.info("Starting Discord bot...")
            try:
                await run_main()
            except Exception as e:
                logger.error(f"Error running bot: {e}", exc_info=True)
                return False
                
            return True
            
        if __name__ == "__main__":
            success = asyncio.run(main())
            if not success:
                sys.exit(1)
    except ImportError:
        # If main fails, try directly importing the bot
        try:
            from bot import Bot
            
            async def main():
                token = os.environ.get('DISCORD_TOKEN')
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
                
                # Connect to database
                await bot.init_db()
                
                # Run the bot
                await bot.start(token)
                
            if __name__ == "__main__":
                try:
                    asyncio.run(main())
                except KeyboardInterrupt:
                    logger.info("Bot stopped via keyboard interrupt")
                except Exception as e:
                    logger.error(f"Bot crashed: {e}", exc_info=True)
                    sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to import bot: {e}", exc_info=True)
            sys.exit(1)

except Exception as e:
    logger.error(f"Initialization failed: {e}", exc_info=True)
    sys.exit(1)