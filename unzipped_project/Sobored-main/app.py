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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Global process reference
bot_process = None

def start_discord_bot():
    """
    Start the Discord bot in a subprocess
    """
    global bot_process
    
    # Print banner
    logger.info("Starting Discord Bot...")
    logger.info("""
  _                 _   _____ _          ____        _   
 | |               | | |  __ (_)        |  _ \      | |  
 | |     __ _ ___  | |_| |  \\_ __  __  | |_) | ___ | |_ 
 | |    / _` / __| | __| | __| |\\ \\/ /  |  _ < / _ \\| __|
 | |___| (_| \\__ \\ | |_| |_\\ \\ | >  <   | |_) | (_) | |_ 
 |______\\__,_|___/  \\__|\\____/_|/_/\\_\\  |____/ \\___/ \\__|
                                                         
    """)
    
    # Start the bot in a subprocess
    # Check if direct_bot.py exists and use it, otherwise fall back to bot.py
    bot_script = "direct_bot.py" if os.path.exists("direct_bot.py") else "bot.py"
    logger.info(f"Using bot script: {bot_script}")
    
    cmd = ["python3", bot_script]
    bot_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1  # Line buffered
    )
    
    # Define function to read and log output from the bot process
    def log_output():
        """Function to continuously read and log output from the bot process"""
        while bot_process and bot_process.poll() is None:
            try:
                line = bot_process.stdout.readline()
                if line:
                    logger.info(f"[Bot] {line.rstrip()}")
            except Exception as e:
                logger.error(f"Error reading bot output: {e}")
                break
        
        logger.info("Bot process output reader terminated")
    
    # Set up a thread to continuously read and log output from the bot
    output_thread = threading.Thread(target=log_output)
    output_thread.daemon = True
    output_thread.start()
    
    logger.info(f"Started Discord bot subprocess with PID {bot_process.pid}")

def cleanup(signum, frame):
    """
    Cleanup function to terminate the bot process when this script is stopped
    """
    global bot_process
    
    logger.info(f"Received signal {signum}, shutting down bot process...")
    
    if bot_process:
        try:
            # Try to terminate gracefully
            bot_process.terminate()
            
            # Wait up to 5 seconds for process to terminate
            for _ in range(5):
                if bot_process.poll() is not None:
                    break
                time.sleep(1)
                
            # If process is still running, kill it forcefully
            if bot_process.poll() is None:
                logger.warning("Bot process did not terminate gracefully, killing...")
                bot_process.kill()
                
            logger.info("Bot process terminated")
        except Exception as e:
            logger.error(f"Error terminating bot process: {e}")
    
    # Exit this process
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# Start the bot when this module is imported
start_discord_bot()

# Define a simple function that Replit can use to "start a server"
def start_server():
    """
    Dummy function for Replit to call
    """
    logger.info("Server function called by Replit")
    
    # Just wait forever while the bot runs
    try:
        while bot_process and bot_process.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup(signal.SIGINT, None)
    
    logger.warning("Bot process has terminated!")
    
if __name__ == "__main__":
    start_server()