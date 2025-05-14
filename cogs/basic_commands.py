"""
Basic Commands Cog
Contains simple commands for testing and basic bot functionality
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BasicCommands(commands.Cog):
    """Basic commands for testing the bot and core functionality"""
    
    def __init__(self, bot):
        """Initialize the cog with a bot instance"""
        self.bot = bot
        self.start_time = datetime.now()
    
    @commands.command(name="ping")
    async def ping(self, ctx):
        """Simple command to check if the bot is responsive"""
        try:
            # Calculate bot latency
            latency = round(self.bot.latency * 1000)
            
            # Create an embed for the response
            embed = discord.Embed(
                title="🏓 Pong!",
                description=f"Bot latency: {latency}ms",
                color=discord.Color.green()
            )
            
            # Add bot uptime
            uptime = datetime.now() - self.start_time
            hours, remainder = divmod(int(uptime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {seconds}s"
            embed.add_field(name="Uptime", value=uptime_str, inline=False)
            
            # Add bot version info
            embed.add_field(name="Version", value="1.0.0", inline=True)
            
            # Add footer with timestamp
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", 
                            icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            embed.timestamp = datetime.now()
            
            await ctx.send(embed=embed)
            logger.info(f"Ping command executed by {ctx.author} with latency {latency}ms")
        except Exception as e:
            logger.error(f"Error in ping command: {e}")
            await ctx.send("Error processing ping command")
    
    @commands.command(name="info")
    async def info(self, ctx):
        """Display information about the bot"""
        try:
            # Create an embed for the bot info
            embed = discord.Embed(
                title="Bot Information",
                description="A sophisticated Discord bot with advanced modular architecture",
                color=discord.Color.blue()
            )
            
            # Add bot statistics
            guild_count = len(self.bot.guilds)
            member_count = sum(g.member_count for g in self.bot.guilds)
            
            embed.add_field(name="Servers", value=str(guild_count), inline=True)
            embed.add_field(name="Users", value=str(member_count), inline=True)
            embed.add_field(name="Commands", value=str(len(self.bot.commands)), inline=True)
            
            # Add system info
            embed.add_field(name="Library", value="py-cord 2.6.1", inline=True)
            embed.add_field(name="Database", value="MongoDB", inline=True)
            embed.add_field(name="Version", value="1.0.0", inline=True)
            
            # Add helpful links
            embed.add_field(name="Links", 
                          value="[Support Server](https://discord.gg/support) | " +
                                "[Documentation](https://docs.example.com) | " +
                                "[GitHub](https://github.com/example/bot)",
                          inline=False)
            
            # Add bot uptime
            uptime = datetime.now() - self.start_time
            days, remainder = divmod(int(uptime.total_seconds()), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
            embed.add_field(name="Uptime", value=uptime_str, inline=False)
            
            # Add footer with timestamp
            embed.set_footer(text=f"Requested by {ctx.author.display_name}", 
                            icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            embed.timestamp = datetime.now()
            
            await ctx.send(embed=embed)
            logger.info(f"Info command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in info command: {e}")
            await ctx.send("Error processing info command")
    
    @commands.command(name="help")
    async def custom_help(self, ctx, command=None):
        """Custom help command to list available commands"""
        try:
            if command:
                # Show help for a specific command
                cmd = self.bot.get_command(command)
                if cmd:
                    embed = discord.Embed(
                        title=f"Command: {cmd.name}",
                        description=cmd.help or "No description available",
                        color=discord.Color.blue()
                    )
                    
                    usage = f"{ctx.prefix}{cmd.name}"
                    if cmd.signature:
                        usage += f" {cmd.signature}"
                    
                    embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
                    
                    if cmd.aliases:
                        embed.add_field(name="Aliases", value=", ".join(cmd.aliases), inline=False)
                    
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"Command '{command}' not found")
            else:
                # Show list of commands grouped by cog
                embed = discord.Embed(
                    title="Help Command",
                    description=f"Use `{ctx.prefix}help <command>` for more info on a command",
                    color=discord.Color.blue()
                )
                
                # Group commands by cog
                cog_commands = {}
                for cmd in self.bot.commands:
                    if cmd.hidden:
                        continue
                    
                    cog_name = cmd.cog_name or "No Category"
                    if cog_name not in cog_commands:
                        cog_commands[cog_name] = []
                    
                    cog_commands[cog_name].append(cmd.name)
                
                # Add each cog's commands to the embed
                for cog_name, cmds in sorted(cog_commands.items()):
                    embed.add_field(
                        name=cog_name,
                        value=", ".join(f"`{cmd}`" for cmd in sorted(cmds)),
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                logger.info(f"Help command executed by {ctx.author}")
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await ctx.send("Error processing help command")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Event triggered when the bot is ready"""
        logger.info("BasicCommands cog is ready")
        self.start_time = datetime.now()

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(BasicCommands(bot))