"""
Discord Direct Implementation

This module provides a minimal implementation of a Discord bot
without relying on the discord.py or py-cord libraries.

It uses direct HTTP and WebSocket connections to the Discord API
to implement the necessary functionality.
"""

import os
import sys
import json
import time
import logging
import asyncio
import urllib.request
import urllib.parse
import hmac
import hashlib
import base64
import random
import string
from typing import Optional, Dict, List, Any, Callable, Awaitable, Union
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DiscordDirect")

# Load environment variables
load_dotenv()

# Discord token
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    logger.error("DISCORD_TOKEN environment variable not set")
    sys.exit(1)

# Discord API constants
API_VERSION = 10
API_BASE_URL = f"https://discord.com/api/v{API_VERSION}"
GATEWAY_URL = f"wss://gateway.discord.gg/?v={API_VERSION}&encoding=json"

# Event handlers
event_handlers = {}

class Bot:
    """A minimal Discord bot implementation."""
    
    def __init__(self, command_prefix: str = "!"):
        """
        Initialize the bot.
        
        Args:
            command_prefix: The command prefix to use
        """
        self.command_prefix = command_prefix
        self.user = None
        self.session_id = None
        self.sequence = None
        self.heartbeat_interval = None
        self.loop = asyncio.get_event_loop()
        self.websocket = None
        self.ready = asyncio.Event()
        self.commands = {}
        
        # Set up event handlers
        self.event_handlers = {
            "READY": self._handle_ready,
            "MESSAGE_CREATE": self._handle_message,
            "GUILD_CREATE": self._handle_guild_create,
        }
    
    def event(self, coro):
        """
        Decorator to register an event handler.
        
        Args:
            coro: The coroutine function to register
            
        Returns:
            The original coroutine function
        """
        event_name = coro.__name__
        if event_name.startswith("on_"):
            event_name = event_name[3:]
        
        event_handlers[event_name] = coro
        return coro
    
    def command(self, name=None):
        """
        Decorator to register a command.
        
        Args:
            name: The name of the command (default: function name)
            
        Returns:
            Decorator function
        """
        def decorator(func):
            cmd_name = name or func.__name__
            self.commands[cmd_name] = func
            return func
        return decorator
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        Make a request to the Discord API.
        
        Args:
            method: The HTTP method to use
            endpoint: The API endpoint to call
            data: The data to send (default: None)
            
        Returns:
            The JSON response
        """
        url = f"{API_BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bot {TOKEN}",
            "User-Agent": "DiscordDirect/1.0",
            "Content-Type": "application/json"
        }
        
        request = urllib.request.Request(
            url,
            method=method,
            headers=headers
        )
        
        if data:
            request.data = json.dumps(data).encode()
        
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            logger.error(f"API request failed: {e}")
            logger.error(f"Response: {e.read().decode()}")
            raise
    
    async def get_gateway(self) -> str:
        """
        Get the gateway URL from the Discord API.
        
        Returns:
            The gateway URL
        """
        response = await self._make_request("GET", "/gateway/bot")
        return response.get("url", GATEWAY_URL)
    
    async def send_message(self, channel_id: str, content: str) -> Dict:
        """
        Send a message to a channel.
        
        Args:
            channel_id: The ID of the channel
            content: The content of the message
            
        Returns:
            The message data
        """
        data = {"content": content}
        return await self._make_request("POST", f"/channels/{channel_id}/messages", data)
    
    async def _send_json(self, data: Dict):
        """
        Send JSON data to the websocket.
        
        Args:
            data: The data to send
        """
        await self.websocket.send(json.dumps(data))
    
    async def _handle_ready(self, data: Dict):
        """
        Handle the READY event.
        
        Args:
            data: The event data
        """
        self.user = data.get("user", {})
        self.session_id = data.get("session_id")
        
        logger.info(f"Connected as {self.user.get('username')}#{self.user.get('discriminator')}")
        logger.info(f"User ID: {self.user.get('id')}")
        
        self.ready.set()
        
        # Call user event handler if any
        if "READY" in event_handlers:
            await event_handlers["READY"](self, data)
    
    async def _handle_message(self, data: Dict):
        """
        Handle the MESSAGE_CREATE event.
        
        Args:
            data: The event data
        """
        # Check if it's a command
        if data.get("author", {}).get("id") != self.user.get("id"):
            content = data.get("content", "")
            
            if content.startswith(self.command_prefix):
                # Extract command name
                parts = content[len(self.command_prefix):].split(maxsplit=1)
                cmd_name = parts[0]
                
                # Execute command if it exists
                if cmd_name in self.commands:
                    try:
                        # Create a simple context object
                        ctx = {"bot": self, "message": data}
                        
                        # Call the command
                        await self.commands[cmd_name](ctx)
                    except Exception as e:
                        logger.error(f"Error executing command {cmd_name}: {e}")
        
        # Call user event handler if any
        if "MESSAGE_CREATE" in event_handlers:
            await event_handlers["MESSAGE_CREATE"](self, data)
    
    async def _handle_guild_create(self, data: Dict):
        """
        Handle the GUILD_CREATE event.
        
        Args:
            data: The event data
        """
        logger.info(f"Joined guild: {data.get('name')} (ID: {data.get('id')})")
        
        # Call user event handler if any
        if "GUILD_CREATE" in event_handlers:
            await event_handlers["GUILD_CREATE"](self, data)
    
    async def _heartbeat_loop(self):
        """Send heartbeats to the gateway."""
        while True:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            
            heartbeat_data = {
                "op": 1,
                "d": self.sequence
            }
            
            await self._send_json(heartbeat_data)
            logger.debug("Sent heartbeat")
    
    async def _gateway_loop(self):
        """
        Main gateway loop.
        
        Connects to the Discord gateway and processes events.
        """
        import websockets
        
        # Get gateway URL
        #gateway_url = await self.get_gateway()
        gateway_url = GATEWAY_URL
        
        # Connect to gateway
        while True:
            try:
                async with websockets.connect(gateway_url) as websocket:
                    self.websocket = websocket
                    
                    # Process messages
                    async for message in websocket:
                        data = json.loads(message)
                        op = data.get("op")
                        
                        # Update sequence number
                        if data.get("s"):
                            self.sequence = data["s"]
                        
                        # Process op codes
                        if op == 10:  # Hello
                            # Get heartbeat interval
                            self.heartbeat_interval = data["d"]["heartbeat_interval"]
                            
                            # Start heartbeat loop
                            self.loop.create_task(self._heartbeat_loop())
                            
                            # Identify
                            identify_data = {
                                "op": 2,
                                "d": {
                                    "token": TOKEN,
                                    "intents": 513,  # GUILDS and GUILD_MESSAGES
                                    "properties": {
                                        "$os": sys.platform,
                                        "$browser": "DiscordDirect",
                                        "$device": "DiscordDirect"
                                    }
                                }
                            }
                            
                            await self._send_json(identify_data)
                        elif op == 11:  # Heartbeat ACK
                            logger.debug("Received heartbeat ACK")
                        elif op == 0:  # Dispatch
                            # Get event name
                            event_name = data.get("t")
                            
                            # Call handler if any
                            if event_name in self.event_handlers:
                                await self.event_handlers[event_name](data["d"])
            except Exception as e:
                logger.error(f"Gateway error: {e}")
                await asyncio.sleep(5)
    
    def run(self):
        """Run the bot."""
        try:
            # Set up asyncio
            self.loop.run_until_complete(self._gateway_loop())
        except KeyboardInterrupt:
            logger.info("Bot stopped")
        finally:
            self.loop.close()

# Create a function to run the bot
def run_bot():
    """Run a Discord bot."""
    # Create the bot
    bot = Bot(command_prefix="!")
    
    # Set up event handlers
    @bot.event
    async def on_ready(bot, data):
        logger.info("Bot is ready!")
    
    @bot.event
    async def on_message_create(bot, message):
        logger.info(f"Received message: {message.get('content')}")
    
    # Set up commands
    @bot.command()
    async def ping(ctx):
        await bot.send_message(ctx["message"]["channel_id"], "Pong!")
    
    @bot.command()
    async def info(ctx):
        await bot.send_message(
            ctx["message"]["channel_id"],
            f"I am a Discord bot running DiscordDirect with user ID {bot.user.get('id')}"
        )
    
    # Run the bot
    bot.run()

if __name__ == "__main__":
    run_bot()