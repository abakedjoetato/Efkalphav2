#!/bin/bash
# Replit Discord Bot Launch Script
# This script should be run with the "Run" button

# Print a welcome message
echo "============================="
echo "  Discord Bot Launch Script  "
echo "============================="
echo ""

# Use the correct Python path
PYTHON_PATH="python3"

# Set up .env file if needed
if [ ! -f ".env" ]; then
  echo "Creating .env file with secrets..."
  echo "DISCORD_TOKEN=$DISCORD_TOKEN" > .env
  
  # Add MONGODB_URI if available
  if [ ! -z "$MONGODB_URI" ]; then
    echo "MONGODB_URI=$MONGODB_URI" >> .env
  fi
else
  # Check if MONGODB_URI is missing
  if [ ! -z "$MONGODB_URI" ] && ! grep -q "MONGODB_URI" .env; then
    echo "Adding MONGODB_URI to .env file..."
    echo "MONGODB_URI=$MONGODB_URI" >> .env
  fi
fi

# Run the bot through our environment fixer
echo "Starting Discord bot through replit_run.py..."
PYTHONPATH="." PYTHONIOENCODING=utf-8 $PYTHON_PATH replit_run.py