#!/bin/bash
# Fixed Discord Bot Launch Script
# This script properly fixes Discord imports and runs the FULL bot with all features

# Print header
echo "============================="
echo "  Fixed Discord Bot Launch   "
echo "============================="
echo ""

# Use the correct Python path
PYTHON_PATH="python3"

# Check for token
if [ -z "$DISCORD_TOKEN" ]; then
  echo "ERROR: DISCORD_TOKEN environment variable is not set."
  echo "Please set the DISCORD_TOKEN in your environment or secrets."
  exit 1
fi

# Set up .env file
if [ ! -f ".env" ]; then
  echo "Creating .env file with secrets..."
  echo "DISCORD_TOKEN=$DISCORD_TOKEN" > .env
  
  # Add MONGODB_URI if available
  if [ ! -z "$MONGODB_URI" ]; then
    echo "MONGODB_URI=$MONGODB_URI" >> .env
  fi
else
  # Update token if needed
  if ! grep -q "DISCORD_TOKEN" .env; then
    echo "Adding DISCORD_TOKEN to .env file..."
    echo "DISCORD_TOKEN=$DISCORD_TOKEN" >> .env
  fi
  
  # Update MongoDB URI if needed
  if [ ! -z "$MONGODB_URI" ] && ! grep -q "MONGODB_URI" .env; then
    echo "Adding MONGODB_URI to .env file..."
    echo "MONGODB_URI=$MONGODB_URI" >> .env
  fi
fi

# First run the Discord import fix
echo "Fixing Discord module imports..."
$PYTHON_PATH fix_discord_import.py

# Check if fix was successful
if [ $? -ne 0 ]; then
  echo "ERROR: Failed to fix Discord imports."
  exit 1
fi

# Patch all cogs and main files for compatibility
echo "Patching cogs and main files for compatibility..."
$PYTHON_PATH patch_cogs.py

# Check if patching was successful
if [ $? -ne 0 ]; then
  echo "WARNING: Some cog patches may not have been applied."
  # Continue anyway
fi

# Create a wrapper script that patches imports before running the bot
cat > fixed_bot_runner.py << 'EOF'
"""
Fixed Bot Runner

This script properly loads discord modules before running the actual bot.
"""

import sys
import os
import importlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FixedBotRunner")

def run_with_fixed_imports():
    """Run the bot with fixed imports."""
    # Import the fix module first to patch imports
    import fix_discord_import
    
    # Clean modules if already imported
    fix_discord_import.clean_sys_modules()
    
    # Patch import system
    fix_discord_import.patch_import_system()
    
    # Verify discord import is working
    if not fix_discord_import.verify_discord_import():
        logger.error("Discord import verification failed, cannot run bot")
        sys.exit(1)
    
    # Now run the main bot
    logger.info("Running main bot...")
    try:
        # Import the bot code
        import bot
        
        # Create and run the bot with production settings
        logger.info("Creating and running bot...")
        discord_bot = bot.Bot(production=True)
        discord_bot.run(os.environ.get("DISCORD_TOKEN"))
    except Exception as e:
        logger.error(f"Error running bot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_with_fixed_imports()
EOF

# Run the fixed bot
echo "Starting the FULL Discord bot with all features..."
$PYTHON_PATH fixed_bot_runner.py