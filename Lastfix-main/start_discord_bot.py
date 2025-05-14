"""
Discord Bot Launcher for Replit

This script is specifically designed to be used with Replit's workflow system.
It launches the Discord bot with proper error handling and monitoring.
"""

import os
import sys
import logging
import asyncio
import subprocess
import signal
import time
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables
BOT_PROCESS = None
SHUTDOWN_REQUESTED = False

def handle_sigterm(signum, frame):
    """Handle SIGTERM signal to gracefully shutdown the bot"""
    global SHUTDOWN_REQUESTED
    logger.info("Received termination signal, shutting down bot...")
    SHUTDOWN_REQUESTED = True
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        try:
            BOT_PROCESS.terminate()
            # Give it some time to terminate gracefully
            time.sleep(2)
            if BOT_PROCESS.poll() is None:
                BOT_PROCESS.kill()
        except Exception as e:
            logger.error(f"Error terminating bot process: {e}")

def start_bot():
    """Start the Discord bot as a subprocess and monitor it"""
    global BOT_PROCESS
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)
    
    # Check for required environment variables
    if not os.environ.get("DISCORD_TOKEN"):
        logger.error("DISCORD_TOKEN environment variable is not set. Bot cannot start.")
        sys.exit(1)
    
    if not os.environ.get("MONGODB_URI"):
        logger.warning("MONGODB_URI environment variable is not set. Database features will be limited.")
    
    # Log start information
    logger.info(f"Starting Discord bot on {datetime.now().isoformat()}")
    
    try:
        # Start the bot using replit_run.py
        BOT_PROCESS = subprocess.Popen(
            ["python", "replit_run.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Log process output
        while BOT_PROCESS and BOT_PROCESS.poll() is None and not SHUTDOWN_REQUESTED:
            # Add a small sleep to prevent high CPU usage
            time.sleep(0.1)
            
            if BOT_PROCESS and BOT_PROCESS.stdout:
                try:
                    line = BOT_PROCESS.stdout.readline()
                    if line:
                        print(line.rstrip())
                except Exception as e:
                    logger.error(f"Error reading output: {e}")
                    break
            
        # Check exit status
        exit_code = BOT_PROCESS.returncode
        if exit_code == 0:
            logger.info("Bot process exited normally")
        else:
            logger.warning(f"Bot process exited with code {exit_code}")
        
        BOT_PROCESS = None
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down.")
        if BOT_PROCESS and BOT_PROCESS.poll() is None:
            BOT_PROCESS.terminate()
    except Exception as e:
        logger.error(f"Error starting or monitoring bot process: {e}")
        if BOT_PROCESS and BOT_PROCESS.poll() is None:
            BOT_PROCESS.terminate()

if __name__ == "__main__":
    start_bot()