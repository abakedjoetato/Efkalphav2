"""
Simplified Discord Bot Implementation
This is a more straightforward version of the Discord bot focusing on core functionality.
"""

import os
import sys
import asyncio
import logging
import importlib
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Set up custom logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import discord.py
import discord
from discord.ext import commands

class SimpleBot(commands.Bot):
    """A simplified Discord bot implementation"""
    
    def __init__(self):
        """Initialize the bot"""
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Initialize the bot with command prefix and intents
        super().__init__(
            command_prefix="!",
            intents=intents,
            case_insensitive=True
        )
        
        # Set bot properties
        self.start_time = datetime.now()
        self.db = None
        
        # Add bot status
        self.activity = discord.Game(name="!help")
    
    async def setup_hook(self):
        """Setup hook called before the bot starts"""
        # Load cogs
        await self.load_cogs()
        
        # Set up database
        await self.setup_database()
    
    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        logger.info("Loading cogs...")
        cogs_dir = 'cogs'
        
        if not os.path.isdir(cogs_dir):
            logger.warning(f"Cogs directory '{cogs_dir}' not found")
            return
        
        # Create a list to track loaded and failed cogs
        loaded_cogs = []
        failed_cogs = []
        
        # Load each cog
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    loaded_cogs.append(cog_name)
                    logger.info(f"Loaded cog: {cog_name}")
                except Exception as e:
                    failed_cogs.append(cog_name)
                    logger.error(f"Failed to load cog {cog_name}: {e}")
                    logger.error(traceback.format_exc())
        
        logger.info(f"Loaded {len(loaded_cogs)} cogs. Failed to load {len(failed_cogs)} cogs.")
    
    async def setup_database(self):
        """Set up the database connection"""
        try:
            # Import database connection utilities
            from utils.db_connection import get_db_connection
            
            # Get the database connection
            self.db = await get_db_connection()
            
            if self.db:
                logger.info("Connected to MongoDB database")
                
                # Ensure indexes
                try:
                    from utils.db_connection import ensure_indexes
                    await ensure_indexes()
                except Exception as e:
                    logger.error(f"Failed to ensure indexes: {e}")
            else:
                logger.error("Failed to connect to MongoDB database")
        except Exception as e:
            logger.error(f"Error setting up database: {e}")
            logger.error(traceback.format_exc())
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Bot is ready!")
    
    async def on_error(self, event_method, *args, **kwargs):
        """Called when an event raises an uncaught exception"""
        logger.error(f"Error in {event_method}")
        logger.error(traceback.format_exc())
    
    async def on_command_error(self, ctx, error):
        """Handle command errors that aren't handled by the ErrorHandling cog"""
        if hasattr(ctx.command, 'on_error'):
            return  # Command has its own error handler
        
        # If we have the error handling cog, let it handle the error
        cog = ctx.bot.get_cog('ErrorHandling')
        if cog:
            logger.debug("Delegating error to ErrorHandling cog")
            return
        
        # If we reach here, no error handler caught this error
        error_message = str(error)
        
        try:
            await ctx.send(f"An error occurred: {error_message}")
        except discord.errors.Forbidden:
            pass  # Can't send messages in this channel
        
        logger.error(f"Unhandled command error in {ctx.command}: {error}")
        logger.error(traceback.format_exc())

async def main():
    """Main entry point for the bot"""
    # Load environment variables
    load_dotenv()
    
    # Check for Discord token
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.critical("DISCORD_TOKEN environment variable not set")
        return 1
    
    # Create and run the bot
    bot = SimpleBot()
    
    try:
        logger.info("Starting bot...")
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.critical(f"Error starting bot: {e}")
        logger.critical(traceback.format_exc())
        return 1
    finally:
        # Close the bot
        if not bot.is_closed():
            await bot.close()
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)