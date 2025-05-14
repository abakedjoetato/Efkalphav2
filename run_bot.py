"""
Discord Bot Runner

This module serves as the primary entry point for running the Discord bot.
It handles initialization, error handling, and proper shutdown.
"""

import os
import sys
import asyncio
import logging
import traceback
import signal
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure proper directory structure
sys.path.insert(0, os.path.abspath('.'))

# Import bot adapter
try:
    from bot_adapter import create_bot
    logger.info("Successfully imported bot_adapter")
except ImportError as e:
    logger.critical(f"Failed to import bot_adapter: {e}")
    sys.exit(1)

# Check if discord token exists
if not os.getenv("DISCORD_TOKEN"):
    logger.critical("DISCORD_TOKEN environment variable is not set")
    sys.exit(1)

# Global variables
bot = None
shutdown_event = asyncio.Event()

def signal_handler(sig, frame):
    """Handle termination signals"""
    logger.info(f"Received signal {sig}, shutting down...")
    shutdown_event.set()

async def main():
    """Main entry point for the bot"""
    global bot
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)
    
    # Initialize metrics and timing
    start_time = datetime.now()
    logger.info(f"Bot initialization started at {start_time}")
    
    try:
        # Create bot instance
        logger.info("Creating bot instance...")
        bot = create_bot()
        
        # Start bot in the background
        logger.info("Starting bot...")
        bot_task = asyncio.create_task(bot.start())
        
        # Wait for shutdown signal
        await shutdown_event.wait()
        logger.info("Shutdown signal received, cleaning up...")
        
        # Close bot properly
        if bot:
            logger.info("Closing bot...")
            await bot.close()
        
        # Cancel running tasks
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        
        return 0
        
    except Exception as e:
        logger.critical(f"Error in main function: {e}")
        logger.critical(traceback.format_exc())
        return 1
    
    finally:
        # Calculate run time
        end_time = datetime.now()
        run_time = end_time - start_time
        logger.info(f"Bot ran for {run_time}")

if __name__ == "__main__":
    # Set up asyncio policies for better Windows support
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run the bot
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, exiting...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)