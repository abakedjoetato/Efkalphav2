"""
Debug Cog
Contains debugging commands and utilities for the bot
"""

import discord
from discord.ext import commands
import logging
import platform
import os
import sys
import json
import asyncio

logger = logging.getLogger(__name__)

class Debug(commands.Cog):
    """Debug commands for bot maintenance and troubleshooting"""
    
    def __init__(self, bot):
        """Initialize the cog with a bot instance"""
        self.bot = bot
    
    @commands.command(name="system")
    @commands.is_owner()
    async def system(self, ctx):
        """Display system information (owner only)"""
        try:
            # Create an embed for the system info
            embed = discord.Embed(
                title="System Information",
                description="Detailed system information and diagnostics",
                color=discord.Color.blue()
            )
            
            # Add Python info
            embed.add_field(
                name="Python",
                value=f"Version: {platform.python_version()}\n"
                      f"Implementation: {platform.python_implementation()}\n"
                      f"Path: {sys.executable}",
                inline=False
            )
            
            # Add platform info
            embed.add_field(
                name="Platform",
                value=f"System: {platform.system()}\n"
                      f"Version: {platform.version()}\n"
                      f"Architecture: {platform.architecture()[0]}",
                inline=False
            )
            
            # Add process info
            pid = os.getpid()
            embed.add_field(
                name="Process",
                value=f"PID: {pid}\n"
                      f"Working Directory: {os.getcwd()}",
                inline=False
            )
            
            # Add bot info
            embed.add_field(
                name="Bot",
                value=f"Servers: {len(self.bot.guilds)}\n"
                      f"Users: {sum(g.member_count for g in self.bot.guilds)}\n"
                      f"Commands: {len(self.bot.commands)}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            logger.info(f"System command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in system command: {e}")
            await ctx.send(f"Error processing system command: {e}")
    
    @commands.command(name="debug")
    @commands.is_owner()
    async def debug(self, ctx, *, code=None):
        """Run a debug command or display debug information (owner only)"""
        try:
            if code:
                # Basic security check - only allow owner
                if ctx.author.id != self.bot.owner_id:
                    await ctx.send("Only the bot owner can execute debug code")
                    return
                
                # This is a very simple implementation and should be expanded
                # with proper security checks and sandboxing in a production bot
                result = eval(code)
                await ctx.send(f"Result: {result}")
            else:
                # Display general debug info
                embed = discord.Embed(
                    title="Debug Information",
                    description="Current bot state and diagnostics",
                    color=discord.Color.blue()
                )
                
                # Add bot status
                embed.add_field(
                    name="Status",
                    value=f"Latency: {round(self.bot.latency * 1000)}ms\n"
                          f"Ready: {self.bot.is_ready()}\n"
                          f"Connected Shards: {self.bot.shard_count or 1}",
                    inline=False
                )
                
                # Add cog info
                cog_list = list(self.bot.cogs.keys())
                embed.add_field(
                    name="Loaded Cogs",
                    value="\n".join(cog_list) if cog_list else "None",
                    inline=False
                )
                
                # Add environment info
                env_vars = {key: value for key, value in os.environ.items() 
                           if not key.startswith(('DISCORD_TOKEN', 'MONGODB_URI'))}
                safe_env = json.dumps(env_vars, indent=2)
                if len(safe_env) > 1000:
                    safe_env = safe_env[:997] + "..."
                
                embed.add_field(
                    name="Environment Variables",
                    value=f"```json\n{safe_env}\n```",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                logger.info(f"Debug command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in debug command: {e}")
            await ctx.send(f"Error processing debug command: {e}")
    
    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(self, ctx, *, cog=None):
        """Reload a cog or all cogs (owner only)"""
        try:
            if cog:
                # Reload a specific cog
                # Ensure it has the correct prefix
                if not cog.startswith("cogs."):
                    cog = f"cogs.{cog}"
                
                await self.bot.reload_extension(cog)
                await ctx.send(f"✅ Reloaded: {cog}")
                logger.info(f"Reloaded cog {cog}")
            else:
                # Reload all cogs
                message = await ctx.send("Reloading all cogs...")
                
                success = []
                failed = []
                
                for extension in list(self.bot.extensions):
                    try:
                        await self.bot.reload_extension(extension)
                        success.append(extension)
                    except Exception as e:
                        failed.append(f"{extension} - {e}")
                
                status = f"Reloaded {len(success)}/{len(success) + len(failed)} cogs"
                if failed:
                    status += f"\nFailed:\n" + "\n".join(failed)
                
                await message.edit(content=status)
                logger.info(f"Reloaded all cogs: {len(success)} successful, {len(failed)} failed")
        except Exception as e:
            logger.error(f"Error in reload command: {e}")
            await ctx.send(f"Error reloading cog: {e}")
    
    @commands.command(name="loadcog")
    @commands.is_owner()
    async def load_cog(self, ctx, *, cog):
        """Load a specific cog (owner only)"""
        try:
            # Ensure it has the correct prefix
            if not cog.startswith("cogs."):
                cog = f"cogs.{cog}"
            
            await self.bot.load_extension(cog)
            await ctx.send(f"✅ Loaded: {cog}")
            logger.info(f"Loaded cog {cog}")
        except Exception as e:
            logger.error(f"Error loading cog {cog}: {e}")
            await ctx.send(f"Error loading cog: {e}")
    
    @commands.command(name="unloadcog")
    @commands.is_owner()
    async def unload_cog(self, ctx, *, cog):
        """Unload a specific cog (owner only)"""
        try:
            # Ensure it has the correct prefix
            if not cog.startswith("cogs."):
                cog = f"cogs.{cog}"
            
            await self.bot.unload_extension(cog)
            await ctx.send(f"✅ Unloaded: {cog}")
            logger.info(f"Unloaded cog {cog}")
        except Exception as e:
            logger.error(f"Error unloading cog {cog}: {e}")
            await ctx.send(f"Error unloading cog: {e}")
    
    @commands.command(name="coglist")
    @commands.is_owner()
    async def cog_list(self, ctx):
        """List all loaded cogs (owner only)"""
        try:
            # Get loaded cogs
            loaded_cogs = list(self.bot.cogs.keys())
            
            # Get all available cogs in the cogs directory
            available_cogs = []
            for filename in os.listdir("cogs"):
                if filename.endswith(".py") and not filename.startswith("_"):
                    cog_name = filename[:-3]
                    available_cogs.append(cog_name)
            
            # Create an embed for the cog list
            embed = discord.Embed(
                title="Cog Status",
                description="List of loaded and available cogs",
                color=discord.Color.blue()
            )
            
            # Add loaded cogs
            embed.add_field(
                name="Loaded Cogs",
                value="\n".join(loaded_cogs) if loaded_cogs else "None",
                inline=True
            )
            
            # Add available but not loaded cogs
            unloaded_cogs = [c for c in available_cogs if c not in loaded_cogs]
            embed.add_field(
                name="Available Cogs (Not Loaded)",
                value="\n".join(unloaded_cogs) if unloaded_cogs else "None",
                inline=True
            )
            
            await ctx.send(embed=embed)
            logger.info(f"Cog list command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in cog list command: {e}")
            await ctx.send(f"Error listing cogs: {e}")

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(Debug(bot))