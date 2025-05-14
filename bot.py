"""
Discord Bot Implementation

This module contains the main Bot class that extends discord.py's commands.Bot
with additional functionality such as enhanced error handling and MongoDB integration.
"""

import os
import sys
import time
import traceback
import asyncio
import logging
import datetime
from typing import Dict, List, Any, Optional, Union, Callable

# Import discord.py
import discord
from discord.ext import commands

# Local imports
try:
    from utils.safe_mongodb import SafeMongoDBClient, SafeMongoDBResult
    from config import config
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

# Configure logger
logger = logging.getLogger("bot")

class Bot(commands.Bot):
    """
    Main bot class with enhanced error handling and initialization
    
    This class extends discord.py's commands.Bot with additional functionality
    such as enhanced error handling, database integration, and premium features.
    """
    
    def __init__(self, *, production: bool = False, debug_guilds: Optional[List[int]] = None):
        """
        Initialize the bot with proper intents and configuration
        
        Args:
            production: Whether the bot is running in production mode
            debug_guilds: List of guild IDs for debug commands
        """
        # Set up intents
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = True
        
        # Get prefix from config
        prefix = config.get("discord", {}).get("prefix", "!")
        
        # Call parent constructor
        super().__init__(
            command_prefix=commands.when_mentioned_or(prefix),
            intents=intents,
            case_insensitive=True,
            strip_after_prefix=True,
            activity=discord.Game(name=f"Type {prefix}help for help")
        )
        
        # Set attributes
        self.production = production
        self.debug_guilds = debug_guilds or []
        self.start_time = datetime.datetime.utcnow()
        self.prefix = prefix
        
        # Database attributes
        self._db_client = None
        self._db = None
        
        # Premium manager
        self.premium_manager = None
        
        # Background tasks
        self.bg_tasks = {}
        
        # Set up global error handlers
        self.setup_error_handlers()
        
        # Add additional check for command permissions
        self.add_check(self.global_command_check)
    
    def setup_error_handlers(self):
        """Set up global error handlers"""
        
        @self.event
        async def on_error(event, *args, **kwargs):
            """Global error handler for bot events"""
            error_info = sys.exc_info()
            exception = error_info[1]
            
            logger.error(f"Error in event {event}: {exception}")
            
            # Print error traceback
            traceback.print_exception(*error_info)
    
    @property
    def db(self):
        """
        Database property with error handling
        
        Returns:
            MongoDB database instance
        
        Raises:
            RuntimeError: If database is not initialized
        """
        if not self._db:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        
        return self._db
    
    async def init_db(self, max_retries=3, retry_delay=2):
        """
        Initialize database connection with error handling and retries
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Seconds to wait between retries
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        db_config = config.get("mongodb", {})
        uri = db_config.get("uri") or os.environ.get("MONGODB_URI", "mongodb://localhost:27017/discordbot")
        db_name = db_config.get("db_name") or os.environ.get("DB_NAME", "discordbot")
        
        logger.info(f"Connecting to MongoDB database: {db_name}")
        
        # Create the client
        self._db_client = SafeMongoDBClient(uri, db_name)
        
        # Try to connect with retries
        for retry in range(max_retries):
            try:
                result = await self._db_client.connect()
                
                if result.success:
                    logger.info(f"Connected to MongoDB database: {db_name}")
                    self._db = self._db_client.database
                    return True
                else:
                    logger.error(f"Failed to connect to MongoDB: {result.error}")
                    
                    if retry < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error("Maximum retries reached")
                        return False
            except Exception as e:
                logger.error(f"Error connecting to MongoDB: {e}")
                
                if retry < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("Maximum retries reached")
                    return False
        
        return False
    
    async def on_ready(self):
        """Handle bot ready event with additional setup"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        
        # Sync application commands
        if not self.debug_guilds:
            logger.info("Syncing global commands...")
            await self.sync_commands()
        else:
            logger.info(f"Syncing commands to debug guilds: {self.debug_guilds}")
            for guild_id in self.debug_guilds:
                guild = self.get_guild(guild_id)
                if guild:
                    logger.info(f"Syncing commands to guild: {guild.name} ({guild.id})")
                    await self.sync_commands(guild_ids=[guild_id])
        
        # Start background task monitor
        self.start_background_task_monitor()
        
        # Start task to check expired premium subscriptions
        if self.premium_manager:
            self.create_background_task(
                self.check_expired_premium_subscriptions(),
                "premium_subscription_checker",
                critical=True
            )
    
    _sync_in_progress = False
    
    async def sync_commands(self, commands=None, method=None, force=False, guild_ids=None, 
                       register_guild_commands=True, check_guilds=True, delete_existing=False):
        """
        Sync application commands with proper error handling
        
        This method extends the parent class method with additional safety checks and error handling.
        
        Args:
            commands: Commands to sync (default: None for all commands)
            method: The sync method to use (default: None)
            force: Whether to force the sync (default: False)
            guild_ids: List of guild IDs to sync to (default: None)
            register_guild_commands: Whether to register guild commands (default: True)
            check_guilds: Whether to check guilds (default: True)
            delete_existing: Whether to delete existing commands (default: False)
        """
        # Prevent multiple syncs at the same time
        if self._sync_in_progress:
            logger.warning("Command sync already in progress, skipping")
            return
        
        self._sync_in_progress = True
        
        try:
            logger.info("Syncing commands...")
            
            if guild_ids:
                logger.info(f"Syncing to specific guild IDs: {guild_ids}")
            else:
                logger.info("Syncing global commands")
                
            result = await super().sync_commands(
                commands=commands,
                method=method,
                force=force,
                guild_ids=guild_ids,
                register_guild_commands=register_guild_commands,
                check_guilds=check_guilds,
                delete_existing=delete_existing
            )
            
            logger.info("Command sync complete")
            return result
        except Exception as e:
            logger.error(f"Error syncing commands: {e}")
            return None
        finally:
            self._sync_in_progress = False
    
    def load_extension(self, name: str, *, package: Optional[str] = None, recursive: bool = False) -> List[str]:
        """
        Load a bot extension with enhanced error handling
        
        Args:
            name: Name of the extension to load
            package: Package to import from
            recursive: Whether to recursively load submodules (for discord.py compatibility)
        
        Returns:
            List[str]: For compatibility with CogMixin, returns a list of loaded extension names
        
        Raises:
            commands.ExtensionError: If loading fails
        """
        try:
            # Call parent method
            super().load_extension(name, package=package)
            return [name]
        except commands.ExtensionError as e:
            logger.error(f"Error loading extension {name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading extension {name}: {e}")
            raise commands.ExtensionFailed(name, e)
    
    async def load_extension_async(self, name: str, *, package: Optional[str] = None) -> List[str]:
        """
        Asynchronous helper to load a bot extension with enhanced error handling
        
        Args:
            name: Name of the extension to load
            package: Package to import from
        
        Returns:
            List[str]: List of loaded extension names
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: self.load_extension(name, package=package)
            )
        except Exception as e:
            logger.error(f"Error loading extension {name}: {e}")
            return []
    
    def start_background_task_monitor(self):
        """Start a background task to monitor other background tasks"""
        async def monitor_background_tasks():
            while not self.is_closed():
                # Check all background tasks
                for task_name, task_info in list(self.bg_tasks.items()):
                    task = task_info["task"]
                    critical = task_info["critical"]
                    
                    # If task is done, check if it failed
                    if task.done():
                        try:
                            # This will re-raise any exception from the task
                            exc = task.exception()
                            if exc:
                                logger.error(f"Background task {task_name} failed with error: {exc}")
                                
                                # If critical, restart the task
                                if critical and not self.is_closed():
                                    logger.info(f"Restarting critical background task: {task_name}")
                                    self.create_background_task(
                                        task_info["coro"], task_name, critical=True
                                    )
                            else:
                                logger.info(f"Background task {task_name} completed successfully")
                                # Remove the task from the list
                                self.bg_tasks.pop(task_name, None)
                        except asyncio.CancelledError:
                            logger.info(f"Background task {task_name} was cancelled")
                            # Remove the task from the list
                            self.bg_tasks.pop(task_name, None)
                        except asyncio.InvalidStateError:
                            # Task is not done yet
                            pass
                
                # Check every 60 seconds
                await asyncio.sleep(60)
        
        # Start the monitor
        monitor_task = self.loop.create_task(monitor_background_tasks())
        monitor_task.set_name("bg_task_monitor")
    
    def create_background_task(self, coro, name, critical=False):
        """
        Create and track a background task with proper naming
        
        Args:
            coro: Coroutine to run as a background task
            name: Name of the task for tracking  
            critical: Whether the task is critical and should be auto-restarted
        """
        # Cancel existing task with the same name if it exists
        if name in self.bg_tasks:
            old_task = self.bg_tasks[name]["task"]
            if not old_task.done():
                logger.info(f"Cancelling existing background task: {name}")
                old_task.cancel()
        
        # Create the task
        task = self.loop.create_task(coro)
        task.set_name(name)
        
        # Add callback for when the task is done
        task.add_done_callback(lambda t: self.task_done(t, name))
        
        # Store the task
        self.bg_tasks[name] = {
            "task": task,
            "critical": critical,
            "coro": coro
        }
        
        logger.info(f"Started background task: {name}")
        return task
    
    def task_done(self, task, name):
        """
        Callback for when a background task is done
        
        Args:
            task: The task that completed
            name: The name of the task
        """
        # Just log errors, the monitor will handle restarting if needed
        try:
            exc = task.exception()
            if exc:
                logger.error(f"Background task {name} failed with error: {exc}")
                logger.error(f"Traceback: {traceback.format_exception(type(exc), exc, exc.__traceback__)}")
        except (asyncio.CancelledError, asyncio.InvalidStateError):
            # Task was cancelled or is not done yet
            pass
    
    async def check_expired_premium_subscriptions(self):
        """Background task to check for expired premium subscriptions"""
        while not self.is_closed():
            try:
                # Check for expired subscriptions
                if self.premium_manager:
                    expired_guilds, expired_users = await self.premium_manager.check_and_remove_expired()
                    if expired_guilds > 0 or expired_users > 0:
                        logger.info(f"Removed premium from {expired_guilds} expired guilds and {expired_users} expired users")
            except Exception as e:
                logger.error(f"Error checking expired premium subscriptions: {e}")
            
            # Check every hour
            await asyncio.sleep(3600)
    
    async def global_command_check(self, ctx):
        """
        Global check for commands to enforce premium features
        
        Args:
            ctx: Command context
            
        Returns:
            bool: Whether the command can be run
        """
        # Owner can always run commands
        if await self.is_owner(ctx.author):
            return True
        
        # Get the command's cog
        cog = ctx.command.cog
        
        if cog:
            # Check if the cog requires premium
            premium_required = getattr(cog, "premium_required", False)
            premium_feature = getattr(cog, "premium_feature", None)
            
            if premium_required or premium_feature:
                # For DMs, check the user's premium status
                if ctx.guild is None:
                    if not self.premium_manager:
                        return False
                    
                    return await self.premium_manager.is_user_premium(ctx.author.id)
                
                # For guilds, check the guild's premium status
                if premium_feature:
                    if not self.premium_manager:
                        return False
                    
                    # Check if the guild has the specific premium feature
                    has_feature = await self.premium_manager.can_use_feature(ctx.guild.id, premium_feature)
                    if not has_feature:
                        await ctx.send(f"This command requires the premium feature: `{premium_feature}`")
                        return False
                
                elif premium_required:
                    if not self.premium_manager:
                        return False
                    
                    # Check if the guild has premium
                    is_premium = await self.premium_manager.is_guild_premium(ctx.guild.id)
                    if not is_premium:
                        await ctx.send("This command requires a premium subscription.")
                        return False
        
        return True
    
    async def on_command_error(self, context, exception):
        """
        Global command error handler
        
        Args:
            context: The context object for the command
            exception: The exception raised
        """
        if isinstance(exception, commands.CommandNotFound):
            # Ignore CommandNotFound errors
            return
        
        if isinstance(exception, commands.MissingRequiredArgument):
            await context.send(f"Missing required argument: `{exception.param.name}`")
            return
        
        if isinstance(exception, commands.BadArgument):
            await context.send(f"Bad argument: {str(exception)}")
            return
        
        if isinstance(exception, commands.MissingPermissions):
            perms = ", ".join(exception.missing_permissions)
            await context.send(f"You need the following permissions to use this command: `{perms}`")
            return
        
        if isinstance(exception, commands.BotMissingPermissions):
            perms = ", ".join(exception.missing_permissions)
            await context.send(f"I need the following permissions to run this command: `{perms}`")
            return
        
        if isinstance(exception, commands.CheckFailure):
            # This is a generic check failure, which could be premium checks or other checks
            # The message would have already been sent in the check function
            return
        
        if isinstance(exception, commands.CommandOnCooldown):
            await context.send(f"This command is on cooldown. Try again in {exception.retry_after:.1f} seconds.")
            return
        
        if isinstance(exception, commands.NoPrivateMessage):
            await context.send("This command cannot be used in private messages.")
            return
        
        # For other errors, log the error
        logger.error(f"Error in command {context.command}: {exception}")
        logger.error(f"Command was invoked with {context.args}, {context.kwargs}")
        
        # Print traceback
        traceback.print_exception(type(exception), exception, exception.__traceback__)
        
        # Send a message to the user
        await context.send("An error occurred while running the command. Please try again later.")
    
    async def on_application_command_error(self, context: Any, exception: Exception):
        """
        Global application command error handler
        
        Args:
            context: The context (ApplicationContext or Interaction depending on py-cord version)
            exception: The exception raised
        """
        # Log the error
        logger.error(f"Error in application command: {exception}")
        
        # Print traceback
        traceback.print_exception(type(exception), exception, exception.__traceback__)
        
        # Send a message to the user
        await self._respond_to_interaction(context, "An error occurred while running the command. Please try again later.")
    
    async def _respond_to_interaction(self, interaction, message, ephemeral=False):
        """
        Helper method to safely respond to an interaction.
        
        Args:
            interaction: The Discord interaction to respond to
            message: The message to send
            ephemeral: Whether the message should be ephemeral
        """
        try:
            if hasattr(interaction, 'response') and hasattr(interaction.response, 'send_message'):
                # This is a discord.py Interaction
                if interaction.response.is_done():
                    await interaction.followup.send(message, ephemeral=ephemeral)
                else:
                    await interaction.response.send_message(message, ephemeral=ephemeral)
            elif hasattr(interaction, 'respond'):
                # This is a py-cord ApplicationContext
                await interaction.respond(message, ephemeral=ephemeral)
            else:
                # Not sure what this is, try our best
                for attr in ['send', 'respond', 'reply', 'send_message']:
                    if hasattr(interaction, attr):
                        method = getattr(interaction, attr)
                        if callable(method):
                            try:
                                kwargs = {}
                                if attr == 'send_message':
                                    kwargs['ephemeral'] = ephemeral
                                await method(message, **kwargs)
                                return
                            except Exception:
                                pass
                
                logger.warning(f"Could not respond to interaction: {interaction}")
        except Exception as e:
            logger.error(f"Error responding to interaction: {e}")
    
    async def close(self):
        """Close the bot and clean up resources"""
        logger.info("Closing bot...")
        
        # Cancel all background tasks
        for task_name, task_info in list(self.bg_tasks.items()):
            task = task_info["task"]
            if not task.done():
                logger.info(f"Cancelling background task: {task_name}")
                task.cancel()
        
        # Close the database connection
        if self._db_client:
            await self._db_client.close()
            logger.info("Closed database connection")
        
        # Call parent close
        await super().close()
        logger.info("Bot closed")