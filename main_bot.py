"""
Main Bot Entry Point

This script initializes and runs the Discord bot using the adapter interface,
handling startup, shutdown, and error conditions properly.
"""

import os
import sys
import logging
import argparse
from bot_adapter import create_bot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("main_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Run the Discord bot")
    parser.add_argument("--prefix", type=str, default="!", help="Command prefix")
    parser.add_argument("--token", type=str, help="Discord bot token (default: DISCORD_TOKEN env var)")
    parser.add_argument("--debug-guild", type=int, action="append", help="Debug guild ID (can be used multiple times)")
    parser.add_argument("--description", type=str, help="Bot description")
    
    return parser.parse_args()

def main():
    """Main entry point for the bot"""
    try:
        # Parse command-line arguments
        args = parse_args()
        
        # Create the bot
        bot = create_bot(
            token=args.token,
            command_prefix=args.prefix,
            description=args.description,
            debug_guilds=args.debug_guild
        )
        
        # Check for token
        if not bot.token:
            logger.error("No Discord token provided. Please set the DISCORD_TOKEN environment variable or use --token.")
            return 1
        
        logger.info(f"Starting bot with prefix: {args.prefix}")
        
        # Run the bot
        bot.run()
        
        return 0
    
    except Exception as e:
        logger.exception(f"Critical error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())