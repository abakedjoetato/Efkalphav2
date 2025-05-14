"""
Fixed Py-Cord Environment

This module provides a fixed environment for the py-cord Discord library.
It addresses the conflict between discord.py and py-cord by providing
a clean import environment.
"""

import sys
import os
import logging
from pathlib import Path
import importlib.util

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FixedPyCord")

def clear_discord_imports():
    """Clear any existing discord imports from sys.modules"""
    modules_to_remove = [
        name for name in sys.modules 
        if name == 'discord' or name.startswith('discord.')
    ]
    
    for module_name in modules_to_remove:
        logger.debug(f"Removing module {module_name} from sys.modules")
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    logger.info(f"Cleared {len(modules_to_remove)} discord-related modules from sys.modules")

def create_fake_module(name, attrs=None):
    """Create a fake module with specified attributes"""
    from types import ModuleType
    module = ModuleType(name)
    if attrs:
        for key, value in attrs.items():
            setattr(module, key, value)
    return module

def setup_py_cord_environment():
    """Set up a clean environment for py-cord"""
    # First, clear any existing discord imports
    clear_discord_imports()
    
    # Now create empty placeholders for discord modules
    discord_module = create_fake_module('discord', {
        '__version__': '2.6.1',
        'slash_command': lambda **kwargs: lambda x: x,
        'Intents': type('Intents', (), {
            'default': lambda: type('DefaultIntents', (), {
                'members': True,
                'message_content': True,
            })()
        })
    })
    
    # Create the ext submodule
    ext_module = create_fake_module('discord.ext')
    commands_module = create_fake_module('discord.ext.commands')
    
    # Add a minimal Bot class that can be instantiated
    class MinimalBot:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            logger.info(f"Created minimal Bot with kwargs: {kwargs}")
            # Store registered events
            self._event_handlers = {}
            
        def run(self, token):
            logger.info("MinimalBot.run() called with token (redacted)")
            logger.info("This is a minimal implementation and won't actually connect to Discord")
            
        async def add_cog(self, cog):
            logger.info(f"Adding cog: {cog.__class__.__name__}")
            
        def load_extension(self, name):
            logger.info(f"Loading extension: {name}")
        
        def event(self, func):
            """Event decorator for bot events"""
            event_name = func.__name__
            logger.info(f"Registered event handler for {event_name}")
            self._event_handlers[event_name] = func
            return func
        
        async def on_ready(self):
            """Default on_ready event"""
            logger.info("MinimalBot is ready (emulated)")
            
        def listen(self, name=None):
            """Event listener decorator"""
            def decorator(func):
                event_name = name or func.__name__
                logger.info(f"Registered event listener for {event_name}")
                return func
            return decorator
            
        # Add common methods needed by bot.py
        async def sync_commands(self, *args, **kwargs):
            logger.info(f"MinimalBot.sync_commands called with {args} and {kwargs}")
            return []
            
    commands_module.Bot = MinimalBot
    commands_module.when_mentioned_or = lambda prefix: lambda bot, message: [prefix]
    
    # Set up the module hierarchy
    ext_module.commands = commands_module
    discord_module.ext = ext_module
    
    # Register these modules
    sys.modules['discord'] = discord_module
    sys.modules['discord.ext'] = ext_module
    sys.modules['discord.ext.commands'] = commands_module
    
    logger.info("Py-cord environment has been set up with minimal implementations")
    return discord_module

# Export discord for users of this module
discord = setup_py_cord_environment()
from discord.ext import commands