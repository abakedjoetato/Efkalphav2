#!/bin/bash
# Simple Discord Bot Launch Script
# This script launches a minimal Discord bot with maximum compatibility

# Print header
echo "============================="
echo "  Simple Discord Bot Launch  "
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

# Run the bot
echo "Starting Simple Discord Bot..."
$PYTHON_PATH simple_bot.py