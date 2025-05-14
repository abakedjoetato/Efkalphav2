#!/bin/bash
# A simple launcher for our Discord bot in Replit

# Set up environment
export PYTHONPATH="$PYTHONPATH:$(pwd)"

# Print banner
echo "  ____  _                       _   ____        _   "
echo " |  _ \(_)___  ___ ___  _ __ __| | | __ )  ___ | |_ "
echo " | | | | / __|/ __/ _ \| '__/ _\` | |  _ \ / _ \| __|"
echo " | |_| | \__ \ (_| (_) | | | (_| | | |_) | (_) | |_ "
echo " |____/|_|___/\___\___/|_|  \__,_| |____/ \___/ \__|"
echo "                                                    "
echo " Simple Discord Bot Runner for Replit"
echo "--------------------------------------"
echo ""

# Run the bot
python3 run_bot.py