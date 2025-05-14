"""
Enhanced run script for the Discord bot with py-cord 2.6.1 compatibility.

This script provides a more robust entry point for running the Discord bot,
with proper error handling, module loading, and configuration management.
"""

import os
import sys
import asyncio
import logging
import importlib.util
from typing import Dict, List, Optional, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Try to import bot-related modules
try:
    from bot import Bot
except ImportError as e:
    logger.error(f"Failed to import Bot class: {e}")
    sys.exit(1)

# Compatibility check
try:
    from utils.compatibility_checker import print_compatibility_report
    print_compatibility_report()
except ImportError:
    logger.warning("Compatibility checker not available, skipping compatibility check")


def get_env_variable(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Get an environment variable, with options for defaults and marking as required.
    
    Args:
        name: Name of the environment variable
        default: Default value if not set
        required: Whether the variable is required
        
    Returns:
        The value of the environment variable, or the default
        
    Raises:
        ValueError: If the variable is required and not set
    """
    value = os.environ.get(name)
    
    # Try to load from .env file if not in environment
    if not value and os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        try:
                            key, val = line.strip().split("=", 1)
                            if key == name:
                                value = val.strip().strip('"').strip("'")
                                break
                        except ValueError:
                            continue
        except Exception as e:
            logger.error(f"Error reading .env file: {e}")
    
    if not value:
        if required:
            raise ValueError(f"Required environment variable {name} not set")
        return default
    
    return value


async def load_cogs(bot: Bot, cogs_dir: str = "cogs") -> Dict[str, bool]:
    """
    Load all cogs from the given directory with error handling.
    
    Args:
        bot: The bot instance
        cogs_dir: Directory containing cog modules
        
    Returns:
        Dictionary mapping cog names to load success status
    """
    results = {}
    
    # Make sure the directory exists
    if not os.path.isdir(cogs_dir):
        logger.error(f"Cogs directory '{cogs_dir}' not found")
        return results
    
    # Get all Python files in the directory
    try:
        cog_files = [f[:-3] for f in os.listdir(cogs_dir) if f.endswith(".py") and not f.startswith("_")]
    except Exception as e:
        logger.error(f"Failed to list files in cogs directory: {e}")
        return results
    
    # Try to load each cog
    for cog_file in cog_files:
        cog_name = f"{cogs_dir}.{cog_file}"
        try:
            if hasattr(bot, "load_extension_async"):
                # Use async loading if available
                await bot.load_extension_async(cog_name)
            else:
                # Fall back to sync loading
                bot.load_extension(cog_name)
            
            logger.info(f"Successfully loaded cog: {cog_name}")
            results[cog_name] = True
        except Exception as e:
            logger.error(f"Failed to load cog {cog_name}: {e}")
            results[cog_name] = False
    
    return results


async def setup_database(bot: Bot) -> bool:
    """
    Set up MongoDB database connection.
    
    Args:
        bot: Bot instance
        
    Returns:
        True if successful, False otherwise
    """
    # Get MongoDB connection string
    mongo_uri = get_env_variable("MONGODB_URI", required=False)
    if not mongo_uri:
        logger.warning("MONGODB_URI not set, database features will be limited")
        return False
    
    # Initialize database connection
    try:
        if hasattr(bot, "init_db"):
            # Use bot.init_db if available
            success = await bot.init_db()
            if success:
                logger.info("Successfully connected to MongoDB database")
                return True
            else:
                logger.error("Failed to connect to MongoDB database")
                return False
        else:
            # Try the safe_mongodb_compat module
            try:
                from utils.safe_mongodb_compat import init_mongodb
                result = await init_mongodb(mongo_uri, "bot_db")
                if result.success:
                    logger.info("Successfully connected to MongoDB database using safe_mongodb_compat")
                    return True
                else:
                    logger.error(f"Failed to connect to MongoDB database: {result.error}")
                    return False
            except ImportError:
                logger.error("Neither bot.init_db nor safe_mongodb_compat.init_mongodb are available")
                return False
    except Exception as e:
        logger.error(f"Unexpected error initializing database: {e}", exc_info=True)
        return False


async def main():
    """Main entry point."""
    try:
        # Get Discord token
        token = get_env_variable("DISCORD_TOKEN", required=True)
        if not token:
            logger.error("DISCORD_TOKEN environment variable not set")
            return
        
        # Create bot with proper intents
        bot = Bot(production=True)
        
        # Start with 1 cog to confirm basic functionality
        template_cog_name = "cogs.cog_template_fixed"
        try:
            if hasattr(bot, "load_extension_async"):
                # Use async loading if available
                await bot.load_extension_async(template_cog_name)
            else:
                # Fall back to sync loading
                bot.load_extension(template_cog_name)
                
            logger.info(f"Successfully loaded template cog: {template_cog_name}")
        except Exception as e:
            logger.warning(f"Couldn't load template cog, but continuing: {e}")
        
        # Load remaining cogs
        cog_results = await load_cogs(bot)
        
        total_cogs = len(cog_results)
        loaded_cogs = sum(1 for success in cog_results.values() if success)
        logger.info(f"Loaded {loaded_cogs}/{total_cogs} cogs")
        
        # Set up MongoDB
        db_success = await setup_database(bot)
        if not db_success:
            logger.warning("Database setup failed or was skipped")
        
        # Start the bot
        logger.info("Starting bot...")
        await bot.start(token)
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    # Run the main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)