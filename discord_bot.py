"""
Discord Bot Implementation using py-cord directly
This is a simplified version that uses py-cord for Discord API access
"""

import os
import sys
import asyncio
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("discord_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Make sure we're using py-cord, not local discord
if 'discord' in sys.modules:
    del sys.modules['discord']
sys.path = [p for p in sys.path if not p.endswith('discord')]

try:
    import discord
    from discord.ext import commands
    import motor.motor_asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    logger.info(f"Successfully imported py-cord version {discord.__version__}")
except ImportError as e:
    logger.critical(f"Error importing required packages: {e}")
    raise

# Load environment variables
load_dotenv()

class DiscordBot(commands.Bot):
    """Main Discord bot class using py-cord"""
    
    def __init__(self):
        """Initialize the bot with proper intents and configuration"""
        # Set up Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Initialize the bot
        super().__init__(
            command_prefix="!",
            intents=intents,
            description="Discord Bot for Replit"
        )
        
        # Bot properties
        self.start_time = datetime.now()
        self.db_client = None
        self.db = None
    
    async def setup_hook(self):
        """Setup hook called when bot is starting"""
        # Connect to MongoDB
        await self.setup_database()
        
        # Load extensions
        await self.load_extensions()
    
    async def setup_database(self):
        """Set up the MongoDB database connection"""
        try:
            # Get MongoDB connection string
            mongo_uri = os.getenv("MONGODB_URI")
            if not mongo_uri:
                logger.warning("MONGODB_URI not found. Database functionality will be limited.")
                return
            
            # Connect to MongoDB
            self.db_client = AsyncIOMotorClient(mongo_uri)
            
            # Extract database name from URI or use default
            db_name = "discord_bot"
            try:
                # Try to parse database name from connection string
                parts = mongo_uri.split("/")
                if len(parts) >= 4:
                    parsed_db = parts[3].split("?")[0]  # Remove query parameters if present
                    if parsed_db:
                        db_name = parsed_db
            except Exception as e:
                logger.error(f"Error parsing database name from connection string: {e}")
            
            # Get database
            self.db = self.db_client[db_name]
            
            # Ping database to check connection
            await self.db_client.admin.command("ping")
            logger.info(f"Connected to MongoDB database: {db_name}")
        
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            self.db_client = None
            self.db = None
    
    async def load_extensions(self):
        """Load all extensions from the cogs folder"""
        try:
            # Load extensions from cogs directory
            cogs_dir = "cogs"
            
            # Check if directory exists
            if not os.path.isdir(cogs_dir):
                logger.warning(f"Cogs directory '{cogs_dir}' not found")
                return
            
            # Load each Python file in the cogs directory
            for filename in os.listdir(cogs_dir):
                if filename.endswith('.py') and not filename.startswith('_'):
                    try:
                        extension_name = f"cogs.{filename[:-3]}"
                        await self.load_extension(extension_name)
                        logger.info(f"Loaded extension: {extension_name}")
                    except Exception as e:
                        logger.error(f"Failed to load extension {filename}: {e}")
                        logger.error(traceback.format_exc())
        
        except Exception as e:
            logger.error(f"Error loading extensions: {e}")
            logger.error(traceback.format_exc())
    
    async def on_ready(self):
        """Event triggered when the bot is ready"""
        logger.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Set status
        try:
            await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="!help"))
        except Exception as e:
            logger.error(f"Error setting presence: {e}")
        
        logger.info("Bot is ready!")
    
    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        # If the command has its own error handler, don't do anything
        if hasattr(ctx.command, 'on_error'):
            return
        
        # If the cog has an error handler, don't do anything
        if ctx.cog and ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
            return
        
        # Get the original error
        error = getattr(error, 'original', error)
        
        # Log the error
        logger.error(f"Command '{ctx.command}' raised an error: {error}")
        
        # Handle different types of errors
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send(f"Command `{ctx.command}` is disabled.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(f"Command `{ctx.command}` cannot be used in private messages.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: `{error.param.name}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"Bad argument: {error}")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I don't have permission to execute this command.")
        else:
            # For all other errors, send a generic message
            await ctx.send(f"An error occurred: {error}")

async def main():
    """Main entry point for the bot"""
    # Check required environment variables
    if not os.getenv("DISCORD_TOKEN"):
        logger.critical("DISCORD_TOKEN environment variable is required.")
        return 1
    
    # Create and start the bot
    bot = DiscordBot()
    
    try:
        logger.info("Starting bot...")
        await bot.start(os.getenv("DISCORD_TOKEN"))
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.critical(f"Error starting bot: {e}")
        logger.critical(traceback.format_exc())
        return 1
    finally:
        # Close bot and database connections
        await bot.close()
        if bot.db_client:
            bot.db_client.close()
    
    return 0

if __name__ == "__main__":
    # Run the bot
    exit_code = asyncio.run(main())
    sys.exit(exit_code)