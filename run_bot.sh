#!/bin/bash

# Ensure script fails on error
set -e

echo "Starting Tower of Temptation Discord Bot..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check for virtual environment
if [ ! -d ".pythonlibs" ]; then
    echo "Virtual environment not found, dependencies may not be installed correctly."
    echo "Please run 'pip install -r requirements.txt' first."
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Using default environment variables."
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the bot
echo "Launching bot..."
python3 main.py

exit 0