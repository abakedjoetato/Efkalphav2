# Tower of Temptation Discord Bot

A Discord bot for the Tower of Temptation game, built with Python, Pycord, and MongoDB for data persistence.

## Important: Running Without Web Server

This bot runs directly without using any web server components (no Flask, no gunicorn). It uses a custom launcher system with process management and heartbeat mechanisms to keep the bot running.

## Setup Instructions

### Prerequisites

- Python 3.11+
- A Discord bot token
- MongoDB database

### Environment Variables

Required environment variables:

```
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_token_here

# MongoDB Configuration
MONGODB_URI=mongodb://username:password@host:port/database
```

### Running the Bot

There are several ways to run the bot:

#### Method 1: Simplified Replit Entry Point (Recommended for Replit)
```bash
python replit_run.py
```

#### Method 2: Using the Main Entry Point
```bash
python main.py
```

#### Method 3: Using the Start Scripts
```bash
# Basic start script
bash start.sh

# Managed process with auto-restart
bash start_bot.sh

# Replit-specific run script
./run
```

#### Method 4: Using Launcher (Longer-running deployments)
```bash
bash launcher.sh
```

#### Method 5: Using Replit's Run Button
Simply click the "Run" button in Replit, which will execute the default run command through main.py.

## Bot Features

- PvP statistics tracking
- Player rivalries
- Guild settings management
- Premium features
- Economy system
- Factions
- More features coming soon!

## MongoDB Database

The bot requires a MongoDB database for data persistence. Make sure to set the `MONGODB_URI` environment variable to your MongoDB connection string.

The bot will attempt to establish a connection to MongoDB at startup and will handle connection errors gracefully, retrying with backoff when needed.

## Discord Bot Token

You'll need to create a Discord bot and get a token. Instructions:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under the "TOKEN" section, click "Copy" to get your token
5. Add this token to your `.env` file

## Troubleshooting

- If you see "DISCORD_TOKEN not set" warnings, make sure you've properly set up your environment variables
- If you encounter a "No default database name defined or provided" error, the bot will automatically use 'tower_of_temptation' as the database name
- For detailed log information, check the following log files:
  - `bot.log`: Contains bot operation logs
  - `app.log`: Contains app launcher logs
- If the bot stops unexpectedly, the app_enhanced.py launcher will automatically attempt to restart it
- All cogs in the codebase are required and must be fixed to function properly. Any errors during cog loading should be addressed

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.