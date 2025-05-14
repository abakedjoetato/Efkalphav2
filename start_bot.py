"""
Enhanced script to start the Discord bot with better diagnostics.
This will launch main.py in a clean way with proper environment setup and error tracking.

This version includes:
- Colorful console output
- Enhanced error handling
- Command-line arguments for different modes
- Diagnostic output for troubleshooting
- Environment variable checking
"""

import subprocess
import sys
import argparse
import os
import time
import traceback
from datetime import datetime

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log(message, color=Colors.BLUE):
    """Print a colored log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.ENDC}")

def check_environment():
    """Check if environment variables are properly set"""
    missing_vars = []
    
    # Check required variables
    if not os.environ.get("DISCORD_TOKEN"):
        missing_vars.append("DISCORD_TOKEN")
    
    # Check optional but important variables
    if not os.environ.get("MONGODB_URI"):
        log("MONGODB_URI environment variable is not set. Database features may be limited.", Colors.YELLOW)
    
    # Report any missing required variables
    if missing_vars:
        log(f"The following required environment variables are not set: {', '.join(missing_vars)}", Colors.RED)
        log("Please set them using the Replit Secrets tab.", Colors.YELLOW)
        return False
    
    return True

def check_python_environment():
    """Check Python environment and modules"""
    try:
        # Try to import key modules
        log("Checking for required Python modules...", Colors.BLUE)
        
        # First try to import py_cord directly
        try:
            import py_cord
            log(f"Found py_cord module version: {py_cord.__version__}", Colors.GREEN)
            # Add an alias to make discord import work correctly
            import sys
            sys.modules['discord'] = py_cord
            log("Successfully aliased py_cord to discord", Colors.GREEN)
            log("Using py-cord library", Colors.GREEN)
        except ImportError:
            log("py-cord not directly importable as py_cord", Colors.YELLOW)
            
            # Try standard discord import
            try:
                import discord
                log(f"Found discord module version: {discord.__version__}", Colors.GREEN)
                
                # Check if it has the ext attribute
                if hasattr(discord, 'ext'):
                    try:
                        # Check if it's py-cord or discord.py
                        if hasattr(discord.ext.commands.Bot, "slash_command"):
                            log("Using py-cord library", Colors.GREEN)
                        else:
                            log("Using discord.py library", Colors.YELLOW)
                            log("WARNING: This bot requires py-cord, not discord.py", Colors.RED)
                    except AttributeError:
                        log("Discord library has ext attribute but structure is unexpected", Colors.YELLOW)
                else:
                    log("Discord library missing ext attribute, not a complete Discord library", Colors.RED)
                    log("Attempting to fix Discord import issues...", Colors.YELLOW)
                    
                    # Try to locate py-cord in site-packages
                    import site
                    import importlib
                    
                    # Look for py-cord in site packages
                    site_packages = site.getsitepackages()
                    log(f"Searching for py-cord in {len(site_packages)} site-packages directories", Colors.BLUE)
                    
                    for site_package in site_packages:
                        py_cord_path = os.path.join(site_package, 'py_cord')
                        if os.path.exists(py_cord_path):
                            log(f"Found py-cord at {py_cord_path}", Colors.GREEN)
                            
                            # Try to import using that path
                            try:
                                spec = importlib.util.spec_from_file_location('py_cord', os.path.join(py_cord_path, '__init__.py'))
                                py_cord = importlib.util.module_from_spec(spec)
                                spec.loader.exec_module(py_cord)
                                
                                # Add it to sys.modules
                                sys.modules['discord'] = py_cord
                                log("Successfully loaded py-cord and aliased to discord", Colors.GREEN)
                                break
                            except Exception as e:
                                log(f"Failed to manually import py-cord: {e}", Colors.RED)
            except ImportError:
                log("Failed to import discord module", Colors.RED)
                return False
        
        # Try to ensure discord properly imports
        try:
            import discord
            from discord.ext import commands
            log("Successfully imported discord.ext.commands", Colors.GREEN)
        except ImportError as e:
            log(f"Failed to import discord.ext.commands: {e}", Colors.RED)
            # Create environment fix file
            with open("discord_fix.py", "w") as f:
                f.write("""
import sys
import importlib.util
import os
import site

def find_and_fix_discord():
    # Look for py-cord in site packages
    for site_package in site.getsitepackages():
        py_cord_path = os.path.join(site_package, 'py_cord')
        if os.path.exists(py_cord_path):
            # Try to import using that path
            try:
                spec = importlib.util.spec_from_file_location('py_cord', os.path.join(py_cord_path, '__init__.py'))
                py_cord = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(py_cord)
                
                # Add it to sys.modules
                sys.modules['discord'] = py_cord
                return True
            except Exception:
                pass
    return False

find_and_fix_discord()
""")
            # Try to use the fix
            try:
                import discord_fix
                import discord
                from discord.ext import commands
                log("Applied discord_fix.py to fix imports", Colors.GREEN)
            except ImportError as e:
                log(f"Failed to fix discord imports: {e}", Colors.RED)
                return False
        
        # Check for MongoDB libraries
        try:
            import motor
            import pymongo
            log(f"Found motor version: {motor.version}", Colors.GREEN)
            log(f"Found pymongo version: {pymongo.version}", Colors.GREEN)
        except ImportError as e:
            log(f"Failed to import MongoDB modules: {e}", Colors.RED)
            return False
            
        return True
    except Exception as e:
        log(f"Error checking Python environment: {e}", Colors.RED)
        traceback.print_exc()
        return False

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Discord Bot Launcher")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode with extra logging")
    parser.add_argument("--check-only", action="store_true", help="Only check environment without starting bot")
    args = parser.parse_args()
    
    # Display startup banner
    print(f"{Colors.HEADER}{Colors.BOLD}============================================{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.GREEN}            DISCORD BOT LAUNCHER            {Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}============================================{Colors.ENDC}")
    
    # Set debug environment variable if --debug is specified or from environment
    if args.debug or os.environ.get("DEBUG") == "1":
        os.environ["DEBUG"] = "1"
        log("Running in DEBUG mode", Colors.YELLOW)
    
    # Load environment variables from .env if dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        log("Loaded environment variables from .env file", Colors.GREEN)
    except ImportError:
        log("python-dotenv not available, skipping .env loading", Colors.YELLOW)
    
    # Check environment variables
    if not check_environment():
        return 1
    
    # Check Python environment
    if not check_python_environment():
        log("Python environment check failed", Colors.RED)
        if not args.debug:
            log("Try running with --debug for more information", Colors.YELLOW)
        return 1
    
    # If only checking environment, exit after checks
    if args.check_only:
        log("Environment check completed successfully", Colors.GREEN)
        return 0
    
    # Start the bot
    log("Starting Discord bot...", Colors.GREEN)
    try:
        # Set PYTHONPATH environment variable to include current directory
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd() + os.pathsep + env.get("PYTHONPATH", "")
        
        # Run the main.py file with process output capture
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Stream the output as it happens
        for line in process.stdout:
            print(line, end='')
            
        # Wait for process to complete
        returncode = process.wait()
        
        if returncode != 0:
            log(f"Bot process exited with code {returncode}", Colors.RED)
            return returncode
    except KeyboardInterrupt:
        log("\nBot stopped by user.", Colors.YELLOW)
        return 0
    except subprocess.CalledProcessError as e:
        log(f"Error starting bot: {e}", Colors.RED)
        return 1
    except Exception as e:
        log(f"Unexpected error: {e}", Colors.RED)
        traceback.print_exc()
        return 1
    
    log("Bot process exited normally", Colors.GREEN)
    return 0

if __name__ == "__main__":
    sys.exit(main())