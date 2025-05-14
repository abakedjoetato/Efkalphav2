"""
Simplified Discord bot runner for Replit environment
"""
import os
import sys
import logging
import asyncio
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Make sure our custom Discord implementation is being used
if "discord.ext.commands" in sys.modules:
    del sys.modules["discord.ext.commands"]

# Import our custom modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import core modules
import discord
from discord.ext import commands

class SimpleBot(commands.Bot):
    """A simplified Discord bot implementation that works in Replit"""
    
    def __init__(self):
        """Initialize the bot with necessary configurations"""
        # Create intents with required permissions
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        
        super().__init__(
            command_prefix="!",  # Simple prefix to match original bot
            intents=intents,
            case_insensitive=True
        )
        
        # Store bot configuration
        self.db_client = None
        self.db = None
        self.premium_servers = set()
        self.config = {}
        self.startup_time = None
        self.is_pycord_261 = True  # Assume compatibility mode
        
        # Register event handlers
        @self.event
        async def on_ready():
            """Called when the bot is ready to be used"""
            logger.info(f"Logged in as {self.user.name} ({self.user.id})")
            logger.info(f"Bot is connected to {len(self.guilds)} servers")
            logger.info("Bot is ready!")
            
        @self.event
        async def on_error(event, *args, **kwargs):
            """Called when an error occurs during an event"""
            logger.error(f"Error in event {event}: {sys.exc_info()[1]}")
            logger.error(f"Event args: {args}")
            
        @self.event 
        async def on_command_error(ctx, error):
            """Called when a command raises an error"""
            logger.error(f"Command error: {error}")
            await ctx.send(f"Error: {error}")

    async def setup_hook(self):
        """Bot initialization that needs to run after connect"""
        try:
            # Connect to MongoDB
            mongo_uri = os.getenv("MONGODB_URI")
            if mongo_uri:
                import motor.motor_asyncio
                logger.info("Connecting to MongoDB...")
                self.db_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
                self.db = self.db_client.lastfix
                logger.info("Connected to MongoDB")
            else:
                logger.warning("MONGODB_URI not set, database functionality will be limited")
                
            # Load cogs
            logger.info("Loading cogs...")
            for filename in os.listdir('cogs'):
                if filename.endswith('.py'):
                    try:
                        await self.load_extension(f'cogs.{filename[:-3]}')
                        logger.info(f"Loaded cog: {filename}")
                    except Exception as e:
                        logger.error(f"Failed to load cog {filename}: {e}")
            logger.info("Finished loading cogs")
                
        except Exception as e:
            logger.error(f"Error in setup: {e}")
            
    async def close(self):
        """Properly close connections and shutdown"""
        logger.info("Bot is shutting down...")
        # Close MongoDB client
        if self.db_client:
            self.db_client.close()
            logger.info("Closed MongoDB connection")
        await super().close()

async def main():
    """Main entry point for the bot"""
    # Get Discord token
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN not set in environment variables or .env file")
        return
        
    # Create bot instance
    bot = SimpleBot()
    
    # Connect to Discord
    try:
        logger.info("Starting bot...")
        await bot.start(token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())