#!/bin/bash
# Start script for the Discord bot

# Check if python is installed
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Error: Python not found"
    exit 1
fi

# Run the bot
$PYTHON run.py