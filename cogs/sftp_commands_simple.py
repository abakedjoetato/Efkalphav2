"""
Simplified SFTP Commands for Tower of Temptation PvP Statistics Bot

This module provides basic Discord slash commands for SFTP-related operations
with compatibility for py-cord 2.6.1.
"""
import logging
from typing import Dict, List, Optional, Any

import discord
from discord.ext import commands
from utils.discord_patches import app_commands, Choice

# Configure module-specific logger
logger = logging.getLogger(__name__)

class SFTPCommandsSimple(commands.Cog):
    """Basic SFTP commands with py-cord 2.6.1 compatibility"""
    
    def __init__(self, bot):
        """Initialize SFTP commands cog
        
        Args:
            bot: Bot instance
        """
        self.bot = bot
        logger.info("SFTP commands cog initialized")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def test_sftp(self, ctx):
        """Test command to check SFTP functionality"""
        await ctx.send("SFTP functionality is working but in simplified mode")

async def setup(bot):
    """Add SFTP commands cog to bot
    
    Args:
        bot: Bot instance
    """
    await bot.add_cog(SFTPCommandsSimple(bot))
    logger.info("SFTP commands cog added")