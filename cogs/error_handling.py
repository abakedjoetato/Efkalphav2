"""
Error Handling Cog
Handles errors for all commands and provides user-friendly error messages
"""

import discord
from discord.ext import commands
import traceback
import logging
import sys
import io
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorHandling(commands.Cog):
    """Error handling for command failures and exceptions"""
    
    def __init__(self, bot):
        """Initialize the cog with a bot instance"""
        self.bot = bot
        self.error_log_channel_id = None  # Set this to a channel ID to log errors there
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        # If command has local error handler, return
        if hasattr(ctx.command, 'on_error'):
            return
        
        # If cog has error handler, return
        if ctx.cog and ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
            return
        
        # Get the original error
        error = getattr(error, 'original', error)
        
        # Log the error
        logger.error(f"Command '{ctx.command}' raised an error: {error}")
        logger.error(f"Command invoked by {ctx.author} in {ctx.guild}/{ctx.channel}")
        error_traceback = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        logger.error(error_traceback)
        
        # Handle specific errors with user-friendly messages
        if isinstance(error, commands.CommandNotFound):
            await self.handle_command_not_found(ctx, error)
        elif isinstance(error, commands.DisabledCommand):
            await self.handle_disabled_command(ctx, error)
        elif isinstance(error, commands.NoPrivateMessage):
            await self.handle_no_private_message(ctx, error)
        elif isinstance(error, commands.MissingRequiredArgument):
            await self.handle_missing_argument(ctx, error)
        elif isinstance(error, commands.BadArgument):
            await self.handle_bad_argument(ctx, error)
        elif isinstance(error, commands.MissingPermissions):
            await self.handle_missing_permissions(ctx, error)
        elif isinstance(error, commands.BotMissingPermissions):
            await self.handle_bot_missing_permissions(ctx, error)
        elif isinstance(error, commands.CommandOnCooldown):
            await self.handle_cooldown(ctx, error)
        elif isinstance(error, commands.NotOwner):
            await self.handle_not_owner(ctx, error)
        else:
            # General error handling
            await self.handle_generic_error(ctx, error)
        
        # Log to error channel if set
        await self.log_to_error_channel(ctx, error)
    
    async def handle_command_not_found(self, ctx, error):
        """Handle CommandNotFound error"""
        embed = discord.Embed(
            title="Command Not Found",
            description=f"The command `{ctx.message.content.split()[0]}` was not found.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Need Help?",
            value=f"Use `{ctx.prefix}help` to see a list of available commands.",
            inline=False
        )
        await ctx.send(embed=embed)
    
    async def handle_disabled_command(self, ctx, error):
        """Handle DisabledCommand error"""
        embed = discord.Embed(
            title="Command Disabled",
            description=f"The command `{ctx.command}` is currently disabled.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    async def handle_no_private_message(self, ctx, error):
        """Handle NoPrivateMessage error"""
        embed = discord.Embed(
            title="Server Only Command",
            description=f"The command `{ctx.command}` can only be used in servers, not in DMs.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    async def handle_missing_argument(self, ctx, error):
        """Handle MissingRequiredArgument error"""
        param = error.param.name
        embed = discord.Embed(
            title="Missing Argument",
            description=f"The command `{ctx.command}` is missing the required argument: `{param}`.",
            color=discord.Color.gold()
        )
        
        # Add command usage
        usage = f"{ctx.prefix}{ctx.command.name}"
        if ctx.command.signature:
            usage += f" {ctx.command.signature}"
            
        embed.add_field(
            name="Usage",
            value=f"`{usage}`",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def handle_bad_argument(self, ctx, error):
        """Handle BadArgument error"""
        embed = discord.Embed(
            title="Invalid Argument",
            description=f"You provided an invalid argument for the command `{ctx.command}`.",
            color=discord.Color.gold()
        )
        
        # Add error details
        embed.add_field(
            name="Error",
            value=str(error),
            inline=False
        )
        
        # Add command usage
        usage = f"{ctx.prefix}{ctx.command.name}"
        if ctx.command.signature:
            usage += f" {ctx.command.signature}"
            
        embed.add_field(
            name="Usage",
            value=f"`{usage}`",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def handle_missing_permissions(self, ctx, error):
        """Handle MissingPermissions error"""
        # Format the missing permissions
        missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
        missing_perms_str = ", ".join(missing_perms)
        
        embed = discord.Embed(
            title="Missing Permissions",
            description=f"You need the following permissions to use the command `{ctx.command}`: {missing_perms_str}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    async def handle_bot_missing_permissions(self, ctx, error):
        """Handle BotMissingPermissions error"""
        # Format the missing permissions
        missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
        missing_perms_str = ", ".join(missing_perms)
        
        embed = discord.Embed(
            title="Bot Missing Permissions",
            description=f"I need the following permissions to run the command `{ctx.command}`: {missing_perms_str}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    async def handle_cooldown(self, ctx, error):
        """Handle CommandOnCooldown error"""
        embed = discord.Embed(
            title="Command on Cooldown",
            description=f"The command `{ctx.command}` is on cooldown.",
            color=discord.Color.gold()
        )
        
        # Calculate remaining time
        seconds = int(error.retry_after)
        if seconds < 60:
            time_str = f"{seconds} second{'s' if seconds != 1 else ''}"
        else:
            minutes = seconds // 60
            seconds = seconds % 60
            time_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
            if seconds:
                time_str += f" and {seconds} second{'s' if seconds != 1 else ''}"
        
        embed.add_field(
            name="Try Again",
            value=f"You can use this command again in {time_str}.",
            inline=False
        )
        await ctx.send(embed=embed)
    
    async def handle_not_owner(self, ctx, error):
        """Handle NotOwner error"""
        embed = discord.Embed(
            title="Owner Command",
            description=f"The command `{ctx.command}` can only be used by the bot owner.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    async def handle_generic_error(self, ctx, error):
        """Handle any generic error"""
        embed = discord.Embed(
            title="Command Error",
            description=f"An error occurred while running the command `{ctx.command}`.",
            color=discord.Color.red()
        )
        
        # Add brief error message
        embed.add_field(
            name="Error",
            value=str(error)[:1024] if str(error) else "Unknown error",
            inline=False
        )
        
        # Add support info
        embed.add_field(
            name="Support",
            value="If this issue persists, please contact the bot owner.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def log_to_error_channel(self, ctx, error):
        """Log error to a designated error channel"""
        if not self.error_log_channel_id:
            return
        
        try:
            # Get the error channel
            error_channel = self.bot.get_channel(self.error_log_channel_id)
            if not error_channel:
                return
            
            # Create an error log embed
            embed = discord.Embed(
                title="Command Error Log",
                description=f"An error occurred in a command",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            # Add command info
            embed.add_field(
                name="Command",
                value=f"`{ctx.command}`" if ctx.command else "Unknown",
                inline=True
            )
            
            # Add user info
            embed.add_field(
                name="User",
                value=f"{ctx.author} ({ctx.author.id})",
                inline=True
            )
            
            # Add location info
            location = "DM"
            if ctx.guild:
                location = f"{ctx.guild.name} ({ctx.guild.id})\n#{ctx.channel.name} ({ctx.channel.id})"
                
            embed.add_field(
                name="Location",
                value=location,
                inline=True
            )
            
            # Add message content
            embed.add_field(
                name="Message",
                value=ctx.message.content[:1024],
                inline=False
            )
            
            # Add error type and message
            embed.add_field(
                name="Error Type",
                value=type(error).__name__,
                inline=True
            )
            
            embed.add_field(
                name="Error Message",
                value=str(error)[:1024] if str(error) else "No message",
                inline=False
            )
            
            # Add traceback as a file attachment if it's too long for an embed
            tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            if len(tb) > 1024:
                # Create a file with the traceback
                file = discord.File(
                    fp=io.BytesIO(tb.encode("utf-8")),
                    filename=f"error_{ctx.message.id}.txt"
                )
                await error_channel.send(embed=embed, file=file)
            else:
                embed.add_field(
                    name="Traceback",
                    value=f"```py\n{tb[:1024]}\n```",
                    inline=False
                )
                await error_channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error logging to error channel: {e}")

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(ErrorHandling(bot))