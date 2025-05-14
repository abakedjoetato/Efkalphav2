"""
Fixed Bot Runner Script

This script provides a clean way to run the Discord bot with
proper error handling and setup of the environment.
"""

import os
import sys
import time
import logging
import argparse
import asyncio
import signal
import subprocess
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("run_fixed.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot process
bot_process = None

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    logger.info(f"Received signal {sig}, shutting down...")
    if bot_process:
        logger.info("Terminating bot process...")
        bot_process.terminate()
    sys.exit(0)

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Signal handlers set up")

async def check_environment():
    """Check if the environment is properly set up"""
    # Check for Discord token
    if not os.environ.get("DISCORD_TOKEN"):
        logger.warning("DISCORD_TOKEN environment variable not set")
        return False
    
    # Check for directories
    required_dirs = ["cogs", "utils"]
    for dir_name in required_dirs:
        if not os.path.isdir(dir_name):
            logger.warning(f"Required directory '{dir_name}' not found")
            return False
    
    # Check for required files
    required_files = [
        "main_bot.py",
        "bot_adapter.py",
        "discord_compat_layer.py",
        "utils/error_telemetry.py",
        "utils/mongodb_adapter.py",
        "utils/premium_manager_enhanced.py",
        "cogs/error_handling.py",
        "cogs/basic_commands.py"
    ]
    
    for file_path in required_files:
        if not os.path.isfile(file_path):
            logger.warning(f"Required file '{file_path}' not found")
            return False
    
    logger.info("Environment check passed")
    return True

def run_bot(prefix: str = "!", debug_guilds: Optional[List[int]] = None):
    """Run the bot process"""
    global bot_process
    
    cmd = [sys.executable, "main_bot.py"]
    
    # Add command-line arguments
    if prefix != "!":
        cmd.extend(["--prefix", prefix])
    
    if debug_guilds:
        for guild_id in debug_guilds:
            cmd.extend(["--debug-guild", str(guild_id)])
    
    logger.info(f"Starting bot with command: {' '.join(cmd)}")
    
    try:
        # Start bot process
        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Create tasks to read output
        async def read_stream(stream, name):
            while True:
                line = stream.readline()
                if not line:
                    break
                logger.info(f"[{name}] {line.rstrip()}")
        
        # Create asyncio tasks to monitor stdout and stderr
        loop = asyncio.get_event_loop()
        stdout_task = loop.create_task(read_stream(bot_process.stdout, "STDOUT"))
        stderr_task = loop.create_task(read_stream(bot_process.stderr, "STDERR"))
        
        # Wait for process to finish
        return_code = bot_process.wait()
        
        # Cancel tasks
        stdout_task.cancel()
        stderr_task.cancel()
        
        logger.info(f"Bot process exited with code {return_code}")
        
        return return_code
    
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        return 1

async def main_async():
    """Async main function"""
    # Check environment
    env_ok = await check_environment()
    if not env_ok:
        logger.error("Environment check failed")
        return 1
    
    # Parse arguments
    parser = argparse.ArgumentParser(description="Run the Discord bot")
    parser.add_argument("--prefix", type=str, default="!", help="Command prefix")
    parser.add_argument("--debug-guild", type=int, action="append", help="Debug guild ID (can be used multiple times)")
    args = parser.parse_args()
    
    # Set up signal handlers
    setup_signal_handlers()
    
    # Run bot in a separate process
    return run_bot(args.prefix, args.debug_guild)

def main():
    """Main entry point"""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(main_async())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())