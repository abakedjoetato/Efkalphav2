"""
Test script for the event dispatcher system
"""
import asyncio
import logging
from utils.event_dispatcher import EventDispatcher

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_events")

async def test_event_system():
    """
    Test the event dispatcher system functionality
    """
    logger.info("Testing event dispatcher system...")
    
    # Create event dispatcher
    dispatcher = EventDispatcher()
    
    # Define handlers
    async def handler1(data):
        logger.info(f"Handler 1 received: {data}")
        return "Result 1"
        
    async def handler2(data):
        logger.info(f"Handler 2 received: {data}")
        return "Result 2"
        
    async def error_handler(data):
        logger.info(f"Error handler received: {data}")
        raise ValueError("Test error in handler")
    
    # Register handlers
    dispatcher.register_handler("test_event", handler1)
    dispatcher.register_handler("test_event", handler2)
    dispatcher.register_handler("error_event", error_handler)
    
    # Dispatch event
    logger.info("Dispatching test_event...")
    results = await dispatcher.dispatch("test_event", {"message": "Hello world"})
    
    logger.info(f"Event results: {results}")
    
    # Test error handling
    logger.info("Testing error handling with error_event...")
    error_results = await dispatcher.dispatch("error_event", {"message": "This will cause an error"})
    
    logger.info(f"Error event results: {error_results}")
    
    # Test unregistering
    logger.info("Testing handler unregistration...")
    dispatcher.unregister_handler("test_event", handler1)
    
    # Dispatch again after unregistering handler1
    after_unreg_results = await dispatcher.dispatch("test_event", {"message": "After unregistration"})
    logger.info(f"After unregistration results: {after_unreg_results}")
    
    # Test handler counts
    logger.info(f"Handler count for 'test_event': {dispatcher.get_handler_count('test_event')}")
    logger.info(f"Total handler count: {dispatcher.get_handler_count()}")
    
    # Clear handlers and verify
    dispatcher.clear_handlers()
    logger.info(f"Handler count after clearing: {dispatcher.get_handler_count()}")
    
    logger.info("Event system tests completed successfully!")
    return True

if __name__ == "__main__":
    asyncio.run(test_event_system())