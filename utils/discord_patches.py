"""
Discord Patches Module

This module applies patches to the discord library to provide compatibility
between different versions of discord.py and py-cord, especially for 2.6.1.
"""

import logging
import sys
import types
import inspect
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

logger = logging.getLogger(__name__)

try:
    import discord
    from discord.ext import commands
    
    # Check if we're using py-cord
    USING_PYCORD = hasattr(commands.Bot, "slash_command")
    
    # Detect py-cord version
    PYCORD_VERSION = getattr(discord, "__version__", "unknown")
    
    # Check if we're using py-cord 2.6.1 or later
    USING_PYCORD_261_PLUS = False
    if USING_PYCORD and PYCORD_VERSION != "unknown":
        try:
            major, minor, patch = PYCORD_VERSION.split(".")
            USING_PYCORD_261_PLUS = int(major) >= 2 and int(minor) >= 6 and int(patch) >= 1
        except (ValueError, AttributeError):
            # If version check fails, try structure detection
            USING_PYCORD_261_PLUS = hasattr(discord, "app_commands")
    
    # Import app_commands if available
    if hasattr(discord, "app_commands"):
        app_commands = discord.app_commands
        
        # Add check function for permissions if not available
        if not hasattr(app_commands, "check"):
            app_commands.check = lambda predicate: lambda f: f
        
        # Create a Choice class if not available in app_commands
        if not hasattr(app_commands, "Choice"):
            class Choice:
                """
                A choice for a slash command option.
                
                Attributes:
                    name: The name of the choice (displayed to users)
                    value: The value of the choice (used in code)
                """
                def __init__(self, name: str, value: str):
                    self.name = name
                    self.value = value
                    
                def __repr__(self):
                    return f"<Choice name={self.name!r} value={self.value!r}>"
            
            # Add Choice to app_commands
            app_commands.Choice = Choice
            
        # Export Choice directly from this module for better compatibility
        globals()['Choice'] = app_commands.Choice
    else:
        # Create mock app_commands if not available
        app_commands = types.ModuleType("app_commands")
        app_commands.command = lambda **kwargs: lambda f: f
        app_commands.describe = lambda **kwargs: lambda f: f
        app_commands.guild_only = lambda: lambda f: f
        app_commands.choices = lambda **kwargs: lambda f: f
        
        # Add check function for permissions
        app_commands.check = lambda predicate: lambda f: f
        
        # Create a Choice class for app_commands
        class Choice:
            """
            A choice for a slash command option.
            
            Attributes:
                name: The name of the choice (displayed to users)
                value: The value of the choice (used in code)
            """
            def __init__(self, name: str, value: str):
                self.name = name
                self.value = value
                
            def __repr__(self):
                return f"<Choice name={self.name!r} value={self.value!r}>"
        
        # Add Choice to app_commands
        app_commands.Choice = Choice
        
        # Export Choice directly from this module for better compatibility
        globals()['Choice'] = app_commands.Choice
    
    # Add hybrid command functionality to py-cord if needed
    T = TypeVar('T')
    
    def hybrid_command(**kwargs):
        """
        Creates a hybrid command that works in both text and slash contexts.
        This is a compatibility shim for pycord 2.6.1.
        """
        def decorator(func: T) -> T:
            # First register it as a regular command
            cmd = commands.command(**kwargs)(func)
            
            # Then, register it as a slash command if possible
            if hasattr(commands, "slash_command"):
                cmd = commands.slash_command(**kwargs)(cmd)
            
            return cast(T, cmd)
        return decorator
    
    def hybrid_group(**kwargs):
        """
        Creates a hybrid command group that works in both text and slash contexts.
        This is a compatibility shim for pycord 2.6.1.
        """
        def decorator(func: T) -> T:
            # For hybrid commands, we need to modify the approach
            # We'll just use the regular group
            cmd = commands.group(**kwargs)(func)
            
            # Since slash_command can't directly decorate a group,
            # we'll just mark it to identify it as a hybrid
            if hasattr(cmd, '__hybrid_command__'):
                cmd.__hybrid_command__ = True
            
            return cast(T, cmd)
        return decorator
    
    # Patch discord.ext.commands if hybrid commands are not available
    if not hasattr(commands, "hybrid_command"):
        logger.info(f"Detected py-cord {PYCORD_VERSION}, adding hybrid command support")
        commands.hybrid_command = hybrid_command
        commands.hybrid_group = hybrid_group
    
    # Log the patch status
    logger.info(f"Detected py-cord {PYCORD_VERSION}, applied compatibility patches")

except ImportError:
    # If Discord is not available, provide empty implementations
    logger.warning("Discord library not found, using mock implementations")
    USING_PYCORD = False
    USING_PYCORD_261_PLUS = False
    PYCORD_VERSION = "unknown"
    
    # Create mock modules
    discord = types.ModuleType("discord")
    commands = types.ModuleType("commands")
    app_commands = types.ModuleType("app_commands")
    
    # Create empty mock classes
    class MockBot:
        def __init__(self, *args, **kwargs):
            pass
    
    class MockCommand:
        def __init__(self, *args, **kwargs):
            pass
    
    # Assign to modules
    commands.Bot = MockBot
    commands.Command = MockCommand
    commands.command = lambda **kwargs: lambda f: f
    commands.group = lambda **kwargs: lambda f: f
    commands.hybrid_command = lambda **kwargs: lambda f: f
    commands.hybrid_group = lambda **kwargs: lambda f: f

# Function to apply all patches
def patch_all():
    """
    Apply all Discord compatibility patches.
    This function ensures that all components are patched for py-cord 2.6.1 compatibility.
    """
    # Patches are applied when this module is imported
    # But we also explicitly apply additional patches here
    
    # Set up ext_commands compatibility first
    try:
        from utils.ext_commands_compat import setup_ext_commands_compat
        setup_ext_commands_compat()
    except ImportError:
        logger.warning("Failed to import ext_commands_compat, some features may not work")
    
    # Apply interaction type patch
    patch_interaction_option_type()
    
    # Get version safely
    version = getattr(discord, "__version__", "unknown")
    logger.info(f"Detected discord library version {version}, applied compatibility patches")
    return True

# Create a dummy class that py-cord 2.6.1 will accept as an Option type
class InteractionType:
    """A dummy class for interaction parameter type hints"""
    pass

def patch_interaction_option_type():
    """
    Patch the command option type system to handle Interaction parameters
    """
    try:
        # Try to import the required components
        try:
            from discord.commands import Option, OptionConverter
        except ImportError:
            logger.warning("Could not import Option and OptionConverter, skipping interaction type patch")
            return
                    
        # Check if Option is available
        if 'Option' not in locals() or Option is None:
            logger.warning("Option class not available, skipping interaction type patch")
            return
            
        # Check if Discord Interaction is defined
        if not hasattr(discord, 'Interaction'):
            class MockInteraction:
                """Mock Interaction class for compatibility"""
                pass
            discord.Interaction = MockInteraction
            logger.info("Created mock Interaction class")
            
        # Monkey patch Option to handle our dummy InteractionType
        try:
            original_init = Option.__init__
            
            def patched_init(self, *args, **kwargs):
                # Replace Interaction type with InteractionType
                if 'input_type' in kwargs and kwargs['input_type'] == discord.Interaction:
                    kwargs['input_type'] = InteractionType
                return original_init(self, *args, **kwargs)
                
            Option.__init__ = patched_init
            logger.info("Successfully patched Option.__init__")
        except Exception as e:
            logger.warning(f"Failed to patch Option.__init__: {e}")
        
        # Also need to patch the converter system
        try:
            if hasattr(discord, 'commands') and hasattr(discord.commands, 'OptionConverter') and \
               hasattr(discord.commands, 'register_converter'):
                # Register a converter for our dummy type
                @discord.commands.register_converter
                class InteractionConverter(OptionConverter):
                    @classmethod
                    async def convert(cls, ctx, value):
                        # Just return the ctx.interaction
                        if hasattr(ctx, 'interaction'):
                            return ctx.interaction
                        return None
                logger.info("Successfully registered InteractionConverter")
        except Exception as e:
            logger.warning(f"Failed to register converter: {e}")
            
    except Exception as e:
        logger.warning(f"Failed to patch interaction option type: {e}")
        import traceback
        logger.debug(traceback.format_exc())

# Provide AppCommandOptionType compatibility for Step 1.5 fix
try:
    # Try to import from discord.enums
    from discord.enums import AppCommandOptionType
except ImportError:
    try:
        # Try to import from discord directly (some versions put it there)
        from discord import AppCommandOptionType
    except ImportError:
        # Define our own version if not available
        from enum import Enum
        
        class AppCommandOptionType(Enum):
            """Compatible version of AppCommandOptionType for py-cord 2.6.1"""
            STRING = 3
            INTEGER = 4
            BOOLEAN = 5
            USER = 6
            CHANNEL = 7
            ROLE = 8
            MENTIONABLE = 9
            NUMBER = 10  # Float/double
            ATTACHMENT = 11
            
        logger.info("Using custom AppCommandOptionType implementation")

# Function to check if patches were applied
def are_patches_applied() -> bool:
    """
    Check if Discord patches were successfully applied.
    """
    try:
        return (
            hasattr(commands, "hybrid_command") and 
            hasattr(commands, "hybrid_group") and
            'AppCommandOptionType' in globals()
        )
    except NameError:
        return False