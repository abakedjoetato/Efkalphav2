"""
Mock Discord module for testing purposes without an actual Discord connection.

This module provides mock implementations of the critical Discord classes and functions
needed for testing the bot without actually connecting to Discord.
"""

import asyncio
import logging
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)

# Version information
__version__ = "2.6.1.mock"

# Mock Discord Intents
class Intents:
    """Mock implementation of Discord Intents"""
    
    def __init__(self, **kwargs):
        self.members = kwargs.get('members', False)
        self.message_content = kwargs.get('message_content', False)
        self.guilds = kwargs.get('guilds', False)
        self.guild_messages = kwargs.get('guild_messages', False)
        self.dm_messages = kwargs.get('dm_messages', False)
        self.reactions = kwargs.get('reactions', False)
        self.voice_states = kwargs.get('voice_states', False)
        self.presences = kwargs.get('presences', False)
        
    @classmethod
    def all(cls):
        """Return intents with all flags enabled"""
        return cls(
            members=True,
            message_content=True,
            guilds=True,
            guild_messages=True,
            dm_messages=True,
            reactions=True,
            voice_states=True,
            presences=True
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

# Mock Discord Objects
class User:
    """Mock Discord User"""
    
    def __init__(self, id: int, name: str, discriminator: str = "0000"):
        self.id = id
        self.name = name
        self.discriminator = discriminator
        
    @property
    def display_name(self):
        return self.name
        
    @property
    def mention(self):
        return f"<@{self.id}>"
        
    def __str__(self):
        return f"{self.name}#{self.discriminator}"

class Member(User):
    """Mock Discord Member (User + Guild info)"""
    
    def __init__(self, id: int, name: str, guild=None, roles=None):
        super().__init__(id, name)
        self.guild = guild
        self.roles = roles or []

class Guild:
    """Mock Discord Guild (Server)"""
    
    def __init__(self, id: int, name: str, owner_id: int = 0):
        self.id = id
        self.name = name
        self.owner_id = owner_id
        self.members = []
        self.channels = []
        self.roles = []
        
    def __str__(self):
        return self.name

class TextChannel:
    """Mock Discord Text Channel"""
    
    def __init__(self, id: int, name: str, guild=None):
        self.id = id
        self.name = name
        self.guild = guild
        
    async def send(self, content=None, **kwargs):
        """Mock sending a message"""
        logger.info(f"[Mock] Sending to #{self.name}: {content}")
        return Message(
            id=0,
            content=content or "",
            author=kwargs.get('author', User(0, "Bot")),
            channel=self
        )
        
    @property
    def mention(self):
        return f"<#{self.id}>"
        
    def __str__(self):
        return f"#{self.name}"

class Message:
    """Mock Discord Message"""
    
    def __init__(self, id: int, content: str, author=None, channel=None):
        self.id = id
        self.content = content
        self.author = author or User(0, "Unknown")
        self.channel = channel
        self.guild = channel.guild if channel and hasattr(channel, 'guild') else None
        
    async def reply(self, content=None, **kwargs):
        """Mock replying to a message"""
        logger.info(f"[Mock] Replying to {self.author.name}: {content}")
        return Message(
            id=0,
            content=content or "",
            author=User(0, "Bot"),
            channel=self.channel
        )
        
    async def add_reaction(self, emoji):
        """Mock adding a reaction"""
        logger.info(f"[Mock] Adding reaction {emoji} to message")

class Role:
    """Mock Discord Role"""
    
    def __init__(self, id: int, name: str, guild=None):
        self.id = id
        self.name = name
        self.guild = guild
        self.color = 0
        self.permissions = 0
        
    @property
    def mention(self):
        return f"<@&{self.id}>"
        
    def __str__(self):
        return self.name

class Embed:
    """Mock Discord Embed"""
    
    def __init__(self, **kwargs):
        self.title = kwargs.get('title')
        self.description = kwargs.get('description')
        self.color = kwargs.get('color', 0)
        self.fields = []
        
    def add_field(self, name, value, inline=False):
        """Add a field to the embed"""
        self.fields.append({
            'name': name,
            'value': value,
            'inline': inline
        })
        return self
        
    def set_thumbnail(self, url):
        """Set the thumbnail image"""
        self.thumbnail = {'url': url}
        return self
        
    def set_footer(self, text, icon_url=None):
        """Set the footer"""
        self.footer = {'text': text}
        if icon_url:
            self.footer['icon_url'] = icon_url
        return self

class Interaction:
    """Mock Discord Interaction"""
    
    def __init__(self, user=None, guild=None, channel=None):
        self.user = user or User(0, "User")
        self.guild = guild
        self.channel = channel or TextChannel(0, "channel", guild)
        self.response = InteractionResponse(self)
        self.followup = InteractionFollowup(self)
        
    @property
    def author(self):
        """For compatibility with Message"""
        return self.user

class InteractionResponse:
    """Mock Discord Interaction Response"""
    
    def __init__(self, interaction):
        self.interaction = interaction
        self._responded = False
        
    async def send_message(self, content=None, **kwargs):
        """Mock sending a response"""
        logger.info(f"[Mock] Sending interaction response: {content}")
        self._responded = True
        
    def is_done(self):
        """Check if this interaction has been responded to"""
        return self._responded

class InteractionFollowup:
    """Mock Discord Interaction Followup"""
    
    def __init__(self, interaction):
        self.interaction = interaction
        
    async def send(self, content=None, **kwargs):
        """Mock sending a followup message"""
        logger.info(f"[Mock] Sending interaction followup: {content}")
        return Message(
            id=0,
            content=content or "",
            author=User(0, "Bot"),
            channel=self.interaction.channel
        )

# Mock Discord enums
class ChannelType(Enum):
    """Mock Channel Type Enum"""
    TEXT = 0
    VOICE = 2
    CATEGORY = 4
    FORUM = 15

class AppCommandOptionType(Enum):
    """Mock Application Command Option Type"""
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10
    ATTACHMENT = 11

# Mock module functions
async def create_mock_guild():
    """Create a mock guild for testing"""
    guild = Guild(123456789, "Test Server", 987654321)
    
    # Add some users
    owner = Member(987654321, "ServerOwner", guild)
    admin = Member(111222333, "Admin", guild)
    regular_user = Member(444555666, "User", guild)
    
    guild.members = [owner, admin, regular_user]
    
    # Add some channels
    general = TextChannel(111222, "general", guild)
    announcements = TextChannel(333444, "announcements", guild)
    
    guild.channels = [general, announcements]
    
    # Add some roles
    admin_role = Role(987, "Admin", guild)
    mod_role = Role(654, "Moderator", guild)
    
    guild.roles = [admin_role, mod_role]
    
    return guild

# Module initialization
async def initialize_mock_discord():
    """Initialize the mock Discord environment"""
    logger.info("Initializing mock Discord environment")
    
    # Create a mock guild
    mock_guild = await create_mock_guild()
    
    return {
        'guild': mock_guild,
        'users': mock_guild.members,
        'channels': mock_guild.channels,
        'roles': mock_guild.roles
    }