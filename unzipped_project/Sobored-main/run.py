#!/usr/bin/env python3
"""
Main entry point for the Discord bot.
This file should be run directly to start the bot.
"""
import os
import sys
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """
    Main entry point for running the bot
    """
    logger.info("Starting Discord Bot...")
    
    # Use the direct bot implementation for maximum compatibility
    try:
        # Add the current directory to the path to ensure imports work
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Import and run the direct bot implementation
        import direct_bot
        
        logger.info("Using direct Discord bot implementation...")
        direct_bot.main()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())