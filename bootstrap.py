"""
Discord Bot Bootstrap Script

This script ensures that our custom discord implementation is 
properly added to the Python path before importing any other modules.
"""
import os
import sys
import logging
import importlib
import types
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bootstrap.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up the environment for the Discord bot"""
    # Get the absolute path to the current directory
    current_dir = os.path.abspath(os.path.dirname(__file__))
    logger.info(f"Current directory: {current_dir}")
    
    # Add the current directory to the Python path
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        logger.info(f"Added {current_dir} to Python path")
    
    # Print the Python path for debugging
    logger.info(f"Python path: {sys.path}")
    
    # Make sure 'discord' is properly set up as a package - this is critical
    discord_dir = os.path.join(current_dir, 'discord')
    
    # Check if we need to manually create a module structure
    if 'discord' not in sys.modules:
        logger.info("Creating discord module")
        discord_module = types.ModuleType('discord')
        discord_module.__path__ = [discord_dir]
        discord_module.__file__ = os.path.join(discord_dir, '__init__.py')
        sys.modules['discord'] = discord_module
        
        # Load the contents of the discord module
        discord_init_path = os.path.join(discord_dir, '__init__.py')
        if os.path.exists(discord_init_path):
            logger.info(f"Loading discord module from {discord_init_path}")
            try:
                with open(discord_init_path, 'r') as f:
                    code = compile(f.read(), discord_init_path, 'exec')
                    exec(code, sys.modules['discord'].__dict__)
                logger.info("Successfully loaded discord module")
            except Exception as e:
                logger.error(f"Error loading discord module: {e}")
                traceback.print_exc()
        else:
            logger.error(f"Discord module file does not exist at {discord_init_path}")
    
    # Set up the discord.ext module
    if 'discord.ext' not in sys.modules:
        logger.info("Creating discord.ext module")
        ext_module = types.ModuleType('discord.ext')
        ext_module.__path__ = [os.path.join(discord_dir, 'ext')]
        ext_module.__file__ = os.path.join(discord_dir, 'ext', '__init__.py')
        sys.modules['discord.ext'] = ext_module
        
        # Load the contents of the ext module
        ext_init_path = os.path.join(discord_dir, 'ext', '__init__.py')
        if os.path.exists(ext_init_path):
            logger.info(f"Loading discord.ext module from {ext_init_path}")
            try:
                with open(ext_init_path, 'r') as f:
                    code = compile(f.read(), ext_init_path, 'exec')
                    exec(code, sys.modules['discord.ext'].__dict__)
                logger.info("Successfully loaded discord.ext module")
            except Exception as e:
                logger.error(f"Error loading discord.ext module: {e}")
                traceback.print_exc()
    
    # Set up discord.ext.commands module
    if 'discord.ext.commands' not in sys.modules:
        logger.info("Creating discord.ext.commands module")
        commands_module = types.ModuleType('discord.ext.commands')
        commands_module.__file__ = os.path.join(discord_dir, 'ext', 'commands.py')
        sys.modules['discord.ext.commands'] = commands_module
        
        # Make command module available in the ext module
        sys.modules['discord.ext'].commands = commands_module
    
    # Try to load the actual commands module content from the file
    try:
        commands_path = os.path.join(discord_dir, 'ext', 'commands.py')
        if os.path.exists(commands_path):
            logger.info(f"Loading commands module from {commands_path}")
            with open(commands_path, 'r') as f:
                code = compile(f.read(), commands_path, 'exec')
                exec(code, sys.modules['discord.ext.commands'].__dict__)
            logger.info("Successfully loaded commands module")
        else:
            logger.error(f"Commands module file does not exist at {commands_path}")
    except Exception as e:
        logger.error(f"Error loading commands module: {e}")
        traceback.print_exc()
        
    # Return True if setup was successful
    return True

def run_bot():
    """Run the Discord bot"""
    try:
        logger.info("Trying to import direct_bot")
        
        # Import the direct_bot module directly
        import direct_bot
        
        logger.info("Bot import successful")
        
        # If it has a main function, call it
        if hasattr(direct_bot, 'main'):
            logger.info("Calling bot main function")
            import asyncio
            asyncio.run(direct_bot.main())
        else:
            logger.warning("Bot module does not have a main function")
            
    except ImportError as e:
        logger.error(f"Error importing bot: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Set up the environment
    if setup_environment():
        # Run the bot
        logger.info("Environment set up successfully, running bot")
        run_bot()