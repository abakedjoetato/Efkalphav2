"""
Enhanced Direct Discord Bot implementation 
that supports cogs and commands without relying on complex imports
"""
import os
import sys
import asyncio
import logging
import importlib
import traceback
import inspect
import motor.motor_asyncio
from dotenv import load_dotenv
from datetime import datetime
import aiohttp
import json
from typing import Dict, List, Optional, Any, Union, Callable, Coroutine, TypeVar

# Import our custom discord module
import discord
from discord.ext import commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("direct_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Type definitions
T = TypeVar('T')
CommandCallback = Callable[..., Coroutine[Any, Any, T]]

# Use our commands.Command implementation
Command = commands.Command

# Legacy Command class for backward compatibility
class DirectCommand:
    """Simple command class for registering and executing bot commands"""
    def __init__(self, callback: CommandCallback, name: str = None, description: str = None, 
                aliases: List[str] = None, guild_only: bool = False):
        self.callback = callback
        self.name = name or callback.__name__
        self.description = description or callback.__doc__ or "No description provided"
        self.aliases = aliases or []
        self.guild_only = guild_only
        self.cog = None
        
    async def invoke(self, ctx, *args, **kwargs):
        """Invoke the command with the given context and arguments"""
        if self.cog:
            return await self.callback(self.cog, ctx, *args, **kwargs)
        return await self.callback(ctx, *args, **kwargs)

# Use Discord commands Context for compatibility
DirectContext = commands.Context

# Our Context implementation that wraps the Discord message object
class Context(DirectContext):
    """Command execution context"""
    def __init__(self, bot, message, command=None):
        # Initialize with minimal required attributes
        super().__init__(bot=bot)
        self.bot = bot
        self.message = message
        self.command = command
        self.author = message.get('author', {})
        self.channel_id = message.get('channel_id')
        self.guild_id = message.get('guild_id')
        self.content = message.get('content', '')
        
    async def send(self, content=None, **kwargs):
        """Send a message to the channel"""
        return await self.bot.send_message(self.channel_id, content, **kwargs)

# Use Discord commands Cog for compatibility
DirectCog = commands.Cog

# Our Cog implementation with additional functionality
class Cog(DirectCog):
    """Base class for bot extensions with extended functionality"""
    def __init__(self, bot):
        self.bot = bot
        
    @classmethod
    def listener(cls, name=None):
        """Decorator to register an event listener"""
        def decorator(func):
            func.__listener_name__ = name or func.__name__
            if not hasattr(func, '__cog_listener__'):
                func.__cog_listener__ = True
            return func
        return decorator
        
    @classmethod
    def command(cls, name=None, **kwargs):
        """Decorator to register a command in a cog"""
        def decorator(func):
            func.__command__ = True
            func.__command_kwargs__ = {'name': name or func.__name__, **kwargs}
            return func
        return decorator

class EnhancedDiscordBot(commands.Bot):
    """
    An enhanced implementation of a Discord bot
    that directly calls the Discord API and supports cogs and commands
    
    This implementation extends our compatibility Bot class but
    uses direct Discord API calls instead of relying on a library.
    """
    
    def __init__(self):
        """Initialize the bot and set up configuration"""
        # Initialize the base Bot class with minimal required options
        super().__init__(command_prefix="!", intents=None)
        
        self.token = os.getenv("DISCORD_TOKEN")
        if not self.token:
            raise ValueError("DISCORD_TOKEN not found in environment variables")
            
        # Set up MongoDB connection
        mongo_uri = os.getenv("MONGODB_URI")
        if mongo_uri:
            self.db_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
            self.db = self.db_client.lastfix
            logger.info("Connected to MongoDB")
        else:
            self.db_client = None
            self.db = None
            logger.warning("MONGODB_URI not set, database functionality will be limited")
            
        # Store bot configuration
        self.base_url = "https://discord.com/api/v10"
        self.gateway_url = None
        self.session = None
        self.ws = None
        self.user = None
        self.guilds = []
        self.channels = {}
        self.startup_time = datetime.now()
        self.heartbeat_interval = None
        self.last_sequence = None
        self.session_id = None
        self.close_event = asyncio.Event()
        
        # Command handling
        self.command_prefix = "!"
        self.commands = {}
        self.cogs = {}
        self.listeners = {}
        self.all_listeners = []
        self.ready = False
        self.bg_tasks = []
        
        # Configuration
        self.premium_servers = set()
        self.config = {}
        self.is_pycord_261 = True  # For compatibility
        
    async def start(self):
        """Start the bot and connect to Discord"""
        self.session = aiohttp.ClientSession()
        
        try:
            # Get the gateway URL
            gateway_info = await self._api_request("GET", "/gateway/bot")
            self.gateway_url = gateway_info["url"]
            
            logger.info("Loading cogs...")
            await self.load_cogs()
            
            # Connect to the gateway
            logger.info(f"Connecting to gateway: {self.gateway_url}")
            await self._connect_to_gateway()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            traceback.print_exc()
            await self.close()
            
    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        cog_dir = 'cogs'
        if not os.path.isdir(cog_dir):
            logger.warning(f"Cog directory '{cog_dir}' not found")
            return
            
        for filename in os.listdir(cog_dir):
            if filename.endswith('.py'):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    logger.info(f"Loaded cog: {cog_name}")
                except Exception as e:
                    logger.error(f"Failed to load cog {cog_name}: {e}")
                    traceback.print_exc()
    
    async def load_extension(self, name):
        """Load a bot extension (cog)"""
        try:
            # Try three different approaches to load the cog:
            # 1. First try using the standard setup function approach (discord.py/py-cord standard)
            # 2. Then try using our Cog class directly
            # 3. If both fail, try using the CogAdapter
            
            # Import the module
            module = importlib.import_module(name)
            
            # Reload in case it was already loaded
            importlib.reload(module)
            
            # Try approach 1: Use setup function (discord.py style)
            if hasattr(module, 'setup'):
                try:
                    # This is how discord.py/py-cord loads extensions
                    await module.setup(self)
                    logger.info(f"Loaded extension {name} via setup function")
                    return True
                except Exception as e:
                    logger.warning(f"Error using setup function for {name}: {e}")
                    # Continue to other approaches
            
            # Try approach 2: Find cog class directly
            cog_cls = None
            for item_name, item in inspect.getmembers(module):
                if inspect.isclass(item) and issubclass(item, commands.Cog) and item is not commands.Cog and item is not Cog:
                    cog_cls = item
                    break
                    
            if cog_cls:
                # Create an instance of the cog
                cog = cog_cls(self)
                
                # Register the cog using Bot's add_cog method
                self.add_cog(cog)
                
                logger.info(f"Loaded extension {name} using direct cog class")
                
                # If the cog has a cog_load method, call it
                if hasattr(cog, 'cog_load'):
                    await cog.cog_load()
                    
                return True
                
            # Try approach 3: Use cog adapter
            logger.info(f"No compatible cog class found in {name}, trying adapter...")
            
            try:
                # Import the cog adapter
                from utils.cog_adapter import CogAdapter
                
                # Load and adapt the cog
                cog = CogAdapter.load_and_adapt_cog(self, name)
                if cog:
                    if name not in self.cogs:
                        self.cogs[name] = cog
                    logger.info(f"Loaded extension {name} using cog adapter")
                    
                    # Register commands and listeners from the adapted cog
                    for attr_name, attr in inspect.getmembers(cog.__class__):
                        # Check if it's a command
                        if hasattr(attr, '__command__'):
                            cmd_kwargs = getattr(attr, '__command_kwargs__', {})
                            cmd = Command(getattr(cog, attr_name), **cmd_kwargs)
                            cmd.cog = cog
                            self.commands[cmd.name] = cmd
                            logger.debug(f"Registered command from adapted cog: {cmd.name}")
                            
                        # Check if it's a listener
                        if hasattr(attr, '__listener_name__'):
                            listener_name = getattr(attr, '__listener_name__')
                            if listener_name not in self.listeners:
                                self.listeners[listener_name] = []
                            self.listeners[listener_name].append(getattr(cog, attr_name))
                            self.all_listeners.append((listener_name, getattr(cog, attr_name)))
                            logger.debug(f"Registered listener from adapted cog: {listener_name}")
                    
                    # If the cog has a cog_load method, call it
                    if hasattr(cog, 'cog_load'):
                        await cog.cog_load()
                        
                    return True
                else:
                    raise ValueError(f"Failed to adapt cog {name}")
            except Exception as adapter_error:
                logger.error(f"Error using adapter for {name}: {adapter_error}")
                raise
                
        except ImportError as e:
            logger.error(f"Could not import module {name}: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Error loading extension {name}: {e}")
            traceback.print_exc()
            raise
            
    async def _connect_to_gateway(self):
        """Connect to the Discord gateway"""
        async with self.session.ws_connect(f"{self.gateway_url}?v=10&encoding=json") as ws:
            self.ws = ws
            
            # Handle the hello event
            hello = await ws.receive_json()
            logger.info(f"Received hello")
            
            if hello["op"] != 10:
                logger.error(f"Expected hello (op 10), got {hello}")
                return
                
            # Set up the heartbeat interval
            self.heartbeat_interval = hello["d"]["heartbeat_interval"] / 1000
            
            # Start the heartbeat task
            heartbeat_task = asyncio.create_task(self._heartbeat())
            
            # Identify with the gateway
            await self._identify()
            
            # Main event loop
            try:
                while not self.close_event.is_set():
                    try:
                        msg = await ws.receive_json()
                        await self._handle_event(msg)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.error(f"Error handling gateway event: {e}")
                        traceback.print_exc()
            except Exception as e:
                logger.error(f"Error in gateway event loop: {e}")
                traceback.print_exc()
            finally:
                heartbeat_task.cancel()
                
    async def _heartbeat(self):
        """Send heartbeats to the gateway"""
        try:
            while not self.close_event.is_set():
                await asyncio.sleep(self.heartbeat_interval)
                
                # Send heartbeat
                await self.ws.send_json({
                    "op": 1,
                    "d": self.last_sequence
                })
                logger.debug("Sent heartbeat")
        except asyncio.CancelledError:
            logger.info("Heartbeat task cancelled")
        except Exception as e:
            logger.error(f"Error in heartbeat task: {e}")
            traceback.print_exc()
            await self.close()
            
    async def _identify(self):
        """Identify with the Discord gateway"""
        await self.ws.send_json({
            "op": 2,
            "d": {
                "token": self.token,
                "intents": 32767,  # All intents
                "properties": {
                    "$os": "linux",
                    "$browser": "LastFix Bot",
                    "$device": "LastFix Bot"
                },
                "presence": {
                    "status": "online",
                    "activities": [{
                        "name": "LastFix Game",
                        "type": 0
                    }]
                }
            }
        })
        logger.info("Sent identify payload")
        
    async def _handle_event(self, event):
        """Handle events from the Discord gateway"""
        op = event.get("op")
        t = event.get("t")
        d = event.get("d")
        s = event.get("s")
        
        # Update sequence number
        if s is not None:
            self.last_sequence = s
            
        # Handle different opcodes
        if op == 0:  # Dispatch event
            logger.debug(f"Received event: {t}")
            
            if t == "READY":
                self.user = d["user"]
                self.session_id = d["session_id"]
                logger.info(f"Connected as {self.user['username']}#{self.user['discriminator']} ({self.user['id']})")
                
                # Call on_ready event handlers
                self.ready = True
                await self._dispatch_event('on_ready')
                
            elif t == "GUILD_CREATE":
                guild_id = d["id"]
                guild_name = d["name"]
                self.guilds.append(d)
                
                # Store channels
                for channel in d.get("channels", []):
                    channel_id = channel["id"]
                    self.channels[channel_id] = channel
                    channel["guild_id"] = guild_id
                
                logger.info(f"Added guild: {guild_name} ({guild_id})")
                
                # Call on_guild_join event handlers
                await self._dispatch_event('on_guild_join', d)
                
            elif t == "MESSAGE_CREATE":
                # Handle new messages
                await self._handle_message(d)
                
                # Call on_message event handlers
                await self._dispatch_event('on_message', d)
                
            # Other events can be added as needed
            await self._dispatch_event(f'on_{t.lower()}', d)
            
        elif op == 11:  # Heartbeat ACK
            logger.debug("Received heartbeat ACK")
            
        elif op == 7:  # Reconnect
            logger.info("Received reconnect request")
            await self.close()
            # Should restart after this
            
        elif op == 9:  # Invalid Session
            logger.warning("Received invalid session, retrying...")
            await asyncio.sleep(5)
            await self._identify()
    
    async def _handle_message(self, message):
        """Handle a message event and execute commands if applicable"""
        # Ignore messages from bots
        if message.get('author', {}).get('bot', False):
            return
            
        # Check if it's a command
        content = message.get('content', '')
        if not content.startswith(self.command_prefix):
            return
            
        # Parse the command
        parts = content[len(self.command_prefix):].strip().split(maxsplit=1)
        command_name = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ''
        
        # Find the command
        command = self.commands.get(command_name)
        if not command:
            # Try aliases
            for cmd in self.commands.values():
                if command_name in cmd.aliases:
                    command = cmd
                    break
                    
        if not command:
            return
            
        # Check guild only
        if command.guild_only and not message.get('guild_id'):
            await self.send_message(message['channel_id'], "This command can only be used in a server.")
            return
            
        # Create context
        ctx = Context(self, message, command)
        
        # Execute the command
        try:
            # Parse arguments
            args = []
            kwargs = {}
            if args_str:
                # Very basic argument parsing, could be improved
                args = args_str.split()
                
            await command.invoke(ctx, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error executing command {command_name}: {e}")
            traceback.print_exc()
            await self.send_message(message['channel_id'], f"Error executing command: {e}")
    
    async def _dispatch_event(self, event_name, *args, **kwargs):
        """Dispatch an event to all registered listeners"""
        listeners = self.listeners.get(event_name, [])
        for listener in listeners:
            try:
                await listener(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {event_name} listener: {e}")
                traceback.print_exc()
                
    async def _api_request(self, method, endpoint, **kwargs):
        """Make a request to the Discord API"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bot {self.token}",
            "User-Agent": "LastFix Enhanced Bot",
            "Content-Type": "application/json"
        }
        
        async with self.session.request(method, url, headers=headers, **kwargs) as resp:
            if resp.status >= 400:
                error_text = await resp.text()
                logger.error(f"API error: {resp.status} {error_text}")
                raise Exception(f"API request failed: {resp.status} {error_text}")
                
            return await resp.json()
            
    async def send_message(self, channel_id, content=None, **kwargs):
        """Send a message to a Discord channel"""
        payload = {}
        if content:
            payload["content"] = content
            
        if "embeds" in kwargs:
            payload["embeds"] = kwargs.pop("embeds")
            
        # Add other kwargs to the payload
        payload.update(kwargs)
        
        response = await self._api_request(
            "POST", 
            f"/channels/{channel_id}/messages",
            json=payload
        )
        return response
    
    def get_channel(self, channel_id):
        """Get a channel by ID"""
        return self.channels.get(channel_id)
    
    def get_guild(self, guild_id):
        """Get a guild by ID"""
        for guild in self.guilds:
            if guild.get('id') == guild_id:
                return guild
        return None
        
    def create_task(self, coro, name=None):
        """Create a background task"""
        task = asyncio.create_task(coro, name=name)
        self.bg_tasks.append(task)
        
        def task_done_callback(t):
            if t.exception():
                logger.error(f"Background task {name} failed: {t.exception()}")
                traceback.print_exc()
            if t in self.bg_tasks:
                self.bg_tasks.remove(t)
                
        task.add_done_callback(task_done_callback)
        return task
        
    async def close(self):
        """Close the connection and clean up"""
        logger.info("Closing bot connection")
        
        self.close_event.set()
        
        # Cancel all background tasks
        for task in self.bg_tasks:
            if not task.done():
                task.cancel()
        
        # Call cog_unload methods
        for cog in self.cogs.values():
            if hasattr(cog, 'cog_unload'):
                try:
                    if inspect.iscoroutinefunction(cog.cog_unload):
                        await cog.cog_unload()
                    else:
                        cog.cog_unload()
                except Exception as e:
                    logger.error(f"Error unloading cog {cog.__class__.__name__}: {e}")
        
        if self.ws and not self.ws.closed:
            await self.ws.close()
            
        if self.session and not self.session.closed:
            await self.session.close()
            
        if self.db_client:
            self.db_client.close()
            
        logger.info("Bot connection closed")
        

async def main():
    """Main entry point for the bot"""
    bot = EnhancedDiscordBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        traceback.print_exc()
    finally:
        await bot.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting due to keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()