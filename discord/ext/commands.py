"""
Discord ext.commands compatibility implementation

This module provides a minimal implementation of discord.ext.commands to support existing code.
"""

import sys
import logging
import inspect
import asyncio
import functools
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union, Coroutine

logger = logging.getLogger(__name__)
logger.info("Loading Discord ext.commands compatibility layer")

# Keep track of registered decorators
_DECORATORS = {}

# Permission exceptions
class MissingPermissions(CommandError):
    """Exception raised when user lacks permissions"""
    def __init__(self, missing_permissions, *args):
        self.missing_permissions = missing_permissions
        message = f'You are missing the following permissions to run this command: {", ".join(missing_permissions)}'
        super().__init__(message, *args)

class CheckFailure(CommandError):
    """Exception raised when check fails"""
    pass

# Base exception classes needed for error handling
class CommandError(Exception):
    """Base exception for all command-related errors"""
    pass

class CommandInvokeError(CommandError):
    """Exception raised when a command raises an exception during execution"""
    def __init__(self, original: Exception):
        self.original = original
        super().__init__(f'Command raised an exception: {original.__class__.__name__}: {original}')

class MissingRequiredArgument(CommandError):
    """Exception raised when a required argument is not passed to a command"""
    def __init__(self, param):
        self.param = param
        super().__init__(f'Missing required argument {param.name}')

class BadArgument(CommandError):
    """Exception raised when a bad argument is passed to a command"""
    pass

class MissingPermissions(CommandError):
    """Exception raised when a user doesn't have permissions to run a command"""
    def __init__(self, missing_permissions: List[str]):
        self.missing_permissions = missing_permissions
        super().__init__(f'You are missing permissions: {", ".join(missing_permissions)}')

class BotMissingPermissions(CommandError):
    """Exception raised when the bot doesn't have permissions for a command"""
    def __init__(self, missing_permissions: List[str]):
        self.missing_permissions = missing_permissions
        super().__init__(f'Bot is missing permissions: {", ".join(missing_permissions)}')

class CommandOnCooldown(CommandError):
    """Exception raised when a command is on cooldown"""
    def __init__(self, cooldown, retry_after):
        self.cooldown = cooldown
        self.retry_after = retry_after
        super().__init__(f'Command is on cooldown. Try again in {retry_after:.2f}s')

class NotOwner(CommandError):
    """Exception raised when a command is only for the owner"""
    pass

class ExtensionError(Exception):
    """Base exception class for errors with extensions."""
    pass

class ExtensionAlreadyLoaded(ExtensionError):
    """Exception raised when an extension is already loaded."""
    def __init__(self, name):
        self.name = name
        super().__init__(f'Extension {name} is already loaded')

class ExtensionNotLoaded(ExtensionError):
    """Exception raised when an extension is not loaded."""
    def __init__(self, name):
        self.name = name
        super().__init__(f'Extension {name} is not loaded')

class NoEntryPointError(ExtensionError):
    """Exception raised when an extension does not have a setup function."""
    def __init__(self, name):
        self.name = name
        super().__init__(f'Extension {name} has no setup function')

class ExtensionFailed(ExtensionError):
    """Exception raised when an extension fails to load."""
    def __init__(self, name, original):
        self.name = name
        self.original = original
        super().__init__(f'Extension {name} raised an error: {original.__class__.__name__}: {original}')

# Command classes
class Command:
    """A command that can be invoked by a user"""
    
    def __init__(self, callback, **kwargs):
        self.callback = callback
        self.name = kwargs.get('name', callback.__name__)
        self.help = kwargs.get('help', callback.__doc__)
        self.brief = kwargs.get('brief', None)
        self.usage = kwargs.get('usage', None)
        self.aliases = kwargs.get('aliases', [])
        self.enabled = kwargs.get('enabled', True)
        self.parent = None
        self.cog = None
        self._return_annotation = self._get_return_annotation()
        
    def _get_return_annotation(self):
        """Get the return annotation of the callback"""
        signature = inspect.signature(self.callback)
        return signature.return_annotation
        
    async def invoke(self, ctx, *args, **kwargs):
        """Invoke the command with the given context and arguments"""
        try:
            return await self.callback(ctx.cog or ctx.bot, ctx, *args, **kwargs)
        except Exception as e:
            raise CommandInvokeError(e)
            
    def __call__(self, *args, **kwargs):
        """Allow the command to be called directly"""
        if asyncio.iscoroutinefunction(self.callback):
            return self.callback(*args, **kwargs)
        else:
            return self.callback(*args, **kwargs)
            
    def __str__(self):
        return self.name

class Group(Command):
    """A command that has subcommands"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commands = {}
        self.all_commands = {}
        
    def add_command(self, command):
        """Add a command to this group"""
        if command.name in self.commands:
            raise CommandError(f'Command {command.name} is already registered')
        
        command.parent = self
        self.commands[command.name] = command
        self.all_commands[command.name] = command
        
        for alias in command.aliases:
            if alias in self.all_commands:
                raise CommandError(f'Alias {alias} is already an existing command or alias')
            self.all_commands[alias] = command
            
    def command(self, *args, **kwargs):
        """Decorator to create a command within this group"""
        def decorator(func):
            cmd = Command(func, **kwargs)
            self.add_command(cmd)
            return cmd
        return decorator
        
    def group(self, *args, **kwargs):
        """Decorator to create a group within this group"""
        def decorator(func):
            cmd = Group(func, **kwargs)
            self.add_command(cmd)
            return cmd
        return decorator

class Bot:
    """Base class for bot functionality"""
    
    def __init__(self, command_prefix, **options):
        self.command_prefix = command_prefix
        self.commands = {}
        self.extensions = {}
        self.cogs = {}
        
        # Set default options
        self.options = {
            'help_command': None,
            'case_insensitive': False,
            'strip_after_prefix': False,
            'description': None,
            'owner_id': None,
            'owner_ids': None,
            'intents': None,
        }
        self.options.update(options)
        
        # Event handlers
        self.event_handlers = {}
        
        # Create public attributes from options
        self.__dict__.update(self.options)
        
        self._check_functions = []
        self._before_invoke = None
        self._after_invoke = None
        
        self.event_handlers = {}
        self.user = None
        self.guilds = []
        
    def add_command(self, command):
        """Add a command to the bot"""
        if command.name in self.commands:
            raise CommandError(f'Command {command.name} is already registered')
            
        self.commands[command.name] = command
        
        for alias in command.aliases:
            if alias in self.commands:
                raise CommandError(f'Alias {alias} is already an existing command or alias')
            self.commands[alias] = command
            
    def command(self, *args, **kwargs):
        """Decorator to create a command for the bot"""
        def decorator(func):
            cmd = Command(func, **kwargs)
            self.add_command(cmd)
            return cmd
        return decorator
        
    def group(self, *args, **kwargs):
        """Decorator to create a command group for the bot"""
        def decorator(func):
            cmd = Group(func, **kwargs)
            self.add_command(cmd)
            return cmd
        return decorator
        
    def event(self, func):
        """Decorator to register an event handler"""
        name = func.__name__
        # Validate event name format - Discord events start with on_
        if not name.startswith('on_'):
            logger.warning(f'Event name "{name}" does not start with "on_", but registering anyway')
        
        self.event_handlers[name] = func
        return func
        
    def check(self, func):
        """Decorator to register a global check function"""
        self._check_functions.append(func)
        return func
        
    def before_invoke(self, func):
        """Decorator to register a function to call before invoking a command"""
        self._before_invoke = func
        return func
        
    def after_invoke(self, func):
        """Decorator to register a function to call after invoking a command"""
        self._after_invoke = func
        return func
        
    async def invoke(self, ctx):
        """Invoke a command with the given context"""
        if ctx.command is None:
            return
            
        # Run command checks
        if not await self.can_run(ctx):
            raise CommandError('Command check failed')
        
        # Run pre-invoke hook
        if self._before_invoke is not None:
            await self._before_invoke(ctx)
            
        try:
            # Invoke the command
            await ctx.command.invoke(ctx)
        finally:
            # Run post-invoke hook
            if self._after_invoke is not None:
                await self._after_invoke(ctx)
                
    async def can_run(self, ctx):
        """Check if the command can be run with the given context"""
        for check in self._check_functions:
            if not await check(ctx):
                return False
        return True
        
    async def start(self, token, *, reconnect=True):
        """Start the bot with the given token"""
        logger.info("Starting bot (mock implementation)")
        try:
            # Set up the bot user
            self.user = type('User', (), {
                'id': 0,
                'name': 'BotUser',
                'discriminator': '0000',
                'bot': True,
                'mention': '<@0>',
                'display_name': 'BotUser',
            })
            
            # Dispatch the ready event
            if 'on_ready' in self.event_handlers:
                await self.event_handlers['on_ready']()
                
            # Just stay alive indefinitely
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by keyboard interrupt")
        finally:
            if 'on_disconnect' in self.event_handlers:
                await self.event_handlers['on_disconnect']()
    
    async def close(self):
        """Close the bot connection"""
        logger.info("Closing bot connection")
        if 'on_disconnect' in self.event_handlers:
            await self.event_handlers['on_disconnect']()
    
    def load_extension(self, name, *, package=None):
        """Load an extension"""
        if name in self.extensions:
            raise ExtensionAlreadyLoaded(name)
            
        try:
            if package:
                module = __import__(name, fromlist=['setup'], level=0)
            else:
                module = __import__(name, fromlist=['setup'])
                
            if not hasattr(module, 'setup'):
                raise NoEntryPointError(name)
                
            module.setup(self)
            self.extensions[name] = module
        except Exception as e:
            if isinstance(e, ExtensionError):
                raise
            else:
                raise ExtensionFailed(name, e)
    
    def unload_extension(self, name):
        """Unload an extension"""
        if name not in self.extensions:
            raise ExtensionNotLoaded(name)
            
        module = self.extensions[name]
        
        # Remove all commands from the extension
        to_remove = []
        for cmd_name, cmd in self.commands.items():
            if cmd.module == name:
                to_remove.append(cmd_name)
                
        for cmd_name in to_remove:
            del self.commands[cmd_name]
            
        # Remove all cogs from the extension
        for cogname, cog in list(self.cogs.items()):
            if cog.__module__ == name:
                self.remove_cog(cogname)
                
        # Call cleanup if exists
        if hasattr(module, 'teardown'):
            try:
                module.teardown(self)
            except Exception:
                pass
                
        # Remove the extension
        del self.extensions[name]
    
    def reload_extension(self, name, *, package=None):
        """Reload an extension"""
        self.unload_extension(name)
        self.load_extension(name, package=package)
    
    def add_cog(self, cog):
        """Add a cog to the bot"""
        if not hasattr(cog, '__cog_name__'):
            cog.__cog_name__ = cog.__class__.__name__
            
        if cog.__cog_name__ in self.cogs:
            raise CommandError(f'Cog {cog.__cog_name__} is already registered')
            
        # Add the cog
        self.cogs[cog.__cog_name__] = cog
        
        # Register the commands from the cog
        members = inspect.getmembers(cog)
        for _, member in members:
            if isinstance(member, Command):
                member.cog = cog
                self.add_command(member)
                
        # Register event handlers from the cog
        for name, method in members:
            if name.startswith('on_'):
                self.event_handlers[name] = method
    
    def remove_cog(self, name):
        """Remove a cog from the bot"""
        if name not in self.cogs:
            return None
            
        cog = self.cogs[name]
        
        # Remove the commands from this cog
        to_remove = []
        for cmd_name, cmd in self.commands.items():
            if cmd.cog == cog:
                to_remove.append(cmd_name)
                
        for cmd_name in to_remove:
            del self.commands[cmd_name]
            
        # Remove event handlers from this cog
        for event_name, method in inspect.getmembers(cog):
            if event_name.startswith('on_') and self.event_handlers.get(event_name) == method:
                del self.event_handlers[event_name]
                
        # Remove the cog
        del self.cogs[name]
        
        return cog

# Context class
class Context:
    """The context of a command invocation"""
    
    def __init__(self, **attrs):
        self.__dict__.update(attrs)
        
    async def send(self, content=None, **kwargs):
        """Send a message to the channel"""
        logger.info(f"[Mock] Sending message to {getattr(self, 'channel', 'unknown')}: {content}")
        return None
        
    async def reply(self, content=None, **kwargs):
        """Reply to the message"""
        logger.info(f"[Mock] Replying to message: {content}")
        return None

# Command prefix handling for bot initialization
def when_mentioned(bot, msg):
    """Returns a callable that checks if the message mentions the bot."""
    return [f'<@{bot.user.id}> ', f'<@!{bot.user.id}> ']

def when_mentioned_or(*prefixes):
    """Returns a callable that checks if the message starts with the prefix or mentions the bot."""
    def inner(bot, msg):
        r = when_mentioned(bot, msg)
        r.extend(prefixes)
        return r
    return inner

# Command decorators
def command(**kwargs):
    """Decorator to create a command"""
    def decorator(func):
        return Command(func, **kwargs)
    return decorator

def group(**kwargs):
    """Decorator to create a command group"""
    def decorator(func):
        return Group(func, **kwargs)
    return decorator

def check(predicate):
    """Decorator to add a check to a command"""
    def decorator(func):
        if isinstance(func, Command):
            func.checks.append(predicate)
        else:
            if not hasattr(func, '__commands_checks__'):
                func.__commands_checks__ = []
            func.__commands_checks__.append(predicate)
        return func
    return decorator

# Cog base class
class CogMeta(type):
    """Metaclass for cogs"""
    
    def __new__(cls, name, bases, attrs):
        # Create the class
        new_cls = super().__new__(cls, name, bases, attrs)
        
        # Set cog name
        new_cls.__cog_name__ = attrs.get('__cog_name__', name)
        
        # Set command attributes
        for attrname, attrvalue in attrs.items():
            if isinstance(attrvalue, Command):
                attrvalue.cog = new_cls
                
        return new_cls

class Cog(metaclass=CogMeta):
    """Base class for cogs"""
    
    @classmethod
    def listener(cls, func):
        """Decorator to mark a function as a listener"""
        if not hasattr(func, '__cog_listener__'):
            func.__cog_listener__ = True
        return func
    
    # Optional Cog setup/cleanup hooks
    def cog_unload(self):
        """Called when the cog is unloaded"""
        pass
        
    def cog_check(self, ctx):
        """Global cog check"""
        return True
        
    async def cog_command_error(self, ctx, error):
        """Called when a command in this cog raises an error"""
        pass