"""
Simple Discord Bot

A minimal, functional Discord bot that connects and responds to commands.
"""

import os
import discord
from discord.ext import commands
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("simple_bot")

# Create bot instance with all intents
intents = discord.Intents.default()
intents.message_content = True  # Enables access to message content
intents.members = True  # Enables access to member data

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Called when the bot is ready to start receiving events."""
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Set presence
    await bot.change_presence(activity=discord.Game(name="!help for commands"))
    
    logger.info("Bot is ready!")

@bot.command(name="ping")
async def ping(ctx):
    """Simple ping command to check if bot is responsive."""
    await ctx.send(f"Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.command(name="hello")
async def hello(ctx):
    """Greets the user."""
    await ctx.send(f"Hello {ctx.author.mention}! How can I help you today?")

@bot.command(name="info")
async def info(ctx):
    """Provides information about the bot."""
    embed = discord.Embed(
        title="Bot Information",
        description="A simple Discord bot created as a starting point.",
        color=discord.Color.blue()
    )
    embed.add_field(name="Commands", value="!ping, !hello, !info", inline=False)
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="Users", value=str(sum(guild.member_count for guild in bot.guilds)), inline=True)
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Try !help to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument provided.")
    else:
        logger.error(f"Error in command {ctx.command}: {error}")
        await ctx.send("An error occurred while processing your command.")

def run_bot():
    """Run the Discord bot."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("No Discord token found. Please set the DISCORD_TOKEN environment variable.")
        return
    
    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        logger.error("Invalid Discord token. Please check your DISCORD_TOKEN environment variable.")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    run_bot()