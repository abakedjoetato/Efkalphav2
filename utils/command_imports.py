"""
Command Imports Module

This module provides compatibility functions for working with Discord commands
across different versions of discord.py and py-cord libraries.
"""

import logging
import sys
from typing import Any, Dict, List, Optional, Union, Callable

logger = logging.getLogger("utils.command_imports")

def is_compatible_with_pycord_261() -> bool:
    """
    Check if the current discord library is compatible with py-cord 2.6.1
    
    Returns:
        bool: True if compatible with py-cord 2.6.1, False otherwise
    """
    try:
        # Check if this is py-cord by trying to import a py-cord specific attribute
        import discord
        version = getattr(discord, "__version__", "0.0.0")
        
        # Parse the version string
        try:
            major, minor, patch = map(int, version.split('.'))
            return major == 2 and minor >= 6
        except (ValueError, AttributeError):
            return False
    except ImportError:
        return False

def get_app_commands():
    """
    Get the appropriate app_commands module based on the available libraries
    
    Returns:
        module: The app_commands module
    """
    try:
        # Try to import from discord.app_commands (py-cord 2.0+)
        from discord import app_commands
        return app_commands
    except (ImportError, AttributeError):
        try:
            # Fallback to discord.ext.commands (older discord.py)
            from discord.ext import commands
            return commands
        except ImportError:
            # Last resort fallback
            logger.error("Could not import app_commands or commands - bot will have limited functionality")
            return None

def get_command_decorators():
    """
    Get the appropriate command decorators based on the available libraries
    
    Returns:
        dict: Dictionary of command decorators
    """
    decorators = {}
    
    # Get the app_commands module
    app_commands = get_app_commands()
    
    if app_commands:
        # Store the decorators
        decorators["command"] = getattr(app_commands, "command", None)
        decorators["describe"] = getattr(app_commands, "describe", None)
        decorators["guild_only"] = getattr(app_commands, "guild_only", None)
        decorators["default_permissions"] = getattr(app_commands, "default_permissions", None)
    
    return decorators

def create_command(name: str, description: str, callback: Callable, **kwargs) -> Any:
    """
    Create a command with the appropriate API based on the available libraries
    
    Args:
        name: Name of the command
        description: Description of the command
        callback: Command callback function
        **kwargs: Additional keyword arguments for the command
        
    Returns:
        Any: Command object
    """
    app_commands = get_app_commands()
    
    if not app_commands:
        return None
    
    # Create the command
    try:
        # Try py-cord 2.0+ app_commands API
        command = app_commands.command(name=name, description=description, **kwargs)(callback)
    except (AttributeError, TypeError) as e:
        try:
            # Fallback to simpler API
            command = app_commands.command(name=name)(callback)
        except Exception as e:
            logger.error(f"Failed to create command {name}: {e}")
            return None
            
    return command