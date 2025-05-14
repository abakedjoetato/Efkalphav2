"""
Cog Adapter Module

This module helps adapt existing Discord.py/Py-cord cogs 
to work with our enhanced direct bot implementation.
"""
import logging
import inspect
import sys
import importlib
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)

class CogAdapter:
    """
    Adapter to convert standard Discord.py/Py-cord cogs
    into a format compatible with our direct bot implementation.
    """
    
    @staticmethod
    def adapt_cog(cog_cls, cog_dir="cogs"):
        """
        Adapt a cog class to work with our direct bot implementation
        
        Args:
            cog_cls: The original cog class
            cog_dir: The directory where cogs are stored
            
        Returns:
            The adapted cog class
        """
        # Import our Cog class
        from direct_bot import Cog
        
        # Create a new class that inherits from our Cog class
        class_name = f"Adapted{cog_cls.__name__}"
        
        # Get all methods from the original cog
        methods = {}
        
        for name, method in inspect.getmembers(cog_cls, inspect.isfunction):
            # Skip special methods
            if name.startswith('__') and name.endswith('__'):
                continue
                
            # Check if it's a command
            is_command = False
            for attr in ['__command__', 'is_command', 'command']:
                if hasattr(method, attr):
                    is_command = True
                    break
                    
            # Check if it's a listener
            is_listener = False
            for attr in ['__listener__', 'is_listener', 'listener']:
                if hasattr(method, attr):
                    is_listener = True
                    break
                    
            # Adapt the method
            if is_command:
                # Add command decorator
                decorated_method = Cog.command()(method)
                methods[name] = decorated_method
            elif is_listener:
                # Add listener decorator
                event_name = getattr(method, '__listener_name__', None) or name
                if event_name.startswith('on_'):
                    decorated_method = Cog.listener(name=event_name)(method)
                    methods[name] = decorated_method
                else:
                    methods[name] = method
            else:
                methods[name] = method
                
        # Create the adapted class
        adapted_cls = type(class_name, (Cog,), methods)
        
        return adapted_cls
        
    @staticmethod
    def load_and_adapt_cog(bot, cog_name, cog_dir="cogs"):
        """
        Load a cog module and adapt it to work with our direct bot implementation
        
        Args:
            bot: The bot instance
            cog_name: The name of the cog to load (e.g., 'cogs.economy')
            cog_dir: The directory where cogs are stored
            
        Returns:
            The loaded and adapted cog instance
        """
        try:
            # Import the module
            module = importlib.import_module(cog_name)
            
            # Reload in case it was already loaded
            importlib.reload(module)
            
            # Find the cog class
            cog_cls = None
            for item_name, item in inspect.getmembers(module):
                if inspect.isclass(item) and (
                    hasattr(item, 'qualified_name') or  # discord.py Cog
                    (hasattr(item, '__cog_name__')) or  # py-cord Cog
                    hasattr(item, 'cog_check') or  # discord.py/py-cord Cog method
                    'Cog' in item.__name__  # Fallback: name contains 'Cog'
                ):
                    cog_cls = item
                    break
                    
            if not cog_cls:
                raise ValueError(f"No cog class found in {cog_name}")
                
            # Adapt the cog class
            adapted_cls = CogAdapter.adapt_cog(cog_cls, cog_dir)
            
            # Create an instance of the adapted cog
            cog = adapted_cls(bot)
            
            return cog
            
        except Exception as e:
            logger.error(f"Error loading and adapting cog {cog_name}: {e}")
            traceback.print_exc()
            raise