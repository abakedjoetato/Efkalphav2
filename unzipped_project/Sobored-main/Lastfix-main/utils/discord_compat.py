"""
Discord Compatibility Layer

This module provides compatibility functions and classes for working with
discord.py and py-cord 2.6.1, addressing various differences in the APIs.

Key features:
1. Compatible SlashCommandGroup creation
2. Safe context attribute access
3. Utility functions for Discord API interactions
4. Runtime patching for cross-version compatibility
5. Command utilities for name and signature extraction
"""

import logging
import inspect
from typing import Optional, List, Union, Any, Callable, Dict, TypeVar, Generic, get_type_hints

import discord
from discord import SlashCommandGroup, ApplicationContext, Interaction
from discord.ext import commands

# Set up logging
logger = logging.getLogger(__name__)

# Check if we can import app_commands (discord.py 2.0+)
try:
    from discord import app_commands
    HAS_APP_COMMANDS = True
except ImportError:
    HAS_APP_COMMANDS = False
    logger.info("app_commands not available, using py-cord compatibility")

# Type variable for generic typing
T = TypeVar('T')


def create_slash_group(
    name: str,
    description: str,
    guild_ids: Optional[List[int]] = None,
    guild_only: bool = False,
    nsfw: bool = False
) -> SlashCommandGroup:
    """
    Create a SlashCommandGroup with compatibility for py-cord 2.6.1.
    
    Args:
        name: The name of the command group
        description: The description of the command group
        guild_ids: Optional list of guild IDs where the command will be registered
        guild_only: Whether the command is guild-only
        nsfw: Whether the command is NSFW
        
    Returns:
        SlashCommandGroup instance
    """
    try:
        # Create kwargs dictionary with only supported parameters
        kwargs = {
            "name": name,
            "description": description,
        }
        
        # Handle guild_ids - some versions use different parameter names
        if guild_ids is not None:
            # Check if the init accepts guild_ids parameter
            sig = inspect.signature(SlashCommandGroup.__init__)
            if "guild_ids" in sig.parameters:
                kwargs["guild_ids"] = guild_ids
            elif "guilds" in sig.parameters:
                kwargs["guilds"] = guild_ids
        
        # Some parameters were added later, so we check if they're supported
        sig = inspect.signature(SlashCommandGroup.__init__)
        if "guild_only" in sig.parameters:
            kwargs["guild_only"] = guild_only
        if "nsfw" in sig.parameters:
            kwargs["nsfw"] = nsfw
            
        group = SlashCommandGroup(**kwargs)
        logger.debug(f"Created SlashCommandGroup: {name}")
        return group
    
    except Exception as e:
        logger.error(f"Error creating SlashCommandGroup '{name}': {e}", exc_info=True)
        # Fallback to basic SlashCommandGroup
        return SlashCommandGroup(name=name, description=description)


def create_subgroup(
    parent: SlashCommandGroup,
    name: str,
    description: str
) -> SlashCommandGroup:
    """
    Create a subgroup of a SlashCommandGroup with compatibility for py-cord 2.6.1.
    
    Args:
        parent: The parent SlashCommandGroup
        name: The name of the subgroup
        description: The description of the subgroup
        
    Returns:
        SlashCommandGroup instance for the subgroup
    """
    try:
        # Different versions have different ways to create subgroups
        if hasattr(parent, "create_subgroup"):
            # Newer versions have a create_subgroup method
            subgroup = parent.create_subgroup(name=name, description=description)
        elif hasattr(parent, "group"):
            # Some versions use group as a method
            if callable(parent.group):
                subgroup = parent.group(name=name, description=description)
            else:
                # Fallback if group exists but isn't callable
                logger.warning(f"parent.group exists but is not callable for {parent.name}")
                subgroup = SlashCommandGroup(name=f"{parent.name}_{name}", description=description)
        else:
            # Fallback: create a new group with a name that indicates hierarchy
            logger.warning(f"Using fallback method to create subgroup '{name}' for parent '{parent.name}'")
            subgroup = SlashCommandGroup(name=f"{parent.name}_{name}", description=description)
            # Attach to parent for reference
            setattr(parent, f"subgroup_{name}", subgroup)
        
        logger.debug(f"Created subgroup '{name}' for parent '{parent.name}'")
        return subgroup
    
    except Exception as e:
        logger.error(f"Error creating subgroup '{name}' for parent '{parent.name}': {e}", exc_info=True)
        # Fallback
        subgroup = SlashCommandGroup(name=f"{parent.name}_{name}", description=description)
        return subgroup


def get_interaction_from_context(ctx: ApplicationContext) -> Optional[Interaction]:
    """
    Safely get the interaction from an ApplicationContext.
    
    Args:
        ctx: The ApplicationContext
        
    Returns:
        The Interaction or None if not available
    """
    # First try the standard attribute
    if hasattr(ctx, "interaction"):
        return ctx.interaction
    
    # Some versions use a protected attribute
    if hasattr(ctx, "_interaction"):
        return ctx._interaction
    
    # Last resort - look for any attribute that is an Interaction
    try:
        for attr_name in dir(ctx):
            if attr_name.startswith("_") and not attr_name.startswith("__"):
                attr = getattr(ctx, attr_name, None)
                if attr and isinstance(attr, Interaction):
                    return attr
    except Exception as e:
        logger.error(f"Error finding interaction in context: {e}")
    
    logger.warning("Could not find interaction in ApplicationContext")
    return None


def get_user_from_context(ctx: ApplicationContext) -> Optional[Union[discord.User, discord.Member]]:
    """
    Safely get the user from an ApplicationContext.
    
    Args:
        ctx: The ApplicationContext
        
    Returns:
        The User/Member or None if not available
    """
    # Try standard attributes first
    if hasattr(ctx, "author") and ctx.author is not None:
        return ctx.author
    
    if hasattr(ctx, "user") and ctx.user is not None:
        return ctx.user
    
    # Get from interaction if possible
    interaction = get_interaction_from_context(ctx)
    if interaction and hasattr(interaction, "user") and interaction.user is not None:
        return interaction.user
    
    logger.warning("Could not find user in ApplicationContext")
    return None


def get_guild_from_context(ctx: ApplicationContext) -> Optional[discord.Guild]:
    """
    Safely get the guild from an ApplicationContext.
    
    Args:
        ctx: The ApplicationContext
        
    Returns:
        The Guild or None if not available
    """
    # Try standard attributes first
    if hasattr(ctx, "guild") and ctx.guild is not None:
        return ctx.guild
    
    # Get from interaction if possible
    interaction = get_interaction_from_context(ctx)
    if interaction and hasattr(interaction, "guild") and interaction.guild is not None:
        return interaction.guild
    
    # Try to get from internal references if available
    try:
        if hasattr(ctx, "bot") and hasattr(ctx, "guild_id") and ctx.guild_id is not None and ctx.bot is not None:
            guild_id = ctx.guild_id
            return ctx.bot.get_guild(guild_id)
    except Exception as e:
        logger.error(f"Error getting guild from context bot: {e}")
    
    logger.warning("Could not find guild in ApplicationContext")
    return None


def get_channel_from_context(ctx: ApplicationContext) -> Optional[discord.abc.GuildChannel]:
    """
    Safely get the channel from an ApplicationContext.
    
    Args:
        ctx: The ApplicationContext
        
    Returns:
        The Channel or None if not available
    """
    # Try standard attributes first
    if hasattr(ctx, "channel") and ctx.channel is not None:
        return ctx.channel
    
    # Get from interaction if possible
    interaction = get_interaction_from_context(ctx)
    if interaction and hasattr(interaction, "channel") and interaction.channel is not None:
        return interaction.channel
    
    # Try to get from guild
    try:
        guild = get_guild_from_context(ctx)
        if guild and hasattr(ctx, "channel_id") and ctx.channel_id is not None:
            channel = guild.get_channel(ctx.channel_id)
            if channel:
                return channel
    except Exception as e:
        logger.error(f"Error getting channel from context guild: {e}")
    
    logger.warning("Could not find channel in ApplicationContext")
    return None


def guild_only(error_message: str = "This command can only be used in a server."):
    """
    Decorator to make a command guild-only with better error handling.
    
    Args:
        error_message: The error message to display when used outside a guild
        
    Returns:
        Command decorator
    """
    def decorator(func):
        async def wrapper(self, ctx, *args, **kwargs):
            # Check if we're in a guild
            guild = get_guild_from_context(ctx)
            if not guild:
                # Get interaction for response
                interaction = get_interaction_from_context(ctx)
                if interaction:
                    # Import here to avoid circular imports
                    try:
                        from utils.interaction_handlers import send_error_response
                        await send_error_response(
                            interaction,
                            error_message,
                            ephemeral=True
                        )
                    except ImportError:
                        # Fallback if interaction_handlers is not available
                        if hasattr(interaction, "response") and hasattr(interaction.response, "send_message"):
                            await interaction.response.send_message(
                                error_message,
                                ephemeral=True
                            )
                    return None
                else:
                    # Fallback for prefix commands
                    try:
                        await ctx.send(error_message)
                    except Exception as e:
                        logger.error(f"Failed to send guild_only message: {e}")
                    return None
            
            # Call the original function
            return await func(self, ctx, *args, **kwargs)
        
        # Copy metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


# Utility function for datetime operations
def get_utcnow():
    """
    Get current UTC time with compatibility across Discord library versions.
    
    Different versions of Discord.py handle this differently:
    - discord.utils.utcnow() in newer versions
    - datetime.datetime.utcnow() in older versions
    
    Returns:
        datetime.datetime: Current UTC time
    """
    try:
        # Try the newer discord.utils.utcnow first
        from discord.utils import utcnow
        return utcnow()
    except (ImportError, AttributeError):
        # Fall back to standard datetime
        import datetime
        return datetime.datetime.now(datetime.timezone.utc)


class SafeApplicationContext:
    """
    Wrapper for ApplicationContext that provides safe attribute access.
    
    This wrapper handles differences between different versions of the Discord.py
    libraries and provides consistent access to common attributes.
    """
    
    def __init__(self, ctx: ApplicationContext):
        """
        Initialize the safe context wrapper.
        
        Args:
            ctx: The original ApplicationContext
        """
        self._ctx = ctx
        self._interaction = get_interaction_from_context(ctx)
    
    @property
    def author(self) -> Union[discord.User, discord.Member, None]:
        """Get the command author (user)."""
        return get_user_from_context(self._ctx)
    
    @property
    def user(self) -> Union[discord.User, discord.Member, None]:
        """Get the command user (alias for author)."""
        return self.author
    
    @property
    def guild(self) -> Optional[discord.Guild]:
        """Get the guild where the command was used."""
        return get_guild_from_context(self._ctx)
    
    @property
    def channel(self) -> Optional[discord.abc.GuildChannel]:
        """Get the channel where the command was used."""
        return get_channel_from_context(self._ctx)
    
    @property
    def bot(self) -> Optional[commands.Bot]:
        """Get the bot instance."""
        if hasattr(self._ctx, "bot"):
            return self._ctx.bot
        return None
    
    @property
    def interaction(self) -> Optional[Interaction]:
        """Get the interaction."""
        return self._interaction
    
    def __getattr__(self, name: str) -> Any:
        """
        Get an attribute from the underlying context.
        
        Args:
            name: The attribute name
            
        Returns:
            The attribute value
            
        Raises:
            AttributeError: If the attribute doesn't exist
        """
        return getattr(self._ctx, name)


# Command utility functions
def get_command_name(command) -> str:
    """
    Get the full name of a command with compatibility across Discord libraries.
    
    Args:
        command: Discord command object
        
    Returns:
        str: Full command name including parent groups
    """
    try:
        if command is None:
            return "unknown_command"
            
        if hasattr(command, "qualified_name"):
            return command.qualified_name
            
        if hasattr(command, "name"):
            # Check if it's part of a group
            parent_name = ""
            if hasattr(command, "parent") and command.parent:
                if hasattr(command.parent, "qualified_name"):
                    parent_name = f"{command.parent.qualified_name} "
                elif hasattr(command.parent, "name"):
                    parent_name = f"{command.parent.name} "
            
            return f"{parent_name}{command.name}".strip()
            
        # Last resort
        return str(command)
        
    except Exception as e:
        logger.error(f"Error getting command name: {e}")
        return "unknown_command"


def format_command_signature(command) -> str:
    """
    Format a command's signature for help text with compatibility across Discord libraries.
    
    Args:
        command: Discord command object
        
    Returns:
        str: Formatted command signature
    """
    try:
        if command is None:
            return "unknown_command"
            
        # Get the command name first
        signature = get_command_name(command)
        
        # Check if signature is already available
        if hasattr(command, "signature") and command.signature:
            return f"{signature} {command.signature}".strip()
            
        # Extract parameters from the callback
        params = []
        if hasattr(command, "callback") and command.callback:
            # Skip self, ctx, and context
            callback = command.callback
            param_names = list(inspect.signature(callback).parameters.keys())
            param_info = inspect.signature(callback).parameters
            
            for name in param_names:
                # Skip self and context parameters
                if name in ("self", "ctx", "context"):
                    continue
                
                # Format based on parameter properties
                param = param_info[name]
                formatted = name
                
                # Check if it has a default value
                if param.default is not inspect.Parameter.empty:
                    if param.default is None:
                        formatted = f"[{name}=None]"
                    else:
                        formatted = f"[{name}={param.default}]"
                # Check if it's a required *args or **kwargs
                elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                    formatted = f"[*{name}]"
                elif param.kind == inspect.Parameter.VAR_KEYWORD:
                    formatted = f"[**{name}]"
                # Otherwise it's required
                else:
                    formatted = f"<{name}>"
                
                params.append(formatted)
        
        # Add parameters to signature
        if params:
            return f"{signature} {' '.join(params)}"
        return signature
        
    except Exception as e:
        logger.error(f"Error formatting command signature: {e}")
        return get_command_name(command)


def is_guild_only(command) -> bool:
    """
    Check if a command is guild-only with compatibility across Discord libraries.
    
    Args:
        command: Discord command object
        
    Returns:
        bool: True if the command is guild-only, False otherwise
    """
    try:
        # Check the guild_only attribute
        if hasattr(command, "guild_only"):
            return bool(command.guild_only)
            
        # Check for the NoPrivateMessage check
        if hasattr(command, "checks") and command.checks:
            for check in command.checks:
                # Get function name and module
                check_name = getattr(check, "__name__", "")
                check_module = getattr(check, "__module__", "")
                
                # Check for common guild-only check patterns
                if check_name == "guild_only":
                    return True
                elif check_name == "check" and "guild_only" in str(check):
                    return True
                elif "commands.guild_only" in f"{check_module}.{check_name}":
                    return True
                elif "NoPrivateMessage" in str(check):
                    return True
        
        # Not found to be guild-only
        return False
        
    except Exception as e:
        logger.error(f"Error checking if command is guild_only: {e}")
        return False


# Function to apply all runtime compatibility patches
def patch_all() -> bool:
    """
    Apply all compatibility patches for discord.py/py-cord.

    This function applies all necessary runtime patches to ensure
    compatibility between different versions of Discord libraries.
    
    Returns:
        bool: True if patches were successfully applied, False otherwise
    """
    try:
        logger.info("Applying Discord compatibility patches...")
        
        # Ensure utility functions are accessible
        from utils.discord_patches import are_patches_applied, PYCORD_VERSION, USING_PYCORD_261_PLUS
        
        # Check if patches were already applied
        if are_patches_applied():
            logger.info(f"Discord patches already applied, detected version: {PYCORD_VERSION}")
            return True
            
        # Patch hybrid commands
        try:
            import discord
            from discord.ext import commands
            if not hasattr(commands, 'hybrid_command'):
                logger.info("Adding hybrid_command support")
                from utils.discord_patches import hybrid_command, hybrid_group
                commands.hybrid_command = hybrid_command
                commands.hybrid_group = hybrid_group
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to patch hybrid commands: {e}")
            
        # Apply other patches as needed
        
        # Verify patches were applied
        if are_patches_applied():
            logger.info("Discord compatibility patches successfully applied")
            return True
        else:
            logger.warning("Discord compatibility patches were not fully applied")
            return False
            
    except Exception as e:
        logger.error(f"Error applying Discord compatibility patches: {e}", exc_info=True)
        return False