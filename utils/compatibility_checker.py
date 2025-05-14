"""
Compatibility Checker Module

This module provides utilities to detect compatibility issues between different
versions of libraries used by the bot, particularly focusing on discord.py and py-cord.
"""

import logging
import sys
import importlib
import inspect
import re
from enum import Enum
from typing import Dict, Tuple, List, Any, Optional, Set, NamedTuple

# Set up logging
logger = logging.getLogger(__name__)

class LibraryType(Enum):
    """Enumeration of supported Discord library types"""
    UNKNOWN = "unknown"
    PYCORD = "pycord"
    DISCORDPY = "discord.py"
    DISCORDPY_OLD = "discord.py<2.0"
    
class Version(NamedTuple):
    """Simple version tuple with comparison support"""
    major: int
    minor: int
    patch: int
    
    @classmethod
    def from_string(cls, version_str: str) -> 'Version':
        """Parse a version string into a Version object"""
        parts = re.findall(r'\d+', version_str)
        if len(parts) >= 3:
            return cls(int(parts[0]), int(parts[1]), int(parts[2]))
        elif len(parts) == 2:
            return cls(int(parts[0]), int(parts[1]), 0)
        elif len(parts) == 1:
            return cls(int(parts[0]), 0, 0)
        return cls(0, 0, 0)
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

class CompatibilityIssue(NamedTuple):
    """Represents a detected compatibility issue"""
    module: str
    feature: str
    description: str
    severity: str  # 'critical', 'major', 'minor'
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.module}.{self.feature}: {self.description}"

def get_discord_library_info() -> Tuple[LibraryType, str, Version]:
    """
    Detect which Discord library is being used and its version.
    
    Returns:
        Tuple of (library type, version string, parsed version)
    """
    try:
        import discord
        
        # Check for py-cord specific attributes
        if hasattr(discord, 'default_permissions') or hasattr(discord, '_Discord__application_commands'):
            # This is likely py-cord
            version_str = getattr(discord, '__version__', 'unknown')
            return (LibraryType.PYCORD, version_str, Version.from_string(version_str))
        
        # Check for discord.py 2.0+ (with app_commands)
        if hasattr(discord, 'app_commands') or hasattr(discord, 'ApplicationCommand'):
            version_str = getattr(discord, '__version__', 'unknown')
            return (LibraryType.DISCORDPY, version_str, Version.from_string(version_str))
        
        # Older discord.py
        version_str = getattr(discord, '__version__', 'unknown')
        return (LibraryType.DISCORDPY_OLD, version_str, Version.from_string(version_str))
        
    except ImportError:
        logger.error("Discord library not found")
        return (LibraryType.UNKNOWN, "not installed", Version(0, 0, 0))
    except Exception as e:
        logger.error(f"Error detecting Discord library: {e}")
        return (LibraryType.UNKNOWN, "error", Version(0, 0, 0))

def get_motor_version() -> Tuple[str, Version]:
    """
    Get the installed motor version if available.
    
    Returns:
        Tuple of (version string, parsed version)
    """
    try:
        import motor
        version_str = getattr(motor, '__version__', 'unknown')
        return (version_str, Version.from_string(version_str))
    except ImportError:
        return ("not installed", Version(0, 0, 0))
    except Exception as e:
        logger.error(f"Error detecting motor version: {e}")
        return ("error", Version(0, 0, 0))

def get_pymongo_version() -> Tuple[str, Version]:
    """
    Get the installed pymongo version if available.
    
    Returns:
        Tuple of (version string, parsed version)
    """
    try:
        import pymongo
        version_str = getattr(pymongo, '__version__', 'unknown')
        return (version_str, Version.from_string(version_str))
    except ImportError:
        return ("not installed", Version(0, 0, 0))
    except Exception as e:
        logger.error(f"Error detecting pymongo version: {e}")
        return ("error", Version(0, 0, 0))

def check_pycord_compatibility() -> List[CompatibilityIssue]:
    """
    Check for py-cord compatibility issues.
    
    Returns:
        List of detected compatibility issues
    """
    issues = []
    
    lib_type, version_str, version = get_discord_library_info()
    
    # Check if using py-cord
    if lib_type != LibraryType.PYCORD:
        issues.append(CompatibilityIssue(
            module="discord",
            feature="library",
            description=f"Expected py-cord but found {lib_type.value} {version_str}",
            severity="critical"
        ))
        return issues
    
    # Check for specific py-cord versions with known issues
    if version.major == 2 and version.minor == 6 and version.patch == 1:
        # Py-cord 2.6.1 has specific issues
        issues.append(CompatibilityIssue(
            module="discord",
            feature="SlashCommandGroup",
            description="py-cord 2.6.1 has issues with SlashCommandGroup.command attribute",
            severity="major"
        ))
        
        issues.append(CompatibilityIssue(
            module="discord",
            feature="interaction_response",
            description="py-cord 2.6.1 has issues with interaction responses",
            severity="major"
        ))
    
    return issues

def check_database_compatibility() -> List[CompatibilityIssue]:
    """
    Check for database compatibility issues.
    
    Returns:
        List of detected compatibility issues
    """
    issues = []
    
    # Check Motor version
    motor_version_str, motor_version = get_motor_version()
    if motor_version_str == "not installed":
        issues.append(CompatibilityIssue(
            module="motor",
            feature="library",
            description="Motor library not installed",
            severity="critical"
        ))
    elif motor_version.major < 2:
        issues.append(CompatibilityIssue(
            module="motor",
            feature="version",
            description=f"Motor version {motor_version_str} is outdated, 2.0+ recommended",
            severity="major"
        ))
    
    # Check PyMongo version
    pymongo_version_str, pymongo_version = get_pymongo_version()
    if pymongo_version_str == "not installed":
        issues.append(CompatibilityIssue(
            module="pymongo",
            feature="library",
            description="PyMongo library not installed",
            severity="critical"
        ))
    elif pymongo_version.major < 3:
        issues.append(CompatibilityIssue(
            module="pymongo",
            feature="version",
            description=f"PyMongo version {pymongo_version_str} is outdated, 3.0+ recommended",
            severity="major"
        ))
    
    return issues

def check_all_compatibility() -> Dict[str, List[CompatibilityIssue]]:
    """
    Run all compatibility checks.
    
    Returns:
        Dict mapping check names to lists of detected issues
    """
    results = {
        "discord": check_pycord_compatibility(),
        "database": check_database_compatibility(),
    }
    
    return results

def print_compatibility_report():
    """Print a compatibility report to the console."""
    print("\n=== Compatibility Report ===\n")
    
    # Check Discord library
    lib_type, version_str, version = get_discord_library_info()
    print(f"Discord Library: {lib_type.value} {version_str}")
    
    # Check database libraries
    motor_version_str, _ = get_motor_version()
    pymongo_version_str, _ = get_pymongo_version()
    print(f"Motor Version: {motor_version_str}")
    print(f"PyMongo Version: {pymongo_version_str}")
    
    # Run all checks
    all_issues = check_all_compatibility()
    total_issues = sum(len(issues) for issues in all_issues.values())
    
    print(f"\nDetected {total_issues} compatibility issues:")
    
    for category, issues in all_issues.items():
        if issues:
            print(f"\n{category.upper()} Issues:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"\n{category.upper()}: No issues detected")
    
    print("\n")

if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    
    # Print compatibility report when run directly
    print_compatibility_report()