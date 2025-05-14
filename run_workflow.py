"""
This script sets up the Discord bot workflow.
"""

import os
import subprocess
import time

# Make sure the run script is executable
if os.path.exists("./run"):
    os.chmod("./run", 0o755)

# Define the command to start the bot
cmd = "./run"

# Run the bot
print("Starting Discord bot...")
process = subprocess.Popen(cmd, shell=True)

try:
    # Keep the script running
    while True:
        # Check if the process is still running
        if process.poll() is not None:
            print("Bot process terminated. Restarting...")
            process = subprocess.Popen(cmd, shell=True)
        
        # Sleep to avoid high CPU usage
        time.sleep(10)
except KeyboardInterrupt:
    # Clean shutdown on keyboard interrupt
    print("Shutting down...")
    process.terminate()
    process.wait()