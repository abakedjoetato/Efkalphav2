"""
Implementation of discord.ext.commands for compatibility

This module provides a set of classes and functions that mimic the
discord.ext.commands module from py-cord 2.6.1.
"""

import inspect
import sys
import functools
import logging
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TypeVar, Union, cast

logger = logging.getLogger(__name__)

# Core command classes
class Command:
    """
    A Discord bot command.
    
    Attributes:
        name: The name of the command
        callback: The function to call when the command is invoked
        description: The description of the command
        help: The help text for the command
        brief: A brief description of the command
        usage: The usage string for the command
        aliases: Aliases for the command
        checks: A list of checks that must pass for the command to be invoked
    """
    
    def __init__(self, func, **kwargs):
        self.callback = func
        self.name = kwargs.get('name', func.__name__)
        self.description = kwargs.get('description', func.__doc__ or "")
        self.help = kwargs.get('help', self.description)
        self.brief = kwargs.get('brief', "")
        self.usage = kwargs.get('usage', "")
        self.aliases = kwargs.get('aliases', [])
        self.checks = []
        self.cog = None
        self.enabled = True
        self.guild_only = kwargs.get('guild_only', False)
        self.parents = []
        self.params = {}
        
        # Try to extract parameters from the function signature
        try:
            sig = inspect.signature(func)
            self.params = sig.parameters
        except Exception:
            pass
    
    async def invoke(self, ctx, *args, **kwargs):
        """Invoke the command"""
        # Run checks first
        for check in self.checks:
            if not await check(ctx):
                raise CheckFailure(f"The check functions for command {self.name} failed.")
                
        # If cog is set, pass self as first arg
        if self.cog is not None:
            return await self.callback(self.cog, ctx, *args, **kwargs)
        else:
            return await self.callback(ctx, *args, **kwargs)

class Group(Command):
    """
    A command group that can have subcommands.
    
    Attributes:
        all_commands: A dictionary of subcommands
    """
    
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)
        self.all_commands = {}
        self.case_insensitive = kwargs.get('case_insensitive', False)
    
    def add_command(self, command):
        """Add a subcommand to the group"""
        command.parents = self.parents + [self]
        self.all_commands[command.name] = command
        return command
    
    def command(self, **kwargs):
        """Create a subcommand for this group"""
        def decorator(func):
            cmd = Command(func, **kwargs)
            self.add_command(cmd)
            return cmd
        return decorator
    
    def group(self, **kwargs):
        """Create a subcommand group for this group"""
        def decorator(func):
            cmd = Group(func, **kwargs)
            self.add_command(cmd)
            return cmd
        return decorator

class Bot:
    """
    The main Discord bot class.
    
    Attributes:
        command_prefix: The command prefix
        commands: A dictionary of commands
        cogs: A dictionary of cogs
        intents: The Discord intents
    """
    
    def __init__(self, command_prefix, **kwargs):
        self.command_prefix = command_prefix
        self.commands = {}
        self.cogs = {}
        self.intents = kwargs.get('intents', None)
        self.case_insensitive = kwargs.get('case_insensitive', False)
        self.description = kwargs.get('description', "")
        self.owner_id = kwargs.get('owner_id', None)
        self.owner_ids = kwargs.get('owner_ids', set())
        self.event_listeners = {}
        
        # Get when_mentioned prefix function if needed
        if command_prefix == when_mentioned:
            self.command_prefix = when_mentioned
            
        # Get when_mentioned_or prefix function if needed
        if isinstance(command_prefix, functools.partial) and command_prefix.func == when_mentioned_or:
            self.command_prefix = command_prefix
    
    def event(self, coro):
        """Register an event handler"""
        if not inspect.iscoroutinefunction(coro):
            raise TypeError('event registered must be a coroutine function')
            
        event_name = coro.__name__
        self.event_listeners[event_name] = coro
        return coro
    
    def command(self, **kwargs):
        """Register a command with the bot"""
        def decorator(func):
            name = kwargs.get('name', func.__name__)
            cmd = Command(func, **kwargs)
            self.add_command(cmd)
            return cmd
        return decorator
    
    def group(self, **kwargs):
        """Register a command group with the bot"""
        def decorator(func):
            name = kwargs.get('name', func.__name__)
            cmd = Group(func, **kwargs)
            self.add_command(cmd)
            return cmd
        return decorator
    
    def add_command(self, command):
        """Add a command to the bot"""
        self.commands[command.name] = command
        return command
    
    def add_cog(self, cog):
        """Add a cog to the bot"""
        cog.bot = self
        cog_name = cog.__class__.__name__
        self.cogs[cog_name] = cog
        
        # Add all commands from the cog
        for attr_name in dir(cog):
            attr = getattr(cog, attr_name)
            if isinstance(attr, Command):
                attr.cog = cog
                self.add_command(attr)
                
        # Add all event listeners from the cog
        for attr_name in dir(cog):
            attr = getattr(cog, attr_name)
            if attr_name.startswith('on_') and inspect.iscoroutinefunction(attr):
                self.event_listeners[attr_name] = attr
                
        # Setup method if available
        if hasattr(cog, 'cog_load') and callable(cog.cog_load):
            try:
                cog.cog_load()
            except Exception as e:
                logger.error(f"Error loading cog {cog_name}: {e}")
                
        return cog
    
    def remove_cog(self, name):
        """Remove a cog from the bot"""
        if name not in self.cogs:
            return None
            
        cog = self.cogs[name]
        
        # Remove all commands from the cog
        for attr_name in dir(cog):
            attr = getattr(cog, attr_name)
            if isinstance(attr, Command):
                self.remove_command(attr.name)
                
        # Remove all event listeners from the cog
        for attr_name in dir(cog):
            attr = getattr(cog, attr_name)
            if attr_name.startswith('on_') and inspect.iscoroutinefunction(attr):
                if attr_name in self.event_listeners and self.event_listeners[attr_name] == attr:
                    del self.event_listeners[attr_name]
                    
        # Cleanup method if available
        if hasattr(cog, 'cog_unload') and callable(cog.cog_unload):
            try:
                cog.cog_unload()
            except Exception as e:
                logger.error(f"Error unloading cog {name}: {e}")
                
        del self.cogs[name]
        return cog
    
    def remove_command(self, name):
        """Remove a command from the bot"""
        if name in self.commands:
            cmd = self.commands[name]
            del self.commands[name]
            return cmd
        return None
    
    def load_extension(self, name, *, package=None):
        """Load an extension (module with a setup function)"""
        if package is None:
            package = __name__
            
        try:
            module = __import__(name, fromlist=['setup'])
            if not hasattr(module, 'setup'):
                raise ExtensionError(f'Extension {name} has no setup function.')
                
            module.setup(self)
            return True
        except Exception as e:
            logger.error(f"Error loading extension {name}: {e}")
            raise ExtensionError(f'Extension {name} could not be loaded.') from e
    
    async def get_context(self, message):
        """Get the command context for a message"""
        return Context(self, message)
    
    async def process_commands(self, message):
        """Process commands in a message"""
        if message.author.bot:
            return
            
        ctx = await self.get_context(message)
        await self.invoke(ctx)
    
    async def invoke(self, ctx):
        """Invoke a command from a context"""
        if not ctx.command:
            return
            
        try:
            await ctx.command.invoke(ctx)
        except Exception as e:
            logger.error(f"Error invoking command {ctx.command.name}: {e}")
            self.dispatch('command_error', ctx, e)
    
    def dispatch(self, event_name, *args, **kwargs):
        """Dispatch an event to all registered listeners"""
        method = 'on_' + event_name
        
        if method in self.event_listeners:
            try:
                self.event_listeners[method](*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event {method}: {e}")
                self.dispatch('error', e)
    
    async def close(self):
        """Close the bot"""
        # Unload all cogs
        for cog_name in list(self.cogs.keys()):
            self.remove_cog(cog_name)
            
        # Clear all commands
        self.commands.clear()
    
    async def start(self, token, *, reconnect=True):
        """Start the bot"""
        # This is normally a complex method that connects to Discord
        # But for our implementation, we just fire the ready event
        logger.info("Starting bot...")
        
        # Fire the ready event
        self.dispatch('ready')
        
        # Just wait indefinitely
        import asyncio
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour

class Context:
    """
    The context for a command.
    
    Attributes:
        bot: The bot instance
        message: The message that triggered the command
        author: The author of the message
        guild: The guild the message was sent in
        channel: The channel the message was sent in
        command: The command that was invoked
        prefix: The prefix used to invoke the command
        invoked_with: The name used to invoke the command
    """
    
    def __init__(self, bot, message, **kwargs):
        self.bot = bot
        self.message = message
        self.author = message.author
        self.guild = message.guild
        self.channel = message.channel
        self.command = None
        self.prefix = kwargs.get('prefix', '')
        self.invoked_with = kwargs.get('invoked_with', '')
        
    async def send(self, content=None, **kwargs):
        """Send a message to the channel"""
        return await self.channel.send(content, **kwargs)
        
    async def reply(self, content=None, **kwargs):
        """Reply to the message"""
        return await self.message.reply(content, **kwargs)

class Cog:
    """Base class for cogs"""
    
    def __init__(self):
        self.bot = None
        
    def cog_load(self):
        """Called when the cog is loaded"""
        pass
        
    def cog_unload(self):
        """Called when the cog is unloaded"""
        pass

# Helper functions for command prefixes
async def _get_prefix_default(bot, message):
    """Default implementation for get_prefix"""
    if callable(bot.command_prefix):
        ret = bot.command_prefix(bot, message)
        if inspect.isawaitable(ret):
            ret = await ret
    else:
        ret = bot.command_prefix
        
    if isinstance(ret, str):
        return [ret]
    return ret

def when_mentioned(bot, message):
    """Prefix function that triggers when the bot is mentioned"""
    return [f'<@{bot.user.id}> ', f'<@!{bot.user.id}> ']

def when_mentioned_or(*prefixes):
    """Prefix function that triggers when the bot is mentioned or a prefix is used"""
    def prefix_func(bot, message):
        r = list(when_mentioned(bot, message))
        r.extend(prefixes)
        return r
    return prefix_func

# Checks and decorators
def check(predicate):
    """Decorator that adds a check to a command"""
    def decorator(func):
        if isinstance(func, Command):
            func.checks.append(predicate)
        else:
            if not hasattr(func, '__checks__'):
                func.__checks__ = []
            func.__checks__.append(predicate)
        return func
    return decorator

def guild_only():
    """Decorator that restricts a command to guild channels only"""
    def predicate(ctx):
        if ctx.guild is None:
            raise CheckFailure('This command can only be used in a guild.')
        return True
    return check(predicate)

def is_owner():
    """Decorator that restricts a command to the bot owner only"""
    def predicate(ctx):
        if ctx.bot.owner_id is not None:
            return ctx.author.id == ctx.bot.owner_id
        elif ctx.bot.owner_ids is not None:
            return ctx.author.id in ctx.bot.owner_ids
        raise CheckFailure('Bot owner is not set.')
    return check(predicate)

# Exception classes
class CommandError(Exception):
    """Base exception for command errors"""
    pass

class CheckFailure(CommandError):
    """Exception raised when a check fails"""
    pass

class MissingRequiredArgument(CommandError):
    """Exception raised when a required argument is missing"""
    pass

class BadArgument(CommandError):
    """Exception raised when an argument can't be converted"""
    pass

class CommandNotFound(CommandError):
    """Exception raised when a command is not found"""
    pass

class CommandInvokeError(CommandError):
    """Exception raised when a command raises an exception"""
    pass

class ExtensionError(Exception):
    """Base exception for extension errors"""
    pass

class ExtensionNotFound(ExtensionError):
    """Exception raised when an extension is not found"""
    pass

class ExtensionNotLoaded(ExtensionError):
    """Exception raised when an extension is not loaded"""
    pass

class ExtensionAlreadyLoaded(ExtensionError):
    """Exception raised when an extension is already loaded"""
    pass

# Hybrid commands
def slash_command(**kwargs):
    """Decorator to create a slash command (compatibility function)"""
    def decorator(func):
        # Just mark it, real implementation not needed
        func.__slash_command__ = True
        return func
    return decorator

def hybrid_command(**kwargs):
    """Decorator to create a hybrid command (both regular and slash)"""
    def decorator(func):
        # First register as a command
        cmd = command(**kwargs)(func)
        # Then mark as a slash command
        cmd.__slash_command__ = True
        cmd.__hybrid_command__ = True
        return cmd
    return decorator

def hybrid_group(**kwargs):
    """Decorator to create a hybrid command group"""
    def decorator(func):
        # First register as a group
        cmd = group(**kwargs)(func)
        # Then mark as a slash command
        cmd.__slash_command__ = True
        cmd.__hybrid_command__ = True
        return cmd
    return decorator

# Converters
class Converter:
    """Base class for command argument converters"""
    async def convert(self, ctx, argument):
        raise NotImplementedError('Derived classes need to implement this.')

class MemberConverter(Converter):
    """Converts to a Discord Member object"""
    async def convert(self, ctx, argument):
        if not ctx.guild:
            raise BadArgument("This command can only be used in a guild.")
            
        # Look for the member (simplified)
        for member in ctx.guild.members:
            if str(member.id) == argument or member.name == argument:
                return member
                
        raise BadArgument(f"Member {argument} not found.")

class UserConverter(Converter):
    """Converts to a Discord User object"""
    async def convert(self, ctx, argument):
        # Try to get member first
        try:
            return await MemberConverter().convert(ctx, argument)
        except BadArgument:
            # If member not found, try to get user (simplified)
            # In a real implementation, this would call the Discord API
            raise BadArgument(f"User {argument} not found.")

class ChannelConverter(Converter):
    """Converts to a Discord Channel object"""
    async def convert(self, ctx, argument):
        if not ctx.guild:
            raise BadArgument("This command can only be used in a guild.")
            
        # Look for the channel (simplified)
        for channel in ctx.guild.channels:
            if str(channel.id) == argument or channel.name == argument:
                return channel
                
        raise BadArgument(f"Channel {argument} not found.")

# Shorthand aliases
command = lambda **kwargs: lambda func: Command(func, **kwargs)
group = lambda **kwargs: lambda func: Group(func, **kwargs)

# Ensure all necessary functions and classes are exported
__all__ = [
    'Bot',
    'Command',
    'Group',
    'Context',
    'Cog',
    'when_mentioned',
    'when_mentioned_or',
    'check',
    'guild_only',
    'is_owner',
    'command',
    'group',
    'slash_command',
    'hybrid_command',
    'hybrid_group',
    'CommandError',
    'CheckFailure',
    'MissingRequiredArgument',
    'BadArgument',
    'CommandNotFound',
    'CommandInvokeError',
    'ExtensionError',
    'ExtensionNotFound',
    'ExtensionNotLoaded',
    'ExtensionAlreadyLoaded',
    'Converter',
    'MemberConverter',
    'UserConverter',
    'ChannelConverter'
]

# For async support
import asyncio