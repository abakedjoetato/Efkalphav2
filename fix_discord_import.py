"""
Fix Discord Import

This module patches the Python import system to correctly handle
Discord module imports and resolve conflicts between discord.py and py-cord.
"""

import os
import sys
import importlib
import logging
import types
import inspect
import subprocess
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DiscordFix")

def detect_discord_libraries():
    """Detect installed Discord libraries and their locations."""
    logger.info("Detecting installed Discord libraries...")
    
    result = {
        "discord.py": None,
        "py-cord": None,
        "discord_module_path": None
    }
    
    # Check for discord module
    try:
        import discord
        result["discord_module_path"] = getattr(discord, "__file__", None)
        
        # Check if it's discord.py or py-cord
        if hasattr(discord, "__version__"):
            version = discord.__version__
            
            # Check if it's py-cord (has application_commands)
            if hasattr(discord, "application_commands"):
                logger.info(f"Detected py-cord version {version}")
                result["py-cord"] = version
            else:
                logger.info(f"Detected discord.py version {version}")
                result["discord.py"] = version
        else:
            logger.warning("Found discord module but couldn't determine version")
    except ImportError:
        logger.warning("No discord module found")
    
    return result

def install_py_cord():
    """Install py-cord in the user's Python environment."""
    logger.info("Installing py-cord in user environment...")
    
    try:
        # First, try to uninstall existing discord.py or py-cord
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "discord.py"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "discord"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "py-cord"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Install py-cord
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "py-cord==2.6.1"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        logger.info("Successfully installed py-cord")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install py-cord: {e}")
        logger.error(f"Error output: {e.stderr.decode()}")
        return False

def create_pycord_loader():
    """Create a custom loader for py-cord that bypasses system-level discord.py."""
    
    class PyCordfinder:
        """
        A meta path finder that can load py-cord even if discord.py is installed.
        """
        
        @classmethod
        def find_spec(cls, fullname, path, target=None):
            # Only handle 'discord' module
            if fullname != 'discord' and not fullname.startswith('discord.'):
                return None
            
            # Find py-cord in site-packages
            for path_entry in sys.path:
                path_obj = Path(path_entry)
                discord_path = path_obj / 'discord'
                
                if not discord_path.exists() or not discord_path.is_dir():
                    continue
                
                # Check if this is py-cord by looking for application_commands.py
                if (discord_path / 'application_commands.py').exists():
                    logger.info(f"Found py-cord at {discord_path}")
                    
                    if fullname == 'discord':
                        # Loading the root module
                        loader = PycodLoader(discord_path)
                        return importlib.util.spec_from_loader(fullname, loader)
                    else:
                        # Loading a submodule
                        subpath = fullname.split('.')[1:]
                        submodule_path = discord_path.joinpath(*subpath)
                        
                        if submodule_path.exists():
                            if submodule_path.is_dir():
                                # It's a package
                                loader = PycodLoader(submodule_path)
                                return importlib.util.spec_from_loader(fullname, loader)
                            elif (submodule_path.with_suffix('.py')).exists():
                                # It's a module
                                loader = PycodLoader(submodule_path.with_suffix('.py'))
                                return importlib.util.spec_from_loader(fullname, loader)
            
            return None
    
    class PycodLoader:
        """
        A custom loader for py-cord modules.
        """
        
        def __init__(self, path):
            self.path = Path(path)
        
        def create_module(self, spec):
            return None  # Use default module creation
        
        def exec_module(self, module):
            if self.path.is_dir():
                # It's a package
                module.__path__ = [str(self.path)]
                module.__package__ = module.__name__
                
                # Load __init__.py
                init_path = self.path / '__init__.py'
                if init_path.exists():
                    with open(init_path, 'r') as f:
                        code = compile(f.read(), str(init_path), 'exec')
                        exec(code, module.__dict__)
            else:
                # It's a module
                with open(self.path, 'r') as f:
                    code = compile(f.read(), str(self.path), 'exec')
                    exec(code, module.__dict__)
    
    return PyCordfinder

def patch_import_system():
    """Patch the import system to prioritize py-cord."""
    finder = create_pycord_loader()
    sys.meta_path.insert(0, finder)
    logger.info("Patched import system to prioritize py-cord")

def clean_sys_modules():
    """Clean discord modules from sys.modules to allow fresh import."""
    to_remove = []
    for module_name in sys.modules:
        if module_name == 'discord' or module_name.startswith('discord.'):
            to_remove.append(module_name)
    
    for module_name in to_remove:
        del sys.modules[module_name]
    
    logger.info(f"Removed {len(to_remove)} discord-related modules from sys.modules")

def verify_discord_import():
    """Verify that discord import works correctly."""
    try:
        import discord
        logger.info(f"Successfully imported discord module from {getattr(discord, '__file__', 'unknown')}")
        
        # Check version
        if hasattr(discord, "__version__"):
            logger.info(f"Discord version: {discord.__version__}")
        
        # Check if it has ext module
        if hasattr(discord, "ext"):
            logger.info("Discord module has 'ext' attribute")
            
            # Try importing commands
            try:
                from discord.ext import commands
                logger.info("Successfully imported discord.ext.commands")
                
                # Check if it's py-cord by looking for slash_command
                if hasattr(commands.Bot, "slash_command"):
                    logger.info("Detected py-cord (has slash_command attribute)")
                else:
                    logger.info("Detected discord.py (no slash_command attribute)")
            except ImportError as e:
                logger.error(f"Failed to import discord.ext.commands: {e}")
        else:
            logger.error("Discord module missing 'ext' attribute")
        
        # Check other critical components
        for attr in ["Client", "Intents", "Embed", "Color"]:
            if hasattr(discord, attr):
                logger.info(f"Discord module has '{attr}' attribute")
            else:
                logger.error(f"Discord module missing '{attr}' attribute")
                
        return True
    except ImportError as e:
        logger.error(f"Failed to import discord: {e}")
        return False

def main():
    """Main entry point."""
    logger.info("Starting Discord import fix")
    
    # Detect installed libraries
    libraries = detect_discord_libraries()
    
    # Clean existing discord modules from sys.modules
    clean_sys_modules()
    
    # Try to install py-cord if needed
    if not libraries["py-cord"]:
        success = install_py_cord()
        if not success:
            logger.warning("Failed to install py-cord, continuing with patching anyway")
    
    # Patch import system
    patch_import_system()
    
    # Verify import
    success = verify_discord_import()
    
    if success:
        logger.info("Discord import fix completed successfully")
    else:
        logger.error("Discord import fix failed")
    
    return success

if __name__ == "__main__":
    main()