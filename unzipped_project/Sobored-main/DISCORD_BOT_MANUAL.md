# Discord Bot Manual

## Overview
This Discord bot is built using py-cord and MongoDB. It provides various features to enhance your Discord server experience including stats tracking, bounties, rivalries, and more.

## Setup Requirements
- Python 3.11+
- Discord Bot Token (set in environment variables)
- MongoDB URI (optional, for advanced features)

## Quick Start
1. Ensure your Discord token is set as an environment variable
2. Run the bot using `./run.sh` or `python start_bot.py`
3. The bot will connect to Discord and be ready to use in your server

## Startup Methods

### Method 1: Using the Shell Script (Recommended)
```bash
./run.sh
```

With debug mode:
```bash
./run.sh --debug
```

### Method 2: Using the Python Launcher
```bash
python start_bot.py
```

With debug mode:
```bash
python start_bot.py --debug
```

### Method 3: Direct Python Execution
```bash
python main.py
```

## Maintenance and Management
You can use the management script to check your setup and perform maintenance:

```bash
# Run all checks
python manage.py

# Check environment variables
python manage.py --check

# Test Discord token
python manage.py --test-token

# Create a backup
python manage.py --backup
```

## Bot Features
This bot includes the following key features:

- **Admin Commands**: Server management and bot controls
- **Bounty System**: Create and track bounties
- **Player Statistics**: Track and display player stats
- **Rivalries System**: Create and manage player rivalries
- **CSV Processing**: Import and process game data from CSV files
- **Event Handling**: Respond to in-game events
- **Economy System**: In-server currency and transactions
- **Kill Feed**: Display game kills in real-time
- **Log Processing**: Process game logs for stats
- **Player Linking**: Link Discord users to game accounts

## Troubleshooting

### Bot Won't Connect
- Ensure your Discord token is correctly set
- Check internet connectivity
- Verify the bot has proper permissions in your server

### Missing Features
- Some features require MongoDB to be configured
- Check console logs for any error messages
- Verify all dependencies are installed correctly

### Command Errors
- Check command syntax and permissions
- Ensure the bot has necessary permissions in your server
- Review error messages in the console logs

## Getting Help
If you need further assistance:

1. Check the error logs in the console
2. Refer to the documentation in the repo
3. Look for error patterns in the cogs loaded during startup

## Advanced Configuration
For advanced users wanting to customize the bot:

- Edit cog files in the `cogs/` directory
- Modify MongoDB schemas in `models/` directory
- Adjust utility functions in `utils/` directory

## Security Notes
- Never share your Discord token
- Keep your environment variables secure
- Regularly backup your bot configuration