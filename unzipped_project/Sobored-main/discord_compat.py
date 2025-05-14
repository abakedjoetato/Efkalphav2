"""
Discord Compatibility Layer

This module ensures proper compatibility between discord.py and py-cord.
It should be imported before any other discord modules.
"""

import sys
import importlib
import logging
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_module_path(name):
    """Find the path to a module"""
    try:
        spec = importlib.util.find_spec(name)
        if spec and spec.origin:
            return spec.origin
        return None
    except (ImportError, AttributeError):
        return None

def ensure_py_cord():
    """Ensure py-cord is being used for discord imports"""
    discord_path = find_module_path("discord")
    if discord_path:
        logger.info(f"Found discord module at: {discord_path}")
        
        # Check if it's py-cord by looking for the parent directory name
        parent_dir = Path(discord_path).parent.name
        if parent_dir == "py_cord":
            logger.info("Using py-cord installation")
            return True
        
    # Try to perform a compatibility fix by finding py-cord installation
    try:
        # Look in the current directory structure
        potential_paths = [
            # Standard pip install 
            Path("__pythonlibs__/lib/python3.11/site-packages/py_cord"),
            # Replit specific paths
            Path("/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages/py_cord"),
            Path("/home/runner/.pythonlibs/lib/python3.11/site-packages/py_cord"),
            # Local installation
            Path("py_cord"),
        ]
        
        for potential_path in potential_paths:
            if potential_path.exists() and potential_path.is_dir():
                logger.info(f"Found py-cord at: {potential_path}")
                
                # Add this module to sys.modules as discord
                if "__init__.py" in os.listdir(potential_path):
                    logger.info("Setting py-cord as the discord module")
                    
                    # Create module spec and load it
                    spec = importlib.util.spec_from_file_location("py_cord", 
                                                                potential_path / "__init__.py")
                    py_cord = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(py_cord)
                    
                    # Replace discord in sys.modules
                    sys.modules["discord"] = py_cord
                    return True
        
        logger.warning("Could not find py-cord installation")
    except Exception as e:
        logger.error(f"Error ensuring py-cord: {e}", exc_info=True)
    
    return False

# Set up py-cord as discord on module import
_ = ensure_py_cord()