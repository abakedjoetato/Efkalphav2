#!/usr/bin/env python3
"""
Main entry point for the Discord bot in Replit environment.
This file is used by the Run button in Replit.
"""
import os
import sys
import logging
import asyncio
import traceback

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

async def main():
    """
    Main entry point for running the bot in Replit
    """
    logger.info("Starting Discord Bot in Replit environment...")
    
    # Use the direct bot implementation for maximum compatibility
    try:
        # Add the current directory to the path to ensure imports work
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        # First check if we have the required environment variables
        if not os.getenv("DISCORD_TOKEN"):
            logger.error("DISCORD_TOKEN not found in environment variables")
            print("Error: DISCORD_TOKEN is missing. Please add it in the Secrets tab.")
            return 1
            
        if not os.getenv("MONGODB_URI"):
            logger.warning("MONGODB_URI not found in environment variables, database functionality will be limited")
            print("Warning: MONGODB_URI is missing. Database functionality will be limited.")
        
        # Import and run the bootstrap script
        import bootstrap
        
        # Set up the environment
        logger.info("Setting up environment...")
        bootstrap.setup_environment()
        
        # Import and run the direct bot
        logger.info("Importing direct_bot...")
        import direct_bot
        
        logger.info("Starting direct_bot main function...")
        await direct_bot.main()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        traceback.print_exc()
        return 1
        
    return 0

def run_bot():
    """Run the bot synchronously"""
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
        return 0
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(run_bot())