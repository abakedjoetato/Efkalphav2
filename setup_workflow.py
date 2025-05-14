"""
Setup Workflow Script

This script sets up the workflow for the Discord bot in Replit.
It creates the necessary configuration files, directories,
and installs required dependencies.
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("setup_workflow.log")
    ]
)

logger = logging.getLogger("setup_workflow")

def create_replit_file():
    """Create the .replit configuration file"""
    replit_config = {
        "run": "python3 app.py",
        "language": "python3",
        "entrypoint": "app.py",
        "hidden": [
            ".git",
            ".gitignore",
            "venv",
            ".config",
            "**/__pycache__",
            "**/.mypy_cache",
            "**/*.pyc"
        ],
        "packager": {
            "features": {}
        },
        "compile": {
            "watch": {
                "ignore": [
                    "logs/"
                ]
            }
        }
    }
    
    with open(".replit", "w") as f:
        json.dump(replit_config, f, indent=2)
        
    logger.info("Created .replit configuration file")

def create_env_file():
    """Create a template .env file if it doesn't exist"""
    if not os.path.exists(".env"):
        with open(".env", "w") as f:
            f.write("""# Discord Bot Configuration
# Replace these with your actual values

# Required
DISCORD_TOKEN=your_discord_bot_token_here

# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017/discordbot
DB_NAME=discordbot

# Logging Configuration
LOG_LEVEL=INFO

# Premium Configuration
DEFAULT_PREMIUM_DURATION=30
""")
        
        logger.info("Created template .env file")
    else:
        logger.info(".env file already exists, skipping")

def create_requirements_file():
    """Create the requirements.txt file"""
    requirements = [
        "python-dotenv",
        "py-cord",
        "motor",
        "pymongo",
        "dnspython",
        "paramiko",
        "matplotlib",
        "numpy",
        "pandas",
        "psutil",
        "aiohttp",
        "aiofiles",
        "pytz"
    ]
    
    with open("requirements.txt", "w") as f:
        for req in requirements:
            f.write(f"{req}\n")
            
    logger.info("Created requirements.txt file")

def create_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        "logs",
        "cogs",
        "utils",
        "models",
        "static",
        "templates"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        
    logger.info(f"Created {len(directories)} directories")

def install_dependencies():
    """Install required dependencies"""
    try:
        logger.info("Installing dependencies...")
        
        # Install requirements
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        
        logger.info("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Set up the Discord bot workflow")
    parser.add_argument("--skip-install", action="store_true", help="Skip installing dependencies")
    parser.add_argument("--create-replit", action="store_true", help="Create .replit file (not recommended on Replit)")
    args = parser.parse_args()
    
    logger.info("Setting up Discord bot workflow")
    
    # Create configuration files
    if args.create_replit:
        try:
            create_replit_file()
        except Exception as e:
            logger.error(f"Failed to create .replit file: {e}")
            
    create_env_file()
    create_requirements_file()
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not args.skip_install:
        success = install_dependencies()
        if not success:
            logger.error("Failed to set up workflow due to dependency installation failure")
            return 1
    else:
        logger.info("Skipping dependency installation")
    
    logger.info("Workflow setup complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())