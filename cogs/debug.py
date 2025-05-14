"""
Debug Commands Cog

Provides debugging and diagnostic commands for the bot.
"""

import os
import sys
import time
import json
import platform
import asyncio
import traceback
import datetime
from typing import Optional

import discord
from discord.ext import commands

class DebugCog(commands.Cog, name="Debug"):
    """
    Debug commands for bot diagnostics and troubleshooting.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.hidden = True  # Hide commands from help
    
    @commands.command(name="debug", hidden=True)
    @commands.is_owner()
    async def debug_info(self, ctx):
        """
        Display debugging information (Bot owner only).
        
        Usage: !debug
        """
        # Collect system info
        system_info = {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "discord.py": discord.__version__,
            "asyncio": asyncio.__version__ if hasattr(asyncio, "__version__") else "Unknown"
        }
        
        # Collect bot info
        bot_info = {
            "uptime": str(datetime.datetime.now() - self.bot.start_time) if hasattr(self.bot, "start_time") else "Unknown",
            "servers": len(self.bot.guilds),
            "users": sum(guild.member_count for guild in self.bot.guilds),
            "commands": len(self.bot.commands),
        }
        
        # Create embed
        embed = discord.Embed(
            title="Debug Information",
            description="Detailed bot diagnostics",
            color=discord.Color.blue()
        )
        
        # Add system info
        embed.add_field(
            name="System",
            value="\n".join(f"**{k}:** {v}" for k, v in system_info.items()),
            inline=False
        )
        
        # Add bot info
        embed.add_field(
            name="Bot",
            value="\n".join(f"**{k}:** {v}" for k, v in bot_info.items()),
            inline=False
        )
        
        # Send the embed
        await ctx.send(embed=embed)
    
    @commands.command(name="reload", hidden=True)
    @commands.is_owner()
    async def reload_cog(self, ctx, cog_name: str):
        """
        Reload a specific cog (Bot owner only).
        
        Usage: !reload <cog_name>
        Example: !reload basic_commands
        """
        try:
            # Check if 'cogs.' prefix is already provided
            if not cog_name.startswith('cogs.'):
                cog_name = f'cogs.{cog_name}'
                
            # Reload the cog
            await self.bot.reload_extension(cog_name)
            
            # Success message
            embed = discord.Embed(
                title="Cog Reloaded",
                description=f"✅ Successfully reloaded `{cog_name}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            # Error message
            embed = discord.Embed(
                title="Reload Failed",
                description=f"❌ Failed to reload `{cog_name}`\n```py\n{str(e)}\n```",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="reloadall", hidden=True)
    @commands.is_owner()
    async def reload_all_cogs(self, ctx):
        """
        Reload all cogs (Bot owner only).
        
        Usage: !reloadall
        """
        # Status message
        status_msg = await ctx.send("Reloading all cogs...")
        
        # Get list of loaded cogs
        cogs = [extension for extension in self.bot.extensions.keys() if extension.startswith('cogs.')]
        
        # Results tracking
        successful = []
        failed = {}
        
        # Reload each cog
        for cog in cogs:
            try:
                await self.bot.reload_extension(cog)
                successful.append(cog)
            except Exception as e:
                failed[cog] = str(e)
        
        # Create result embed
        embed = discord.Embed(
            title="Reload Results",
            description=f"✅ **{len(successful)}/{len(cogs)}** cogs reloaded successfully",
            color=discord.Color.orange()
        )
        
        # Add successful reloads if any
        if successful:
            embed.add_field(
                name="✅ Successful",
                value="\n".join(f"`{cog}`" for cog in successful),
                inline=False
            )
        
        # Add failed reloads if any
        if failed:
            embed.add_field(
                name="❌ Failed",
                value="\n".join(f"`{cog}`: {error}" for cog, error in failed.items()),
                inline=False
            )
        
        # Send results
        await status_msg.edit(content=None, embed=embed)
    
    @commands.command(name="listcogs", hidden=True)
    @commands.is_owner()
    async def list_cogs(self, ctx):
        """
        List all loaded cogs (Bot owner only).
        
        Usage: !listcogs
        """
        # Get loaded cogs
        loaded_cogs = [extension for extension in self.bot.extensions.keys()]
        
        # Create embed
        embed = discord.Embed(
            title="Loaded Cogs",
            description=f"**{len(loaded_cogs)}** cogs currently loaded",
            color=discord.Color.blue()
        )
        
        # Add cogs to embed
        if loaded_cogs:
            embed.add_field(
                name="Cogs",
                value="\n".join(f"`{cog}`" for cog in loaded_cogs),
                inline=False
            )
        else:
            embed.add_field(
                name="Cogs",
                value="No cogs loaded",
                inline=False
            )
        
        # Send embed
        await ctx.send(embed=embed)
    
    @commands.command(name="eval", hidden=True)
    @commands.is_owner()
    async def eval_code(self, ctx, *, code: str):
        """
        Evaluate Python code (Bot owner only).
        
        Usage: !eval <code>
        Example: !eval print("Hello, world!")
        """
        # Remove code block formatting if present
        if code.startswith("```") and code.endswith("```"):
            code = "\n".join(code.split("\n")[1:-1])
        
        # Add return for expressions
        code = f"async def _eval_expr():\n{textwrap.indent(code, '    ')}\n\nreturn await _eval_expr()"
        
        # Execute code
        try:
            # Create environment
            env = {
                'bot': self.bot,
                'ctx': ctx,
                'discord': discord,
                'commands': commands,
                'channel': ctx.channel,
                'author': ctx.author,
                'guild': ctx.guild,
                'message': ctx.message
            }
            env.update(globals())
            
            # Execute code
            exec_result = exec(code, env)
            result = await eval(f"_eval_expr()", env)
            
            # Format result
            if result is not None:
                result_str = str(result)
                
                # Truncate if too long
                if len(result_str) > 1900:
                    result_str = result_str[:1900] + "..."
                
                # Send result
                await ctx.send(f"```py\n{result_str}\n```")
            else:
                await ctx.send("✅ Code executed successfully (no output)")
        
        except Exception as e:
            # Format error
            error_str = traceback.format_exc()
            
            # Truncate if too long
            if len(error_str) > 1900:
                error_str = error_str[:1900] + "..."
            
            # Send error
            await ctx.send(f"❌ Error:\n```py\n{error_str}\n```")
    
    @commands.command(name="clearcache", hidden=True)
    @commands.is_owner()
    async def clear_cache(self, ctx):
        """
        Clear bot's internal caches (Bot owner only).
        
        Usage: !clearcache
        """
        # Status message
        status_msg = await ctx.send("Clearing caches...")
        
        try:
            # Clear cache attributes if they exist
            if hasattr(self.bot, '_connection'):
                if hasattr(self.bot._connection, '_emoji_references'):
                    self.bot._connection._emoji_references.clear()
                
                if hasattr(self.bot._connection, '_voice_clients'):
                    for vc in self.bot._connection._voice_clients:
                        try:
                            await vc.disconnect(force=True)
                        except:
                            pass
                    self.bot._connection._voice_clients.clear()
            
            # Send success message
            embed = discord.Embed(
                title="Cache Cleared",
                description="✅ Internal caches have been cleared",
                color=discord.Color.green()
            )
            await status_msg.edit(content=None, embed=embed)
        except Exception as e:
            # Send error message
            embed = discord.Embed(
                title="Error",
                description=f"❌ Failed to clear caches:\n```py\n{str(e)}\n```",
                color=discord.Color.red()
            )
            await status_msg.edit(content=None, embed=embed)
    
    @commands.command(name="permcheck", hidden=True)
    @commands.has_permissions(administrator=True)
    async def check_permissions(self, ctx, channel: Optional[discord.TextChannel] = None):
        """
        Check bot permissions in a channel (Admin only).
        
        Usage: !permcheck [channel]
        Example: !permcheck #general
        """
        # Use provided channel or current channel
        channel = channel or ctx.channel
        
        # Get bot member
        bot_member = channel.guild.get_member(self.bot.user.id)
        
        # Get permissions
        perms = channel.permissions_for(bot_member)
        
        # Create embed
        embed = discord.Embed(
            title=f"Bot Permissions in #{channel.name}",
            description="List of permissions in this channel",
            color=discord.Color.blue()
        )
        
        # Add permissions to embed
        for perm, value in perms:
            emoji = "✅" if value else "❌"
            embed.add_field(
                name=f"{emoji} {perm}",
                value=str(value),
                inline=True
            )
        
        # Send embed
        await ctx.send(embed=embed)
    
    @commands.command(name="botstat", hidden=True)
    @commands.has_permissions(administrator=True)
    async def bot_stats(self, ctx):
        """
        Show detailed bot statistics (Admin only).
        
        Usage: !botstat
        """
        # Collect basic stats
        uptime = datetime.datetime.now() - self.bot.start_time if hasattr(self.bot, "start_time") else datetime.timedelta(seconds=0)
        
        # Memory usage
        import psutil
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # Convert to MB
        
        # Create embed
        embed = discord.Embed(
            title="Bot Statistics",
            description="Detailed bot performance statistics",
            color=discord.Color.blue()
        )
        
        # Add statistics
        embed.add_field(name="Uptime", value=str(uptime), inline=True)
        embed.add_field(name="Memory Usage", value=f"{memory_usage:.2f} MB", inline=True)
        embed.add_field(name="Python Version", value=platform.python_version(), inline=True)
        embed.add_field(name="Discord.py Version", value=discord.__version__, inline=True)
        embed.add_field(name="Server Count", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="User Count", value=str(sum(guild.member_count for guild in self.bot.guilds)), inline=True)
        embed.add_field(name="Command Count", value=str(len(self.bot.commands)), inline=True)
        
        # Get cog counts
        cog_count = len(self.bot.cogs)
        extension_count = len(self.bot.extensions)
        
        embed.add_field(name="Cog Count", value=str(cog_count), inline=True)
        embed.add_field(name="Extension Count", value=str(extension_count), inline=True)
        
        # Send embed
        await ctx.send(embed=embed)

# Required imports for eval command
import textwrap
import io

async def setup(bot):
    """Add the debug cog to the bot"""
    await bot.add_cog(DebugCog(bot))