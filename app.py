"""
Minimal entry point for Replit to start the Discord bot

This file is just a shim to satisfy Replit's expectations
while launching the actual Discord bot process without Flask.
"""

import os
import sys
import signal
import subprocess
import threading
import time
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app_launcher.log")
    ]
)

logger = logging.getLogger("app_launcher")

# Global variables
bot_process: Optional[subprocess.Popen] = None
log_thread: Optional[threading.Thread] = None
stop_log_thread: bool = False

def start_discord_bot():
    """
    Start the Discord bot in a subprocess
    """
    global bot_process, log_thread, stop_log_thread
    
    # Kill any existing process
    if bot_process is not None:
        try:
            bot_process.terminate()
            bot_process.wait(timeout=5)
        except:
            try:
                bot_process.kill()
            except:
                pass
    
    # Reset thread flags
    stop_log_thread = True
    if log_thread is not None and log_thread.is_alive():
        log_thread.join(5)
    
    # Start the bot process
    cmd = ["./run_replit.sh"]
    
    logger.info(f"Starting Discord bot process: {' '.join(cmd)}")
    
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Start the bot process
        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )
        
        logger.info(f"Discord bot process started with PID {bot_process.pid}")
        
        # Start the log thread
        stop_log_thread = False
        log_thread = threading.Thread(target=log_output)
        log_thread.daemon = True
        log_thread.start()
        
        return True
    except Exception as e:
        logger.error(f"Failed to start Discord bot process: {e}")
        return False
    
def log_output():
    """Function to continuously read and log output from the bot process"""
    global bot_process, stop_log_thread
    
    logger.info("Started log output thread")
    
    while not stop_log_thread and bot_process and bot_process.poll() is None:
        try:
            # Read a line from the process output
            line = bot_process.stdout.readline()
            
            if line:
                # Log and print the output
                line = line.rstrip()
                print(line)
            else:
                # No more output, check if the process is still running
                if bot_process.poll() is not None:
                    break
                    
                # Small delay to avoid spinning
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error reading bot output: {e}")
            time.sleep(1)
            
    logger.info("Log output thread stopped")

def cleanup(signum, frame):
    """
    Cleanup function to terminate the bot process when this script is stopped
    """
    global bot_process, log_thread, stop_log_thread
    
    logger.info(f"Received signal {signum}, shutting down")
    
    # Stop the log thread
    stop_log_thread = True
    if log_thread is not None and log_thread.is_alive():
        log_thread.join(5)
        
    # Stop the bot process
    if bot_process is not None:
        try:
            bot_process.terminate()
            try:
                bot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Bot process did not exit gracefully, force killing")
                bot_process.kill()
        except Exception as e:
            logger.error(f"Error stopping bot process: {e}")
            
    sys.exit(0)

def start_server():
    """
    Dummy function for Replit to call
    """
    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    logger.info("App launcher starting")
    
    # Start the Discord bot
    start_discord_bot()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(60)
            
            # Check if the bot process is still running
            if bot_process is not None and bot_process.poll() is not None:
                logger.warning("Bot process has stopped, restarting")
                start_discord_bot()
    except KeyboardInterrupt:
        cleanup(signal.SIGINT, None)
        
    logger.info("App launcher exiting")

# For Flask/Replit compatibility
app = None

if __name__ == "__main__":
    start_server()