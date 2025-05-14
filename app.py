"""
Enhanced entry point for Replit to start the Discord bot

This file satisfies Replit's expectations for a web service while
actually running our Discord bot in a background process.
"""

import os
import sys
import signal
import subprocess
import threading
import time
import logging
import traceback
from datetime import datetime

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
bot_process = None
log_thread = None
stop_log_thread = False
start_time = datetime.now()

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
    cmd = ["./run_fixed"]
    
    logger.info(f"Starting Discord bot process: {' '.join(cmd)}")
    
    try:
        # Make the script executable if it isn't already
        if not os.access("run_fixed", os.X_OK):
            os.chmod("run_fixed", 0o755)
            logger.info("Made run_fixed executable")
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Check if Discord token exists
        if not os.getenv("DISCORD_TOKEN"):
            logger.critical("DISCORD_TOKEN environment variable is not set")
            return False
        
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
        logger.error(traceback.format_exc())
        return False
    
def log_output():
    """Function to continuously read and log output from the bot process"""
    global bot_process, stop_log_thread
    
    logger.info("Started log output thread")
    
    # Open a log file for the bot output
    log_file = open("bot_output.log", "a", encoding="utf-8")
    
    while not stop_log_thread and bot_process and bot_process.poll() is None:
        try:
            # Read a line from the process output
            line = bot_process.stdout.readline()
            
            if line:
                # Log and print the output
                line = line.rstrip()
                print(line)
                
                # Write to log file with timestamp
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"[{timestamp}] {line}\n")
                log_file.flush()  # Ensure it's written immediately
            else:
                # No more output, check if the process is still running
                if bot_process.poll() is not None:
                    break
                    
                # Small delay to avoid spinning
                time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error reading bot output: {e}")
            time.sleep(1)
    
    # Close the log file
    log_file.close()
            
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
            logger.info(f"Terminating bot process (PID {bot_process.pid})...")
            bot_process.terminate()
            try:
                bot_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Bot process did not exit gracefully, force killing")
                bot_process.kill()
        except Exception as e:
            logger.error(f"Error stopping bot process: {e}")
    
    # Calculate runtime
    runtime = datetime.now() - start_time
    logger.info(f"Bot ran for {runtime}")
            
    sys.exit(0)

def start_server():
    """
    Function for Replit to call
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
# This will be imported by Replit to run the app
app = type('App', (), {'run': start_server})()

if __name__ == "__main__":
    start_server()