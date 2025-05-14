#!/bin/bash
# Bot Launcher Script with Process Monitoring

# Configuration
LOG_FILE="bot.log"
MAX_RESTARTS=100
RESTART_DELAY=5
RESTART_COUNT=0
PYTHON_CMD="python3"
BOT_SCRIPT="run.py"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   Discord Bot Launcher & Monitor     ${NC}"
echo -e "${BLUE}======================================${NC}"

# Check if Python is installed
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED}Error: Python not found!${NC}"
    echo "Please install Python 3.8 or newer."
    exit 1
fi

# Check if bot script exists
if [ ! -f "$BOT_SCRIPT" ]; then
    echo -e "${RED}Error: Bot script '$BOT_SCRIPT' not found!${NC}"
    echo "Please make sure the script exists in the current directory."
    exit 1
fi

# Function to check if required secrets exist
check_secrets() {
    if [ -z "$DISCORD_TOKEN" ]; then
        echo -e "${YELLOW}Warning: DISCORD_TOKEN environment variable not set.${NC}"
        
        # Check if .env file exists and contains DISCORD_TOKEN
        if [ -f ".env" ] && grep -q "DISCORD_TOKEN" .env; then
            echo -e "${GREEN}Found DISCORD_TOKEN in .env file.${NC}"
        else
            echo -e "${RED}DISCORD_TOKEN not found in .env file.${NC}"
            echo "Please set the DISCORD_TOKEN environment variable or add it to .env file."
            return 1
        fi
    fi
    
    if [ -z "$MONGODB_URI" ]; then
        echo -e "${YELLOW}Warning: MONGODB_URI environment variable not set.${NC}"
        echo -e "${YELLOW}Some database features may not work properly.${NC}"
        
        # Check if .env file exists and contains MONGODB_URI
        if [ -f ".env" ] && grep -q "MONGODB_URI" .env; then
            echo -e "${GREEN}Found MONGODB_URI in .env file.${NC}"
        else
            echo -e "${YELLOW}MONGODB_URI not found in .env file.${NC}"
            echo "Database features may be limited."
        fi
    fi
    
    return 0
}

# Function to log with timestamp
log() {
    local level=$1
    local message=$2
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    case $level in
        "INFO")
            echo -e "${GREEN}[$timestamp] [INFO] $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}[$timestamp] [WARNING] $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}[$timestamp] [ERROR] $message${NC}"
            ;;
        *)
            echo -e "[$timestamp] $message"
            ;;
    esac
    
    # Also log to file
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Check required secrets
if ! check_secrets; then
    log "ERROR" "Critical secrets missing. Cannot start bot."
    exit 1
fi

# Set up signal handling for clean exit
trap handle_exit INT TERM
handle_exit() {
    log "INFO" "Received signal to stop. Shutting down gracefully..."
    
    # If we have the PID, try to kill the bot process
    if [ -n "$BOT_PID" ]; then
        kill -TERM $BOT_PID 2>/dev/null
        # Wait a bit to let it shut down properly
        sleep 2
        # Force kill if it's still running
        if kill -0 $BOT_PID 2>/dev/null; then
            kill -KILL $BOT_PID 2>/dev/null
            log "WARNING" "Had to force kill the bot process."
        fi
    fi
    
    log "INFO" "Bot launcher exiting."
    exit 0
}

# Function to run the bot in a loop
run_bot() {
    while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
        log "INFO" "Starting bot (Attempt $((RESTART_COUNT+1))/$MAX_RESTARTS)..."
        
        # Run the bot in the background and capture its PID
        $PYTHON_CMD $BOT_SCRIPT &
        BOT_PID=$!
        
        # Wait for the bot to exit
        wait $BOT_PID
        EXIT_CODE=$?
        
        # Check if bot exited normally or crashed
        if [ $EXIT_CODE -eq 0 ]; then
            log "INFO" "Bot exited normally with code $EXIT_CODE."
            break
        else
            log "ERROR" "Bot crashed with exit code $EXIT_CODE."
            RESTART_COUNT=$((RESTART_COUNT+1))
            
            if [ $RESTART_COUNT -lt $MAX_RESTARTS ]; then
                log "WARNING" "Restarting bot in $RESTART_DELAY seconds..."
                sleep $RESTART_DELAY
            else
                log "ERROR" "Maximum restart attempts ($MAX_RESTARTS) reached. Giving up."
                break
            fi
        fi
    done
    
    # If we reached the maximum restart count, exit with error
    if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
        log "ERROR" "Bot kept crashing. Please check the logs."
        exit 1
    fi
}

# Main execution
log "INFO" "Launcher starting..."

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
log "INFO" "Using Python $PYTHON_VERSION"

# Check for dependencies
log "INFO" "Checking dependencies..."
$PYTHON_CMD -c "import discord; print('discord.py/py-cord version:', discord.__version__)" 2>/dev/null
if [ $? -ne 0 ]; then
    log "ERROR" "Discord library not installed. Please install discord.py or py-cord."
    exit 1
fi

# Run the bot monitoring loop
run_bot

# If we reach here, the bot exited normally
log "INFO" "Launcher exiting."
exit 0