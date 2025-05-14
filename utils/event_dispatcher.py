"""
Event Dispatcher System

This module provides a centralized event dispatching system with error handling,
allowing bot components to communicate through a publish-subscribe pattern.
"""
import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, Union, Coroutine

class EventDispatcher:
    """
    Centralized event dispatching system with error handling.
    
    This class allows registering handlers for custom bot events
    and safely dispatching events to all registered handlers.
    """
    
    def __init__(self):
        """Initialize event dispatcher"""
        self.handlers = {}
        self.logger = logging.getLogger("event_dispatcher")
        
    def register_handler(self, event_name, handler):
        """
        Register a handler for an event.
        
        Args:
            event_name: Name of the event
            handler: Async function to handle the event
        """
        if event_name not in self.handlers:
            self.handlers[event_name] = []
            
        if handler not in self.handlers[event_name]:
            self.handlers[event_name].append(handler)
            self.logger.debug(f"Registered handler for event: {event_name}")
        else:
            self.logger.debug(f"Handler already registered for event: {event_name}")
        
    def unregister_handler(self, event_name, handler):
        """
        Unregister a handler for an event.
        
        Args:
            event_name: Name of the event
            handler: Handler to unregister
            
        Returns:
            bool: Whether the handler was unregistered
        """
        if event_name in self.handlers and handler in self.handlers[event_name]:
            self.handlers[event_name].remove(handler)
            self.logger.debug(f"Unregistered handler for event: {event_name}")
            return True
        return False
        
    async def dispatch(self, event_name, *args, **kwargs):
        """
        Dispatch an event to all registered handlers.
        
        Args:
            event_name: Name of the event
            *args: Positional arguments for handlers
            **kwargs: Keyword arguments for handlers
            
        Returns:
            List: Results from all handlers
        """
        if event_name not in self.handlers:
            self.logger.debug(f"No handlers registered for event: {event_name}")
            return []
            
        results = []
        for handler in self.handlers[event_name]:
            try:
                result = await handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                error_details = traceback.format_exc()
                self.logger.error(f"Error in event handler for {event_name}: {e}")
                self.logger.debug(f"Exception details: {error_details}")
                results.append(None)
                
        return results

    def get_handler_count(self, event_name=None):
        """
        Get the number of handlers for an event or total handlers.
        
        Args:
            event_name: Optional event name to check
            
        Returns:
            int: Number of handlers
        """
        if event_name:
            return len(self.handlers.get(event_name, []))
        
        # Count all handlers across all events
        return sum(len(handlers) for handlers in self.handlers.values())
        
    def clear_handlers(self, event_name=None):
        """
        Clear all handlers for an event or all events.
        
        Args:
            event_name: Optional event name to clear handlers for
            
        Returns:
            int: Number of handlers cleared
        """
        if event_name:
            handler_count = len(self.handlers.get(event_name, []))
            if event_name in self.handlers:
                del self.handlers[event_name]
                self.logger.debug(f"Cleared all handlers for event: {event_name}")
            return handler_count
            
        # Clear all handlers
        handler_count = self.get_handler_count()
        self.handlers = {}
        self.logger.debug(f"Cleared all event handlers ({handler_count} total)")
        return handler_count

# Global instance for easy access
global_dispatcher = EventDispatcher()

def get_dispatcher():
    """
    Get the global event dispatcher instance.
    
    Returns:
        EventDispatcher: Global event dispatcher instance
    """
    return global_dispatcher