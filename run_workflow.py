"""
Run Workflow

This script sets up and runs the Discord bot in a controlled manner,
with proper handling of startup, shutdown, and errors.
"""

import os
import sys
import time
import signal
import asyncio
import logging
import datetime
import traceback
import subprocess
from typing import Optional, List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("workflow.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global bot process
bot_process = None

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    logger.info(f"Received signal {sig}, shutting down...")
    if bot_process:
        logger.info("Terminating bot process")
        bot_process.terminate()
    sys.exit(0)

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Signal handlers set up")

async def check_prerequisites():
    """Check if prerequisites are met"""
    # Check for Discord token
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set")
        return False
    
    # Check required directories
    for dir_name in ["cogs", "utils"]:
        if not os.path.isdir(dir_name):
            logger.error(f"Required directory '{dir_name}' not found")
            return False
    
    # Check required files
    required_files = [
        "main_bot.py",
        "bot_adapter.py",
        "discord_compat_layer.py"
    ]
    
    for file_path in required_files:
        if not os.path.isfile(file_path):
            logger.error(f"Required file '{file_path}' not found")
            return False
    
    logger.info("All prerequisites met")
    return True

async def run_bot():
    """Run the bot process"""
    global bot_process
    
    try:
        # Build command
        cmd = [sys.executable, "main_bot.py"]
        
        # Run the bot
        logger.info(f"Starting bot with command: {' '.join(cmd)}")
        
        # Start bot process
        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Set up stream readers
        async def read_stream(stream, name):
            try:
                while True:
                    line = stream.readline()
                    if not line:
                        break
                    logger.info(f"[{name}] {line.rstrip()}")
            except Exception as e:
                logger.error(f"Error reading from {name}: {e}")
        
        # Create tasks to read from stdout and stderr
        stdout_task = asyncio.create_task(read_stream(bot_process.stdout, "STDOUT"))
        stderr_task = asyncio.create_task(read_stream(bot_process.stderr, "STDERR"))
        
        # Wait for tasks to complete or for process to exit
        await asyncio.gather(stdout_task, stderr_task)
        
        # Get process exit code
        exit_code = bot_process.wait()
        logger.info(f"Bot process exited with code {exit_code}")
        
        return exit_code
    
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        traceback.print_exc()
        return 1

async def main():
    """Main workflow function"""
    # Set up signal handlers
    setup_signal_handlers()
    
    # Check prerequisites
    if not await check_prerequisites():
        logger.error("Prerequisites check failed")
        return 1
    
    try:
        # Run the bot
        return await run_bot()
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        return 0
    
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Run the main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)