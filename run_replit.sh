#!/bin/bash

# Script to run the Discord bot on Replit

# Ensure logs directory exists
mkdir -p logs

# Run the bot with proper Python path
echo "Starting Discord bot via run_replit.py..."
exec python3 run_replit.py