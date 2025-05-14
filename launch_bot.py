"""
Launch Bot

This script launches the Discord bot with all fixes applied.
"""

import os
import sys
import logging
import subprocess
import importlib
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LaunchBot")

# Load environment variables
load_dotenv()

def check_token():
    """Check if the Discord token is available."""
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        logger.error("DISCORD_TOKEN environment variable not set")
        return False
    return True

def run_install_pycord():
    """Run the install_pycord.py script."""
    logger.info("Running install_pycord.py...")
    
    try:
        result = subprocess.run(
            [sys.executable, "install_pycord.py"],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Print the output
        for line in result.stdout.splitlines():
            logger.info(f"install_pycord.py: {line}")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run install_pycord.py: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def run_patch_cogs():
    """Run the patch_cogs.py script."""
    logger.info("Running patch_cogs.py...")
    
    try:
        result = subprocess.run(
            [sys.executable, "patch_cogs.py"],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Print the output
        for line in result.stdout.splitlines():
            logger.info(f"patch_cogs.py: {line}")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run patch_cogs.py: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def run_bot():
    """Run the Discord bot."""
    logger.info("Starting Discord bot...")
    
    try:
        # First try running using the adapter
        logger.info("Running with discord_adapter.py...")
        subprocess.run(
            [sys.executable, "discord_adapter.py"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run discord_adapter.py: {e}")
        
        # Try running the original bot.py
        try:
            logger.info("Trying to run original bot.py...")
            subprocess.run(
                [sys.executable, "bot.py"],
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to run bot.py: {e}")
            return False
    
    return True

def main():
    """Main entry point."""
    logger.info("Starting bot launch sequence")
    
    # Check if the token is available
    if not check_token():
        return False
    
    # Run the install_pycord.py script
    if not run_install_pycord():
        logger.warning("Failed to install py-cord, continuing anyway...")
    
    # Run the patch_cogs.py script
    if not run_patch_cogs():
        logger.warning("Failed to patch cogs, continuing anyway...")
    
    # Run the bot
    if not run_bot():
        logger.error("Failed to run bot")
        return False
    
    logger.info("Bot launch sequence completed")
    return True

if __name__ == "__main__":
    main()