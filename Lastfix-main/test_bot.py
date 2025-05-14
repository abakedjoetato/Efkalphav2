"""
Test bot for validating cog functionality

This simple bot loads our test cogs to ensure they work properly.
"""

import os
import logging
import discord
from discord.ext import commands

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create the bot instance
bot = commands.Bot(
    intents=discord.Intents.all(),
    command_prefix="!"  # Fallback prefix for non-slash commands
)

@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user}")
    
    # Sync application commands
    logger.info("Syncing application commands...")
    await bot.sync_commands()
    logger.info("Application commands synced!")

# Load our updated cogs
def load_cogs():
    try:
        # Load our fixed bounties cog
        bot.load_extension("cogs.bounties_fixed")
        logger.info("Loaded fixed bounties cog")
    except Exception as e:
        logger.error(f"Failed to load bounties_fixed cog: {e}")
        
    try:
        # Also load our simple test cog as a fallback
        bot.load_extension("cogs.simple_bounties")
        logger.info("Loaded simple bounties cog")
    except Exception as e:
        logger.error(f"Failed to load simple_bounties cog: {e}")

# Entry point
def main():
    logger.info("Starting test bot...")
    load_cogs()
    
    # Run the bot with the token
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("No DISCORD_TOKEN found in environment variables!")
        return
    
    bot.run(token)

if __name__ == "__main__":
    main()