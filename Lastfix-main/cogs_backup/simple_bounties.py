"""
Simple Bounties Cog - For testing with py-cord 2.6.1
"""

import discord
from discord.ext import commands

class SimpleBounties(commands.Cog):
    """A simple bounties cog for testing compatibility."""
    
    def __init__(self, bot):
        self.bot = bot
        
    # Create individual slash commands instead of using groups
    @discord.slash_command(
        name="bounty_place",
        description="Place a bounty on a player"
    )
    async def bounty_place(
        self,
        ctx,
        player_name: str,
        amount: int
    ):
        """Place a bounty on a player."""
        await ctx.respond(f"Placing {amount} bounty on {player_name}...")
    
    @discord.slash_command(
        name="bounty_list",
        description="List all active bounties"
    )
    async def bounty_list(self, ctx):
        """List all active bounties."""
        await ctx.respond("Listing all active bounties...")

def setup(bot):
    bot.add_cog(SimpleBounties(bot))