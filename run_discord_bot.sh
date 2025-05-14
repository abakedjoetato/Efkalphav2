#!/bin/bash
# Improved Discord Bot Launcher for Replit

# Print a welcome message
echo "============================="
echo "  Discord Bot Launch Script  "
echo "============================="
echo ""

# Use the correct Python path
PYTHON_PATH="/home/runner/workspace/.pythonlibs/bin/python3"

# Ensure environment variables are set up
if [ ! -f ".env" ]; then
  echo "Creating .env file with secrets..."
  echo "DISCORD_TOKEN=$DISCORD_TOKEN" > .env
  echo "MONGODB_URI=$MONGODB_URI" >> .env
else
  # Update .env to ensure MONGODB_URI is present
  if ! grep -q "MONGODB_URI" .env; then
    echo "Adding MONGODB_URI to .env file..."
    echo "MONGODB_URI=$MONGODB_URI" >> .env
  fi
fi

# Set environment variables for better debugging
export DEBUG=1
export PYTHONPATH="."

# Start the Discord bot
echo "Starting Discord bot..."
PYTHONIOENCODING=utf-8 $PYTHON_PATH run_discord_bot.py