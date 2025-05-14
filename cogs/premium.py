"""
Premium Cog
Handles premium features and subscription management
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime, timedelta
import traceback

logger = logging.getLogger(__name__)

class Premium(commands.Cog):
    """Premium features and subscription management"""
    
    def __init__(self, bot):
        """Initialize the cog with a bot instance"""
        self.bot = bot
    
    @commands.group(name="premium", invoke_without_command=True)
    async def premium(self, ctx):
        """Premium features and subscription management"""
        try:
            # Create an embed for premium info
            embed = discord.Embed(
                title="Premium Features",
                description="Access exclusive features and enhance your server with premium!",
                color=discord.Color.gold()
            )
            
            # Get premium status for the guild
            if hasattr(self.bot, 'premium_manager'):
                status = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
                
                # Add premium status
                if status["is_premium"]:
                    embed.add_field(
                        name="Status",
                        value=f"✅ This server has premium tier: **{status['tier'].capitalize()}**",
                        inline=False
                    )
                    
                    # Add expiration info
                    if status["expires_at"]:
                        expires_str = status["expires_at"].strftime("%Y-%m-%d")
                        embed.add_field(
                            name="Expires",
                            value=f"{expires_str} ({status['days_left']} days left)",
                            inline=True
                        )
                    
                    # Add features
                    features = "\n".join([f"• {feature.replace('_', ' ').title()}" for feature in status["features"]])
                    embed.add_field(
                        name="Features",
                        value=features if features else "No features available",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Status",
                        value="❌ This server does not have premium",
                        inline=False
                    )
                    
                    # Add features teaser
                    basic_features = "\n".join([f"• {feature.replace('_', ' ').title()}" 
                                              for feature in self.bot.premium_manager.premium_tiers["basic"]["features"]])
                    embed.add_field(
                        name="Basic Tier Features",
                        value=basic_features,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Status",
                    value="Premium features are not available at this time",
                    inline=False
                )
            
            # Add subcommands
            embed.add_field(
                name="Commands",
                value=(
                    f"`{ctx.prefix}premium status` - View detailed premium status\n"
                    f"`{ctx.prefix}premium features` - View available premium features\n"
                    f"`{ctx.prefix}premium upgrade` - Upgrade to premium"
                ),
                inline=False
            )
            
            await ctx.send(embed=embed)
            logger.info(f"Premium command executed by {ctx.author} in {ctx.guild.name}")
        except Exception as e:
            logger.error(f"Error in premium command: {e}")
            logger.error(traceback.format_exc())
            await ctx.send("An error occurred while checking premium status")
    
    @premium.command(name="status")
    async def premium_status(self, ctx):
        """View detailed premium status for this server"""
        try:
            # Create an embed for premium status
            embed = discord.Embed(
                title="Premium Status",
                description=f"Detailed premium status for {ctx.guild.name}",
                color=discord.Color.gold()
            )
            
            # Get premium status for the guild
            if hasattr(self.bot, 'premium_manager'):
                status = await self.bot.premium_manager.get_premium_status(ctx.guild.id)
                
                # Add premium status
                if status["is_premium"]:
                    embed.add_field(
                        name="Status",
                        value=f"✅ Premium Active",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Tier",
                        value=status["tier"].capitalize(),
                        inline=True
                    )
                    
                    # Add expiration info
                    if status["expires_at"]:
                        expires_str = status["expires_at"].strftime("%Y-%m-%d")
                        embed.add_field(
                            name="Expires",
                            value=f"{expires_str}",
                            inline=True
                        )
                        
                        embed.add_field(
                            name="Days Left",
                            value=str(status["days_left"]),
                            inline=True
                        )
                    
                    # Add limits
                    limits = []
                    for limit_name, limit_value in status["limits"].items():
                        if limit_name != "features":
                            limits.append(f"• {limit_name.replace('max_', '').replace('_', ' ').title()}: {limit_value}")
                    
                    embed.add_field(
                        name="Limits",
                        value="\n".join(limits) if limits else "No limits defined",
                        inline=False
                    )
                    
                    # Add features
                    features = []
                    for feature in status["features"]:
                        description = self.bot.premium_manager.premium_features.get(feature, "")
                        features.append(f"• **{feature.replace('_', ' ').title()}**: {description}")
                    
                    embed.add_field(
                        name="Features",
                        value="\n".join(features) if features else "No features available",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Status",
                        value="❌ This server does not have premium",
                        inline=False
                    )
                    
                    # Add upgrade info
                    embed.add_field(
                        name="Upgrade",
                        value=f"Use `{ctx.prefix}premium upgrade` to see upgrade options",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Status",
                    value="Premium features are not available at this time",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            logger.info(f"Premium status command executed by {ctx.author} in {ctx.guild.name}")
        except Exception as e:
            logger.error(f"Error in premium status command: {e}")
            logger.error(traceback.format_exc())
            await ctx.send("An error occurred while checking premium status")
    
    @premium.command(name="features")
    async def premium_features(self, ctx):
        """View available premium features"""
        try:
            # Create an embed for premium features
            embed = discord.Embed(
                title="Premium Features",
                description="All available premium features by tier",
                color=discord.Color.gold()
            )
            
            if hasattr(self.bot, 'premium_manager'):
                # Get premium tiers and features
                tiers = self.bot.premium_manager.premium_tiers
                features = self.bot.premium_manager.premium_features
                
                # Add each tier and its features
                for tier_name, tier_data in tiers.items():
                    tier_features = []
                    
                    for feature in tier_data.get("features", []):
                        description = features.get(feature, "")
                        tier_features.append(f"• **{feature.replace('_', ' ').title()}**: {description}")
                    
                    embed.add_field(
                        name=f"{tier_name.capitalize()} Tier",
                        value="\n".join(tier_features) if tier_features else "No features available",
                        inline=False
                    )
                
                # Get current tier for the guild
                current_tier = await self.bot.premium_manager.get_premium_tier(ctx.guild.id)
                
                if current_tier != "none":
                    embed.add_field(
                        name="Current Tier",
                        value=f"This server has the **{current_tier.capitalize()}** tier",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Current Tier",
                        value=f"This server does not have premium. Use `{ctx.prefix}premium upgrade` to upgrade",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Features",
                    value="Premium features are not available at this time",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            logger.info(f"Premium features command executed by {ctx.author} in {ctx.guild.name}")
        except Exception as e:
            logger.error(f"Error in premium features command: {e}")
            logger.error(traceback.format_exc())
            await ctx.send("An error occurred while getting premium features")
    
    @premium.command(name="upgrade")
    async def premium_upgrade(self, ctx):
        """Upgrade to premium"""
        try:
            # Create an embed for premium upgrade
            embed = discord.Embed(
                title="Upgrade to Premium",
                description="Upgrade your server to access premium features!",
                color=discord.Color.gold()
            )
            
            # Add premium tiers
            if hasattr(self.bot, 'premium_manager'):
                tiers = self.bot.premium_manager.premium_tiers
                
                for tier_name, tier_data in tiers.items():
                    # Create a brief summary of the tier
                    feature_count = len(tier_data.get("features", []))
                    custom_commands = tier_data.get("max_custom_commands", 0)
                    
                    field_value = (
                        f"• {feature_count} Premium Features\n"
                        f"• {custom_commands} Custom Commands\n"
                        f"• Priority Support: {'✅' if 'priority_support' in tier_data.get('features', []) else '❌'}\n"
                    )
                    
                    embed.add_field(
                        name=f"{tier_name.capitalize()} Tier",
                        value=field_value,
                        inline=True
                    )
                
                # Add current tier for the guild
                current_tier = await self.bot.premium_manager.get_premium_tier(ctx.guild.id)
                
                if current_tier != "none":
                    embed.add_field(
                        name="Current Tier",
                        value=f"This server has the **{current_tier.capitalize()}** tier",
                        inline=False
                    )
                
                # Add upgrade instructions
                embed.add_field(
                    name="How to Upgrade",
                    value=(
                        "To upgrade your server, please visit our website or contact the bot developer.\n"
                        "You can use the buttons below to get more information."
                    ),
                    inline=False
                )
                
                # Create buttons (if using discord.py with view support)
                try:
                    # This requires discord.py 2.0+ or similar with view support
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Visit Website", url="https://example.com/premium"))
                    view.add_item(discord.ui.Button(label="Join Support Server", url="https://discord.gg/example"))
                    
                    await ctx.send(embed=embed, view=view)
                except AttributeError:
                    # Fallback for older discord.py versions
                    embed.add_field(
                        name="Links",
                        value=(
                            "[Visit Website](https://example.com/premium)\n"
                            "[Join Support Server](https://discord.gg/example)"
                        ),
                        inline=False
                    )
                    
                    await ctx.send(embed=embed)
            else:
                embed.add_field(
                    name="Upgrade",
                    value="Premium upgrades are not available at this time",
                    inline=False
                )
                
                await ctx.send(embed=embed)
            
            logger.info(f"Premium upgrade command executed by {ctx.author} in {ctx.guild.name}")
        except Exception as e:
            logger.error(f"Error in premium upgrade command: {e}")
            logger.error(traceback.format_exc())
            await ctx.send("An error occurred while getting premium upgrade information")
    
    @commands.command(name="add_premium", hidden=True)
    @commands.is_owner()
    async def add_premium(self, ctx, guild_id: int = None, tier: str = "basic", days: int = 30):
        """Add premium to a guild (owner only)"""
        try:
            # Check if premium manager exists
            if not hasattr(self.bot, 'premium_manager'):
                await ctx.send("Premium manager is not available")
                return
            
            # Get guild ID (use current guild if not provided)
            if guild_id is None:
                guild_id = ctx.guild.id
            
            # Verify tier is valid
            if tier not in self.bot.premium_manager.premium_tiers and tier != "none":
                await ctx.send(f"Invalid tier: {tier}. Valid tiers: {', '.join(self.bot.premium_manager.premium_tiers.keys())}")
                return
            
            # Add premium
            if tier == "none":
                success = await self.bot.premium_manager.remove_premium(guild_id)
                
                if success:
                    await ctx.send(f"✅ Removed premium from guild {guild_id}")
                else:
                    await ctx.send(f"❌ Failed to remove premium from guild {guild_id}")
            else:
                success = await self.bot.premium_manager.add_premium(guild_id, tier, days)
                
                if success:
                    await ctx.send(f"✅ Added premium tier {tier} to guild {guild_id} for {days} days")
                else:
                    await ctx.send(f"❌ Failed to add premium to guild {guild_id}")
            
            logger.info(f"Add premium command executed by {ctx.author} for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error in add_premium command: {e}")
            logger.error(traceback.format_exc())
            await ctx.send(f"An error occurred: {e}")
    
    @commands.command(name="extend_premium", hidden=True)
    @commands.is_owner()
    async def extend_premium(self, ctx, guild_id: int = None, days: int = 30):
        """Extend premium for a guild (owner only)"""
        try:
            # Check if premium manager exists
            if not hasattr(self.bot, 'premium_manager'):
                await ctx.send("Premium manager is not available")
                return
            
            # Get guild ID (use current guild if not provided)
            if guild_id is None:
                guild_id = ctx.guild.id
            
            # Extend premium
            success = await self.bot.premium_manager.extend_premium(guild_id, days)
            
            if success:
                await ctx.send(f"✅ Extended premium for guild {guild_id} by {days} days")
            else:
                await ctx.send(f"❌ Failed to extend premium for guild {guild_id}")
            
            logger.info(f"Extend premium command executed by {ctx.author} for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error in extend_premium command: {e}")
            logger.error(traceback.format_exc())
            await ctx.send(f"An error occurred: {e}")

async def setup(bot):
    """Add the cog to the bot"""
    # Initialize premium manager if it doesn't exist
    if not hasattr(bot, 'premium_manager'):
        # Import and setup premium manager
        from utils.premium_manager import setup as setup_premium
        bot.premium_manager = setup_premium(bot)
        
        # Initialize premium manager
        await bot.premium_manager.initialize()
    
    # Add the cog
    await bot.add_cog(Premium(bot))
    logger.info("Premium cog loaded")