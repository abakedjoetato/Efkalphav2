"""
Premium Features Cog

This cog provides commands related to premium features in the Discord bot.
It integrates with the premium feature access system to manage and display
premium feature information.
"""

import logging
import discord
from discord.ext import commands
from typing import Optional

# Import premium feature access utilities
from utils.premium_feature_access import (
    PremiumManager, 
    FeatureAccessLevel,
    requires_premium_feature
)

# Configure logger
logger = logging.getLogger("cogs.premium")

class Premium(commands.Cog):
    """
    Premium features management cog
    
    This cog provides commands to view and manage premium features.
    """
    
    def __init__(self, bot):
        """
        Initialize the cog
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        
    @commands.command(name="premium")
    async def premium_info(self, ctx):
        """
        View information about premium features
        
        This command shows information about available premium features
        and the guild's current premium status.
        """
        # Get the premium manager from the bot
        premium_manager = getattr(self.bot, "premium_manager", None)
        if not premium_manager:
            await ctx.send("❌ Premium features are not available.")
            return
            
        # Get guild premium info
        if ctx.guild:
            # Guild context, show guild-specific info
            embed = await premium_manager.get_guild_features_embed(ctx.guild.id)
            await ctx.send(embed=embed)
        else:
            # DM context, show general info
            embed = premium_manager.get_premium_info_embed()
            await ctx.send(embed=embed)
            
    @commands.command(name="premium_set")
    @commands.has_permissions(administrator=True)
    async def set_premium_level(self, ctx, level: int):
        """
        Set the premium level for the guild (Admin only)
        
        Args:
            level: Premium level (0-4)
        """
        # Validate the level
        if level < 0 or level > 4:
            await ctx.send("❌ Invalid premium level. Must be between 0 and 4.")
            return
            
        # Get the premium manager from the bot
        premium_manager = getattr(self.bot, "premium_manager", None)
        if not premium_manager:
            await ctx.send("❌ Premium features are not available.")
            return
            
        # Set the premium level
        success = await premium_manager.set_guild_premium_level(ctx.guild.id, level)
        
        if success:
            level_name = FeatureAccessLevel.get_name(level)
            await ctx.send(f"✅ Premium level set to **{level_name}** (Level {level}).")
        else:
            await ctx.send("❌ Failed to set premium level.")
            
    @commands.command(name="premium_features")
    async def list_premium_features(self, ctx):
        """List all available premium features"""
        # Get the premium manager from the bot
        premium_manager = getattr(self.bot, "premium_manager", None)
        if not premium_manager:
            await ctx.send("❌ Premium features are not available.")
            return
            
        # Get all features
        features = premium_manager.registry.get_all_features()
        
        if not features:
            await ctx.send("No premium features are registered.")
            return
            
        # Group by level
        levels = {}
        for feature in features:
            level = feature.required_level
            if level not in levels:
                levels[level] = []
            levels[level].append(feature)
            
        # Create embed
        embed = discord.Embed(
            title="Premium Features",
            description="Here are all available premium features:",
            color=0x00a8ff
        )
        
        # Add fields for each level
        for level in sorted(levels.keys()):
            level_features = levels[level]
            level_name = FeatureAccessLevel.get_name(level)
            
            field_value = ""
            for feature in level_features:
                field_value += f"**{feature.name}**: {feature.description}\n"
                
            embed.add_field(
                name=f"{level_name} Tier (Level {level})",
                value=field_value,
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @commands.command(name="premium_check")
    @requires_premium_feature("advanced_logging")
    async def premium_check(self, ctx):
        """Test command that requires premium features"""
        await ctx.send("✅ Your guild has access to the advanced_logging feature!")
        
def setup(bot):
    """
    Set up the premium cog
    
    Args:
        bot: The Discord bot instance
    """
    bot.add_cog(Premium(bot))
    logger.info("Premium cog loaded")