"""
Extension Commands Compatibility Module

This module provides a compatibility layer for discord.ext.commands when it's not available.
It creates mock implementations of key components to allow import statements to succeed.
"""

import logging
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TypeVar, Generic, Type

logger = logging.getLogger(__name__)

T = TypeVar('T')
CommandT = TypeVar('CommandT', bound='Command')

class CommandError(Exception):
    """Base exception for command-related errors."""
    pass

class ExtensionError(Exception):
    """Base exception for extension-related errors."""
    pass

class ExtensionNotFound(ExtensionError):
    """Raised when an extension could not be found."""
    pass

class ExtensionAlreadyLoaded(ExtensionError):
    """Raised when an extension is already loaded."""
    pass

class ExtensionFailed(ExtensionError):
    """Raised when an extension failed to load."""
    def __init__(self, name: str, original: Exception) -> None:
        self.name = name
        self.original = original
        super().__init__(f'Extension {name} raised an error: {original}')

class CheckFailure(CommandError):
    """Exception raised when a check fails."""
    pass

class MissingRequiredArgument(CommandError):
    """Exception raised when a required argument is missing."""
    pass

class BadArgument(CommandError):
    """Exception raised when a bad argument is provided."""
    pass

class NoPrivateMessage(CheckFailure):
    """Exception raised when a command cannot be used in private messages."""
    pass

class MissingPermissions(CheckFailure):
    """Exception raised when a user is missing permissions required to run a command."""
    pass

class BotMissingPermissions(CheckFailure):
    """Exception raised when the bot is missing permissions required to run a command."""
    pass

class CommandNotFound(CommandError):
    """Exception raised when a command is not found."""
    pass

class DisabledCommand(CommandError):
    """Exception raised when a command is disabled."""
    pass

class CommandOnCooldown(CommandError):
    """Exception raised when a command is on cooldown."""
    pass

class NotOwner(CheckFailure):
    """Exception raised when the message author is not the owner of the bot."""
    pass

class Context:
    """Represents the context in which a command is being invoked."""
    def __init__(self, **kwargs) -> None:
        self.bot = kwargs.get('bot', None)
        self.guild = kwargs.get('guild', None)
        self.author = kwargs.get('author', None)
        self.channel = kwargs.get('channel', None)
        self.message = kwargs.get('message', None)
        self.command = kwargs.get('command', None)
        self.kwargs = {}
        self.args = []
        self.interaction = None

    async def send(self, content=None, **kwargs):
        """Mock implementation of send."""
        logger.warning("Mock Context.send called")
        return None

class Command:
    """A class that implements the protocol for a bot text command."""
    def __init__(self, func, **kwargs):
        self.callback = func
        self.name = kwargs.get('name', func.__name__)
        self.aliases = kwargs.get('aliases', [])
        self.brief = kwargs.get('brief', '')
        self.description = kwargs.get('description', '')
        self.enabled = kwargs.get('enabled', True)
        self.help = kwargs.get('help', '')
        self.hidden = kwargs.get('hidden', False)
        self.rest_is_raw = kwargs.get('rest_is_raw', False)
        self.ignore_extra = kwargs.get('ignore_extra', True)
        self.cooldown_after_parsing = kwargs.get('cooldown_after_parsing', False)
        self.checks = []
        self.cog = None

    async def __call__(self, *args, **kwargs):
        """Mock implementation of Command.__call__."""
        return await self.callback(*args, **kwargs)

    def error(self, coro):
        """
        A decorator that registers a coroutine as a local error handler.
        """
        self.on_error = coro
        return coro

    def add_check(self, func):
        """Adds a check to the command."""
        self.checks.append(func)
        return self

    def remove_check(self, func):
        """Removes a check from the command."""
        try:
            self.checks.remove(func)
        except ValueError:
            pass
        return self

class Group(Command):
    """Mock implementation of Group, a subclass of Command."""
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)
        self.all_commands = {}
        self.case_insensitive = kwargs.get('case_insensitive', False)

    def command(self, *args, **kwargs):
        """Decorator to create a command and register it to the group."""
        def decorator(func):
            cmd = Command(func, **kwargs)
            self.add_command(cmd)
            return cmd
        return decorator

    def add_command(self, command):
        """Add a command to this group."""
        if not isinstance(command, Command):
            raise TypeError('command must be a subclass of Command')
        self.all_commands[command.name] = command
        for alias in command.aliases:
            self.all_commands[alias] = command
        command.parent = self
        return self

    def remove_command(self, name):
        """Remove a command from this group."""
        command = self.all_commands.pop(name, None)
        if command is not None:
            for alias in command.aliases:
                self.all_commands.pop(alias, None)
        return command

def command(name=None, cls=None, **attrs):
    """A shortcut decorator that invokes :func:`command` and adds it to the bot."""
    if cls is None:
        cls = Command

    def decorator(func):
        if isinstance(func, Command):
            raise TypeError('Callback is already a command.')
        
        cmd = cls(func, name=name or func.__name__, **attrs)
        cmd.__module__ = func.__module__
        
        return cmd
    
    return decorator

def group(name=None, **attrs):
    """A shortcut decorator that invokes :func:`group` and adds it to the bot."""
    attrs.setdefault('cls', Group)
    return command(name=name, **attrs)

class Bot:
    """Mock implementation of Bot."""
    def __init__(self, **kwargs):
        self.all_commands = {}
        self.cogs = {}
        self.extensions = {}

    def add_command(self, command):
        """Add a command to the bot."""
        if not isinstance(command, Command):
            raise TypeError('command must be a subclass of Command')
        self.all_commands[command.name] = command
        for alias in command.aliases:
            self.all_commands[alias] = command
        command.parent = self
        return self

    def remove_command(self, name):
        """Remove a command from the bot."""
        command = self.all_commands.pop(name, None)
        if command is not None:
            for alias in command.aliases:
                self.all_commands.pop(alias, None)
        return command

    def command(self, *args, **kwargs):
        """Decorator to register a command to the bot."""
        def decorator(func):
            cmd = command(*args, **kwargs)(func)
            self.add_command(cmd)
            return cmd
        return decorator

    def group(self, *args, **kwargs):
        """Decorator to register a group to the bot."""
        def decorator(func):
            cmd = group(*args, **kwargs)(func)
            self.add_command(cmd)
            return cmd
        return decorator

    def add_cog(self, cog):
        """Add a cog to the bot."""
        self.cogs[cog.__class__.__name__] = cog
        return self

    def remove_cog(self, name):
        """Remove a cog from the bot."""
        return self.cogs.pop(name, None)

    def load_extension(self, name):
        """Load an extension."""
        return []

    def unload_extension(self, name):
        """Unload an extension."""
        pass

    def reload_extension(self, name):
        """Reload an extension."""
        pass

class Cog:
    """A class to help organize commands and listeners into logical groupings."""
    def __init__(self, name=None):
        self.name = name or self.__class__.__name__

def setup_ext_commands_compat():
    """Set up discord.ext.commands compatibility if needed."""
    try:
        # Try to import discord.ext.commands to check if it exists
        import discord.ext.commands
        logger.info("discord.ext.commands is available, no need for compatibility layer")
        return False
    except (ImportError, AttributeError):
        # Create a module to serve as discord.ext.commands
        try:
            # First ensure discord.ext exists
            if not hasattr(sys.modules, 'discord') or not hasattr(sys.modules['discord'], 'ext'):
                import types
                if 'discord' not in sys.modules:
                    discord_module = types.ModuleType('discord')
                    sys.modules['discord'] = discord_module
                
                if not hasattr(sys.modules['discord'], 'ext'):
                    ext_module = types.ModuleType('discord.ext')
                    sys.modules['discord'].ext = ext_module
                    sys.modules['discord.ext'] = ext_module
            
            # Create a commands module
            import types
            commands_module = types.ModuleType('discord.ext.commands')
            
            # Add all our mock classes to it
            for name, obj in globals().items():
                if isinstance(obj, type) or callable(obj):
                    setattr(commands_module, name, obj)
            
            # Register the module
            sys.modules['discord.ext.commands'] = commands_module
            sys.modules['discord'].ext.commands = commands_module
            
            logger.info("Set up discord.ext.commands compatibility layer")
            return True
        except Exception as e:
            logger.error(f"Failed to set up discord.ext.commands compatibility: {e}")
            return False

# Set up the compatibility layer when this module is imported
setup_ext_commands_compat()