# Discord Bot Quick Start Guide

This quick start guide will help you get your Discord bot up and running in just a few steps.

## Prerequisites
- Your Discord bot token (set in Replit Secrets as DISCORD_TOKEN)
- MongoDB URI (optional, for advanced features)

## Starting the Bot

### Option 1: Using the Run Script (Recommended)
```
./run.sh
```

### Option 2: Using the Python Launcher
```
python start_bot.py
```

### Option 3: Direct Method
```
python main.py
```

## Verifying the Bot is Working
When the bot starts successfully, you should see:
- "Bot logged in as [Your Bot Name]"
- "Connected to [number] guilds"
- "Application commands synced!"
- "Bot is ready!"

## Testing the Bot
Try using some of the bot's commands in your Discord server:
- `/help` - Get a list of available commands
- `/ping` - Check if the bot is responsive
- `/info` - Get information about the bot

## Troubleshooting
If you encounter any issues:
1. Check that your Discord token is correctly set
2. Make sure the bot has been invited to your server
3. Verify the bot has the necessary permissions
4. Look for error messages in the console logs

## Management Tools
Use the management script to check your setup:
```
python manage.py
```

## Additional Resources
- See `README_REPLIT.md` for detailed setup instructions
- Check `DISCORD_BOT_MANUAL.md` for comprehensive documentation
- Review the Cogs folder to understand available commands