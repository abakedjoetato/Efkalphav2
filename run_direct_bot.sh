#!/bin/bash
# A minimal runner for our direct Discord bot implementation

# Set up environment
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# Print banner
echo "  _____  _               _     ____        _   "
echo " |  __ \(_)             | |   |  _ \      | |  "
echo " | |  | |_ _ __ ___  ___| |_  | |_) | ___ | |_ "
echo " | |  | | | '__/ _ \/ __| __| |  _ < / _ \| __|"
echo " | |__| | | | |  __/ (__| |_  | |_) | (_) | |_ "
echo " |_____/|_|_|  \___|\___|\__| |____/ \___/ \__|"
echo "                                               "
echo " Direct Discord Bot Runner for Replit"
echo "-----------------------------------"
echo ""

# Run the bot
python3 direct_bot.py