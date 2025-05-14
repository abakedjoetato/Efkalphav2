"""
Discord API Implementation for Replit Environment

This is a bridging module with minimal implementation to avoid circular imports.
"""

import sys
import logging
import types
import importlib.util
from enum import Enum, IntEnum

logger = logging.getLogger(__name__)
logger.info("Loading minimal Discord bridge (for Replit)")

# Set up versioning for compatibility
__version__ = "2.6.1"
version_info = (2, 6, 1)

# Core Discord classes that are needed immediately
class Intents:
    """Discord Intents implementation"""
    
    def __init__(self, **kwargs):
        self.members = kwargs.get('members', False)
        self.presences = kwargs.get('presences', False)
        self.message_content = kwargs.get('message_content', False)
        self.guilds = kwargs.get('guilds', False)
        self.guild_messages = kwargs.get('guild_messages', False)
        self.dm_messages = kwargs.get('dm_messages', False)
        self.guild_reactions = kwargs.get('guild_reactions', False)
        self.dm_reactions = kwargs.get('dm_reactions', False)
        
        # For validation
        self.value = sum([
            (1 << 0) if self.guilds else 0,
            (1 << 1) if self.members else 0,
            (1 << 9) if self.guild_reactions else 0,
            (1 << 7) if self.guild_messages else 0,
            (1 << 15) if self.message_content else 0,
        ])
        
    @classmethod
    def all(cls):
        """Return intents with all flags enabled"""
        return cls(
            members=True,
            presences=True,
            message_content=True,
            guilds=True,
            guild_messages=True,
            dm_messages=True,
            guild_reactions=True,
            dm_reactions=True
        )
        
    @classmethod
    def default(cls):
        """Return default intents"""
        return cls(
            guilds=True,
            guild_messages=True,
            dm_messages=True
        )
        
    @classmethod
    def none(cls):
        """Return intents with no flags enabled"""
        return cls()

# Create base classes needed by bot.py
class User:
    """Discord User implementation"""
    
    def __init__(self, id=0, name="User", discriminator="0000", bot=False):
        self.id = id
        self.name = name
        self.discriminator = discriminator
        self.bot = bot
        self.display_name = name
        
    @property
    def mention(self):
        return f"<@{self.id}>"
        
    def __str__(self):
        return f"{self.name}#{self.discriminator}"

class Member(User):
    """Discord Member implementation (user + guild info)"""
    
    def __init__(self, id=0, name="User", guild=None, discriminator="0000", roles=None, bot=False):
        super().__init__(id, name, discriminator, bot)
        self.guild = guild
        self.roles = roles or []
        
    def __str__(self):
        return f"{self.name}#{self.discriminator}"

class Guild:
    """Discord Guild (Server) implementation"""
    
    def __init__(self, id=0, name="Server", owner=None, members=None):
        self.id = id
        self.name = name
        self.owner = owner
        self.members = members or []
        self.me = None  # Bot member in this guild
        
    def __str__(self):
        return self.name

class TextChannel:
    """Discord TextChannel implementation"""
    
    def __init__(self, id=0, name="channel", guild=None):
        self.id = id
        self.name = name
        self.guild = guild
        
    async def send(self, content=None, **kwargs):
        """Send a message to the channel"""
        logger.info(f"[Mock] Sending message to {self.name}: {content}")
        return Message(
            id=0,
            content=content or "",
            author=None,
            channel=self
        )
        
    @property
    def mention(self):
        return f"<#{self.id}>"
        
    def __str__(self):
        return self.name

class Message:
    """Discord Message implementation"""
    
    def __init__(self, id=0, content="", author=None, channel=None, guild=None):
        self.id = id
        self.content = content
        self.author = author
        self.channel = channel
        self.guild = guild or getattr(channel, 'guild', None)
        
    async def reply(self, content=None, **kwargs):
        """Reply to the message"""
        logger.info(f"[Mock] Replying to message: {content}")
        return Message(
            id=0,
            content=content or "",
            author=None,
            channel=self.channel
        )
        
    async def add_reaction(self, emoji):
        """Add a reaction to the message"""
        logger.info(f"[Mock] Adding reaction {emoji} to message")

class Color:
    """Discord Color implementation"""
    
    def __init__(self, value):
        self.value = value
        
    def __int__(self):
        return self.value
        
    def __str__(self):
        return f"#{self.value:06x}"
        
    def __eq__(self, other):
        return isinstance(other, Color) and self.value == other.value
        
    @classmethod
    def from_rgb(cls, r, g, b):
        """Create a Color from RGB values"""
        return cls((r << 16) + (g << 8) + b)
    
    # Add some predefined colors
    @classmethod
    def default(cls):
        return cls(0)
    
    @classmethod
    def blue(cls):
        return cls.from_rgb(59, 136, 195)
    
    @classmethod
    def green(cls):
        return cls.from_rgb(46, 204, 113)
    
    @classmethod
    def red(cls):
        return cls.from_rgb(231, 76, 60)
    
    @classmethod
    def gold(cls):
        return cls.from_rgb(241, 196, 15)
    
    @classmethod
    def purple(cls):
        return cls.from_rgb(142, 68, 173)


class Embed:
    """Discord Embed implementation"""
    
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.description = kwargs.get('description')
        self.color = kwargs.get('color', 0)
        self.url = kwargs.get('url')
        self.timestamp = kwargs.get('timestamp')
        self.fields = []
        self.footer = None
        self.image = None
        self.thumbnail = None
        self.author = None
        
    def add_field(self, name, value, inline=False):
        """Add a field to the embed"""
        self.fields.append({
            'name': name,
            'value': value,
            'inline': inline
        })
        return self
        
    def set_footer(self, text, icon_url=None):
        """Set the footer"""
        self.footer = {
            'text': text,
            'icon_url': icon_url
        }
        return self
        
    def set_image(self, url):
        """Set the image"""
        self.image = {'url': url}
        return self
        
    def set_thumbnail(self, url):
        """Set the thumbnail"""
        self.thumbnail = {'url': url}
        return self
        
    def set_author(self, name, url=None, icon_url=None):
        """Set the author"""
        self.author = {
            'name': name,
            'url': url,
            'icon_url': icon_url
        }
        return self

# Set up module structure
ext = types.ModuleType("discord.ext")
sys.modules['discord.ext'] = ext

# Import our custom implementations to populate the namespace
try:
    import discord.ext.commands
    sys.modules['discord.ext.commands'] = discord.ext.commands
    ext.commands = discord.ext.commands
except ImportError as e:
    logger.error(f"Error importing discord.ext.commands: {e}")
    
try:
    import discord.app_commands
    sys.modules['discord.app_commands'] = discord.app_commands
    app_commands = discord.app_commands
    
    # Import and expose key classes
    if hasattr(discord.app_commands, 'Interaction'):
        Interaction = discord.app_commands.Interaction
    if hasattr(discord.app_commands, 'ApplicationContext'):
        ApplicationContext = discord.app_commands.ApplicationContext
    if hasattr(discord.app_commands, 'SlashCommandGroup'):
        SlashCommandGroup = discord.app_commands.SlashCommandGroup
except ImportError as e:
    logger.error(f"Error importing discord.app_commands: {e}")
    app_commands = types.ModuleType("discord.app_commands")
    sys.modules['discord.app_commands'] = app_commands

# Export relevant symbols
__all__ = [
    # Core classes
    'Intents',
    'Message',
    'User',
    'Member',
    'Guild',
    'TextChannel', 
    'Embed',
    'Color',
    
    # App commands and interactions
    'Interaction',
    'ApplicationContext',
    'SlashCommandGroup',
    
    # Version info
    '__version__', 
    'version_info',
    
    # Modules
    'ext',
    'app_commands'
]