"""
Bot Adapter Module

This module provides a clean interface to interact with Discord API using py-cord,
while respecting the structure and expectations of our existing codebase.
"""

import os
import sys
import time
import asyncio
import logging
import datetime
import traceback
import importlib
from typing import Dict, List, Any, Optional, Union, Callable

# Import from compatibility layer
import discord_compat_layer as dcl
from discord_compat_layer import (
    Embed, Color, Bot, Cog, Intents,
    Context, Activity, ActivityType
)

# Import utilities
from utils.error_telemetry import get_error_telemetry
from utils.mongodb_adapter import get_mongodb_adapter
from utils.premium_manager_enhanced import get_premium_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("bot_adapter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotAdapter:
    """
    Adapter for Discord Bot to work with py-cord while maintaining compatibility
    with the existing codebase structure.
    """
    def __init__(self, token=None, command_prefix="!", description=None, debug_guilds=None):
        """Initialize the bot adapter"""
        # Configuration
        self.token = token or os.environ.get("DISCORD_TOKEN")
        self.command_prefix = command_prefix
        self.description = description or "Discord Bot with modular architecture"
        self.debug_guilds = debug_guilds
        
        # Create intents with all permissions
        intents = dcl.create_intents()
        
        # Create bot instance
        self.bot = Bot(
            command_prefix=self.command_prefix,
            description=self.description,
            intents=intents
        )
        
        # Add utility attributes
        self.bot.adapter = self
        
        # Components
        self.db = None  # MongoDB adapter
        self.premium_manager = None  # Premium features manager
        self.error_telemetry = get_error_telemetry(self.bot)
        
        # Setup event handlers
        self._setup_event_handlers()
        
        logger.info("Bot adapter initialized")
    
    def _setup_event_handlers(self):
        """Set up event handlers for the bot"""
        
        @self.bot.event
        async def on_ready():
            """Called when the bot is ready"""
            # Set presence
            activity = Activity(
                type=ActivityType.listening,
                name=f"{self.command_prefix}help | {len(self.bot.guilds)} servers"
            )
            await self.bot.change_presence(activity=activity)
            
            # Log bot information
            guilds = len(self.bot.guilds)
            users = sum(g.member_count for g in self.bot.guilds)
            
            logger.info(f"Logged in as {self.bot.user.name} (ID: {self.bot.user.id})")
            logger.info(f"Connected to {guilds} guilds with {users} users")
            logger.info(f"Using command prefix: {self.command_prefix}")
            
            # Sync application commands if debugging guilds are specified
            if self.debug_guilds:
                try:
                    logger.info(f"Syncing commands to guilds: {self.debug_guilds}")
                    await self.bot.sync_commands(guild_ids=self.debug_guilds)
                except Exception as e:
                    logger.error(f"Error syncing commands: {e}")
        
        @self.bot.event
        async def on_command_error(ctx, error):
            """Global error handler for commands"""
            # Handle specific error types differently
            if isinstance(error, dcl.CommandNotFound):
                # Don't log command not found errors
                return
                
            elif isinstance(error, dcl.MissingRequiredArgument):
                # Create a user-friendly error message
                embed = Embed(
                    title="Missing Argument",
                    description=f"You're missing the `{error.param.name}` argument for this command.",
                    color=Color.yellow()
                )
                embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
                await ctx.send(embed=embed)
                
            elif isinstance(error, dcl.BadArgument):
                # Create a user-friendly error message
                embed = Embed(
                    title="Invalid Argument",
                    description=f"You provided an invalid argument for this command.",
                    color=Color.yellow()
                )
                embed.add_field(name="Error", value=str(error))
                embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
                await ctx.send(embed=embed)
                
            else:
                # Log the error
                error_type = error.__class__.__name__
                error_msg = str(error)
                
                # Create a user-friendly error message
                embed = Embed(
                    title="Command Error",
                    description=f"An error occurred while executing this command.",
                    color=Color.red()
                )
                embed.add_field(name="Error Type", value=error_type)
                embed.add_field(name="Error Message", value=error_msg[:1024])
                embed.set_footer(text="This error has been logged and will be investigated.")
                await ctx.send(embed=embed)
                
                # Log detailed error information
                logger.error(f"Command error in {ctx.command}: {error_type}: {error_msg}")
                traceback.print_exception(type(error), error, error.__traceback__)
                
                # Log to error telemetry
                if self.error_telemetry:
                    context = {
                        'guild_id': ctx.guild.id if ctx.guild else None,
                        'channel_id': ctx.channel.id,
                        'user_id': ctx.author.id,
                        'command': ctx.command.qualified_name,
                        'message': ctx.message.content
                    }
                    self.error_telemetry.log_error(error, context, ctx.command.qualified_name)
    
    async def connect_to_database(self):
        """Connect to MongoDB database"""
        try:
            # Get MongoDB adapter
            self.db = get_mongodb_adapter()
            
            # Connect to database
            connected = await self.db.connect()
            
            if connected:
                logger.info("Connected to MongoDB database")
                
                # Initialize premium manager with database
                self.premium_manager = get_premium_manager(self.db)
                
                # Start premium cache cleanup task
                self.bot.create_task(self.premium_manager.start_cache_cleanup_task(), name="premium_cache_cleanup")
                
                return True
            else:
                logger.error("Failed to connect to MongoDB database")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            return False
    
    async def setup_premium_manager(self):
        """Set up premium features manager"""
        if not self.db:
            logger.warning("Cannot set up premium manager without database connection")
            return False
        
        try:
            # Initialize premium manager if not already done
            if not self.premium_manager:
                self.premium_manager = get_premium_manager(self.db)
            
            # Check if premium collections exist
            guild_premium_collection = await self.db.get_collection('guild_premium')
            user_premium_collection = await self.db.get_collection('user_premium')
            
            if guild_premium_collection and user_premium_collection:
                logger.info("Premium manager set up successfully")
                return True
            else:
                logger.warning("Premium collections not found in database")
                return False
        
        except Exception as e:
            logger.error(f"Error setting up premium manager: {e}")
            return False
    
    async def load_cogs(self, cogs_dir="cogs"):
        """Load all cogs from the specified directory"""
        loaded_cogs = []
        failed_cogs = []
        
        try:
            # Get list of cog files
            cog_files = [f for f in os.listdir(cogs_dir) if f.endswith('.py') and not f.startswith('_')]
            
            # Log cog loading
            logger.info(f"Found {len(cog_files)} cogs to load")
            
            # Load each cog
            for cog_file in cog_files:
                cog_name = cog_file[:-3]  # Remove .py extension
                cog_path = f"{cogs_dir}.{cog_name}"
                
                try:
                    # Load cog
                    await self.bot.load_extension(cog_path)
                    loaded_cogs.append(cog_name)
                    logger.info(f"Loaded cog: {cog_name}")
                
                except Exception as e:
                    failed_cogs.append((cog_name, str(e)))
                    logger.error(f"Failed to load cog {cog_name}: {e}")
                    traceback.print_exception(type(e), e, e.__traceback__)
            
            # Log results
            if loaded_cogs:
                logger.info(f"Successfully loaded {len(loaded_cogs)} cogs: {', '.join(loaded_cogs)}")
            
            if failed_cogs:
                logger.error(f"Failed to load {len(failed_cogs)} cogs:")
                for cog_name, error in failed_cogs:
                    logger.error(f"  - {cog_name}: {error}")
            
            return loaded_cogs, failed_cogs
        
        except Exception as e:
            logger.error(f"Error loading cogs: {e}")
            return loaded_cogs, failed_cogs
    
    async def start(self):
        """Start the bot with proper initialization"""
        try:
            # Connect to database
            await self.connect_to_database()
            
            # Set up premium manager
            await self.setup_premium_manager()
            
            # Load cogs
            await self.load_cogs()
            
            # Login and connect to Discord
            logger.info("Starting bot...")
            await self.bot.start(self.token)
        
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
    
    async def close(self):
        """Close the bot and database connections"""
        try:
            # Disconnect from database
            if self.db:
                await self.db.disconnect()
            
            # Close bot connection
            await self.bot.close()
            
            logger.info("Bot has been closed")
        
        except Exception as e:
            logger.error(f"Error closing bot: {e}")
            raise
    
    def run(self):
        """Run the bot (blocking)"""
        try:
            # Run the bot
            asyncio.run(self.start())
        
        except KeyboardInterrupt:
            logger.info("Bot stopped by keyboard interrupt")
        
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            traceback.print_exception(type(e), e, e.__traceback__)
        
        finally:
            # Ensure bot is closed properly
            logger.info("Cleaning up...")
            try:
                if self.bot and self.bot.loop.is_running():
                    asyncio.run(self.close())
            except:
                pass

def create_bot(token=None, command_prefix="!", description=None, debug_guilds=None):
    """Create a new bot adapter instance"""
    return BotAdapter(token, command_prefix, description, debug_guilds)