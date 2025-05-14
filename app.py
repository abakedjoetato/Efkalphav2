"""
Enhanced entry point for Replit to start the Discord bot

This file satisfies Replit's expectations for a web service while
actually running our Discord bot in a background process.
"""

import os
import sys
import time
import signal
import logging
import subprocess
import threading
from flask import Flask, render_template_string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("app_launcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables
bot_process = None
output_buffer = []
MAX_OUTPUT_LINES = 1000

# Create Flask app
app = Flask(__name__)

# HTML template for web interface
TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Discord Bot Status</title>
    <meta http-equiv="refresh" content="30">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #5865F2;
            text-align: center;
            margin-bottom: 30px;
        }
        .status {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        .output {
            background-color: #2C2F33;
            color: #ffffff;
            padding: 15px;
            border-radius: 5px;
            font-family: monospace;
            height: 500px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .running {
            color: #57F287;
            font-weight: bold;
        }
        .stopped {
            color: #ED4245;
            font-weight: bold;
        }
        .info {
            margin-top: 20px;
            font-size: 14px;
            color: #555;
        }
    </style>
</head>
<body>
    <h1>Discord Bot Status</h1>
    <div class="status">
        <h2>Bot Status: <span class="{{ 'running' if is_running else 'stopped' }}">{{ 'Running' if is_running else 'Stopped' }}</span></h2>
        <p>Started at: {{ start_time }}</p>
        <p>Uptime: {{ uptime }}</p>
    </div>
    <h3>Bot Output:</h3>
    <div class="output">{{ output }}</div>
    <div class="info">
        <p>This page refreshes automatically every 30 seconds.</p>
        <p>The Discord bot runs in a background process and will continue running even if this page is closed.</p>
    </div>
</body>
</html>
"""

def start_discord_bot():
    """
    Start the Discord bot in a subprocess
    """
    global bot_process, output_buffer
    
    if bot_process is not None:
        logger.info("Bot is already running, not starting another instance")
        return
    
    try:
        # Clear output buffer
        output_buffer = []
        
        # Start the bot using the run_workflow.py script
        cmd = [sys.executable, "run_workflow.py"]
        logger.info(f"Starting Discord bot with command: {' '.join(cmd)}")
        
        # Create bot process
        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Start thread to log output
        threading.Thread(target=log_output, daemon=True).start()
        
        logger.info("Discord bot started")
    
    except Exception as e:
        logger.error(f"Failed to start Discord bot: {e}")
        if bot_process:
            try:
                bot_process.terminate()
            except:
                pass
            bot_process = None

def log_output():
    """Function to continuously read and log output from the bot process"""
    global bot_process, output_buffer
    
    if bot_process is None:
        return
    
    try:
        # Read stdout
        for line in bot_process.stdout:
            line = line.rstrip()
            logger.info(f"[BOT] {line}")
            
            # Add to output buffer
            output_buffer.append(line)
            
            # Trim buffer if it gets too large
            if len(output_buffer) > MAX_OUTPUT_LINES:
                output_buffer = output_buffer[-MAX_OUTPUT_LINES:]
        
        # Read stderr
        for line in bot_process.stderr:
            line = line.rstrip()
            logger.error(f"[BOT-ERR] {line}")
            
            # Add to output buffer
            output_buffer.append(f"ERROR: {line}")
            
            # Trim buffer if it gets too large
            if len(output_buffer) > MAX_OUTPUT_LINES:
                output_buffer = output_buffer[-MAX_OUTPUT_LINES:]
    
    except Exception as e:
        logger.error(f"Error reading bot output: {e}")
    
    finally:
        # Check if process has exited
        if bot_process.poll() is not None:
            logger.info(f"Bot process exited with code {bot_process.returncode}")
            global bot_process_start_time
            bot_process_start_time = None

def cleanup(signum, frame):
    """
    Cleanup function to terminate the bot process when this script is stopped
    """
    global bot_process
    
    logger.info(f"Received signal {signum}, shutting down")
    
    if bot_process:
        logger.info("Terminating bot process")
        try:
            bot_process.terminate()
            bot_process.wait(timeout=5)
        except:
            logger.error("Failed to terminate bot process gracefully, killing")
            try:
                bot_process.kill()
            except:
                pass
    
    logger.info("Cleanup complete")
    sys.exit(0)

def get_uptime():
    """Get uptime of the bot process"""
    global bot_process_start_time
    
    if bot_process_start_time is None:
        return "Not running"
    
    uptime_seconds = int(time.time() - bot_process_start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} days")
    if hours > 0:
        parts.append(f"{hours} hours")
    if minutes > 0:
        parts.append(f"{minutes} minutes")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} seconds")
    
    return ", ".join(parts)

def is_bot_running():
    """Check if the bot process is running"""
    global bot_process
    
    if bot_process is None:
        return False
    
    return bot_process.poll() is None

@app.route('/')
def index():
    """Root route to display bot status"""
    global output_buffer, bot_process_start_time
    
    return render_template_string(
        TEMPLATE,
        is_running=is_bot_running(),
        start_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(bot_process_start_time)) if bot_process_start_time else "Not started",
        uptime=get_uptime(),
        output="\n".join(output_buffer)
    )

# Initialize bot process start time
bot_process_start_time = None

def start_server():
    """
    Function for Replit to call
    """
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    # Start the Discord bot
    global bot_process_start_time
    bot_process_start_time = time.time()
    threading.Thread(target=start_discord_bot, daemon=True).start()
    
    # Give the bot a moment to start
    time.sleep(2)
    
    # Return the Flask app
    return app

# Create app for Replit
app = start_server()

# If this script is run directly, start the Flask server
if __name__ == "__main__":
    # Start Flask server on port 8080
    app.run(host='0.0.0.0', port=8080)