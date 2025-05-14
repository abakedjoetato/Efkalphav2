"""
Discord Adapter

This module provides a compatibility layer for different Discord libraries,
ensuring that the bot works with any version of discord.py or py-cord.
"""

import os
import sys
import logging
import importlib
from typing import Optional, Dict, Any, List, Union
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DiscordAdapter")

# Load environment variables
load_dotenv()

# Discord token
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    logger.error("DISCORD_TOKEN environment variable not set")
    sys.exit(1)

# Try to import discord
try:
    import discord
    logger.info(f"Imported discord module")
    
    # Check version
    if hasattr(discord, "__version__"):
        logger.info(f"Discord library version: {discord.__version__}")
        
        # Check if it's py-cord
        if hasattr(discord, "application_commands"):
            logger.info("Detected py-cord (has application_commands)")
        else:
            logger.info("Detected discord.py (no application_commands)")
    
    # Check if it has ext module
    if hasattr(discord, "ext"):
        logger.info("Discord module has ext attribute")
        
        # Try importing commands
        try:
            from discord.ext import commands
            logger.info("Successfully imported discord.ext.commands")
        except ImportError as e:
            logger.error(f"Failed to import discord.ext.commands: {e}")
            sys.exit(1)
    else:
        logger.error("Discord module missing ext attribute")
        sys.exit(1)
        
except ImportError as e:
    logger.error(f"Failed to import discord: {e}")
    sys.exit(1)

class DiscordBot:
    """
    Discord bot with compatibility for any Discord library.
    
    This class provides a unified interface for Discord bots,
    regardless of whether they're using discord.py or py-cord.
    """
    
    def __init__(self, command_prefix: str = "!", **options):
        """
        Initialize the Discord bot.
        
        Args:
            command_prefix: The command prefix to use
            **options: Additional options for the bot
        """
        # Set default options
        default_options = {
            "intents": discord.Intents.default(),
            "description": "Discord Bot"
        }
        
        # Enable additional intents
        default_options["intents"].message_content = True
        default_options["intents"].members = True
        
        # Merge options
        options = {**default_options, **options}
        
        # Create the bot
        self.bot = commands.Bot(command_prefix=command_prefix, **options)
        
        # Set up events
        @self.bot.event
        async def on_ready():
            logger.info(f"Bot is ready! Logged in as {self.bot.user}")
            logger.info(f"Bot ID: {self.bot.user.id}")
            logger.info(f"Connected to {len(self.bot.guilds)} guilds")
            
            # Set activity
            activity = discord.Activity(
                type=discord.ActivityType.playing,
                name="Emeralds Killfeed"
            )
            await self.bot.change_presence(activity=activity)
    
    def load_extension(self, name: str):
        """
        Load an extension.
        
        Args:
            name: The name of the extension to load
            
        Returns:
            Whether the extension was loaded successfully
        """
        try:
            self.bot.load_extension(name)
            logger.info(f"Loaded extension: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load extension {name}: {e}")
            return False
    
    def load_extensions_from_directory(self, directory: str):
        """
        Load all extensions from a directory.
        
        Args:
            directory: The directory to load extensions from
            
        Returns:
            The number of extensions loaded successfully
        """
        logger.info(f"Loading extensions from {directory}...")
        
        # Import glob
        import glob
        
        # Get Python files
        extension_files = glob.glob(f"{directory}/*.py")
        
        # Load each extension
        count = 0
        for file_path in extension_files:
            # Get extension name
            file_name = os.path.basename(file_path)
            extension_name = f"{directory}.{os.path.splitext(file_name)[0]}"
            
            # Skip __init__.py and similar files
            if file_name.startswith("__"):
                continue
            
            # Load the extension
            if self.load_extension(extension_name):
                count += 1
        
        logger.info(f"Loaded {count} extensions from {directory}")
        return count
    
    def run(self):
        """Run the bot."""
        logger.info("Starting bot...")
        self.bot.run(TOKEN)
        
# Create a function to run the bot
def run_bot():
    """Run the Discord bot."""
    # Create the bot
    bot = DiscordBot(command_prefix="!")
    
    # Load extensions
    try:
        # First try to load from cogs directory
        if os.path.exists("cogs"):
            bot.load_extensions_from_directory("cogs")
        
        # Then try to load from commands directory
        if os.path.exists("commands"):
            bot.load_extensions_from_directory("commands")
    except Exception as e:
        logger.error(f"Error loading extensions: {e}")
    
    # Run the bot
    bot.run()

if __name__ == "__main__":
    run_bot()