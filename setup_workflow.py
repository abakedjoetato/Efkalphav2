"""
Setup workflow for the Discord bot in Replit environment
"""

import os
import sys
import logging
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("setup_workflow.log")
    ]
)

logger = logging.getLogger(__name__)

def setup_environment():
    """Set up the environment for the Discord bot"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    logger.info("Created logs directory")
    
    # Ensure run_replit.sh is executable
    try:
        os.chmod("run_replit.sh", 0o755)
        logger.info("Made run_replit.sh executable")
    except Exception as e:
        logger.error(f"Failed to make run_replit.sh executable: {e}")
        
    # Create .env file if it doesn't exist
    if not os.path.exists(".env"):
        try:
            with open(".env", "w") as f:
                f.write("# Discord Bot Environment Variables\n")
                f.write("# Add your configuration here\n")
                f.write("\n")
                f.write("# Discord Bot Token\n")
                f.write("# DISCORD_TOKEN=your_token_here\n")
                f.write("\n")
                f.write("# MongoDB Connection URI\n")
                f.write("# MONGODB_URI=your_mongodb_uri_here\n")
                f.write("\n")
                f.write("# Debug Mode\n")
                f.write("DEBUG=false\n")
                
            logger.info("Created .env file template")
        except Exception as e:
            logger.error(f"Failed to create .env file: {e}")
    
    # Verify file permissions
    try:
        os.chmod("app.py", 0o755)
        logger.info("Made app.py executable")
    except Exception as e:
        logger.error(f"Failed to make app.py executable: {e}")
        
    logger.info("Environment setup complete")

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        "py-cord", "motor", "pymongo", "dnspython", "python-dotenv",
        "aiohttp", "aiofiles", "asyncio", "asyncssh", "paramiko", 
        "pytz", "requests", "pydantic", "pillow", "psutil"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
            
    if missing_packages:
        logger.warning(f"Missing packages: {', '.join(missing_packages)}")
        try:
            pip_command = [sys.executable, "-m", "pip", "install"] + missing_packages
            subprocess.check_call(pip_command)
            logger.info(f"Installed missing packages: {', '.join(missing_packages)}")
        except Exception as e:
            logger.error(f"Failed to install missing packages: {e}")
    else:
        logger.info("All required packages are installed")

def main():
    """Main entry point"""
    logger.info("Setting up Discord bot workflow")
    
    # Set up environment
    setup_environment()
    
    # Check dependencies
    check_dependencies()
    
    logger.info("Discord bot workflow setup complete")
    logger.info("Run the bot with: python app.py")

if __name__ == "__main__":
    main()