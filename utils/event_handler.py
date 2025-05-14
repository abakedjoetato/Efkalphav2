"""
Event Handler Module

This module provides utilities for handling Discord events in a structured way.
"""

import logging
import asyncio
import inspect
from typing import Dict, List, Callable, Any, Optional, Union, Coroutine
import traceback

# Configure logger
logger = logging.getLogger("utils.event_handler")

class EventHandler:
    """
    Event handler for Discord events
    
    This class manages event handlers and provides utilities for
    registering and triggering event handlers.
    
    Attributes:
        bot: The Discord bot instance
        handlers: Dictionary of event names to lists of handler functions
    """
    
    def __init__(self, bot):
        """
        Initialize the event handler
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.handlers: Dict[str, List[Callable]] = {}
        
    def register_handler(self, event_name: str, handler: Callable) -> None:
        """
        Register an event handler
        
        Args:
            event_name: Name of the event
            handler: Handler function
        """
        if event_name not in self.handlers:
            self.handlers[event_name] = []
            
        self.handlers[event_name].append(handler)
        logger.debug(f"Registered handler for event: {event_name}")
        
    def unregister_handler(self, event_name: str, handler: Callable) -> bool:
        """
        Unregister an event handler
        
        Args:
            event_name: Name of the event
            handler: Handler function
            
        Returns:
            bool: True if the handler was unregistered, False otherwise
        """
        if event_name in self.handlers and handler in self.handlers[event_name]:
            self.handlers[event_name].remove(handler)
            logger.debug(f"Unregistered handler for event: {event_name}")
            return True
            
        return False
        
    async def trigger_event(self, event_name: str, *args, **kwargs) -> List[Any]:
        """
        Trigger all handlers for an event
        
        Args:
            event_name: Name of the event
            *args: Arguments to pass to the handlers
            **kwargs: Keyword arguments to pass to the handlers
            
        Returns:
            List[Any]: List of results from the handlers
        """
        results = []
        
        if event_name in self.handlers:
            for handler in self.handlers[event_name]:
                try:
                    # Check if the handler is a coroutine function
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(*args, **kwargs)
                    else:
                        result = handler(*args, **kwargs)
                        
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_name}: {e}")
                    logger.debug(traceback.format_exc())
                    
        return results
        
    def setup_discord_events(self) -> None:
        """
        Set up Discord event handlers
        
        This method sets up handlers for Discord events by monkey patching
        the bot's event dispatcher.
        """
        # Get the original dispatch method
        original_dispatch = self.bot.dispatch
        
        # Create a new dispatch method that also triggers our handlers
        def new_dispatch(event_name, *args, **kwargs):
            # Call the original dispatch method
            original_dispatch(event_name, *args, **kwargs)
            
            # Also trigger our handlers
            asyncio.create_task(self.trigger_event(event_name, *args, **kwargs))
            
        # Replace the dispatch method
        self.bot.dispatch = new_dispatch
        
        logger.info("Set up Discord event handlers")

def event(handler: Optional[Callable] = None, *, name: Optional[str] = None):
    """
    Decorator for registering event handlers
    
    This decorator can be used to register event handlers for Discord events.
    
    Args:
        handler: Handler function
        name: Optional event name (default: function name)
        
    Returns:
        Callable: Decorated handler function
    """
    def decorator(func):
        # Get the event name from the function name or parameter
        event_name = name or func.__name__
        
        # Store the event name in the function
        func.__event_name__ = event_name
        
        return func
        
    # Handle both @event and @event(name="event_name") syntax
    if handler is None:
        return decorator
    else:
        return decorator(handler)