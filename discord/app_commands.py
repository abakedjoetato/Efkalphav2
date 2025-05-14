"""
Discord app_commands compatibility module

This module provides compatibility with discord.app_commands.
"""

import logging
import inspect
import functools
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Union, Coroutine

logger = logging.getLogger(__name__)
logger.info("Loading Discord app_commands compatibility layer")

# Application context for interactions
class Interaction:
    """Represents an interaction with a Discord application command"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.application_id = kwargs.get('application_id', 0)
        self.type = kwargs.get('type', 0)
        self.guild_id = kwargs.get('guild_id', None)
        self.channel_id = kwargs.get('channel_id', None)
        self.user = kwargs.get('user', None)
        self.token = kwargs.get('token', '')
        self.data = kwargs.get('data', {})
        self.command = kwargs.get('command', None)
        self._responded = False
        self._deferred = False
        
    async def respond(self, content=None, **kwargs):
        """Respond to the interaction"""
        self._responded = True
        logger.info(f"[Mock] Responding to interaction: {content}")
        return None
        
    async def send_message(self, content=None, **kwargs):
        """Send a message in response to the interaction"""
        self._responded = True
        logger.info(f"[Mock] Sending message: {content}")
        return None
        
    async def defer(self, **kwargs):
        """Defer the response"""
        self._deferred = True
        logger.info("[Mock] Deferring interaction response")
        return None
        
    @property
    def response(self):
        """Get the response object"""
        return self  # For simplicity, we use self as the response

class ApplicationContext:
    """Context for application commands"""
    def __init__(self, bot=None, interaction=None):
        self.bot = bot
        self.interaction = interaction
        self.command = getattr(interaction, 'command', None)
        self.guild_id = getattr(interaction, 'guild_id', None)
        self.channel_id = getattr(interaction, 'channel_id', None)
        self.user = getattr(interaction, 'user', None)
        
    async def respond(self, content=None, **kwargs):
        """Respond to the interaction"""
        if self.interaction:
            return await self.interaction.respond(content, **kwargs)
        logger.warning("No interaction to respond to")
        return None
        
    async def send(self, content=None, **kwargs):
        """Send a message"""
        if self.interaction:
            return await self.interaction.send_message(content, **kwargs)
        logger.warning("No interaction to send message with")
        return None
        
    async def defer(self, **kwargs):
        """Defer the response"""
        if self.interaction:
            return await self.interaction.defer(**kwargs)
        logger.warning("No interaction to defer")
        return None

# Slash command option types
class AppCommandOptionType(IntEnum):
    """Application Command Option Types"""
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10  # equivalent to float
    ATTACHMENT = 11

# For command options
class Choice:
    """Represents a choice for a slash command option"""
    def __init__(self, name: str, value: Union[str, int, float]):
        self.name = name
        self.value = value

# Command classes
class Command:
    """Represents a slash command"""
    def __init__(self, callback, name: str = None, description: str = None, **kwargs):
        self.callback = callback
        self.name = name or callback.__name__
        self.description = description or callback.__doc__ or "No description"
        self.guild_only = kwargs.get('guild_only', False)
        self.default_permissions = kwargs.get('default_permissions', None)
        self.guilds = kwargs.get('guilds', None)
        self.checks = []
        self.parent = None
        
    async def __call__(self, interaction, *args, **kwargs):
        """Call the command callback"""
        return await self.callback(interaction, *args, **kwargs)

class Group:
    """Represents a slash command group"""
    def __init__(self, name: str, description: str = None, **kwargs):
        self.name = name
        self.description = description or "No description"
        self.guild_only = kwargs.get('guild_only', False)
        self.default_permissions = kwargs.get('default_permissions', None)
        self.guilds = kwargs.get('guilds', None)
        self.commands = {}
        self.parent = None
        
    def command(self, name: str = None, description: str = None, **kwargs):
        """Add a command to this group"""
        def decorator(func):
            cmd = command(name=name, description=description, **kwargs)(func)
            cmd.parent = self
            self.commands[cmd.name] = cmd
            return cmd
        return decorator
        
    def add_command(self, cmd):
        """Add a command to this group"""
        cmd.parent = self
        self.commands[cmd.name] = cmd
        return cmd

class SlashCommandGroup(Group):
    """Alias for Group for py-cord compatibility"""
    pass

# Decorators
def command(name: str = None, description: str = None, **kwargs):
    """Create a slash command"""
    def decorator(func):
        cmd = Command(func, name=name, description=description, **kwargs)
        
        # Store the command on the function
        func.__command__ = cmd
        return func
    return decorator

def describe(**kwargs):
    """Decorator to add descriptions to parameters"""
    def decorator(func):
        if not hasattr(func, '__param_descriptions__'):
            func.__param_descriptions__ = {}
        func.__param_descriptions__.update(kwargs)
        return func
    return decorator

def guild_only():
    """Decorator to mark a command as guild only"""
    def decorator(func):
        func.__guild_only__ = True
        return func
    return decorator

def choices(**kwargs):
    """Decorator to add choices to command parameters"""
    def decorator(func):
        if not hasattr(func, '__param_choices__'):
            func.__param_choices__ = {}
        for param_name, choices_list in kwargs.items():
            func.__param_choices__[param_name] = choices_list
        return func
    return decorator

def check(predicate):
    """Decorator to add a check to a command"""
    def decorator(func):
        if hasattr(func, '__command__'):
            func.__command__.checks.append(predicate)
        elif not hasattr(func, '__command_checks__'):
            func.__command_checks__ = []
            func.__command_checks__.append(predicate)
        else:
            func.__command_checks__.append(predicate)
        return func
    return decorator

# For translations
def locale_str(string: str):
    """Placeholder for locale string"""
    return string

# For transformers
class Transform:
    """Base class for transformers"""
    pass

# For context menus
def context_menu(name: str, **kwargs):
    """Create a context menu command"""
    def decorator(func):
        func.__context_menu__ = True
        func.__context_menu_name__ = name
        return func
    return decorator