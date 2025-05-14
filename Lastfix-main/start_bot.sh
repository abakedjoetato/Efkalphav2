#!/bin/bash
# Simple wrapper to start the bot using the launcher

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print a banner
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}         Discord Bot Starter          ${NC}"
echo -e "${BLUE}======================================${NC}"

# Check if launcher exists
if [ ! -f "launcher.sh" ]; then
    echo -e "${RED}Error: launcher.sh not found!${NC}"
    echo "This script must be run from the same directory as launcher.sh."
    exit 1
fi

# Make sure the launcher is executable
chmod +x launcher.sh

# Start the bot in the background, detached from the terminal
echo -e "${GREEN}Starting the bot using launcher.sh...${NC}"
echo -e "${YELLOW}The bot will continue running in the background.${NC}"
echo -e "${YELLOW}Check bot.log for output and error messages.${NC}"

nohup ./launcher.sh > /dev/null 2>&1 &

# Print the process ID
BOT_LAUNCHER_PID=$!
echo -e "${GREEN}Bot launcher started with PID: ${BOT_LAUNCHER_PID}${NC}"

# Save the PID to a file for later reference
echo $BOT_LAUNCHER_PID > bot_pid.txt
echo -e "${GREEN}PID saved to bot_pid.txt${NC}"

# Instructions for stopping the bot
echo -e "${BLUE}------ How to Stop the Bot ------${NC}"
echo -e "To stop the bot, run: ${YELLOW}kill \$(cat bot_pid.txt)${NC}"
echo -e "Or if that doesn't work: ${YELLOW}pkill -f launcher.sh${NC}"
echo -e "${BLUE}--------------------------------${NC}"

exit 0