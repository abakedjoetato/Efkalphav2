"""
Py-Cord Adapter

This module provides compatibility between discord.py and py-cord.
Import this module before importing discord to ensure py-cord is used properly.
"""

import os
import sys
import importlib
from pathlib import Path

# First ensure we load real discord from py-cord if available
try:
    # Try removing the discord module if it's already been imported
    if 'discord' in sys.modules:
        del sys.modules['discord']
    
    # Now try to locate and add py-cord directly to the import path
    pycord_paths = [
        # Replit paths
        Path("/home/runner/workspace/.pythonlibs/lib/python3.11/site-packages"),
        Path("/home/runner/.pythonlibs/lib/python3.11/site-packages"),
        # Local path
        Path("."),
    ]
    
    # Add these paths to the Python path
    for pycord_path in pycord_paths:
        if pycord_path.exists() and str(pycord_path) not in sys.path:
            sys.path.insert(0, str(pycord_path))
    
    # Try importing discord (hopefully py-cord)
    import discord
    
    # Verify this is py-cord by checking for slash_command attribute
    if not hasattr(discord.ext.commands.Bot, "slash_command"):
        print("Warning: Imported discord is not py-cord. Adapter failed.")
    else:
        print(f"Successfully loaded py-cord as discord: {discord.__version__}")
except Exception as e:
    print(f"Error in py-cord adapter: {e}")

# Export discord for users of this module
try:
    import discord
    # Also make sure discord.ext.commands is available
    from discord.ext import commands
except ImportError:
    print("Failed to import discord. Bot will not function correctly.")