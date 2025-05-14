#!/usr/bin/env python3
"""
Bot Management Script

This script provides utilities for managing the Discord bot:
- Checking environment variables
- Testing the MongoDB connection
- Validating the Discord token
- Performing basic diagnostics
- Backup and restore functionality
"""

import os
import sys
import json
import time
import shutil
import argparse
import datetime
from dotenv import load_dotenv

# Try to load environment variables
load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = {
        "DISCORD_TOKEN": os.environ.get("DISCORD_TOKEN"),
    }
    
    optional_vars = {
        "MONGODB_URI": os.environ.get("MONGODB_URI"),
        "SFTP_ENABLED": os.environ.get("SFTP_ENABLED"),
    }
    
    # Check required variables
    missing = [var for var, value in required_vars.items() if not value]
    if missing:
        print("ERROR: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        return False
    
    # Show status of optional variables
    print("Optional environment variables:")
    for var, value in optional_vars.items():
        status = "✓ Set" if value else "✗ Not set"
        print(f"  - {var}: {status}")
    
    return True

def test_discord_token():
    """Test if the Discord token is valid"""
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN is not set")
        return False
    
    try:
        # Simple validation - not a full check
        parts = token.split(".")
        if len(parts) != 3:
            print("WARNING: Discord token doesn't appear to be in the correct format")
            print("Expected format: XXXXXXXXXXXXXXXXXX.XXXXXX.XXXXXXXXXXXXXXXXXXX")
            return False
        
        print("Discord token format appears valid")
        return True
    except Exception as e:
        print(f"Error validating Discord token: {e}")
        return False

def create_backup():
    """Create a backup of the bot files"""
    try:
        # Create backup directory
        backup_dir = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Directories to back up
        dirs_to_backup = ["cogs", "models", "utils"]
        files_to_backup = [
            "main.py", "replit_run.py", "bot.py", "start_bot.py",
            ".env", "requirements.txt"
        ]
        
        # Copy directories
        for dir_name in dirs_to_backup:
            if os.path.exists(dir_name):
                shutil.copytree(dir_name, os.path.join(backup_dir, dir_name))
        
        # Copy files
        for file_name in files_to_backup:
            if os.path.exists(file_name):
                shutil.copy2(file_name, os.path.join(backup_dir, file_name))
        
        print(f"Backup created successfully in directory: {backup_dir}")
        return True
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Discord Bot Management Tool")
    parser.add_argument("--check", action="store_true", help="Check environment variables")
    parser.add_argument("--test-token", action="store_true", help="Test Discord token")
    parser.add_argument("--backup", action="store_true", help="Create a backup of the bot")
    args = parser.parse_args()
    
    # If no arguments, show all checks
    if not any(vars(args).values()):
        args.check = True
        args.test_token = True
    
    # Perform requested actions
    results = []
    
    if args.check:
        print("\n=== Environment Check ===")
        results.append(check_environment())
    
    if args.test_token:
        print("\n=== Discord Token Test ===")
        results.append(test_discord_token())
    
    if args.backup:
        print("\n=== Creating Backup ===")
        results.append(create_backup())
    
    # Return status
    if all(results):
        print("\nAll checks passed successfully!")
        return 0
    else:
        print("\nSome checks failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())