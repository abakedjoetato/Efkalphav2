"""
Basic Commands Cog

This cog provides essential commands for the bot.
"""

import os
import re
import time
import datetime
import platform
import logging
from typing import Dict, List, Any, Optional, Union, Callable

# Import from compatibility layer
import discord_compat_layer as dcl
from discord_compat_layer import (
    Embed, Color, Colour, 
    Bot, Cog, Context, command,
    has_permissions, guild_only, is_owner
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("basic_commands.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BasicCommands(Cog, name="Basic Commands"):
    """
    Basic commands for general bot functionality.
    """
    
    def __init__(self, bot):
        """Initialize the basic commands cog"""
        self.bot = bot
        self.start_time = datetime.datetime.now()
        logger.info("Basic commands cog initialized")
    
    @command(name="ping", help="Check the bot's response time")
    async def ping(self, ctx):
        """
        Check the bot's response time.
        
        Usage: !ping
        """
        start_time = time.time()
        message = await ctx.send("Pinging...")
        end_time = time.time()
        
        # Calculate response time
        api_latency = round((end_time - start_time) * 1000)
        websocket_latency = round(self.bot.latency * 1000)
        
        # Create embed
        embed = Embed(
            title="🏓 Pong!",
            description="Bot Response Times",
            color=Color.green()
        )
        embed.add_field(name="API Latency", value=f"`{api_latency}ms`", inline=True)
        embed.add_field(name="Websocket Latency", value=f"`{websocket_latency}ms`", inline=True)
        
        await message.edit(content=None, embed=embed)
    
    @command(name="about", help="Display information about the bot")
    async def about(self, ctx):
        """
        Display information about the bot.
        
        Usage: !about
        """
        # Calculate uptime
        uptime = datetime.datetime.now() - self.start_time
        days, remainder = divmod(uptime.total_seconds(), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        uptime_str = f"{int(days)} days, {int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"
        
        # Get system info
        python_version = platform.python_version()
        discord_version = dcl.get_real_discord().__version__
        os_info = f"{platform.system()} {platform.release()}"
        
        # Create embed
        embed = Embed(
            title=f"About {self.bot.user.name}",
            description="A discord bot with advanced features and modular architecture.",
            color=Color.blue()
        )
        
        # Add bot info
        embed.add_field(name="Version", value="`1.0.0`", inline=True)
        embed.add_field(name="Library", value=f"`py-cord {discord_version}`", inline=True)
        embed.add_field(name="Python", value=f"`{python_version}`", inline=True)
        embed.add_field(name="OS", value=f"`{os_info}`", inline=True)
        embed.add_field(name="Uptime", value=f"`{uptime_str}`", inline=True)
        embed.add_field(name="Servers", value=f"`{len(self.bot.guilds)}`", inline=True)
        
        # Add footer
        embed.set_footer(text=f"Requested by {ctx.author}")
        
        # Add bot avatar if available
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        await ctx.send(embed=embed)
    
    @command(name="help", help="Show the help menu")
    async def custom_help(self, ctx, command_name: Optional[str] = None):
        """
        Show the help menu or help for a specific command.
        
        Usage: !help [command]
        Example: !help ping
        """
        if command_name:
            return await self._show_command_help(ctx, command_name)
        
        # Create main help embed
        embed = Embed(
            title="Bot Help",
            description="Here are the available commands. Use `!help [command]` for more details on a specific command.",
            color=Color.blue()
        )
        
        # Group commands by cog
        cog_commands = {}
        for cmd in self.bot.commands:
            cog_name = cmd.cog_name or "No Category"
            if cog_name not in cog_commands:
                cog_commands[cog_name] = []
            cog_commands[cog_name].append(cmd)
        
        # Add fields for each cog
        for cog_name, commands in sorted(cog_commands.items()):
            # Skip hidden cogs/commands
            if cog_name.lower() == "owner" and not await self.bot.is_owner(ctx.author):
                continue
            
            command_list = []
            for cmd in sorted(commands, key=lambda x: x.name):
                # Skip hidden commands
                if cmd.hidden:
                    continue
                command_list.append(f"`{cmd.name}` - {cmd.help or 'No description'}")
            
            if command_list:
                embed.add_field(name=cog_name, value="\n".join(command_list), inline=False)
        
        # Add footer
        embed.set_footer(text=f"Type !help [command] for more info | {len(self.bot.commands)} commands total")
        
        await ctx.send(embed=embed)
    
    async def _show_command_help(self, ctx, command_name):
        """Show help for a specific command"""
        command = self.bot.get_command(command_name)
        
        if not command:
            embed = Embed(
                title="Command Not Found",
                description=f"Command `{command_name}` not found.",
                color=Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Create command help embed
        embed = Embed(
            title=f"Help: {command.name}",
            description=command.help or "No description available.",
            color=Color.blue()
        )
        
        # Add usage
        usage = f"{ctx.prefix}{command.qualified_name} {command.signature}"
        embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
        
        # Add aliases if any
        if command.aliases:
            aliases = ", ".join([f"`{alias}`" for alias in command.aliases])
            embed.add_field(name="Aliases", value=aliases, inline=False)
        
        # Add cooldown if any
        if command._buckets._cooldown:
            cd = command._buckets._cooldown
            embed.add_field(
                name="Cooldown",
                value=f"`{cd.rate}` uses every `{cd.per:.0f}` seconds",
                inline=False
            )
        
        # Add subcommands if any
        if hasattr(command, "commands"):
            subcommands = ", ".join([f"`{c.name}`" for c in command.commands])
            if subcommands:
                embed.add_field(name="Subcommands", value=subcommands, inline=False)
                embed.set_footer(text=f"Type {ctx.prefix}help {command.name} [subcommand] for more info on a subcommand")
        
        await ctx.send(embed=embed)
    
    @command(name="serverinfo", help="Display information about the server")
    @guild_only()
    async def server_info(self, ctx):
        """
        Display information about the server.
        
        Usage: !serverinfo
        """
        guild = ctx.guild
        
        # Get member counts
        total_members = guild.member_count
        online_members = len([m for m in guild.members if m.status != dcl.Status.offline])
        
        # Get channel counts
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        # Get date info
        created_at = guild.created_at.strftime("%B %d, %Y")
        
        # Create embed
        embed = Embed(
            title=f"{guild.name} - Server Information",
            color=Color.blue()
        )
        
        # Add guild icon if available
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Add basic info
        embed.add_field(name="Owner", value=f"{guild.owner.mention} ({guild.owner.id})", inline=False)
        embed.add_field(name="Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="Created On", value=f"`{created_at}`", inline=True)
        
        # Add member stats
        embed.add_field(name="Members", value=f"`{total_members}` Total\n`{online_members}` Online", inline=True)
        
        # Add channel stats
        embed.add_field(name="Channels", value=f"`{text_channels}` Text\n`{voice_channels}` Voice\n`{categories}` Categories", inline=True)
        
        # Add roles
        roles = len(guild.roles) - 1  # Subtract @everyone role
        embed.add_field(name="Roles", value=f"`{roles}`", inline=True)
        
        # Add emojis
        emoji_count = len(guild.emojis)
        embed.add_field(name="Emojis", value=f"`{emoji_count}`", inline=True)
        
        # Add boost info
        boost_level = guild.premium_tier
        boosts = guild.premium_subscription_count
        embed.add_field(name="Boost Level", value=f"`{boost_level}` (Boosts: `{boosts}`)", inline=True)
        
        # Add footer
        embed.set_footer(text=f"Requested by {ctx.author}")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the basic commands cog to the bot"""
    await bot.add_cog(BasicCommands(bot))
    logger.info("Basic commands cog loaded")