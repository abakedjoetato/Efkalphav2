"""
Discord Compatibility Layer

This module provides compatibility between our custom 'discord' directory 
and the installed 'discord' package (py-cord).

It imports all commonly used Discord classes and functions so they can be 
imported by other modules in a unified way, regardless of where
the actual implementation is.
"""

import sys
import os
import logging
import importlib
from typing import Union, Optional, Any, Dict, List, Callable, Tuple, Type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("discord_compat_layer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Store real discord module
_real_discord = None
_real_commands = None

def get_real_discord():
    """
    Get the real discord module (the installed py-cord package)
    
    Returns:
        module: The discord module from py-cord
    """
    global _real_discord
    
    if _real_discord is None:
        # Save current sys.modules state
        old_modules = dict(sys.modules)
        
        # If a custom 'discord' module is in sys.modules, temporarily remove it
        custom_discord = sys.modules.get('discord')
        if custom_discord:
            del sys.modules['discord']
        
        # Import the real discord module
        try:
            import discord as real_discord
            _real_discord = real_discord
            logger.info(f"Successfully imported real discord module (version: {_real_discord.__version__})")
        except ImportError as e:
            logger.error(f"Failed to import real discord module: {e}")
            raise
        finally:
            # Restore the previous state of sys.modules
            if custom_discord:
                sys.modules['discord'] = custom_discord
    
    return _real_discord

def get_real_commands():
    """
    Get the real discord.commands module from py-cord
    
    Returns:
        module: The discord.commands module from py-cord
    """
    global _real_commands
    
    if _real_commands is None:
        discord = get_real_discord()
        _real_commands = discord.commands
        logger.info("Successfully imported real discord.commands module")
    
    return _real_commands

# Import the real discord module
discord = get_real_discord()
commands = get_real_commands()

# Re-export common discord classes and functions
# Basic Discord components
Client = discord.Client
Intents = discord.Intents
Interaction = discord.Interaction
Webhook = discord.Webhook
Embed = discord.Embed
Color = discord.Color 
Colour = discord.Colour
ChannelType = discord.ChannelType
Member = discord.Member
User = discord.User
Guild = discord.Guild
Message = discord.Message
TextChannel = discord.TextChannel
VoiceChannel = discord.VoiceChannel
CategoryChannel = discord.CategoryChannel
Thread = discord.Thread
Role = discord.Role
Emoji = discord.Emoji
Activity = discord.Activity
ActivityType = discord.ActivityType
Reaction = discord.Reaction
File = discord.File
ButtonStyle = discord.ButtonStyle
Permissions = discord.Permissions

# Command-related components
Bot = commands.Bot
Cog = commands.Cog
Context = commands.Context
command = commands.command
group = commands.group
has_permissions = commands.has_permissions
guild_only = commands.guild_only
is_owner = commands.is_owner
cooldown = commands.cooldown
CommandError = commands.CommandError
CommandNotFound = commands.CommandNotFound
MissingRequiredArgument = commands.MissingRequiredArgument
BadArgument = commands.BadArgument

# Enums and status
Status = discord.Status
utils = discord.utils

# Errors
DiscordException = discord.DiscordException
LoginFailure = discord.LoginFailure
HTTPException = discord.HTTPException
Forbidden = discord.Forbidden
NotFound = discord.NotFound

# Discord UI elements
ui = discord.ui
View = discord.ui.View
Button = discord.ui.Button
Select = discord.ui.Select

# Application command elements
app_commands = discord.app_commands
SlashCommandGroup = discord.app_commands.Group

# Export constants
__version__ = discord.__version__

def create_intents():
    """Create default intents for the bot with commonly needed permissions"""
    intents = Intents.default()
    intents.members = True
    intents.message_content = True
    intents.presences = True
    return intents

def safe_send(ctx_or_channel, content=None, *, embed=None, file=None, files=None, view=None, **kwargs):
    """
    Safely send a message, handling common errors
    
    Args:
        ctx_or_channel: Context or Channel to send message to
        content: Message content
        embed: Embed to send
        file: File to send
        files: List of files to send
        view: View to attach to message
        **kwargs: Additional arguments to pass to send
        
    Returns:
        Message: The sent message, or None if sending failed
    """
    try:
        send_method = getattr(ctx_or_channel, "send", None)
        if send_method is None:
            logger.error(f"Object {ctx_or_channel} has no 'send' method")
            return None
            
        return send_method(content=content, embed=embed, file=file, files=files, view=view, **kwargs)
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        return None