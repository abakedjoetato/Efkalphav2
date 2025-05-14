"""
Copy Files from Extracted Zip

This script copies important files from the extracted zip.
"""

import os
import sys
import shutil
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("CopyFiles")

def copy_file(source, destination):
    """
    Copy a file.
    
    Args:
        source: Source file path
        destination: Destination file path
    
    Returns:
        Whether the copy was successful
    """
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Copy the file
        shutil.copy2(source, destination)
        logger.info(f"Copied: {source} -> {destination}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy file: {e}")
        return False

def copy_directory(source, destination):
    """
    Copy a directory recursively.
    
    Args:
        source: Source directory path
        destination: Destination directory path
    
    Returns:
        Whether the copy was successful
    """
    try:
        if not os.path.exists(source):
            logger.error(f"Source directory does not exist: {source}")
            return False
            
        # Ensure destination exists
        os.makedirs(destination, exist_ok=True)
        
        # Copy all files
        for item in os.listdir(source):
            source_item = os.path.join(source, item)
            dest_item = os.path.join(destination, item)
            
            if os.path.isdir(source_item):
                # Create subdirectory
                os.makedirs(dest_item, exist_ok=True)
                # Recursively copy subdirectory
                copy_directory(source_item, dest_item)
            else:
                # Copy file
                shutil.copy2(source_item, dest_item)
                logger.info(f"Copied: {source_item} -> {dest_item}")
        
        logger.info(f"Directory copied: {source} -> {destination}")
        return True
    except Exception as e:
        logger.error(f"Failed to copy directory: {e}")
        return False

def main():
    """Main entry point."""
    logger.info("Starting file copy")
    
    # Source directory
    source_dir = os.path.join(os.getcwd(), "temp_extract", "Lastfix-main")
    if not os.path.exists(source_dir):
        logger.error(f"Source directory not found: {source_dir}")
        return False
    
    # Target directory
    target_dir = os.getcwd()
    
    # Files to copy
    files_to_copy = [
        ("bot.py", "bot.py"),
        ("config.py", "config.py"),
        ("database.py", "database.py"),
        ("canvas.py", "canvas.py"),
        ("commands.py", "commands.py"),
        ("bot_integration.py", "bot_integration.py"),
        ("discord_app_commands.py", "discord_app_commands.py"),
        ("apply_compatibility.py", "apply_compatibility.py"),
        ("PYCORD_261_COMPATIBILITY.md", "PYCORD_261_COMPATIBILITY.md"),
        ("LastFix.md", "LastFix.md"),
        (".env", ".env")
    ]
    
    # Copy individual files
    for source, dest in files_to_copy:
        source_path = os.path.join(source_dir, source)
        dest_path = os.path.join(target_dir, dest)
        
        if os.path.exists(source_path):
            copy_file(source_path, dest_path)
        else:
            logger.warning(f"Source file not found: {source_path}")
    
    # Directories to copy
    dirs_to_copy = [
        ("cogs", "cogs"),
        ("utils", "utils"),
        ("models", "models"),
        ("commands", "commands")
    ]
    
    # Copy directories
    for source, dest in dirs_to_copy:
        source_path = os.path.join(source_dir, source)
        dest_path = os.path.join(target_dir, dest)
        
        if os.path.exists(source_path):
            # Remove existing directory if any
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path)
            
            copy_directory(source_path, dest_path)
        else:
            logger.warning(f"Source directory not found: {source_path}")
    
    logger.info("File copy completed successfully")
    return True

if __name__ == "__main__":
    main()