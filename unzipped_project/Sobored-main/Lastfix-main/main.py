"""
Replit entrypoint for the Discord bot

This launches the Discord bot using replit_run.py, which provides
the proper cog loading and environment initialization.
"""

import subprocess
import sys
import os
import logging

# Set up logging for this script
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_bot():
    """Start the Discord bot via subprocess."""
    try:
        # Make sure required environment variables are set
        if not os.environ.get("DISCORD_TOKEN"):
            logger.error("DISCORD_TOKEN environment variable is not set. Bot cannot start.")
            return
        
        if not os.environ.get("MONGODB_URI"):
            logger.warning("MONGODB_URI environment variable is not set. Database features will be limited.")
        
        # Start the bot using replit_run.py
        logger.info("Starting Discord bot via replit_run.py...")
        result = subprocess.run(
            ["python", "replit_run.py"],
            capture_output=False,  # Allow output to go to console
            text=True
        )
        
        # Check the return code
        if result.returncode != 0:
            logger.error(f"Bot process exited with code {result.returncode}")
        else:
            logger.info("Bot process exited normally")
    
    except Exception as e:
        logger.error(f"Error starting bot process: {e}")
        

if __name__ == "__main__":
    print("Starting Discord bot with all cogs loaded...")
    start_bot()
    print("Discord bot process has exited.")