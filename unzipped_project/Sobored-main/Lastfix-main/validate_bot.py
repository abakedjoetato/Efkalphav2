"""
Bot Validation Script

This script performs a one-time verification check to ensure the bot
can properly connect to Discord and MongoDB.
"""

import os
import sys
import asyncio
import logging
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

async def validate_bot():
    """Main validation function."""
    logger.info("Starting Discord bot validation...")
    success = True
    
    # Check for Discord token
    discord_token = os.environ.get("DISCORD_TOKEN")
    if not discord_token:
        logger.error("❌ DISCORD_TOKEN environment variable not found")
        success = False
    else:
        logger.info("✅ DISCORD_TOKEN found")
    
    # Check for MongoDB URI
    mongodb_uri = os.environ.get("MONGODB_URI")
    if not mongodb_uri:
        logger.error("❌ MONGODB_URI environment variable not found")
        success = False
    else:
        logger.info("✅ MONGODB_URI found")
    
    # Attempt to import required modules
    try:
        import discord
        from discord.ext import commands
        logger.info(f"✅ Discord library imported successfully (version: {discord.__version__})")
        
        if hasattr(discord, '__title__') and discord.__title__ == 'py-cord':
            logger.info("✅ Using py-cord library")
            if discord.__version__ == '2.6.1':
                logger.info("✅ Correct py-cord version (2.6.1) detected")
            else:
                logger.warning(f"⚠️ Using py-cord version {discord.__version__}, but 2.6.1 is recommended")
        else:
            logger.warning("⚠️ Using discord.py instead of py-cord, which may cause compatibility issues")
    
    except ImportError as e:
        logger.error(f"❌ Failed to import Discord library: {e}")
        success = False
    
    try:
        import motor.motor_asyncio
        logger.info("✅ Motor MongoDB driver imported successfully")
        
        # Try to connect to MongoDB
        try:
            if mongodb_uri:
                client = motor.motor_asyncio.AsyncIOMotorClient(
                    mongodb_uri, 
                    serverSelectionTimeoutMS=5000
                )
                # Force a connection to test it
                await client.admin.command('ping')
                logger.info("✅ Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            success = False
    
    except ImportError as e:
        logger.error(f"❌ Failed to import MongoDB libraries: {e}")
        success = False
    
    # Try to import and apply compatibility patches
    try:
        try:
            from utils.discord_patches import patch_all as patches_patch_all
            patches_patch_all()
            logger.info("✅ Successfully imported and applied discord_patches")
        except ImportError:
            try:
                from utils.discord_compat import patch_all as compat_patch_all
                compat_patch_all()
                logger.info("✅ Successfully imported and applied discord_compat")
            except ImportError:
                logger.warning("⚠️ Could not import compatibility patches. Bot may have issues with py-cord 2.6.1")
    except Exception as e:
        logger.error(f"❌ Error applying compatibility patches: {e}")
    
    # Final verdict
    if success:
        logger.info("✅ All validation checks passed! The bot should be able to run correctly.")
        return 0
    else:
        logger.error("❌ Some validation checks failed. Please fix the issues before running the bot.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(validate_bot())
    sys.exit(exit_code)