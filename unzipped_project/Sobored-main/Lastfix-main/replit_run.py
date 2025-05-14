"""
Replit Run Script

This script is specifically designed to be the entrypoint for Replit.
It loads environment variables and starts the Discord bot.
"""

import os
import sys
import asyncio
import logging
import traceback
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check if environment variables are set
discord_token = os.environ.get("DISCORD_TOKEN")
if not discord_token:
    logger.error("DISCORD_TOKEN environment variable not set.")
    sys.exit(1)

async def load_cogs(bot):
    """Load all cogs from the cogs directory."""
    logger.info("Loading cogs...")
    cog_count = 0
    failed_cogs = 0
    
    # Define explicitly which cogs to load and in what order
    # Critical/Infrastructure cogs come first
    priority_cogs = [
        "cogs.error_handling_cog_simple",  # Error handling (simplified for compatibility)
        "cogs.general",                   # Basic commands
        "cogs.admin",                     # Admin commands
        "cogs.help"                       # Help system
    ]
    
    # Feature cogs
    feature_cogs = [
        "cogs.setup_fixed",           # Server setup
        "cogs.bounties_fixed",        # Bounty system
        "cogs.premium_new_updated_fixed",  # Premium features
        "cogs.stats_fixed",           # Player statistics
        "cogs.rivalries_fixed",       # Player rivalries
        "cogs.new_csv_processor",     # CSV processing
        "cogs.events",                # Event handling
        "cogs.economy",               # Economy system
        "cogs.factions",              # Faction management
        "cogs.guild_settings",        # Guild settings
        "cogs.killfeed",              # Kill feed
        "cogs.log_processor",         # Log processing
        "cogs.player_links",          # Player linking
        "cogs.sftp_commands_simple"   # SFTP commands (simplified for compatibility)
    ]
    
    # Optional/template cogs
    optional_cogs = [
        "cogs.cog_template_fixed"     # Template for new cogs
    ]
    
    # Combine all cogs
    all_cogs = priority_cogs + feature_cogs + optional_cogs
    
    # Try to load all cogs
    for cog_name in all_cogs:
        try:
            if hasattr(bot, "load_extension_async"):
                await bot.load_extension_async(cog_name)
            else:
                bot.load_extension(cog_name)
            logger.info(f"Loaded cog: {cog_name}")
            cog_count += 1
        except Exception as e:
            logger.error(f"Failed to load cog {cog_name}: {e}")
            logger.error(traceback.format_exc())
            failed_cogs += 1
    
    logger.info(f"Loaded {cog_count} cogs, failed to load {failed_cogs} cogs")

async def setup_database(bot):
    """Set up the MongoDB database connection."""
    # Get MongoDB connection string
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        logger.warning("MONGODB_URI not set, database features will be limited")
        return False
    
    # Initialize database connection
    try:
        if hasattr(bot, "init_db"):
            success = await bot.init_db()
            if success:
                logger.info("Successfully connected to MongoDB database")
                return True
            else:
                logger.error("Failed to connect to MongoDB database")
                return False
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

async def main():
    """Main function to start the bot."""
    try:
        # Import the Bot class
        from bot import Bot
        
        # Try to import and apply various compatibility patches
        try:
            # First try the discord_patches module
            try:
                from utils.discord_patches import patch_all
                patch_all()
                logger.info("Applied discord_patches compatibility patches")
            except ImportError:
                # Fall back to discord_compat module
                from utils.discord_compat import patch_all
                patch_all()
                logger.info("Applied discord_compat compatibility patches")
        except ImportError:
            logger.warning("Could not import compatibility patches. Some features may not work correctly.")
        
        # Create bot
        logger.info("Creating Discord bot instance...")
        bot = Bot(production=True)
        
        # Set up database BEFORE loading cogs
        logger.info("Setting up database connection...")
        await setup_database(bot)
        
        # Load cogs AFTER database setup
        logger.info("Loading cogs...")
        await load_cogs(bot)
        
        # Start the bot
        logger.info("Starting Discord bot...")
        await bot.start(discord_token)
    
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Run the bot
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)