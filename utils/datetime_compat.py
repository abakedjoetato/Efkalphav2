"""
Datetime Compatibility Module

This module provides compatibility functions for datetime operations
that have changed between different versions of Discord libraries.
"""

import datetime
from typing import Optional, Union

# Define a variable for discord utcnow function, will be set if available
discord_utcnow = None

# Try to import discord.utils.utcnow if available
try:
    from discord.utils import utcnow as discord_utcnow
    HAS_DISCORD_UTCNOW = True
except ImportError:
    HAS_DISCORD_UTCNOW = False

def utcnow() -> datetime.datetime:
    """
    Get the current UTC datetime with compatibility across Discord library versions.
    
    Returns:
        datetime.datetime: Current UTC datetime
    """
    if HAS_DISCORD_UTCNOW and discord_utcnow is not None:
        return discord_utcnow()
    else:
        return datetime.datetime.now(datetime.timezone.utc)

def format_iso(dt: Optional[datetime.datetime]) -> Optional[str]:
    """
    Format a datetime as ISO 8601 string with compatibility.
    
    Args:
        dt: Datetime to format
        
    Returns:
        str or None: ISO 8601 string or None if dt is None
    """
    if dt is None:
        return None
    return dt.isoformat()

def parse_iso(iso_string: Optional[str]) -> Optional[datetime.datetime]:
    """
    Parse an ISO 8601 string into a datetime object with compatibility.
    
    Args:
        iso_string: ISO 8601 string to parse
        
    Returns:
        datetime.datetime or None: Parsed datetime or None if iso_string is None
    """
    if not iso_string:
        return None
    try:
        return datetime.datetime.fromisoformat(iso_string)
    except ValueError:
        try:
            # Fallback for older Python versions or different ISO formats
            return datetime.datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            # Try without microseconds
            try:
                return datetime.datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                # Last resort - just return current time
                return utcnow()