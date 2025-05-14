# Discord Bot Setup and Usage Guide

## Overview
This is a Discord bot built using py-cord and MongoDB. The bot is set up and ready to run in this Replit environment.

## Quick Start
1. Make sure your Discord token is set in the Replit Secrets tab
2. Run the bot using one of the methods below

## Starting the Bot

### Using the Shell Script (Easiest)
Simply run:
```
./run.sh
```

With debug mode:
```
./run.sh --debug
```

### Using the Python Launcher
You can start the bot using the enhanced launcher script:
```
python start_bot.py
```

Additional options:
```
# Run with debug mode enabled
python start_bot.py --debug
```

### Direct Method
Alternatively, you can run the bot directly:
```
python main.py
```

The bot will automatically:
1. Load all necessary cogs (command modules)
2. Connect to MongoDB (if configured)
3. Connect to Discord and make the bot available in your servers

## Environment Variables
The following environment variables are already configured:
- `DISCORD_TOKEN`: Your Discord bot token (stored securely in Replit secrets)

If you need to use MongoDB features, you can add:
- `MONGODB_URI`: Your MongoDB connection string

## Features
The bot includes numerous features such as:
- Error handling
- Admin commands
- Help system
- Setup commands
- Bounty system
- Player statistics
- Rivalries system
- CSV processing
- Event handling
- Economy system
- Guild settings
- Kill feed
- Log processing
- Player linking

## Project Structure
- `main.py`: Entry point for the bot
- `replit_run.py`: Actual bot initialization code
- `bot.py`: Main bot class definition
- `cogs/`: Directory containing all command modules
- `utils/`: Utility functions and helpers
- `models/`: Data models for MongoDB

## How to Add the Bot to Your Server
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Navigate to the "OAuth2" section
4. Under "URL Generator", select the "bot" and "applications.commands" scopes
5. Select the bot permissions you need
6. Copy the generated URL and open it in a browser
7. Select the server to add the bot to

## Running as a Service (Advanced)
If you want to run the bot on your own server as a background service:

1. Copy the `discord-bot.service` file to your system's systemd directory:
   ```
   sudo cp discord-bot.service /etc/systemd/system/
   ```

2. Edit the service file to include your specific paths and username:
   ```
   sudo nano /etc/systemd/system/discord-bot.service
   ```

3. Enable and start the service:
   ```
   sudo systemctl enable discord-bot.service
   sudo systemctl start discord-bot.service
   ```

4. Check the status:
   ```
   sudo systemctl status discord-bot.service
   ```

## Troubleshooting
If you encounter issues:
- Check the console logs for error messages
- Ensure your Discord token is correctly set
- If using MongoDB, verify the connection string is correct