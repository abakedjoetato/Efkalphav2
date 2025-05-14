#!/bin/bash
# Launch the Discord bot
# This script launches the Discord bot with all fixes applied

# Print header
echo "============================="
echo "     Discord Bot Launch      "
echo "============================="
echo ""

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

# Run the bot launcher
echo "Launching Discord bot..."
python3 launch_bot.py