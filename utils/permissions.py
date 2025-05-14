"""
Permissions Module

This module provides utilities for checking permissions and creating
custom command checks for the Discord bot.
"""

import logging
import discord
from discord.ext import commands
from typing import Dict, List, Optional, Union, Callable

# Configure logger
logger = logging.getLogger("utils.permissions")

def is_owner_check(ctx):
    """
    Check if a user is the bot owner
    
    Args:
        ctx: Command context
        
    Returns:
        bool: True if the user is the bot owner, False otherwise
    """
    # Check if the user is in the bot owner IDs
    if hasattr(ctx.bot, 'owner_id'):
        if isinstance(ctx.bot.owner_id, int):
            return ctx.author.id == ctx.bot.owner_id
        elif isinstance(ctx.bot.owner_id, list):
            return ctx.author.id in ctx.bot.owner_id
            
    # Check if the user is the application owner
    return ctx.author.id == ctx.bot.owner_id

def is_owner():
    """
    Check decorator for bot owner
    
    Returns:
        Callable: Command check
    """
    return commands.check(is_owner_check)

def is_guild_owner():
    """
    Check decorator for guild owner
    
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Check if the user is the guild owner
        return ctx.author.id == ctx.guild.owner_id
        
    return commands.check(predicate)

def is_admin():
    """
    Check decorator for admin permissions
    
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Check if the user has admin permissions
        return ctx.author.guild_permissions.administrator
        
    return commands.check(predicate)

def has_role(role_name: str):
    """
    Check decorator for a specific role
    
    Args:
        role_name: Role name to check for
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Get the role by name
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role is None:
            return False
            
        # Check if the user has the role
        return role in ctx.author.roles
        
    return commands.check(predicate)

def has_any_role(*role_names: str):
    """
    Check decorator for any of the specified roles
    
    Args:
        *role_names: Role names to check for
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Get the user's roles
        user_roles = [role.name for role in ctx.author.roles]
        
        # Check if the user has any of the roles
        return any(role in user_roles for role in role_names)
        
    return commands.check(predicate)

def has_all_roles(*role_names: str):
    """
    Check decorator for all of the specified roles
    
    Args:
        *role_names: Role names to check for
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Get the user's roles
        user_roles = [role.name for role in ctx.author.roles]
        
        # Check if the user has all of the roles
        return all(role in user_roles for role in role_names)
        
    return commands.check(predicate)

def has_permissions(**perms):
    """
    Check decorator for guild permissions
    
    This decorator checks if the user has the specified permissions.
    
    Args:
        **perms: Permissions to check for
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Get the user's permissions
        permissions = ctx.author.guild_permissions
        
        # Check if the user has the permissions
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) != value]
        
        if missing:
            logger.debug(f"User {ctx.author} missing permissions: {missing}")
            return False
            
        return True
        
    return commands.check(predicate)

def bot_has_permissions(**perms):
    """
    Check decorator for bot permissions
    
    This decorator checks if the bot has the specified permissions.
    
    Args:
        **perms: Permissions to check for
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Get the bot's permissions
        permissions = ctx.guild.me.guild_permissions
        
        # Check if the bot has the permissions
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) != value]
        
        if missing:
            logger.debug(f"Bot missing permissions: {missing}")
            return False
            
        return True
        
    return commands.check(predicate)

def in_guild(*guild_ids: int):
    """
    Check decorator for specific guilds
    
    This decorator checks if the command is being used in one of the specified guilds.
    
    Args:
        *guild_ids: Guild IDs to check for
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Check if the guild is in the list
        return ctx.guild.id in guild_ids
        
    return commands.check(predicate)

def not_in_guild(*guild_ids: int):
    """
    Check decorator for excluding specific guilds
    
    This decorator checks if the command is not being used in one of the specified guilds.
    
    Args:
        *guild_ids: Guild IDs to exclude
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return True
            
        # Check if the guild is not in the list
        return ctx.guild.id not in guild_ids
        
    return commands.check(predicate)

def in_channel(*channel_ids: int):
    """
    Check decorator for specific channels
    
    This decorator checks if the command is being used in one of the specified channels.
    
    Args:
        *channel_ids: Channel IDs to check for
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the channel is in the list
        return ctx.channel.id in channel_ids
        
    return commands.check(predicate)

def not_in_channel(*channel_ids: int):
    """
    Check decorator for excluding specific channels
    
    This decorator checks if the command is not being used in one of the specified channels.
    
    Args:
        *channel_ids: Channel IDs to exclude
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the channel is not in the list
        return ctx.channel.id not in channel_ids
        
    return commands.check(predicate)

def is_nsfw():
    """
    Check decorator for NSFW channels
    
    This decorator checks if the command is being used in an NSFW channel.
    
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the channel is NSFW
        if isinstance(ctx.channel, discord.TextChannel):
            return ctx.channel.is_nsfw()
            
        # DM channels are considered NSFW
        return isinstance(ctx.channel, discord.DMChannel)
        
    return commands.check(predicate)

def is_dm():
    """
    Check decorator for DM channels
    
    This decorator checks if the command is being used in a DM channel.
    
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the channel is a DM
        return isinstance(ctx.channel, discord.DMChannel)
        
    return commands.check(predicate)

def is_not_dm():
    """
    Check decorator for non-DM channels
    
    This decorator checks if the command is not being used in a DM channel.
    
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the channel is not a DM
        return not isinstance(ctx.channel, discord.DMChannel)
        
    return commands.check(predicate)

def is_mod_or_higher():
    """
    Check decorator for moderator or higher
    
    This decorator checks if the user has the manage_messages permission
    or higher (administrator).
    
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Check if the user has the permissions
        return (ctx.author.guild_permissions.manage_messages or
                ctx.author.guild_permissions.administrator)
                
    return commands.check(predicate)

def can_manage_server():
    """
    Check decorator for server management
    
    This decorator checks if the user has the manage_guild permission
    or higher (administrator).
    
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command is in a guild
        if ctx.guild is None:
            return False
            
        # Check if the user has the permissions
        return (ctx.author.guild_permissions.manage_guild or
                ctx.author.guild_permissions.administrator)
                
    return commands.check(predicate)

def group_only(*group_names: str):
    """
    Check decorator for specific command groups
    
    This decorator checks if the command belongs to one of the specified groups.
    
    Args:
        *group_names: Command group names to check for
        
    Returns:
        Callable: Command check
    """
    def predicate(ctx):
        # Check if the command has a parent
        if not ctx.command.parent:
            return False
            
        # Check if the parent's name is in the list
        return ctx.command.parent.name in group_names
        
    return commands.check(predicate)