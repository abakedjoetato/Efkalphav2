"""
Discord Compatibility Layer package

This package provides compatibility layers for Discord API interactions,
supporting both discord.py and py-cord 2.6.1. This implementation also
works when Discord libraries aren't available in the environment.
"""
import sys
import logging
import types
from enum import Enum, IntEnum

# Set up versioning for compatibility
__version__ = "2.6.1"
version_info = (2, 6, 1)

logger = logging.getLogger(__name__)
logger.info(f"Loading Discord compatibility layer (version {__version__})")

# Core Discord classes
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

class ChannelType(IntEnum):
    """Discord Channel Types"""
    TEXT = 0
    PRIVATE = 1
    VOICE = 2
    GROUP = 3
    CATEGORY = 4
    NEWS = 5
    STORE = 6
    NEWS_THREAD = 10
    PUBLIC_THREAD = 11
    PRIVATE_THREAD = 12
    STAGE_VOICE = 13
    FORUM = 15

class AppCommandOptionType(IntEnum):
    """Discord Application Command Option Types"""
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10
    ATTACHMENT = 11

class Status(Enum):
    """Discord Status Types"""
    ONLINE = "online"
    OFFLINE = "offline"
    IDLE = "idle"
    DND = "dnd"
    DO_NOT_DISTURB = "dnd"
    INVISIBLE = "invisible"

class Color:
    """Discord Color Implementation"""
    def __init__(self, value):
        self.value = value
        
    @classmethod
    def from_rgb(cls, r, g, b):
        return cls((r << 16) + (g << 8) + b)
    
    # Standard colors
    blurple = 0x5865F2
    green = 0x57F287
    yellow = 0xFEE75C
    red = 0xED4245
    white = 0xFFFFFF
    black = 0x000000

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

class Message:
    """Discord Message implementation"""
    
    def __init__(self, id, content, author=None, channel=None, guild=None):
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
            author=User(0, "Bot", discriminator="0000", bot=True),
            channel=self.channel
        )
        
    async def add_reaction(self, emoji):
        """Add a reaction to the message"""
        logger.info(f"[Mock] Adding reaction {emoji} to message")

class User:
    """Discord User implementation"""
    
    def __init__(self, id, name, discriminator="0000", bot=False):
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
    
    def __init__(self, id, name, guild, discriminator="0000", roles=None, bot=False):
        super().__init__(id, name, discriminator, bot)
        self.guild = guild
        self.roles = roles or []
        
    def __str__(self):
        return f"{self.name}#{self.discriminator}"

class Interaction:
    """Discord Interaction implementation"""
    
    def __init__(self, user=None, guild=None, channel=None):
        self.user = user or User(0, "User")
        self.guild = guild
        self.channel = channel
        self.response = InteractionResponse(self)
        self.followup = InteractionFollowup(self)
        
    @property
    def author(self):
        """For compatibility with Message"""
        return self.user

class InteractionResponse:
    """Discord Interaction Response implementation"""
    
    def __init__(self, interaction):
        self.interaction = interaction
        self._responded = False
        
    async def send_message(self, content=None, **kwargs):
        """Send a response to the interaction"""
        self._responded = True
        logger.info(f"[Mock] Sending interaction response: {content}")
        
    def is_done(self):
        """Check if this interaction has been responded to"""
        return self._responded

class InteractionFollowup:
    """Discord Interaction Followup implementation"""
    
    def __init__(self, interaction):
        self.interaction = interaction
        
    async def send(self, content=None, **kwargs):
        """Send a followup message"""
        logger.info(f"[Mock] Sending interaction followup: {content}")
        return Message(
            id=0,
            content=content or "",
            author=User(0, "Bot", discriminator="0000", bot=True),
            channel=self.interaction.channel
        )

# Create the ext namespace and ext.commands module
ext = types.ModuleType("ext")
app_commands = types.ModuleType("app_commands")
sys.modules['discord.ext'] = ext
sys.modules['discord.app_commands'] = app_commands

# Don't import interaction_handlers to avoid circular imports
# These basic functions will be enough for most usage

def is_interaction(obj):
    """Check if an object is an interaction"""
    return isinstance(obj, Interaction)

def is_context(obj):
    """Check if an object is a context"""
    # Command context will be defined in ext.commands
    return hasattr(obj, 'send') and hasattr(obj, 'message')

async def safely_respond_to_interaction(interaction, content, ephemeral=False):
    """Safely respond to an interaction"""
    if not is_interaction(interaction):
        return False
    
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(content, ephemeral=ephemeral)
        else:
            await interaction.followup.send(content, ephemeral=ephemeral)
        return True
    except Exception as e:
        logger.error(f"Error responding to interaction: {e}")
        return False

async def hybrid_send(ctx_or_interaction, content, **kwargs):
    """Send a message to either a context or an interaction"""
    if is_interaction(ctx_or_interaction):
        return await safely_respond_to_interaction(ctx_or_interaction, content)
    else:
        return await ctx_or_interaction.send(content, **kwargs)

def get_user(ctx_or_interaction):
    """Get the user from a context or interaction"""
    if hasattr(ctx_or_interaction, 'user'):
        return ctx_or_interaction.user
    elif hasattr(ctx_or_interaction, 'author'):
        return ctx_or_interaction.author
    return None

def get_guild(ctx_or_interaction):
    """Get the guild from a context or interaction"""
    return getattr(ctx_or_interaction, 'guild', None)

def get_guild_id(ctx_or_interaction):
    """Get the guild ID from a context or interaction"""
    guild = get_guild(ctx_or_interaction)
    return getattr(guild, 'id', None)

# Exports from this module (proper discord API compatibility)
__all__ = [
    # Core classes
    'Intents',
    'AppCommandOptionType',
    'ChannelType',
    'Status',
    'Color',
    'Embed',
    'Message',
    'User',
    'Member',
    'Interaction',
    'InteractionResponse',
    'InteractionFollowup',
    
    # Attributes
    '__version__',
    'version_info',
    
    # Helper functions
    'is_interaction',
    'is_context',
    'safely_respond_to_interaction',
    'hybrid_send',
    'get_user',
    'get_guild',
    'get_guild_id'
]