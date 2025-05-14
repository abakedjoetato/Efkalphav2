"""
Error Handler Module

This module provides utilities for handling errors in a consistent way.
"""

import logging
import traceback
import asyncio
import discord
from discord.ext import commands
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable
import datetime
import uuid
import json
import os

# Configure logger
logger = logging.getLogger("utils.error_handler")

class ErrorManager:
    """
    Error manager for handling errors
    
    This class manages error handling and provides utilities for
    logging, reporting, and resolving errors.
    
    Attributes:
        bot: The Discord bot instance
        errors: Dictionary of error IDs to error information
        error_callbacks: Dictionary of error types to error handler functions
    """
    
    def __init__(self, bot, log_dir: str = "logs"):
        """
        Initialize the error manager
        
        Args:
            bot: The Discord bot instance
            log_dir: Directory for error logs
        """
        self.bot = bot
        self.errors: Dict[str, Dict[str, Any]] = {}
        self.error_callbacks: Dict[type, List[Callable]] = {}
        self.log_dir = log_dir
        
        # Create the log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
    def register_error_handler(self, error_type: type, handler: Callable) -> None:
        """
        Register an error handler
        
        Args:
            error_type: Type of error to handle
            handler: Handler function
        """
        if error_type not in self.error_callbacks:
            self.error_callbacks[error_type] = []
            
        self.error_callbacks[error_type].append(handler)
        logger.debug(f"Registered handler for error type: {error_type.__name__}")
        
    def unregister_error_handler(self, error_type: type, handler: Callable) -> bool:
        """
        Unregister an error handler
        
        Args:
            error_type: Type of error to handle
            handler: Handler function
            
        Returns:
            bool: True if the handler was unregistered, False otherwise
        """
        if error_type in self.error_callbacks and handler in self.error_callbacks[error_type]:
            self.error_callbacks[error_type].remove(handler)
            logger.debug(f"Unregistered handler for error type: {error_type.__name__}")
            return True
            
        return False
        
    async def handle_error(self, error: Exception, ctx = None, **kwargs) -> str:
        """
        Handle an error
        
        Args:
            error: The error to handle
            ctx: Optional command context
            **kwargs: Additional context information
            
        Returns:
            str: Error ID
        """
        # Generate a unique error ID
        error_id = str(uuid.uuid4())
        
        # Create an error entry
        error_info = {
            "id": error_id,
            "type": type(error).__name__,
            "message": str(error),
            "timestamp": datetime.datetime.now().isoformat(),
            "traceback": traceback.format_exc(),
            "context": kwargs
        }
        
        # Add command context if available
        if ctx:
            error_info["command"] = {
                "name": ctx.command.name if ctx.command else "Unknown",
                "channel": str(ctx.channel),
                "guild": str(ctx.guild) if ctx.guild else "DM",
                "author": str(ctx.author)
            }
            
        # Store the error
        self.errors[error_id] = error_info
        
        # Log the error
        logger.error(f"Error {error_id}: {type(error).__name__}: {error}")
        logger.debug(traceback.format_exc())
        
        # Write the error to a file
        try:
            error_file = os.path.join(self.log_dir, f"error_{error_id}.json")
            with open(error_file, "w") as f:
                json.dump(error_info, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write error log: {e}")
            
        # Call error handlers
        await self._call_error_handlers(error, ctx, error_id, **kwargs)
        
        return error_id
        
    async def _call_error_handlers(self, error: Exception, ctx, error_id: str, **kwargs) -> None:
        """
        Call error handlers for an error
        
        Args:
            error: The error to handle
            ctx: Command context
            error_id: Error ID
            **kwargs: Additional context information
        """
        # Get the error type
        error_type = type(error)
        
        # Try to find handlers for the error type or its parent types
        handled = False
        
        # Check for direct handler
        if error_type in self.error_callbacks:
            for handler in self.error_callbacks[error_type]:
                try:
                    await self._call_handler(handler, error, ctx, error_id, **kwargs)
                    handled = True
                except Exception as e:
                    logger.error(f"Error in error handler: {e}")
                    
        # Check for parent type handlers if not handled
        if not handled:
            for registered_type, handlers in self.error_callbacks.items():
                if issubclass(error_type, registered_type) and registered_type != error_type:
                    for handler in handlers:
                        try:
                            await self._call_handler(handler, error, ctx, error_id, **kwargs)
                            handled = True
                        except Exception as e:
                            logger.error(f"Error in error handler: {e}")
                            
        # If still not handled, use the default handler
        if not handled and ctx:
            await self._default_error_handler(error, ctx, error_id)
            
    async def _call_handler(self, handler: Callable, error: Exception, ctx, error_id: str, **kwargs) -> None:
        """
        Call an error handler
        
        Args:
            handler: Handler function
            error: The error to handle
            ctx: Command context
            error_id: Error ID
            **kwargs: Additional context information
        """
        # Check if the handler is a coroutine function
        if asyncio.iscoroutinefunction(handler):
            await handler(error, ctx, error_id, **kwargs)
        else:
            handler(error, ctx, error_id, **kwargs)
            
    async def _default_error_handler(self, error: Exception, ctx, error_id: str) -> None:
        """
        Default error handler
        
        Args:
            error: The error to handle
            ctx: Command context
            error_id: Error ID
        """
        if isinstance(error, commands.CommandNotFound):
            # Command not found
            await ctx.send("❌ Command not found.")
        elif isinstance(error, commands.MissingRequiredArgument):
            # Missing argument
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            # Bad argument
            await ctx.send(f"❌ Bad argument: {error}")
        elif isinstance(error, commands.MissingPermissions):
            # Missing permissions
            await ctx.send(f"❌ You don't have permission to use this command.")
        elif isinstance(error, commands.BotMissingPermissions):
            # Bot missing permissions
            await ctx.send(f"❌ I don't have permission to do that.")
        elif isinstance(error, commands.CommandOnCooldown):
            # Command on cooldown
            await ctx.send(f"❌ Command on cooldown. Try again in {error.retry_after:.1f} seconds.")
        elif isinstance(error, commands.CheckFailure):
            # Check failure
            await ctx.send(f"❌ You don't have permission to use this command.")
        else:
            # Other error
            await ctx.send(f"❌ An error occurred (ID: {error_id})")
            
    def create_error_embed(self, error: Exception, error_id: str) -> discord.Embed:
        """
        Create an error embed
        
        Args:
            error: The error
            error_id: Error ID
            
        Returns:
            discord.Embed: Error embed
        """
        embed = discord.Embed(
            title="Error",
            description=f"An error occurred: {type(error).__name__}",
            color=0xff0000
        )
        
        embed.add_field(
            name="Error Message",
            value=str(error),
            inline=False
        )
        
        embed.add_field(
            name="Error ID",
            value=error_id,
            inline=True
        )
        
        embed.add_field(
            name="Timestamp",
            value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            inline=True
        )
        
        return embed
        
    def get_error(self, error_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an error by ID
        
        Args:
            error_id: Error ID
            
        Returns:
            Optional[Dict[str, Any]]: Error information or None if not found
        """
        return self.errors.get(error_id)
        
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent errors
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List[Dict[str, Any]]: List of recent errors
        """
        # Sort errors by timestamp (newest first)
        return sorted(
            self.errors.values(),
            key=lambda e: e["timestamp"],
            reverse=True
        )[:limit]
        
        
# Decorator for error handlers
def error_handler(error_type: type):
    """
    Decorator for registering error handlers
    
    Args:
        error_type: Type of error to handle
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func):
        # Mark the function as an error handler
        func.__error_handler__ = True
        func.__error_type__ = error_type
        
        return func
        
    return decorator