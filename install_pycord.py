"""
Install Py-cord

This script installs py-cord into the user's local Python environment.
"""

import os
import sys
import subprocess
import logging
import shutil
import tempfile
import site
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("InstallPycord")

def get_python_lib_dir():
    """
    Get the Python lib directory for the current user.
    """
    # Try to find .pythonlibs
    pythonlibs_path = Path(os.getcwd()) / ".pythonlibs"
    
    if pythonlibs_path.exists():
        # Find site-packages directory
        site_packages = list(pythonlibs_path.glob("**/site-packages"))
        if site_packages:
            return str(site_packages[0])
    
    # Fall back to site-packages
    return site.getsitepackages()[0]

def install_package(package_name, version=None):
    """
    Install a package using pip.
    
    Args:
        package_name: The name of the package to install
        version: The version of the package to install
    
    Returns:
        Whether the installation was successful
    """
    # Build the command
    cmd = [sys.executable, "-m", "pip", "install", "--user"]
    
    if version:
        cmd.append(f"{package_name}=={version}")
    else:
        cmd.append(package_name)
    
    # Run the command
    try:
        logger.info(f"Installing {package_name}{f' {version}' if version else ''}...")
        
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Successfully installed {package_name}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install {package_name}: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def uninstall_package(package_name):
    """
    Uninstall a package using pip.
    
    Args:
        package_name: The name of the package to uninstall
    
    Returns:
        Whether the uninstallation was successful
    """
    # Build the command
    cmd = [sys.executable, "-m", "pip", "uninstall", "-y", package_name]
    
    # Run the command
    try:
        logger.info(f"Uninstalling {package_name}...")
        
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"Successfully uninstalled {package_name}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to uninstall {package_name}: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False

def manual_install_pycord():
    """
    Manually install py-cord by downloading and extracting the wheel file.
    
    Returns:
        Whether the installation was successful
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Download py-cord
        logger.info("Downloading py-cord...")
        try:
            subprocess.run(
                [
                    sys.executable, "-m", "pip", "download",
                    "--no-deps", "--dest", tmp_dir, "py-cord==2.6.1"
                ],
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download py-cord: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False
        
        # Find the wheel file
        wheel_files = list(tmp_path.glob("*.whl"))
        if not wheel_files:
            logger.error("No wheel file found for py-cord")
            return False
        
        wheel_file = wheel_files[0]
        logger.info(f"Found wheel file: {wheel_file}")
        
        # Extract the wheel file
        try:
            import zipfile
            
            # Get the target directory
            target_dir = get_python_lib_dir()
            logger.info(f"Extracting to: {target_dir}")
            
            # Create the target directory if it doesn't exist
            os.makedirs(target_dir, exist_ok=True)
            
            # Extract the wheel file
            with zipfile.ZipFile(wheel_file, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            logger.info("Successfully extracted py-cord")
            return True
        except Exception as e:
            logger.error(f"Failed to extract py-cord: {e}")
            return False

def main():
    """Main entry point."""
    logger.info("Starting py-cord installation")
    
    # Try to uninstall discord.py first
    uninstall_package("discord.py")
    uninstall_package("discord")
    
    # Try to install py-cord using pip
    if install_package("py-cord", "2.6.1"):
        logger.info("Successfully installed py-cord using pip")
    else:
        # Try manual installation
        logger.info("Trying manual installation...")
        if manual_install_pycord():
            logger.info("Successfully installed py-cord manually")
        else:
            logger.error("Failed to install py-cord")
            return False
    
    # Verify installation
    try:
        import discord
        logger.info(f"Imported discord module from {getattr(discord, '__file__', 'unknown')}")
        
        if hasattr(discord, "__version__"):
            logger.info(f"Discord version: {discord.__version__}")
        
        if hasattr(discord, "ext"):
            logger.info("Discord module has ext attribute")
            
            # Try importing commands
            try:
                from discord.ext import commands
                logger.info("Successfully imported discord.ext.commands")
                
                # Check if it's py-cord
                if hasattr(commands.Bot, "slash_command"):
                    logger.info("Detected py-cord (has slash_command)")
                else:
                    logger.warning("Detected discord.py (no slash_command)")
            except ImportError as e:
                logger.error(f"Failed to import discord.ext.commands: {e}")
        else:
            logger.error("Discord module missing ext attribute")
    except ImportError as e:
        logger.error(f"Failed to import discord: {e}")
        return False
    
    logger.info("Py-cord installation completed")
    return True

if __name__ == "__main__":
    main()