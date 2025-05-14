"""
Premium Commands Cog

This cog provides commands for premium feature management.
"""

import logging
import discord
from discord.ext import commands
import asyncio
from typing import Optional, Union
import datetime

# Import premium utilities
from utils.premium_manager import requires_premium_feature
from utils.premium_models import PremiumTier, PremiumGuild, PremiumUser
from utils.permissions import is_owner, is_admin, is_guild_owner

# Configure logger
logger = logging.getLogger("cogs.premium_commands")

class PremiumCommands(commands.Cog):
    """
    Premium feature commands
    
    This cog provides commands for premium feature management.
    """
    
    def __init__(self, bot):
        """
        Initialize the cog
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        
    @property
    def premium_manager(self):
        """
        Get the premium manager
        
        Returns:
            PremiumManager: Premium manager instance
        """
        return getattr(self.bot, "premium_manager", None)
        
    @property
    def db_client(self):
        """
        Get the MongoDB client
        
        Returns:
            SafeMongoDBClient: MongoDB client instance
        """
        return getattr(self.bot, "_db_client", None)
        
    @commands.group(name="premium", invoke_without_command=True)
    async def premium_group(self, ctx):
        """
        Premium feature management
        
        This command group provides access to premium feature management.
        """
        if ctx.invoked_subcommand is None:
            # Show premium info
            if self.premium_manager:
                if ctx.guild:
                    # Show guild premium info
                    embed = await self.premium_manager.get_guild_features_embed(ctx.guild.id)
                else:
                    # Show general premium info
                    embed = self.premium_manager.get_premium_info_embed()
                    
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Premium features are not available.")
                
    @premium_group.command(name="info")
    async def premium_info(self, ctx):
        """
        View premium feature information
        
        This command shows information about available premium features.
        """
        if self.premium_manager:
            embed = self.premium_manager.get_premium_info_embed()
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Premium features are not available.")
            
    @premium_group.command(name="status")
    async def premium_status(self, ctx):
        """
        View guild premium status
        
        This command shows the premium status of the current guild.
        """
        if not ctx.guild:
            await ctx.send("❌ This command can only be used in a guild.")
            return
            
        if self.premium_manager:
            embed = await self.premium_manager.get_guild_features_embed(ctx.guild.id)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Premium features are not available.")
            
    @premium_group.command(name="set")
    @is_owner()
    async def set_premium(self, ctx, guild_id: Optional[int] = None, tier: str = "FREE", days: int = 30):
        """
        Set guild premium tier (Owner only)
        
        This command sets the premium tier for a guild.
        
        Args:
            guild_id: Guild ID (default: current guild)
            tier: Premium tier (FREE, BASIC, STANDARD, PRO, ENTERPRISE)
            days: Subscription duration in days (default: 30)
        """
        # Default to current guild
        if guild_id is None and ctx.guild:
            guild_id = ctx.guild.id
            
        if not guild_id:
            await ctx.send("❌ Please specify a guild ID.")
            return
            
        if not self.premium_manager or not self.db_client:
            await ctx.send("❌ Premium features are not available.")
            return
            
        # Get the guild from Discord
        guild = self.bot.get_guild(guild_id)
        guild_name = f"{guild.name} ({guild_id})" if guild else f"Unknown ({guild_id})"
        
        # Validate tier
        tier_upper = tier.upper()
        valid_tiers = ["FREE", "BASIC", "STANDARD", "PRO", "ENTERPRISE"]
        
        if tier_upper not in valid_tiers:
            await ctx.send(f"❌ Invalid tier. Must be one of: {', '.join(valid_tiers)}")
            return
            
        # Set the guild tier
        success = await self.premium_manager.set_guild_tier(guild_id, tier_upper)
        
        if success:
            # Extend subscription
            if days > 0 and tier_upper != "FREE":
                guild_db = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
                
                if guild_db:
                    # Extend subscription
                    expires_at = guild_db.extend_subscription(days)
                    
                    # Save the guild
                    await guild_db.save(self.db_client)
                    
                    # Format expiration date
                    expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
                    
                    await ctx.send(f"✅ Set {guild_name} to **{tier_upper}** tier. Expires on: {expires_str}")
                else:
                    await ctx.send(f"✅ Set {guild_name} to **{tier_upper}** tier.")
            else:
                await ctx.send(f"✅ Set {guild_name} to **{tier_upper}** tier.")
        else:
            await ctx.send(f"❌ Failed to set premium tier for {guild_name}.")
            
    @premium_group.command(name="feature")
    @is_owner()
    async def enable_feature(self, ctx, feature_name: str, guild_id: Optional[int] = None, enable: bool = True):
        """
        Enable/disable a feature for a guild (Owner only)
        
        This command enables or disables a specific feature for a guild.
        
        Args:
            feature_name: Feature name
            guild_id: Guild ID (default: current guild)
            enable: Whether to enable (True) or disable (False) the feature
        """
        # Default to current guild
        if guild_id is None and ctx.guild:
            guild_id = ctx.guild.id
            
        if not guild_id:
            await ctx.send("❌ Please specify a guild ID.")
            return
            
        if not self.premium_manager:
            await ctx.send("❌ Premium features are not available.")
            return
            
        # Get the guild from Discord
        guild = self.bot.get_guild(guild_id)
        guild_name = f"{guild.name} ({guild_id})" if guild else f"Unknown ({guild_id})"
        
        # Get the feature
        feature = self.premium_manager.get_feature(feature_name)
        
        if not feature:
            await ctx.send(f"❌ Feature not found: {feature_name}")
            return
            
        # Enable/disable the feature
        if enable:
            success = await self.premium_manager.enable_guild_feature(guild_id, feature_name)
            
            if success:
                await ctx.send(f"✅ Enabled feature **{feature_name}** for {guild_name}.")
            else:
                await ctx.send(f"❌ Failed to enable feature **{feature_name}** for {guild_name}.")
        else:
            success = await self.premium_manager.disable_guild_feature(guild_id, feature_name)
            
            if success:
                await ctx.send(f"✅ Disabled feature **{feature_name}** for {guild_name}.")
            else:
                await ctx.send(f"❌ Failed to disable feature **{feature_name}** for {guild_name}.")
                
    @premium_group.command(name="extend")
    @is_owner()
    async def extend_subscription(self, ctx, guild_id: Optional[int] = None, days: int = 30):
        """
        Extend guild subscription (Owner only)
        
        This command extends the premium subscription for a guild.
        
        Args:
            guild_id: Guild ID (default: current guild)
            days: Number of days to extend (default: 30)
        """
        # Default to current guild
        if guild_id is None and ctx.guild:
            guild_id = ctx.guild.id
            
        if not guild_id:
            await ctx.send("❌ Please specify a guild ID.")
            return
            
        if not self.premium_manager:
            await ctx.send("❌ Premium features are not available.")
            return
            
        # Get the guild from Discord
        guild = self.bot.get_guild(guild_id)
        guild_name = f"{guild.name} ({guild_id})" if guild else f"Unknown ({guild_id})"
        
        # Extend the subscription
        expires_at = await self.premium_manager.extend_guild_subscription(guild_id, days)
        
        if expires_at:
            # Format expiration date
            expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
            
            await ctx.send(f"✅ Extended premium subscription for {guild_name} by {days} days. Expires on: {expires_str}")
        else:
            await ctx.send(f"❌ Failed to extend premium subscription for {guild_name}.")
            
    @premium_group.command(name="list")
    @is_owner()
    async def list_premium(self, ctx):
        """
        List premium guilds (Owner only)
        
        This command lists all guilds with premium status.
        """
        if not self.premium_manager:
            await ctx.send("❌ Premium features are not available.")
            return
            
        # Get all premium guilds
        guilds = await self.premium_manager.get_premium_guilds()
        
        if not guilds:
            await ctx.send("No guilds have premium status.")
            return
            
        # Create pages of guild information
        pages = []
        
        # 5 guilds per page
        for i in range(0, len(guilds), 5):
            guild_chunk = guilds[i:i + 5]
            
            # Create embed for this page
            embed = discord.Embed(
                title="Premium Guilds",
                description=f"Guilds {i + 1}-{i + len(guild_chunk)} of {len(guilds)}",
                color=0x00a8ff
            )
            
            # Add guild information
            for guild_db in guild_chunk:
                # Get the guild from Discord
                guild = self.bot.get_guild(guild_db.guild_id)
                guild_name = guild.name if guild else f"Unknown ({guild_db.guild_id})"
                
                # Get tier name
                tier_name = PremiumTier.get_name(guild_db.tier)
                
                # Format expiration date
                expires_str = "No expiration"
                if guild_db.expires_at:
                    expires_str = guild_db.expires_at.strftime("%Y-%m-%d %H:%M:%S")
                    
                # Create field value
                value = f"ID: {guild_db.guild_id}\nTier: {tier_name}\nExpires: {expires_str}"
                
                if guild_db.notes:
                    value += f"\nNotes: {guild_db.notes}"
                    
                embed.add_field(
                    name=guild_name,
                    value=value,
                    inline=False
                )
                
            pages.append(embed)
            
        # Send the first page
        if pages:
            message = await ctx.send(embed=pages[0])
            
            # Add reactions for navigation if there are multiple pages
            if len(pages) > 1:
                await message.add_reaction("◀️")
                await message.add_reaction("▶️")
                
                # Current page index
                current_page = 0
                
                # Check function for reactions
                def check(reaction, user):
                    return (user == ctx.author and
                            reaction.message.id == message.id and
                            str(reaction.emoji) in ["◀️", "▶️"])
                            
                # Navigation loop
                while True:
                    try:
                        # Wait for a reaction
                        reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                        
                        # Remove the user's reaction
                        await reaction.remove(user)
                        
                        # Navigate based on the reaction
                        if str(reaction.emoji) == "▶️" and current_page < len(pages) - 1:
                            current_page += 1
                        elif str(reaction.emoji) == "◀️" and current_page > 0:
                            current_page -= 1
                            
                        # Update the embed
                        await message.edit(embed=pages[current_page])
                    except asyncio.TimeoutError:
                        # Remove reactions on timeout
                        await message.clear_reactions()
                        break
                        
    # Example premium command
    @commands.command(name="premium_test")
    @requires_premium_feature("advanced_analytics")
    async def premium_test(self, ctx):
        """
        Test premium feature access
        
        This command demonstrates premium feature access control.
        """
        await ctx.send("✅ You have access to the advanced_analytics premium feature!")
        
    # Example premium commands for different tiers
    @commands.command(name="premium_basic")
    @requires_premium_feature("advanced_logging")
    async def premium_basic(self, ctx):
        """
        Test BASIC premium tier feature
        
        This command requires the BASIC premium tier.
        """
        await ctx.send("✅ You have access to the advanced_logging feature (BASIC tier)!")
        
    @commands.command(name="premium_standard")
    @requires_premium_feature("custom_commands")
    async def premium_standard(self, ctx):
        """
        Test STANDARD premium tier feature
        
        This command requires the STANDARD premium tier.
        """
        await ctx.send("✅ You have access to the custom_commands feature (STANDARD tier)!")
        
    @commands.command(name="premium_pro")
    @requires_premium_feature("advanced_analytics")
    async def premium_pro(self, ctx):
        """
        Test PRO premium tier feature
        
        This command requires the PRO premium tier.
        """
        await ctx.send("✅ You have access to the advanced_analytics feature (PRO tier)!")
        
    @commands.command(name="premium_enterprise")
    @requires_premium_feature("custom_integrations")
    async def premium_enterprise(self, ctx):
        """
        Test ENTERPRISE premium tier feature
        
        This command requires the ENTERPRISE premium tier.
        """
        await ctx.send("✅ You have access to the custom_integrations feature (ENTERPRISE tier)!")
        
def setup(bot):
    """
    Set up the premium commands cog
    
    Args:
        bot: The Discord bot instance
    """
    bot.add_cog(PremiumCommands(bot))
    logger.info("Premium commands cog loaded")