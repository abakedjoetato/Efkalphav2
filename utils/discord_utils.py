"""
Discord utility functions for cogs
"""

import logging
import asyncio
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Coroutine

import discord
from discord.ext import commands

from utils.safe_mongodb import SafeMongoDBResult, SafeDocument
from utils.discord_patches import app_commands

logger = logging.getLogger(__name__)

async def server_id_autocomplete(ctx):
    """Autocomplete for server IDs
    
    Args:
        ctx: The AutocompleteContext
        
    Returns:
        List of guild IDs that the bot is connected to
    """
    try:
        guilds = ctx.bot.guilds
        choices = [
            (f"{guild.name} ({guild.id})", str(guild.id)) 
            for guild in guilds[:25]
        ]
        return choices
    except Exception as e:
        logger.error(f"Error in server_id_autocomplete: {e}")
        return [("Error fetching servers", "0")]

async def command_handler(coro, *args, **kwargs):
    """
    Wrapper for command handling with proper error handling
    
    Args:
        coro: The coroutine to execute
        args: Arguments to pass to the coroutine
        kwargs: Keyword arguments to pass to the coroutine
        
    Returns:
        The result of the coroutine
    """
    try:
        return await coro(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in command_handler: {e}")
        raise

async def defer_interaction(interaction):
    """
    Safely defer an interaction with error handling
    
    Args:
        interaction: The interaction to defer
        
    Returns:
        True if deferred successfully, False otherwise
    """
    try:
        if not interaction.response.is_done():
            await interaction.response.defer()
            return True
    except Exception as e:
        logger.error(f"Failed to defer interaction: {e}")
    return False

async def safely_respond_to_interaction(
    interaction, 
    message: str, 
    ephemeral: bool = False, 
    embed: Optional[discord.Embed] = None
):
    """
    Safely respond to an interaction with error handling
    
    Args:
        interaction: The interaction to respond to
        message: The message to send
        ephemeral: Whether the response should be ephemeral
        embed: Optional embed to send
        
    Returns:
        True if responded successfully, False otherwise
    """
    try:
        if not interaction.response.is_done():
            if embed:
                await interaction.response.send_message(message, ephemeral=ephemeral, embed=embed)
            else:
                await interaction.response.send_message(message, ephemeral=ephemeral)
            return True
        else:
            if embed:
                await interaction.followup.send(message, ephemeral=ephemeral, embed=embed)
            else:
                await interaction.followup.send(message, ephemeral=ephemeral)
            return True
    except Exception as e:
        logger.error(f"Failed to respond to interaction: {e}")
        return False

async def db_operation(db_func, *args, **kwargs):
    """
    Wrapper for database operations with proper error handling
    
    Args:
        db_func: The database function to execute
        args: Arguments to pass to the function
        kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the database function
    """
    try:
        return await db_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in db_operation: {e}")
        return SafeMongoDBResult.error_result(f"Database error: {e}")

async def get_guild_document(db, guild_id: Union[str, int]) -> Optional[Dict[str, Any]]:
    """
    Get a guild document from the database safely.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        
    Returns:
        Optional[Dict[str, Any]]: Guild document or None if not found
    """
    if not db:
        logger.warning("Database not available for get_guild_document")
        return None
        
    try:
        guilds_collection = db.guilds
        str_guild_id = str(guild_id)
        
        # Use get_document_safely from safe_database if available
        if hasattr(db, "get_document_safely"):
            return await db.get_document_safely(guilds_collection, {"guild_id": str_guild_id})
            
        # Alternative implementation
        from utils.safe_database import get_document_safely
        return await get_document_safely(guilds_collection, {"guild_id": str_guild_id})
    except Exception as e:
        logger.error(f"Error in get_guild_document for guild {guild_id}: {e}")
        return None

async def hybrid_send(
    ctx_or_interaction, 
    content=None, 
    *,
    embed=None,
    embeds=None,
    file=None,
    files=None,
    view=None,
    ephemeral=False,
    delete_after=None,
    allowed_mentions=None,
    reference=None,
    mention_author=None
):
    """
    Send a response to either a Context or Interaction object.
    
    This function handles all the compatibility checks and uses the appropriate method.
    
    Args:
        ctx_or_interaction: Context or Interaction object
        content: Message content
        embed: Embed to send
        embeds: List of embeds to send
        file: File to send
        files: List of files to send
        view: View to attach
        ephemeral: Whether the response should be ephemeral
        delete_after: Seconds after which to delete the message
        allowed_mentions: Allowed mentions for the message
        reference: Message to reply to
        mention_author: Whether to mention the author in a reply
        
    Returns:
        Message object or None
    """
    # Set up kwargs for the send call
    kwargs = {
        'embed': embed,
        'embeds': embeds,
        'file': file,
        'files': files,
        'view': view,
        'delete_after': delete_after,
        'allowed_mentions': allowed_mentions,
    }
    
    # Remove None values to prevent API errors
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    try:
        # Handle interaction objects
        if isinstance(ctx_or_interaction, discord.Interaction):
            interaction = ctx_or_interaction
            
            # For interactions we can set ephemeral
            if ephemeral:
                kwargs['ephemeral'] = True
            
            # Check if the interaction response is already done
            if interaction.response.is_done():
                # Use followup if the response is already sent
                return await interaction.followup.send(content, **kwargs)
            else:
                # Use the response directly
                return await interaction.response.send_message(content, **kwargs)
                
        # Handle context objects
        elif isinstance(ctx_or_interaction, commands.Context):
            ctx = ctx_or_interaction
            
            # For context objects, we can use reference and mention_author
            if reference is not None:
                kwargs['reference'] = reference
                
            if mention_author is not None:
                kwargs['mention_author'] = mention_author
                
            # Regular contexts don't support ephemeral
            # (ephemeral is silently ignored here)
            return await ctx.send(content, **kwargs)
            
        # Handle application contexts (slash commands)
        elif hasattr(ctx_or_interaction, "respond") and callable(getattr(ctx_or_interaction, "respond")):
            # For application contexts, ephemeral is supported
            if ephemeral:
                kwargs['ephemeral'] = True
                
            return await ctx_or_interaction.respond(content, **kwargs)
            
        # Handle other types by trying to use a send method
        elif hasattr(ctx_or_interaction, "send") and callable(getattr(ctx_or_interaction, "send")):
            return await ctx_or_interaction.send(content, **kwargs)
            
        # If all else fails, log an error
        else:
            logger.error(f"Cannot send to object of type {type(ctx_or_interaction)}")
            return None
            
    except Exception as e:
        logger.error(f"Error in hybrid_send: {e}")
        # Try to send an error message
        try:
            if isinstance(ctx_or_interaction, discord.Interaction):
                if not ctx_or_interaction.response.is_done():
                    await ctx_or_interaction.response.send_message(f"Error sending message: {str(e)}", ephemeral=True)
                else:
                    await ctx_or_interaction.followup.send(f"Error sending message: {str(e)}", ephemeral=True)
            elif hasattr(ctx_or_interaction, "send"):
                await ctx_or_interaction.send(f"Error sending message: {str(e)}")
        except Exception:
            # If we can't send an error message, just log it
            logger.error("Failed to send error message", exc_info=True)
        return None