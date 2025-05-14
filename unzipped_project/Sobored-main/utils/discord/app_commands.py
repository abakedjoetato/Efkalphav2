"""
Implementation of discord.app_commands for compatibility

This module provides a set of classes and functions that mimic the
discord.app_commands module from py-cord 2.6.1.
"""

import inspect
import logging
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Union

logger = logging.getLogger(__name__)

# Slash command option types
class AppCommandOptionType(IntEnum):
    """Type of application command option"""
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10
    ATTACHMENT = 11

# Slash command contexts
class CommandInteraction:
    """
    Context for a slash command.
    
    Attributes:
        user: The user who triggered the command
        guild: The guild the command was triggered in
        channel: The channel the command was triggered in
    """
    
    def __init__(self, user=None, guild=None, channel=None):
        self.user = user
        self.guild = guild
        self.channel = channel
        self.response = CommandResponse(self)
        
    async def response_send(self, content=None, **kwargs):
        """Send a response to the interaction"""
        logger.info(f"[Slash] Responding to interaction: {content}")
        return self.response.send_message(content, **kwargs)

class CommandResponse:
    """
    Response to a slash command.
    
    Attributes:
        interaction: The interaction this response is for
    """
    
    def __init__(self, interaction):
        self.interaction = interaction
        self._responded = False
    
    async def send_message(self, content=None, **kwargs):
        """Send a response to the interaction"""
        self._responded = True
        logger.info(f"[Slash] Response sent: {content}")
        
        # Return a dummy message
        from utils.discord import Message, User
        return Message(
            id=0,
            content=content or "",
            author=User(0, "Bot", discriminator="0000", bot=True),
            channel=self.interaction.channel
        )
    
    def is_done(self):
        """Check if this interaction has been responded to"""
        return self._responded

# Slash command decorators
def command(*, name=None, description="No description provided", **kwargs):
    """Decorator to create a slash command"""
    def decorator(func):
        func.__slash_command__ = True
        func.__slash_command_name__ = name or func.__name__
        func.__slash_command_description__ = description
        func.__slash_command_options__ = kwargs.get('options', [])
        return func
    return decorator

def describe(**kwargs):
    """Decorator to describe slash command parameters"""
    def decorator(func):
        func.__slash_command_parameter_descriptions__ = kwargs
        return func
    return decorator

def choices(**kwargs):
    """Decorator to add choices to slash command parameters"""
    def decorator(func):
        func.__slash_command_parameter_choices__ = kwargs
        return func
    return decorator

def guild_only():
    """Decorator to restrict a slash command to guild channels only"""
    def decorator(func):
        func.__slash_command_guild_only__ = True
        return func
    return decorator

def check(predicate):
    """Decorator that adds a check to a slash command"""
    def decorator(func):
        if not hasattr(func, '__slash_command_checks__'):
            func.__slash_command_checks__ = []
        func.__slash_command_checks__.append(predicate)
        return func
    return decorator

# Slash command classes
class Choice:
    """
    A choice for a slash command option.
    
    Attributes:
        name: The name of the choice (displayed to users)
        value: The value of the choice (used in code)
    """
    def __init__(self, name: str, value: Union[str, int, float]):
        self.name = name
        self.value = value
        
    def __repr__(self):
        return f"<Choice name={self.name!r} value={self.value!r}>"

class SlashCommandGroup:
    """
    A group of slash commands.
    
    Attributes:
        name: The name of the group
        description: The description of the group
        commands: The commands in the group
    """
    
    def __init__(self, name, description="No description provided", guild_ids=None):
        self.name = name
        self.description = description
        self.guild_ids = guild_ids
        self.commands = {}
        
    def command(self, name=None, description="No description provided", **kwargs):
        """Create a subcommand for this group"""
        def decorator(func):
            cmd_name = name or func.__name__
            func.__slash_command__ = True
            func.__slash_command_name__ = cmd_name
            func.__slash_command_description__ = description
            func.__slash_command_options__ = kwargs.get('options', [])
            func.__slash_command_guild_ids__ = self.guild_ids
            self.commands[cmd_name] = func
            return func
        return decorator
    
    def __call__(self, *args, **kwargs):
        """Make the group callable as a decorator"""
        return self.command(*args, **kwargs)

class Transformer:
    """Base class for custom option transformers"""
    
    @classmethod
    async def transform(cls, interaction, value):
        """Transform a value from a command option"""
        return value

# Function to create a complete command tree for a bot
def setup_app_commands(bot):
    """Setup app_commands for a bot"""
    # Collect all slash commands from the bot and its cogs
    slash_commands = {}
    
    # Collect commands from the bot
    for cmd_name, cmd in bot.commands.items():
        if hasattr(cmd, '__slash_command__') and cmd.__slash_command__:
            slash_commands[cmd_name] = cmd
    
    # Collect commands from cogs
    for cog_name, cog in bot.cogs.items():
        for attr_name in dir(cog):
            attr = getattr(cog, attr_name)
            if hasattr(attr, '__slash_command__') and attr.__slash_command__:
                slash_commands[attr.__slash_command_name__] = attr
    
    logger.info(f"Registered {len(slash_commands)} slash commands")
    return slash_commands

# Ensure all necessary functions and classes are exported
__all__ = [
    'AppCommandOptionType',
    'CommandInteraction',
    'CommandResponse',
    'command',
    'describe',
    'choices',
    'guild_only',
    'check',
    'Choice',
    'SlashCommandGroup',
    'Transformer',
    'setup_app_commands'
]