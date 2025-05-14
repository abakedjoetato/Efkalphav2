#!/bin/bash

# Run Discord bot with proper error handling and automatic restart
echo "Starting Discord Bot..."

# Make sure the script is executable
chmod +x run_discord_bot.sh

# Check for Python
if ! command -v python &> /dev/null; then
    echo "Python is not installed!"
    exit 1
fi

# Check for required environment variables
if [ -z "$DISCORD_TOKEN" ]; then
    echo "ERROR: DISCORD_TOKEN environment variable is not set!"
    exit 1
fi

if [ -z "$MONGODB_URI" ]; then
    echo "WARNING: MONGODB_URI environment variable is not set. Database features will be limited."
fi

# Run the bot with improved error handling
python replit_run.py

# Exit with the status code from the Python script
exit $?