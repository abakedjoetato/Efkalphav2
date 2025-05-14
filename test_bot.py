"""
Test Discord Bot

This is a minimal test bot to verify Discord connectivity.
"""

import os
import sys
import logging
import importlib
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(), 
        logging.FileHandler("test_bot.log")
    ]
)
logger = logging.getLogger("TestBot")

# Load environment variables
load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")

# Verify token
if not TOKEN:
    logger.error("DISCORD_TOKEN environment variable is not set")
    sys.exit(1)

def find_discord_module():
    """Try different approaches to import the Discord module"""
    # Check system path first
    logger.info("Python system path:")
    for p in sys.path:
        logger.info(f"- {p}")
    
    # Try direct import
    try:
        import discord
        logger.info(f"Found discord module at: {discord.__file__}")
        
        # Check for extension module
        if hasattr(discord, 'ext'):
            logger.info("Discord module has 'ext' attribute")
            import discord.ext.commands
            logger.info("Successfully imported discord.ext.commands")
            
            # Check if it's py-cord
            if hasattr(discord.ext.commands.Bot, 'slash_command'):
                logger.info("Detected py-cord (has slash_command attribute)")
            else:
                logger.info("Detected discord.py (no slash_command attribute)")
                
            return discord
        else:
            logger.error("Discord module missing 'ext' attribute")
    except ImportError as e:
        logger.error(f"Failed to import discord: {e}")
    except AttributeError as e:
        logger.error(f"Attribute error with discord module: {e}")
        
    # Try to find the module manually
    try:
        for path in sys.path:
            discord_path = os.path.join(path, 'discord')
            if os.path.exists(discord_path):
                logger.info(f"Found discord module at: {discord_path}")
    except Exception as e:
        logger.error(f"Error searching for discord module: {e}")
        
    return None

def run_bot():
    """Run a minimal Discord bot"""
    discord = find_discord_module()
    
    if not discord:
        logger.error("Could not find a working discord module")
        sys.exit(1)
    
    # Create a minimal client
    try:
        if hasattr(discord, 'Client'):
            client = discord.Client(intents=discord.Intents.default())
            
            @client.event
            async def on_ready():
                logger.info(f"Logged in as {client.user} (ID: {client.user.id})")
                logger.info("Bot is connected to Discord!")
                
            logger.info("Starting Discord client...")
            client.run(TOKEN)
        else:
            logger.error("Discord module doesn't have Client class")
    except Exception as e:
        logger.error(f"Error running Discord client: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Starting test Discord bot...")
    run_bot()
    logger.info("Test bot process exited")