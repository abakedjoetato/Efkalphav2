# How to Run the Discord Bot

This document explains the different ways to run the Discord bot in various environments, including Replit.

## Prerequisites

Before running the bot, make sure you have:

1. Set up the Discord Bot Token as an environment variable
   - In Replit: Set the `DISCORD_TOKEN` environment variable in the Secrets tab
   - Locally: Create a `.env` file with `DISCORD_TOKEN=your_token_here`

2. Set up the MongoDB connection string as an environment variable
   - In Replit: Set the `MONGODB_URI` environment variable in the Secrets tab
   - Locally: Add `MONGODB_URI=your_mongodb_connection_string` to your `.env` file

## Running Methods

### Method 1: Using Replit Run Button

The simplest way to run the bot on Replit is to use the Run button. This will execute `main.py`, which starts the bot process.

### Method 2: Using Replit Workflow (Recommended)

For more reliability and better monitoring in Replit:

1. Click on the "Tools" button in the sidebar
2. Choose "Workflows"
3. Select "Create workflow"
4. Enter settings:
   - Name: `discord_bot`
   - Command: `python start_discord_bot.py`
5. Enable "Prevent sleep"
6. Click "Create workflow"
7. Start the workflow

### Method 3: Using the Shell Scripts

For manual execution:

1. Open a Shell terminal
2. Run: `./run_discord_bot.sh`

### Method 4: Directly Running Python Files

For development or debugging:

1. `python main.py` - Simple entry point
2. `python replit_run.py` - Direct execution with detailed logging
3. `python start_discord_bot.py` - Managed execution with process monitoring

## Troubleshooting

If the bot fails to start:

1. Check bot logs in `bot.log`
2. Verify environment variables are set correctly
3. Check for MongoDB connection issues
4. Ensure Python libraries are installed (`pip install -r requirements_clean.txt`)

## Configuration

The bot can be configured by editing:

1. `replit_run.py` - Main initialization sequence
2. `bot.py` - Bot class and core functionality

## Database Setup

The bot requires MongoDB for full functionality. If MongoDB is not configured:

1. User profiles and stats will not be saved
2. Commands that rely on database operations will not function
3. Error messages will be shown when database-dependent features are used