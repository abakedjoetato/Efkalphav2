"""
Template Cog with py-cord 2.6.1 Compatibility (Simplified)

This is a simplified version of the template cog that demonstrates
proper command usage with py-cord 2.6.1.
"""

import logging
from typing import Optional

import discord
from discord import Option, Interaction, ApplicationContext
from discord.ext import commands

# Import compatibility utilities
from utils.discord_compat import create_slash_group, create_subgroup

# Set up logging
logger = logging.getLogger(__name__)

class SimpleTemplateCog(commands.Cog):
    """A simplified template cog for py-cord 2.6.1"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Create slash command group
        self.simple_group = create_slash_group(
            name="simple",
            description="Simple commands for demonstration",
            guild_ids=getattr(self.bot, "debug_guilds", None)
        )
        
        # Register commands on the group
        @self.simple_group.command(
            name="ping",
            description="Check if the bot is responsive"
        )
        async def ping(ctx: ApplicationContext):
            await ctx.respond(f"Pong! Bot latency: {round(self.bot.latency * 1000)}ms")
        
        @self.simple_group.command(
            name="echo",
            description="Echo back a message"
        )
        async def echo(
            ctx: ApplicationContext,
            message: Option(str, "Message to echo back", required=True)
        ):
            await ctx.respond(f"You said: {message}")
        
        logger.info(f"{self.__class__.__name__} cog initialized")
    
    # Normal prefixed command
    @commands.command(name="simple_test", help="Test prefixed command")
    async def test_prefix_command(self, ctx):
        """Test prefixed command implementation"""
        await ctx.send("Simple prefix command working!")


def setup(bot):
    """Add the cog to the bot"""
    bot.add_cog(SimpleTemplateCog(bot))