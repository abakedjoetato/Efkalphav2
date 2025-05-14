"""
Admin Cog

This cog provides administrative commands for bot management.
"""

import logging
import discord
from discord.ext import commands
import os
import sys
import asyncio
import platform
import time
import datetime
import traceback
import psutil
from typing import Optional, Union, List

# Import permission utilities
from utils.permissions import is_owner, is_admin, is_mod_or_higher

# Configure logger
logger = logging.getLogger("cogs.admin")

class Admin(commands.Cog):
    """
    Administrative commands
    
    This cog provides commands for bot administration and monitoring.
    """
    
    def __init__(self, bot):
        """
        Initialize the cog
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.start_time = datetime.datetime.now()
        
    @commands.group(name="admin", invoke_without_command=True)
    @is_admin()
    async def admin_group(self, ctx):
        """
        Admin commands
        
        This command group provides access to administrative commands.
        Use a subcommand to perform specific administrative actions.
        """
        if ctx.invoked_subcommand is None:
            # Show help for the group
            await ctx.send_help(ctx.command)
            
    @admin_group.command(name="status")
    @is_admin()
    async def status(self, ctx):
        """
        View bot status
        
        This command shows the current status and statistics of the bot.
        """
        # Calculate uptime
        uptime = datetime.datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        
        # Create status embed
        embed = discord.Embed(
            title="Bot Status",
            description="Current bot status and statistics",
            color=0x00a8ff
        )
        
        # Bot information
        embed.add_field(
            name="Bot Version",
            value="1.0.0",
            inline=True
        )
        
        # Library information
        try:
            from discord import __version__ as discord_version
        except ImportError:
            discord_version = "Unknown"
        
        embed.add_field(
            name="Library",
            value=f"py-cord {discord_version}",
            inline=True
        )
        
        # Python information
        embed.add_field(
            name="Python Version",
            value=platform.python_version(),
            inline=True
        )
        
        # Bot statistics
        total_guilds = len(self.bot.guilds)
        total_members = sum(guild.member_count for guild in self.bot.guilds)
        
        embed.add_field(
            name="Servers",
            value=str(total_guilds),
            inline=True
        )
        
        embed.add_field(
            name="Members",
            value=str(total_members),
            inline=True
        )
        
        embed.add_field(
            name="Commands",
            value=str(len(self.bot.commands)),
            inline=True
        )
        
        # System information
        embed.add_field(
            name="Uptime",
            value=uptime_str,
            inline=True
        )
        
        # Get CPU and memory usage
        try:
            process = psutil.Process(os.getpid())
            memory_usage = process.memory_info().rss / 1024 / 1024
            cpu_usage = process.cpu_percent(interval=0.1)
            
            embed.add_field(
                name="Memory Usage",
                value=f"{memory_usage:.2f} MB",
                inline=True
            )
            
            embed.add_field(
                name="CPU Usage",
                value=f"{cpu_usage:.2f}%",
                inline=True
            )
        except:
            pass
            
        # Add footer
        embed.set_footer(text=f"Requested by {ctx.author.name}")
        
        await ctx.send(embed=embed)
        
    @admin_group.command(name="guilds")
    @is_admin()
    async def list_guilds(self, ctx):
        """
        List all guilds
        
        This command lists all guilds the bot is in.
        """
        # Create pages of guild information
        guilds = self.bot.guilds
        pages = []
        
        # 10 guilds per page
        for i in range(0, len(guilds), 10):
            guild_chunk = guilds[i:i + 10]
            
            # Create embed for this page
            embed = discord.Embed(
                title="Guild List",
                description=f"Guilds {i + 1}-{i + len(guild_chunk)} of {len(guilds)}",
                color=0x00a8ff
            )
            
            # Add guild information
            for guild in guild_chunk:
                embed.add_field(
                    name=guild.name,
                    value=f"ID: {guild.id}\nMembers: {guild.member_count}\nOwner: {guild.owner}",
                    inline=False
                )
                
            pages.append(embed)
            
        # Send the first page
        if pages:
            message = await ctx.send(embed=pages[0])
            
            # Add reactions for navigation if there are multiple pages
            if len(pages) > 1:
                await message.add_reaction("◀️")
                await message.add_reaction("▶️")
                
                # Current page index
                current_page = 0
                
                # Check function for reactions
                def check(reaction, user):
                    return (user == ctx.author and
                            reaction.message.id == message.id and
                            str(reaction.emoji) in ["◀️", "▶️"])
                            
                # Navigation loop
                while True:
                    try:
                        # Wait for a reaction
                        reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                        
                        # Remove the user's reaction
                        await reaction.remove(user)
                        
                        # Navigate based on the reaction
                        if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                            current_page += 1
                        elif str(reaction.emoji) == "◀️" and current_page > 0:
                            current_page -= 1
                            
                        # Update the embed
                        await message.edit(embed=pages[current_page])
                    except asyncio.TimeoutError:
                        # Remove reactions on timeout
                        await message.clear_reactions()
                        break
        else:
            await ctx.send("No guilds found.")
            
    @admin_group.command(name="leave")
    @is_owner()
    async def leave_guild(self, ctx, guild_id: int):
        """
        Leave a guild
        
        This command makes the bot leave a guild.
        
        Args:
            guild_id: ID of the guild to leave
        """
        # Get the guild
        guild = self.bot.get_guild(guild_id)
        
        if guild:
            # Ask for confirmation
            confirm_message = await ctx.send(f"⚠️ Are you sure you want to leave {guild.name} ({guild_id})? Reply with 'yes' to confirm.")
            
            # Wait for confirmation
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
                
            try:
                # Wait for confirmation
                await self.bot.wait_for('message', check=check, timeout=30.0)
                
                # Leave the guild
                await guild.leave()
                await ctx.send(f"✅ Left guild: {guild.name} ({guild_id})")
            except asyncio.TimeoutError:
                # Timeout waiting for confirmation
                await confirm_message.edit(content="❌ Guild leave cancelled due to timeout")
        else:
            await ctx.send(f"❌ Guild with ID {guild_id} not found")
            
    @admin_group.command(name="load")
    @is_owner()
    async def load_cog(self, ctx, cog: str):
        """
        Load a cog
        
        This command loads a cog.
        
        Args:
            cog: Name of the cog to load
        """
        try:
            # Add 'cogs.' prefix if not already present
            if not cog.startswith("cogs."):
                cog = f"cogs.{cog}"
                
            # Load the cog
            self.bot.load_extension(cog)
            await ctx.send(f"✅ Loaded cog: {cog}")
        except Exception as e:
            await ctx.send(f"❌ Failed to load cog: {cog}\nError: {e}")
            
    @admin_group.command(name="unload")
    @is_owner()
    async def unload_cog(self, ctx, cog: str):
        """
        Unload a cog
        
        This command unloads a cog.
        
        Args:
            cog: Name of the cog to unload
        """
        try:
            # Add 'cogs.' prefix if not already present
            if not cog.startswith("cogs."):
                cog = f"cogs.{cog}"
                
            # Unload the cog
            self.bot.unload_extension(cog)
            await ctx.send(f"✅ Unloaded cog: {cog}")
        except Exception as e:
            await ctx.send(f"❌ Failed to unload cog: {cog}\nError: {e}")
            
    @admin_group.command(name="reload")
    @is_owner()
    async def reload_cog(self, ctx, cog: str):
        """
        Reload a cog
        
        This command reloads a cog.
        
        Args:
            cog: Name of the cog to reload
        """
        try:
            # Add 'cogs.' prefix if not already present
            if not cog.startswith("cogs."):
                cog = f"cogs.{cog}"
                
            # Reload the cog
            self.bot.reload_extension(cog)
            await ctx.send(f"✅ Reloaded cog: {cog}")
        except Exception as e:
            await ctx.send(f"❌ Failed to reload cog: {cog}\nError: {e}")
            
    @admin_group.command(name="logs")
    @is_owner()
    async def view_logs(self, ctx, lines: int = 20):
        """
        View bot logs
        
        This command shows the recent bot logs.
        
        Args:
            lines: Number of log lines to show (default: 20)
        """
        try:
            # Limit the number of lines
            if lines > 100:
                lines = 100
                
            # Get the log file
            log_file = "bot.log"
            
            # Read the last n lines
            with open(log_file, "r", encoding="utf-8") as f:
                log_content = f.readlines()
                
            # Get the last n lines
            log_lines = log_content[-lines:]
            
            # Format the log lines
            formatted_logs = "```\n"
            for line in log_lines:
                formatted_logs += line
                
            formatted_logs += "```"
            
            # Send the logs
            await ctx.send(f"Last {len(log_lines)} lines of logs:")
            
            # Split long logs into multiple messages
            if len(formatted_logs) > 2000:
                chunks = [formatted_logs[i:i + 1990] for i in range(0, len(formatted_logs), 1990)]
                for chunk in chunks:
                    await ctx.send(chunk)
            else:
                await ctx.send(formatted_logs)
        except Exception as e:
            await ctx.send(f"❌ Error viewing logs: {e}")
            
    @admin_group.command(name="restart")
    @is_owner()
    async def restart_bot(self, ctx):
        """
        Restart the bot
        
        This command restarts the bot. The bot should automatically
        restart if it's running in a proper environment.
        """
        # Ask for confirmation
        confirm_message = await ctx.send("⚠️ Are you sure you want to restart the bot? Reply with 'yes' to confirm.")
        
        # Wait for confirmation
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
            
        try:
            # Wait for confirmation
            await self.bot.wait_for('message', check=check, timeout=30.0)
            
            # Confirm restart
            await ctx.send("✅ Restarting bot...")
            
            # Close the bot
            await self.bot.close()
            
            # Exit with a success code (0) to trigger a restart
            sys.exit(0)
        except asyncio.TimeoutError:
            # Timeout waiting for confirmation
            await confirm_message.edit(content="❌ Restart cancelled due to timeout")
            
    @admin_group.command(name="shutdown")
    @is_owner()
    async def shutdown_bot(self, ctx):
        """
        Shut down the bot
        
        This command shuts down the bot. It will not automatically
        restart.
        """
        # Ask for confirmation
        confirm_message = await ctx.send("⚠️ Are you sure you want to shut down the bot? Reply with 'yes' to confirm.")
        
        # Wait for confirmation
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
            
        try:
            # Wait for confirmation
            await self.bot.wait_for('message', check=check, timeout=30.0)
            
            # Confirm shutdown
            await ctx.send("✅ Shutting down bot...")
            
            # Close the bot
            await self.bot.close()
            
            # Exit with a non-zero code to prevent restart
            sys.exit(1)
        except asyncio.TimeoutError:
            # Timeout waiting for confirmation
            await confirm_message.edit(content="❌ Shutdown cancelled due to timeout")
            
    @admin_group.command(name="eval")
    @is_owner()
    async def eval_code(self, ctx, *, code: str):
        """
        Evaluate Python code
        
        This command evaluates Python code and returns the result.
        
        Args:
            code: Python code to evaluate
        """
        # Ask for confirmation for safety
        confirm_message = await ctx.send("⚠️ Are you sure you want to evaluate this code? Reply with 'yes' to confirm.")
        
        # Wait for confirmation
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
            
        try:
            # Wait for confirmation
            await self.bot.wait_for('message', check=check, timeout=30.0)
            
            # Set up environment
            env = {
                'bot': self.bot,
                'ctx': ctx,
                'discord': discord,
                'commands': commands,
                'guild': ctx.guild,
                'channel': ctx.channel,
                'author': ctx.author
            }
            
            # Add all global variables
            env.update(globals())
            
            # Execute the code
            try:
                result = eval(code, env)
                
                # Handle coroutines
                if asyncio.iscoroutine(result):
                    result = await result
                    
                # Format the result
                result_str = f"```python\n{result}\n```"
                
                # Send the result
                await ctx.send(f"✅ Result:\n{result_str}")
            except Exception as e:
                # Send the error
                error_str = f"```python\n{traceback.format_exc()}\n```"
                await ctx.send(f"❌ Error:\n{error_str}")
        except asyncio.TimeoutError:
            # Timeout waiting for confirmation
            await confirm_message.edit(content="❌ Evaluation cancelled due to timeout")
            
    @admin_group.command(name="exec")
    @is_owner()
    async def exec_code(self, ctx, *, code: str):
        """
        Execute Python code
        
        This command executes Python code and returns the result.
        
        Args:
            code: Python code to execute
        """
        # Ask for confirmation for safety
        confirm_message = await ctx.send("⚠️ Are you sure you want to execute this code? Reply with 'yes' to confirm.")
        
        # Wait for confirmation
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
            
        try:
            # Wait for confirmation
            await self.bot.wait_for('message', check=check, timeout=30.0)
            
            # Set up environment
            env = {
                'bot': self.bot,
                'ctx': ctx,
                'discord': discord,
                'commands': commands,
                'guild': ctx.guild,
                'channel': ctx.channel,
                'author': ctx.author
            }
            
            # Add all global variables
            env.update(globals())
            
            # Create a function to capture stdout
            output = []
            
            # Redirect stdout
            def capture_stdout(string):
                output.append(string)
                
            # Override print
            def custom_print(*args, **kwargs):
                # Convert args to string
                string = " ".join(map(str, args))
                
                # Add to output
                output.append(string)
                
            # Store original print
            original_print = print
            
            # Replace print
            env['print'] = custom_print
            
            try:
                # Execute the code
                code = compile(code, '<exec>', 'exec')
                exec(code, env)
                
                # Format the output
                if output:
                    result_str = f"```\n{chr(10).join(output)}\n```"
                else:
                    result_str = "```\nNo output\n```"
                    
                # Send the result
                await ctx.send(f"✅ Output:\n{result_str}")
            except Exception as e:
                # Send the error
                error_str = f"```python\n{traceback.format_exc()}\n```"
                await ctx.send(f"❌ Error:\n{error_str}")
            finally:
                # Restore original print
                print = original_print
        except asyncio.TimeoutError:
            # Timeout waiting for confirmation
            await confirm_message.edit(content="❌ Execution cancelled due to timeout")
            
def setup(bot):
    """
    Set up the admin cog
    
    Args:
        bot: The Discord bot instance
    """
    # Try to install psutil if it's not available
    try:
        import psutil
    except ImportError:
        import subprocess
        import sys
        
        logger.info("Installing psutil for system monitoring...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        
        # Import again
        import psutil
        
    bot.add_cog(Admin(bot))
    logger.info("Admin cog loaded")