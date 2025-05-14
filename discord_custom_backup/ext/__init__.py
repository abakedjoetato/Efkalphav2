"""
Discord extensions package for compatibility with existing code.
"""

import sys
import logging
import types
import importlib

logger = logging.getLogger(__name__)
logger.info("Loading Discord ext module")

# Import or create the commands module and expose it in this namespace
try:
    # Make sure our local commands implementation is accessible
    import discord.ext.commands
    logger.info("Successfully imported discord.ext.commands")
    commands = discord.ext.commands
except ImportError:
    logger.info("Creating commands module in discord.ext")
    # Create a commands module if it doesn't exist
    try:
        # Get absolute path to the commands module
        commands_spec = importlib.util.find_spec("discord.ext.commands")
        if commands_spec is None:
            logger.info("Creating commands module from commands.py")
            # Import our own commands.py file
            commands = importlib.import_module(".commands", package="discord.ext")
            sys.modules["discord.ext.commands"] = commands
            logger.info("Commands module created and available")
        else:
            commands = importlib.import_module("discord.ext.commands")
            logger.info("Commands module imported from existing spec")
    except Exception as e:
        logger.error(f"Failed to set up commands module: {e}")
        # Create a fallback module
        commands = types.ModuleType("discord.ext.commands") 
        sys.modules["discord.ext.commands"] = commands

# Export only commands for now
__all__ = ["commands"]