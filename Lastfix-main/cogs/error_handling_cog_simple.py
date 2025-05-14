"""
Simplified Error Handling Cog for Tower of Temptation PvP Statistics Bot

This cog provides centralized error handling for all commands with py-cord 2.6.1 compatibility.
"""
import logging
import traceback
from typing import Dict, Any, Optional, List, Union

import discord
from discord.ext import commands
from utils.discord_patches import app_commands, Choice

# Configure module-specific logger
logger = logging.getLogger(__name__)

class ErrorHandlingCog(commands.Cog):
    """
    Error handling cog for the Discord bot.
    
    This cog provides centralized error handling and debugging tools.
    """
    
    def __init__(self, bot):
        """Initialize error handling cog
        
        Args:
            bot: Bot instance
        """
        self.bot = bot
        logger.info("Error handling cog initialized")
        
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle traditional command errors
        
        Args:
            ctx: Command context
            error: Error that occurred
        """
        # Log the error
        logger.error(f"Error in command {ctx.command}: {error}")
        logger.error(traceback.format_exception(type(error), error, error.__traceback__))
        
    @commands.Cog.listener()
    async def on_app_command_error(self, interaction, error):
        """Handle application command errors
        
        Args:
            interaction: Discord interaction
            error: Error that occurred
        """
        # Log the error
        logger.error(f"Error in app command: {error}")
        logger.error(traceback.format_exception(type(error), error, error.__traceback__))

async def setup(bot):
    """Add error handling cog to bot
    
    Args:
        bot: Bot instance
    """
    await bot.add_cog(ErrorHandlingCog(bot))
    logger.info("Error handling cog added")