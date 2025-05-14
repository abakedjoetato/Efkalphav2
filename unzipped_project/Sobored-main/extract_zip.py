"""
Extract ZIP File

This script extracts the Lastfix-main.zip file to use the existing libraries.
"""

import os
import sys
import zipfile
import logging
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ExtractZip")

def extract_zip(zip_path, target_dir=None):
    """
    Extract a ZIP file.
    
    Args:
        zip_path: Path to the ZIP file
        target_dir: Directory to extract to (default: current directory)
    
    Returns:
        Whether the extraction was successful
    """
    if not target_dir:
        target_dir = os.getcwd()
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            logger.info(f"Extracting {zip_path} to {target_dir}...")
            zip_ref.extractall(target_dir)
        
        logger.info("Extraction successful")
        return True
    except Exception as e:
        logger.error(f"Failed to extract ZIP file: {e}")
        return False

def get_zip_file():
    """
    Find the Lastfix-main.zip file.
    
    Returns:
        Path to the ZIP file or None if not found
    """
    # Look for the zip file in various locations
    potential_paths = [
        os.path.join(os.getcwd(), "Lastfix-main.zip"),
        os.path.join(os.getcwd(), "attached_assets", "Lastfix-main.zip")
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            logger.info(f"Found ZIP file at: {path}")
            return path
    
    logger.error("Could not find Lastfix-main.zip")
    return None

def copy_libraries(source_dir):
    """
    Copy libraries from the extracted ZIP file.
    
    Args:
        source_dir: Directory containing the extracted files
    
    Returns:
        Whether the copy was successful
    """
    libraries_dir = os.path.join(source_dir, "lib")
    if not os.path.exists(libraries_dir):
        logger.error(f"Libraries directory not found at: {libraries_dir}")
        return False
    
    # Create a lib directory if it doesn't exist
    target_dir = os.path.join(os.getcwd(), "lib")
    os.makedirs(target_dir, exist_ok=True)
    
    # Copy all files
    for root, dirs, files in os.walk(libraries_dir):
        # Get relative path
        rel_path = os.path.relpath(root, libraries_dir)
        
        # Create target directory
        if rel_path != ".":
            os.makedirs(os.path.join(target_dir, rel_path), exist_ok=True)
        
        # Copy files
        for file in files:
            source_file = os.path.join(root, file)
            target_file = os.path.join(target_dir, rel_path, file)
            shutil.copy2(source_file, target_file)
            logger.info(f"Copied: {target_file}")
    
    logger.info(f"Libraries copied to: {target_dir}")
    return True

def main():
    """Main entry point."""
    logger.info("Starting ZIP extraction")
    
    # Find the ZIP file
    zip_file = get_zip_file()
    if not zip_file:
        logger.error("No ZIP file found, aborting")
        return False
    
    # Create a temporary directory
    temp_dir = os.path.join(os.getcwd(), "temp_extract")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Extract the ZIP file
    if not extract_zip(zip_file, temp_dir):
        logger.error("Failed to extract ZIP file, aborting")
        return False
    
    # List the extracted files
    logger.info("Extracted files:")
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            logger.info(f"  {os.path.join(root, file)}")
    
    # Copy libraries
    if not copy_libraries(temp_dir):
        logger.error("Failed to copy libraries, aborting")
        return False
    
    logger.info("ZIP extraction completed successfully")
    return True

if __name__ == "__main__":
    main()