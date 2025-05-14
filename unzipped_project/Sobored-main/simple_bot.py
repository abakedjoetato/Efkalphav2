"""
Simple Discord Bot

A minimal Discord bot implementation that works with any version of discord.py or py-cord.
"""

import os
import sys
import logging
import importlib.util
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SimpleBot")

# Load environment variables
load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")

# Check for token
if not TOKEN:
    logger.error("DISCORD_TOKEN environment variable is not set")
    sys.exit(1)

# Try to import discord in a way that works with any version
try:
    # First try importing py-cord
    try:
        import py_cord as discord
        logger.info("Successfully imported py-cord module as discord")
    except ImportError:
        # Fall back to regular discord import
        import discord
        logger.info("Successfully imported discord module")
    
    # Function to safely get attribute
    def safe_get_attr(obj, attr_name):
        return getattr(obj, attr_name, None)
    
    # Create a bot class that works with any discord library
    class SimpleBot:
        def __init__(self):
            # Create intents - handle any discord library version
            try:
                intents = discord.Intents.default()
                try:
                    intents.message_content = True
                except:
                    logger.info("message_content intent not available")
                    
                try:
                    intents.members = True
                except:
                    logger.info("members intent not available")
                    
                # Create client with intents
                self.client = discord.Client(intents=intents)
                logger.info("Created Discord client with intents")
            except:
                # Fallback for very old discord.py versions
                logger.info("Intents not available, creating basic client")
                self.client = discord.Client()
            
            # Register event handlers
            @self.client.event
            async def on_ready():
                logger.info(f"Logged in as {self.client.user}")
                logger.info(f"Connected successfully!")
                
            @self.client.event
            async def on_message(message):
                # Don't respond to our own messages
                if message.author == self.client.user:
                    return
                    
                # Simple ping command
                if message.content.startswith('!ping'):
                    await message.channel.send('Pong!')
                    
                # Info command
                if message.content.startswith('!info'):
                    try:
                        embed_class = safe_get_attr(discord, 'Embed')
                        color_class = safe_get_attr(discord, 'Color')
                        
                        if embed_class and color_class:
                            embed = embed_class(
                                title="Simple Discord Bot",
                                description="A minimal bot implementation",
                                color=color_class.green()
                            )
                            
                            # Add version info if available
                            version = safe_get_attr(discord, '__version__')
                            lib_name = "py-cord" if hasattr(discord, 'application_commands') else "discord.py"
                            embed.add_field(
                                name="Library", 
                                value=f"{lib_name} {version or 'unknown'}", 
                                inline=True
                            )
                            
                            await message.channel.send(embed=embed)
                        else:
                            await message.channel.send(
                                "Simple Discord Bot\n"
                                "A minimal bot implementation"
                            )
                    except Exception as e:
                        logger.error(f"Error sending embed: {e}")
                        await message.channel.send("Simple Discord Bot - A minimal implementation")
                
        def run(self):
            """Run the bot"""
            try:
                logger.info("Starting bot...")
                self.client.run(TOKEN)
            except Exception as e:
                logger.error(f"Error running bot: {e}")
                sys.exit(1)
                
except ImportError as e:
    logger.error(f"Failed to import Discord module: {e}")
    sys.exit(1)

def main():
    """Run the Discord bot"""
    logger.info("Initializing Simple Discord Bot")
    bot = SimpleBot()
    bot.run()
    
if __name__ == "__main__":
    main()