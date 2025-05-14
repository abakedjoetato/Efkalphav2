"""
Run Workflow

This script sets up and runs the Discord bot in a controlled manner,
with proper handling of startup, shutdown, and errors.
"""

import os
import sys
import time
import logging
import signal
import asyncio
import subprocess
import traceback

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

# Global flag for graceful shutdown
SHUTDOWN_REQUESTED = False

def signal_handler(sig, frame):
    """Handle termination signals gracefully"""
    global SHUTDOWN_REQUESTED
    if not SHUTDOWN_REQUESTED:
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        SHUTDOWN_REQUESTED = True
    else:
        logger.warning(f"Received signal {sig} again, forcing exit...")
        sys.exit(1)

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Signal handlers set up")

async def check_prerequisites():
    """Check if prerequisites are met"""
    # Check if python is available
    try:
        subprocess.run(["python", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info("Python is available")
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Python is not available")
        return False
    
    # Check if py-cord is installed
    try:
        import discord
        logger.info(f"py-cord is installed (version: {discord.__version__})")
    except ImportError:
        logger.error("py-cord is not installed")
        return False
    
    # Check if MongoDB connection is available
    if "MONGODB_URI" in os.environ:
        logger.info("MongoDB URI is set")
    else:
        logger.warning("MongoDB URI is not set, database features will be disabled")
    
    # Check if Discord token is set
    if "DISCORD_TOKEN" in os.environ:
        logger.info("Discord token is set")
    else:
        logger.error("Discord token is not set")
        return False
    
    return True

async def run_bot():
    """Run the bot process"""
    logger.info("Starting bot process...")
    
    # Check if the main bot file exists
    if not os.path.isfile("main_bot.py"):
        logger.error("main_bot.py not found")
        return False
    
    # Start the bot process
    process = None
    try:
        # Using asyncio subprocess to manage the process
        process = await asyncio.create_subprocess_exec(
            "python", "main_bot.py",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        logger.info(f"Bot process started with PID {process.pid}")
        
        # Set up asynchronous reading of stdout and stderr
        async def read_stream(stream, name):
            while True:
                line = await stream.readline()
                if not line:
                    break
                logger.info(f"[{name}] {line.decode().rstrip()}")
        
        # Create tasks for reading stdout and stderr
        stdout_task = asyncio.create_task(read_stream(process.stdout, "STDOUT"))
        stderr_task = asyncio.create_task(read_stream(process.stderr, "STDERR"))
        
        # Wait for process to complete or shutdown request
        while not SHUTDOWN_REQUESTED and process.returncode is None:
            await asyncio.sleep(1)
        
        # If shutdown was requested, terminate the process
        if SHUTDOWN_REQUESTED and process.returncode is None:
            logger.info("Terminating bot process...")
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
                logger.info("Bot process terminated gracefully")
            except asyncio.TimeoutError:
                logger.warning("Bot process did not terminate within timeout, killing...")
                process.kill()
                await process.wait()
                logger.info("Bot process killed")
        
        # Wait for stdout/stderr reader tasks to complete
        await stdout_task
        await stderr_task
        
        # Get process return code
        return_code = process.returncode
        logger.info(f"Bot process exited with code {return_code}")
        return return_code == 0
        
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        logger.error(traceback.format_exc())
        
        # Ensure process is terminated
        if process and process.returncode is None:
            try:
                process.terminate()
                await asyncio.sleep(2)
                if process.returncode is None:
                    process.kill()
            except Exception:
                pass
        
        return False

async def main():
    """Main workflow function"""
    logger.info("Starting workflow...")
    
    # Set up signal handlers
    setup_signal_handlers()
    
    # Check prerequisites
    prereqs_ok = await check_prerequisites()
    if not prereqs_ok:
        logger.error("Prerequisites check failed")
        return 1
    
    # Run the bot
    success = await run_bot()
    
    if success:
        logger.info("Workflow completed successfully")
        return 0
    else:
        logger.error("Workflow failed")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by keyboard")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unhandled exception in workflow: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)