"""
Command Tree Module

This module provides a compatibility layer for Discord command trees,
ensuring consistent behavior across different versions of discord.py and py-cord.
"""

import logging
import inspect
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable, TypeVar, Generic

# Setup logger
logger = logging.getLogger("utils.command_tree")

# Import our compatibility check function
from utils.command_imports import is_compatible_with_pycord_261

def create_command_tree(bot):
    """
    Create a command tree for the bot with the appropriate API
    
    Args:
        bot: The Discord bot instance
        
    Returns:
        Any: Command tree object or None
    """
    try:
        # Get the app_commands module from discord
        from discord import app_commands
        
        # For py-cord 2.6.1+, use the built-in CommandTree
        if is_compatible_with_pycord_261():
            logger.info("Creating command tree with py-cord 2.6.1 API")
            return app_commands.CommandTree(bot)
        else:
            # Older discord.py compatibility
            logger.info("Creating command tree with older discord.py API")
            return app_commands.CommandTree(bot)
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to create command tree: {e}")
        return None

class SafeCommandTree:
    """
    Wrapper for CommandTree with error handling and compatibility
    """
    
    def __init__(self, bot):
        """
        Initialize the safe command tree
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self._tree = create_command_tree(bot)
        self.commands = []
        
    def command(self, *, name: Optional[str] = None, description: Optional[str] = None, **kwargs):
        """
        Decorator to create a command with error handling
        
        Args:
            name: Name of the command
            description: Description of the command
            **kwargs: Additional keyword arguments for the command
            
        Returns:
            Callable: Command decorator
        """
        def decorator(func):
            """
            Decorator to register the command
            
            Args:
                func: Command callback function
                
            Returns:
                Any: Command object
            """
            try:
                if self._tree is None:
                    logger.error(f"Command tree is None, cannot register command {name or func.__name__}")
                    return func
                
                # Get the final command name
                cmd_name = name or func.__name__
                
                # Create parameters for the command
                cmd_kwargs = {
                    "name": cmd_name
                }
                
                # Add description if provided
                if description is not None:
                    cmd_kwargs["description"] = description
                
                # Add any additional kwargs
                cmd_kwargs.update(kwargs)
                
                # Register the command
                cmd = self._tree.command(**cmd_kwargs)(func)
                
                # Store the command for later reference
                self.commands.append(cmd)
                
                return cmd
            except Exception as e:
                logger.error(f"Failed to register command {name or func.__name__}: {e}")
                return func
                
        return decorator
    
    async def sync(self, guild=None):
        """
        Sync commands to Discord
        
        Args:
            guild: Optional guild to sync to
            
        Returns:
            List: List of commands
        """
        try:
            if self._tree is None:
                logger.error("Command tree is None, cannot sync commands")
                return []
                
            # Sync the commands
            if guild is not None:
                return await self._tree.sync(guild=guild)
            else:
                return await self._tree.sync()
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
            return []