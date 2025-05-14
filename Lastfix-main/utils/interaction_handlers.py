"""
Interaction Handlers Module

This module provides safe interaction response handling for Discord bot commands
with compatibility for py-cord 2.6.1.

Key features:
1. Safe interaction response management (checking if already responded)
2. Consistent error and success message formatting
3. Type checking and fallbacks for different interaction states
"""

import logging
from typing import Any, Dict, Optional, Union, TypeVar, cast

import discord
from discord import Interaction, Embed, Colour, ApplicationContext
from discord.errors import NotFound, Forbidden, HTTPException

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for generic typing
T = TypeVar('T')

# We use Any for WebhookMessage because the type can differ between versions
ResponseType = Union[Any, None]


async def safely_respond_to_interaction(
    interaction: Interaction,
    content: Optional[str] = None,
    embed: Optional[Embed] = None,
    embeds: Optional[list] = None,
    ephemeral: bool = False,
    **kwargs
) -> ResponseType:
    """
    Safely respond to an interaction with proper error handling.
    
    Args:
        interaction: The Discord interaction to respond to
        content: Text content to send
        embed: Embed to send
        embeds: List of embeds to send
        ephemeral: Whether the response should be ephemeral
        **kwargs: Additional keyword arguments for the response
        
    Returns:
        The response object if successful, None otherwise
    """
    try:
        # Check if the interaction has already been responded to
        if interaction.response.is_done():
            # Already responded, edit the original message
            try:
                return await interaction.edit_original_response(
                    content=content,
                    embed=embed,
                    embeds=embeds,
                    **kwargs
                )
            except (NotFound, Forbidden, HTTPException) as e:
                logger.error(f"Failed to edit original response: {e}")
                return None
        else:
            # Not responded yet, send the initial response
            await interaction.response.send_message(
                content=content,
                embed=embed,
                embeds=embeds,
                ephemeral=ephemeral,
                **kwargs
            )
            
            # Return the original response for potential future edits
            try:
                return await interaction.original_response()
            except (NotFound, Forbidden, HTTPException) as e:
                logger.error(f"Failed to get original response after sending: {e}")
                return None
    except Exception as e:
        logger.error(f"Error responding to interaction: {e}", exc_info=True)
        # Try a more direct approach as fallback
        try:
            if not interaction.response.is_done():
                if embed and not content:
                    # Only embed provided
                    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                elif content and not embed:
                    # Only content provided
                    await interaction.response.send_message(content=content, ephemeral=ephemeral)
                else:
                    # Both or neither provided - use a generic message as fallback
                    await interaction.response.send_message(
                        content=content or "Action processed",
                        embed=embed,
                        ephemeral=ephemeral
                    )
        except Exception as e2:
            logger.error(f"Critical error responding to interaction: {e2}", exc_info=True)
        return None


async def send_thinking_response(
    interaction: Interaction,
    ephemeral: bool = False
) -> bool:
    """
    Send a thinking (defer) response to an interaction.
    
    Args:
        interaction: The Discord interaction to defer
        ephemeral: Whether the eventual response should be ephemeral
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if interaction.response.is_done():
            logger.warning("Attempted to defer an already-responded interaction")
            return False
        
        await interaction.response.defer(ephemeral=ephemeral)
        return True
    except Exception as e:
        logger.error(f"Error deferring interaction: {e}", exc_info=True)
        return False


async def send_error_response(
    interaction: Interaction,
    error_message: str,
    ephemeral: bool = True,
    title: str = "Error",
    exception: Optional[Exception] = None
) -> ResponseType:
    """
    Send a standardized error response to an interaction.
    
    Args:
        interaction: The Discord interaction to respond to
        error_message: The error message to display
        ephemeral: Whether the response should be ephemeral
        title: Title for the error embed
        exception: Optional exception object for logging
        
    Returns:
        The response object if successful, None otherwise
    """
    # Log the error
    if exception:
        logger.error(f"Error in command: {error_message}", exc_info=exception)
    else:
        logger.error(f"Error in command: {error_message}")
    
    # Create an error embed
    embed = discord.Embed(
        title=title,
        description=error_message,
        color=discord.Color.red()
    )
    
    # Add a footer to indicate it's an error
    embed.set_footer(text="An error occurred")
    
    # Send the response
    return await safely_respond_to_interaction(
        interaction,
        embed=embed,
        ephemeral=ephemeral
    )


async def send_success_response(
    interaction: Interaction,
    message: str,
    ephemeral: bool = False,
    title: str = "Success"
) -> ResponseType:
    """
    Send a standardized success response to an interaction.
    
    Args:
        interaction: The Discord interaction to respond to
        message: The success message to display
        ephemeral: Whether the response should be ephemeral
        title: Title for the success embed
        
    Returns:
        The response object if successful, None otherwise
    """
    # Create a success embed
    embed = discord.Embed(
        title=title,
        description=message,
        color=discord.Color.green()
    )
    
    # Send the response
    return await safely_respond_to_interaction(
        interaction,
        embed=embed,
        ephemeral=ephemeral
    )


def get_error_embed(
    error_message: str,
    title: str = "Error",
    color: Optional[Colour] = None
) -> Embed:
    """
    Create a standardized error embed.
    
    Args:
        error_message: The error message to display
        title: Title for the error embed
        color: Color for the embed
        
    Returns:
        Discord Embed object
    """
    embed = discord.Embed(
        title=title,
        description=error_message,
        color=color or discord.Color.red()
    )
    embed.set_footer(text="An error occurred")
    return embed


def get_success_embed(
    message: str,
    title: str = "Success",
    color: Optional[Colour] = None
) -> Embed:
    """
    Create a standardized success embed.
    
    Args:
        message: The success message to display
        title: Title for the success embed
        color: Color for the embed
        
    Returns:
        Discord Embed object
    """
    embed = discord.Embed(
        title=title,
        description=message,
        color=color or discord.Color.green()
    )
    return embed


# Direct response functions without a responder class
async def edit_original_response_safe(
    interaction: Interaction,
    content: Optional[str] = None,
    embed: Optional[Embed] = None,
    embeds: Optional[list] = None,
    **kwargs
) -> ResponseType:
    """
    Safely edit the original response with proper error handling.
    
    Args:
        interaction: The Discord interaction to edit
        content: New text content
        embed: New embed
        embeds: New list of embeds
        **kwargs: Additional keyword arguments for the edit
        
    Returns:
        The response object if successful, None otherwise
    """
    try:
        return await interaction.edit_original_response(
            content=content,
            embed=embed,
            embeds=embeds,
            **kwargs
        )
    except Exception as e:
        logger.error(f"Error editing original response: {e}", exc_info=True)
        return None


class InteractionResponder:
    """
    Class for handling interaction responses consistently.
    
    This class provides a unified interface for sending responses to Discord interactions,
    with proper error handling and response tracking.
    """
    
    def __init__(self, interaction: Interaction):
        """
        Initialize the responder with an interaction.
        
        Args:
            interaction: The Discord interaction to respond to
        """
        self.interaction = interaction
        self.has_responded = False
        self.response = None
    
    async def defer(self, ephemeral: bool = False) -> bool:
        """
        Defer the response to show a thinking state.
        
        Args:
            ephemeral: Whether the eventual response should be ephemeral
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.has_responded:
                logger.warning("Attempted to defer an already-responded interaction")
                return False
            
            await self.interaction.response.defer(ephemeral=ephemeral)
            self.has_responded = True
            return True
        except Exception as e:
            logger.error(f"Error deferring interaction: {e}", exc_info=True)
            return False
    
    async def send_message(
        self,
        content: Optional[str] = None,
        embed: Optional[Embed] = None,
        embeds: Optional[list] = None,
        ephemeral: bool = False,
        **kwargs
    ) -> ResponseType:
        """
        Send a message response to the interaction.
        
        Args:
            content: Text content to send
            embed: Embed to send
            embeds: List of embeds to send
            ephemeral: Whether the response should be ephemeral
            **kwargs: Additional keyword arguments for the response
            
        Returns:
            The response object if successful, None otherwise
        """
        return await safely_respond_to_interaction(
            self.interaction,
            content=content,
            embed=embed,
            embeds=embeds,
            ephemeral=ephemeral,
            **kwargs
        )
    
    async def send_error(
        self,
        error_message: str,
        ephemeral: bool = True,
        title: str = "Error",
        exception: Optional[Exception] = None
    ) -> ResponseType:
        """
        Send an error response to the interaction.
        
        Args:
            error_message: The error message to display
            ephemeral: Whether the response should be ephemeral
            title: Title for the error embed
            exception: Optional exception object for logging
            
        Returns:
            The response object if successful, None otherwise
        """
        return await send_error_response(
            self.interaction,
            error_message,
            ephemeral=ephemeral,
            title=title,
            exception=exception
        )
    
    async def send_success(
        self,
        message: str,
        ephemeral: bool = False,
        title: str = "Success"
    ) -> ResponseType:
        """
        Send a success response to the interaction.
        
        Args:
            message: The success message to display
            ephemeral: Whether the response should be ephemeral
            title: Title for the success embed
            
        Returns:
            The response object if successful, None otherwise
        """
        return await send_success_response(
            self.interaction,
            message,
            ephemeral=ephemeral,
            title=title
        )
    
    async def edit_response(
        self,
        content: Optional[str] = None,
        embed: Optional[Embed] = None,
        embeds: Optional[list] = None,
        **kwargs
    ) -> ResponseType:
        """
        Edit the original response.
        
        Args:
            content: New text content
            embed: New embed
            embeds: New list of embeds
            **kwargs: Additional keyword arguments for the edit
            
        Returns:
            The response object if successful, None otherwise
        """
        return await edit_original_response_safe(
            self.interaction,
            content=content,
            embed=embed,
            embeds=embeds,
            **kwargs
        )