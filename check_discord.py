"""
Check Discord Module

This script checks whether the discord module is available
and prints information about it.
"""

import sys
import os
import inspect
import importlib
import importlib.util
import pkgutil

print("=" * 50)
print("Discord Module Check")
print("=" * 50)

# Print Python version and path
print(f"Python version: {sys.version}")
print("Python path:")
for p in sys.path:
    print(f"  {p}")

try:
    # Try to import discord
    import discord
    print(f"\nSuccessfully imported discord module")
    
    # Get module info
    if hasattr(discord, "__file__"):
        print(f"Module file: {discord.__file__}")
    else:
        print("Module does not have a __file__ attribute")
    
    if hasattr(discord, "__version__"):
        print(f"Module version: {discord.__version__}")
    else:
        print("Module does not have a __version__ attribute")
    
    # Check if it's py-cord or discord.py
    if hasattr(discord, "application_commands"):
        print("Module appears to be py-cord (has application_commands)")
    else:
        print("Module appears to be discord.py (no application_commands)")
    
    # Check for ext module
    if hasattr(discord, "ext"):
        print("Module has 'ext' attribute")
        
        # Try importing commands
        try:
            from discord.ext import commands
            print("Successfully imported discord.ext.commands")
            
            # Check if it's py-cord
            if hasattr(commands.Bot, "slash_command"):
                print("Module has slash_command (py-cord)")
            else:
                print("Module does not have slash_command (discord.py)")
        except ImportError as e:
            print(f"Failed to import discord.ext.commands: {e}")
    else:
        print("Module does not have 'ext' attribute")
    
    # Print module attributes
    print("\nModule attributes:")
    for attr in dir(discord):
        if not attr.startswith("_"):
            print(f"  {attr}")
            
    # Look for Client class
    if hasattr(discord, "Client"):
        print("\nFound discord.Client class")
    else:
        print("\nCould not find discord.Client class")
        
    # Look for Intents class
    if hasattr(discord, "Intents"):
        print("Found discord.Intents class")
    else:
        print("Could not find discord.Intents class")
        
except ImportError as e:
    print(f"\nFailed to import discord module: {e}")
    
    # Try to find discord module in path
    print("\nSearching for discord module in path:")
    for path in sys.path:
        discord_path = os.path.join(path, "discord")
        if os.path.exists(discord_path):
            print(f"  Found at: {discord_path}")
            
            # Check if it's a directory or file
            if os.path.isdir(discord_path):
                print(f"  It's a directory")
                
                # List files in directory
                print("  Files in directory:")
                for f in os.listdir(discord_path):
                    print(f"    {f}")
            else:
                print(f"  It's a file")
        
print("\nCheck complete")