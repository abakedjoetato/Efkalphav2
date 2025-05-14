"""
Bounties Cog with SlashCommandGroup support for py-cord 2.6.1
"""

import discord
from discord.ext import commands
from typing import Optional, Union, Dict, Any

class BountiesGroup(commands.Cog):
    """Bounty system commands using SlashCommandGroup for py-cord 2.6.1"""
    
    def __init__(self, bot):
        self.bot = bot
        self._db_initialized = hasattr(bot, 'db')
        
    # Define the command group
    bounty = discord.SlashCommandGroup(
        name="bounty", 
        description="Manage player bounties"
    )
    
    # Define subcommands within the group
    @bounty.command(
        name="place",
        description="Place a bounty on a player"
    )
    async def bounty_place(
        self, 
        ctx,
        player_name: discord.Option(str, "Name of the player to place a bounty on"),
        amount: discord.Option(int, "Amount of currency to offer as a bounty"), 
        server_id: discord.Option(str, "The server ID (optional)", required=False) = None
    ):
        """Place a bounty on a player."""
        
        # Check if database is initialized
        if not self._db_initialized:
            await ctx.respond("Database not initialized. Cannot place bounty.", ephemeral=True)
            return
            
        # Check for valid amount
        if amount <= 0:
            await ctx.respond("Bounty amount must be greater than 0.", ephemeral=True)
            return
            
        # Check for valid player name
        if not player_name or len(player_name) < 2:
            await ctx.respond("Please provide a valid player name.", ephemeral=True)
            return
            
        # Respond with success message
        await ctx.respond(f"Placing a {amount} bounty on player {player_name}...")
        
        # Here you would normally add the database code to create the bounty
    
    @bounty.command(
        name="list",
        description="List all active bounties"
    )
    async def bounty_list(
        self, 
        ctx,
        server_id: discord.Option(str, "The server ID (optional)", required=False) = None
    ):
        """List all active bounties."""
        
        # Check if database is initialized
        if not self._db_initialized:
            await ctx.respond("Database not initialized. Cannot list bounties.", ephemeral=True)
            return
            
        # Respond with bounty list
        await ctx.respond("Here are the active bounties:")
        
        # Here you would normally add the database code to list the bounties

    # Add more subcommands as needed
    @bounty.command(
        name="remove",
        description="Remove a bounty you've placed"
    )
    async def bounty_remove(
        self,
        ctx,
        bounty_id: discord.Option(str, "ID of the bounty to remove"),
        server_id: discord.Option(str, "The server ID (optional)", required=False) = None
    ):
        """Remove a bounty you've placed."""
        await ctx.respond(f"Removing bounty with ID {bounty_id}...")

# Setup function to add the cog to the bot
def setup(bot):
    bot.add_cog(BountiesGroup(bot))