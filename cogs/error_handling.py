"""
Error Handling Cog

This cog provides global error handling for bot commands,
with detailed error reporting and recovery options.
"""

import os
import re
import sys
import logging
import traceback
from typing import Dict, List, Any, Optional, Union, Callable

# Import from compatibility layer
import discord_compat_layer as dcl
from discord_compat_layer import (
    Embed, Color, Colour, 
    Bot, Cog, Context,
    CommandError, CommandNotFound, MissingRequiredArgument, BadArgument
)

# Import error telemetry
from utils.error_telemetry import get_error_telemetry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("error_handler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ErrorHandler(Cog, name="Error Handler"):
    """
    Global error handler for bot commands.
    
    This cog handles various command errors and provides helpful
    feedback to users when commands fail.
    """
    
    def __init__(self, bot):
        """Initialize the error handler"""
        self.bot = bot
        self.error_count = 0
        self.telemetry = get_error_telemetry(bot)
        logger.info("Error handler initialized")
    
    @Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Handle command errors globally.
        
        This listener is triggered whenever a command raises an exception.
        It provides appropriate error messages and logs details for debugging.
        
        Args:
            ctx: Command context
            error: The exception raised
        """
        # Increment error counter
        self.error_count += 1
        
        # Get the command that was executed
        command = ctx.command.qualified_name if ctx.command else "Unknown command"
        
        # Create context dictionary for error logging
        context = {
            "user": ctx.author,
            "guild": ctx.guild,
            "channel": ctx.channel,
            "command": command,
            "message": ctx.message.content
        }
        
        # Ignore command not found errors
        if isinstance(error, CommandNotFound):
            return
        
        # Get original error if it's wrapped
        if hasattr(error, "original"):
            original = error.original
            error_class = original.__class__.__name__
            error_msg = str(original)
        else:
            original = error
            error_class = error.__class__.__name__
            error_msg = str(error)
        
        # Log the error
        logger.error(f"Command '{command}' raised error: {error_class}: {error_msg}")
        logger.error(f"User: {ctx.author} (ID: {ctx.author.id})")
        logger.error(f"Guild: {ctx.guild} (ID: {ctx.guild.id if ctx.guild else 'DM'})")
        logger.error(f"Channel: {ctx.channel} (ID: {ctx.channel.id})")
        logger.error(f"Message: {ctx.message.content}")
        
        # Log to telemetry
        self.telemetry.log_error(original or error, context, command)
        
        # Handle specific error types
        if isinstance(error, MissingRequiredArgument):
            await self._handle_missing_argument(ctx, error)
            return
            
        elif isinstance(error, BadArgument):
            await self._handle_bad_argument(ctx, error)
            return
        
        # For other errors, send a generic error message
        await self._handle_generic_error(ctx, error, command)
    
    async def _handle_missing_argument(self, ctx, error):
        """Handle missing argument errors"""
        embed = Embed(
            title="Missing Required Argument",
            description=f"The command `{ctx.command}` is missing a required argument: `{error.param.name}`",
            color=Color.gold()
        )
        embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
        embed.set_footer(text="See !help for command details")
        
        await ctx.send(embed=embed)
    
    async def _handle_bad_argument(self, ctx, error):
        """Handle bad argument errors"""
        embed = Embed(
            title="Invalid Argument",
            description=f"Invalid argument provided for the command `{ctx.command}`",
            color=Color.gold()
        )
        embed.add_field(name="Error", value=str(error))
        embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
        embed.set_footer(text="See !help for command details")
        
        await ctx.send(embed=embed)
    
    async def _handle_generic_error(self, ctx, error, command):
        """Handle generic errors"""
        # Create error embed
        embed = Embed(
            title="Command Error",
            description=f"An error occurred while executing the `{command}` command.",
            color=Color.red()
        )
        
        # Add error details
        error_type = error.__class__.__name__
        error_msg = str(error)
        
        # Clean up error message (remove sensitive info)
        error_msg = self._sanitize_error(error_msg)
        
        embed.add_field(name="Error Type", value=error_type)
        embed.add_field(name="Error Message", value=error_msg[:1024] or "Unknown error")
        embed.set_footer(text="This error has been logged")
        
        # Send error message
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")
            # Try to send a simple message if embed fails
            try:
                await ctx.send(f"An error occurred: {error_type}")
            except Exception:
                pass
    
    def _sanitize_error(self, error_msg):
        """Sanitize error message to remove sensitive information"""
        # Remove tokens, passwords, API keys, etc.
        patterns = [
            r'token=\S+',
            r'password=\S+',
            r'api_key=\S+',
            r'secret=\S+',
            r'Authorization: \S+',
            r'Bearer \S+',
            r'mongodb\+srv://\S+',
            r'mongodb://\S+',
            r'postgres://\S+',
            r'mysql://\S+',
            r'redis://\S+',
        ]
        
        sanitized = error_msg
        for pattern in patterns:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized)
        
        return sanitized
    
    @Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        """
        Handle non-command errors.
        
        This listener is triggered for any unhandled errors in event handlers.
        
        Args:
            event: The event that raised the exception
            args: Event arguments
            kwargs: Event keyword arguments
        """
        # Get error information
        error_type, error, tb = sys.exc_info()
        
        # Create context dictionary for error logging
        context = {
            "event": event,
            "args": str(args),
            "kwargs": str(kwargs)
        }
        
        # Log the error
        logger.error(f"Event '{event}' raised error: {error_type.__name__}: {error}")
        logger.error("".join(traceback.format_exception(error_type, error, tb)))
        
        # Log to telemetry
        if error:
            self.telemetry.log_error(error, context, f"Event: {event}")

async def setup(bot):
    """Add the error handler cog to the bot"""
    await bot.add_cog(ErrorHandler(bot))
    logger.info("Error handler cog loaded")