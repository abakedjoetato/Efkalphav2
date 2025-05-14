"""
Premium Features Cog

Manages premium features and subscription status for the bot.
"""

import os
import discord
import logging
from datetime import datetime, timedelta
from discord.ext import commands

# Configure logging
logger = logging.getLogger(__name__)

# Premium-related constants
PREMIUM_TIERS = {
    "basic": {
        "emoji": "🥉",
        "color": discord.Color.light_gray(),
        "description": "Basic tier with essential premium features."
    },
    "standard": {
        "emoji": "🥈",
        "color": discord.Color.silver(),
        "description": "Standard tier with additional premium features."
    },
    "premium": {
        "emoji": "🥇",
        "color": discord.Color.gold(),
        "description": "Premium tier with all premium features."
    }
}

class PremiumCog(commands.Cog, name="Premium"):
    """
    Commands for managing premium features and subscription status.
    """
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("PremiumCog initialized")
    
    async def _get_premium_manager(self):
        """Get the premium manager from bot"""
        if hasattr(self.bot, 'premium_manager'):
            return self.bot.premium_manager
        
        try:
            # Try to import and get premium manager dynamically
            from utils.premium_manager_enhanced import get_premium_manager
            return await get_premium_manager(self.bot)
        except ImportError:
            try:
                # Fallback to original premium manager
                from utils.premium_manager import get_premium_manager
                return await get_premium_manager(self.bot)
            except ImportError:
                logger.error("No premium manager module found")
                return None
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Verify premium manager is available when bot is ready"""
        premium_manager = await self._get_premium_manager()
        if premium_manager:
            logger.info("Premium manager is available")
        else:
            logger.warning("Premium manager is not available")
    
    @commands.command(name="premium")
    async def premium_status(self, ctx):
        """
        Check premium status for this server.
        
        Usage: !premium
        """
        premium_manager = await self._get_premium_manager()
        if not premium_manager:
            await ctx.send("⚠️ Premium features are currently unavailable.")
            return
        
        # Get premium status for guild
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        status = await premium_manager.get_premium_status(guild_id)
        
        # Create embed based on premium status
        if status.is_premium:
            # Get tier info
            tier_info = PREMIUM_TIERS.get(status.tier, {
                "emoji": "✨", 
                "color": discord.Color.blue(),
                "description": "Custom premium tier."
            })
            
            embed = discord.Embed(
                title=f"{tier_info['emoji']} Premium Status: Active",
                description=tier_info["description"],
                color=tier_info["color"],
                timestamp=datetime.now()
            )
            
            # Add basic info
            embed.add_field(name="Tier", value=status.tier.title(), inline=True)
            
            # Add expiration info
            if status.expires_at:
                embed.add_field(
                    name="Expires",
                    value=status.expires_at.strftime("%Y-%m-%d"),
                    inline=True
                )
                embed.add_field(
                    name="Days Left",
                    value=str(status.days_left),
                    inline=True
                )
            
            # Add feature list
            if status.features:
                features_str = "\n".join(f"✅ {feature.replace('_', ' ').title()}" for feature in status.features)
                embed.add_field(
                    name="Features",
                    value=features_str[:1024],  # Limit to Discord's field size
                    inline=False
                )
            
            # Add limits if any
            if status.limits:
                limits_str = "\n".join(f"• {key.replace('max_', '').replace('_', ' ').title()}: {value}" 
                                     for key, value in status.limits.items())
                embed.add_field(
                    name="Limits",
                    value=limits_str[:1024],  # Limit to Discord's field size
                    inline=False
                )
            
        else:
            embed = discord.Embed(
                title="❌ Premium Status: Inactive",
                description="This server does not have premium features enabled.",
                color=discord.Color.dark_grey(),
                timestamp=datetime.now()
            )
            
            # Add info about how to get premium
            embed.add_field(
                name="Get Premium",
                value="To enable premium features, contact the bot developer.",
                inline=False
            )
            
            # Add available tiers
            tiers_str = "\n".join(f"{info['emoji']} **{tier.title()}:** {info['description']}" 
                                for tier, info in PREMIUM_TIERS.items())
            embed.add_field(
                name="Available Tiers",
                value=tiers_str,
                inline=False
            )
        
        # Set footer
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="features")
    async def premium_features(self, ctx):
        """
        List available premium features for this server.
        
        Usage: !features
        """
        premium_manager = await self._get_premium_manager()
        if not premium_manager:
            await ctx.send("⚠️ Premium features are currently unavailable.")
            return
        
        # Get guild ID
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        
        # Check if guild has premium
        is_premium = await premium_manager.is_premium(guild_id)
        
        # Create embed
        embed = discord.Embed(
            title="✨ Premium Features",
            timestamp=datetime.now()
        )
        
        if is_premium:
            # Get tier
            tier = await premium_manager.get_premium_tier(guild_id)
            tier_info = PREMIUM_TIERS.get(tier, {
                "emoji": "✨", 
                "color": discord.Color.blue(),
                "description": "Custom premium tier."
            })
            
            # Set embed color and description
            embed.color = tier_info["color"]
            embed.description = f"This server has the {tier_info['emoji']} **{tier.title()}** tier."
            
            # Get available features
            available_features = await premium_manager.get_available_features(guild_id)
            
            if available_features:
                # Format features as a list
                features_str = "\n".join(f"✅ **{key.replace('_', ' ').title()}:** {value}" 
                                        for key, value in available_features.items())
                embed.add_field(
                    name="Available Features",
                    value=features_str[:1024],  # Limit to Discord's field size
                    inline=False
                )
            else:
                embed.add_field(
                    name="Available Features",
                    value="No premium features available for your tier.",
                    inline=False
                )
            
            # Get feature limits
            limits = {}
            common_limits = ["max_custom_commands", "max_welcome_messages", "max_auto_roles"]
            for limit_name in common_limits:
                limit_value = await premium_manager.get_feature_limit(guild_id, limit_name)
                if limit_value > 0:
                    limits[limit_name] = limit_value
            
            if limits:
                limits_str = "\n".join(f"• **{key.replace('max_', '').replace('_', ' ').title()}:** {value}" 
                                     for key, value in limits.items())
                embed.add_field(
                    name="Feature Limits",
                    value=limits_str,
                    inline=False
                )
            
        else:
            # Not premium
            embed.color = discord.Color.dark_grey()
            embed.description = "This server does not have premium features enabled."
            
            # List available tiers
            tiers_str = "\n".join(f"{info['emoji']} **{tier.title()}:** {info['description']}" 
                                for tier, info in PREMIUM_TIERS.items())
            embed.add_field(
                name="Available Tiers",
                value=tiers_str,
                inline=False
            )
            
            # Add info about how to get premium
            embed.add_field(
                name="Get Premium",
                value="To enable premium features, contact the bot developer.",
                inline=False
            )
        
        # Set footer
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="addpremium")
    @commands.is_owner()
    async def add_premium(self, ctx, guild_id: int, tier: str = "basic", days: int = 30):
        """
        Add premium to a server (Bot owner only).
        
        Usage: !addpremium <guild_id> [tier] [days]
        Example: !addpremium 123456789 premium 90
        
        Tiers: basic, standard, premium
        """
        premium_manager = await self._get_premium_manager()
        if not premium_manager:
            await ctx.send("⚠️ Premium manager is not available.")
            return
        
        # Validate tier
        tier = tier.lower()
        if tier not in PREMIUM_TIERS and tier != "none":
            await ctx.send(f"❌ Invalid tier: {tier}. Valid tiers are: basic, standard, premium, none")
            return
        
        # Validate days
        if days <= 0:
            await ctx.send("❌ Days must be a positive number.")
            return
        
        # Add premium
        success = await premium_manager.add_premium(guild_id, tier, days)
        
        if success:
            # Get tier info
            tier_info = PREMIUM_TIERS.get(tier, {
                "emoji": "✨", 
                "color": discord.Color.blue()
            })
            
            embed = discord.Embed(
                title=f"{tier_info['emoji']} Premium Added",
                description=f"Successfully added premium to guild {guild_id}.",
                color=tier_info["color"],
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Guild ID", value=str(guild_id), inline=True)
            embed.add_field(name="Tier", value=tier.title(), inline=True)
            embed.add_field(name="Duration", value=f"{days} days", inline=True)
            
            # Calculate expiration date
            expires_at = datetime.now() + timedelta(days=days)
            embed.add_field(
                name="Expires",
                value=expires_at.strftime("%Y-%m-%d"),
                inline=True
            )
            
            # Try to get guild name
            guild = self.bot.get_guild(guild_id)
            if guild:
                embed.add_field(name="Guild Name", value=guild.name, inline=True)
            
            await ctx.send(embed=embed)
            
            # If the guild is current guild, also announce it
            if ctx.guild and ctx.guild.id == guild_id:
                # Create announcement embed
                announce_embed = discord.Embed(
                    title=f"{tier_info['emoji']} Premium Activated!",
                    description=f"This server now has premium tier **{tier.title()}** for {days} days!",
                    color=tier_info["color"],
                    timestamp=datetime.now()
                )
                
                announce_embed.add_field(
                    name="Expires",
                    value=expires_at.strftime("%Y-%m-%d"),
                    inline=True
                )
                
                announce_embed.add_field(
                    name="More Info",
                    value=f"Use `!premium` to see available features.",
                    inline=True
                )
                
                # Send in a different channel if possible
                system_channel = ctx.guild.system_channel
                if system_channel and system_channel.permissions_for(ctx.guild.me).send_messages:
                    await system_channel.send(embed=announce_embed)
        else:
            await ctx.send(f"❌ Failed to add premium to guild {guild_id}.")
    
    @commands.command(name="removepremium")
    @commands.is_owner()
    async def remove_premium(self, ctx, guild_id: int):
        """
        Remove premium from a server (Bot owner only).
        
        Usage: !removepremium <guild_id>
        Example: !removepremium 123456789
        """
        premium_manager = await self._get_premium_manager()
        if not premium_manager:
            await ctx.send("⚠️ Premium manager is not available.")
            return
        
        # Check if guild has premium
        has_premium = await premium_manager.is_premium(guild_id)
        if not has_premium:
            await ctx.send(f"❌ Guild {guild_id} does not have premium.")
            return
        
        # Get current tier for info message
        current_tier = await premium_manager.get_premium_tier(guild_id)
        
        # Remove premium
        success = await premium_manager.remove_premium(guild_id)
        
        if success:
            embed = discord.Embed(
                title="❌ Premium Removed",
                description=f"Successfully removed premium from guild {guild_id}.",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Guild ID", value=str(guild_id), inline=True)
            embed.add_field(name="Previous Tier", value=current_tier.title(), inline=True)
            
            # Try to get guild name
            guild = self.bot.get_guild(guild_id)
            if guild:
                embed.add_field(name="Guild Name", value=guild.name, inline=True)
            
            await ctx.send(embed=embed)
            
            # If the guild is current guild, also announce it
            if ctx.guild and ctx.guild.id == guild_id:
                # Create announcement embed
                announce_embed = discord.Embed(
                    title="❌ Premium Deactivated",
                    description="This server's premium subscription has ended.",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                
                announce_embed.add_field(
                    name="Previous Tier",
                    value=current_tier.title(),
                    inline=True
                )
                
                announce_embed.add_field(
                    name="More Info",
                    value="Contact the bot owner to reactivate premium.",
                    inline=True
                )
                
                # Send in a different channel if possible
                system_channel = ctx.guild.system_channel
                if system_channel and system_channel.permissions_for(ctx.guild.me).send_messages:
                    await system_channel.send(embed=announce_embed)
        else:
            await ctx.send(f"❌ Failed to remove premium from guild {guild_id}.")
    
    @commands.command(name="extendpremium")
    @commands.is_owner()
    async def extend_premium(self, ctx, guild_id: int, days: int = 30):
        """
        Extend premium duration for a server (Bot owner only).
        
        Usage: !extendpremium <guild_id> [days]
        Example: !extendpremium 123456789 60
        """
        premium_manager = await self._get_premium_manager()
        if not premium_manager:
            await ctx.send("⚠️ Premium manager is not available.")
            return
        
        # Check if guild has premium
        has_premium = await premium_manager.is_premium(guild_id)
        if not has_premium:
            await ctx.send(f"❌ Guild {guild_id} does not have premium. Use `!addpremium` instead.")
            return
        
        # Validate days
        if days <= 0:
            await ctx.send("❌ Days must be a positive number.")
            return
        
        # Get current tier for info message
        current_tier = await premium_manager.get_premium_tier(guild_id)
        tier_info = PREMIUM_TIERS.get(current_tier, {
            "emoji": "✨", 
            "color": discord.Color.blue()
        })
        
        # Extend premium
        success = await premium_manager.extend_premium(guild_id, days)
        
        if success:
            # Get updated status
            status = await premium_manager.get_premium_status(guild_id)
            
            embed = discord.Embed(
                title=f"{tier_info['emoji']} Premium Extended",
                description=f"Successfully extended premium for guild {guild_id}.",
                color=tier_info["color"],
                timestamp=datetime.now()
            )
            
            embed.add_field(name="Guild ID", value=str(guild_id), inline=True)
            embed.add_field(name="Tier", value=current_tier.title(), inline=True)
            embed.add_field(name="Added Days", value=f"{days} days", inline=True)
            
            # Add expiration date if available
            if status and status.expires_at:
                embed.add_field(
                    name="New Expiration Date",
                    value=status.expires_at.strftime("%Y-%m-%d"),
                    inline=True
                )
                
                embed.add_field(
                    name="Days Left",
                    value=str(status.days_left),
                    inline=True
                )
            
            # Try to get guild name
            guild = self.bot.get_guild(guild_id)
            if guild:
                embed.add_field(name="Guild Name", value=guild.name, inline=True)
            
            await ctx.send(embed=embed)
            
            # If the guild is current guild, also announce it
            if ctx.guild and ctx.guild.id == guild_id:
                # Create announcement embed
                announce_embed = discord.Embed(
                    title=f"{tier_info['emoji']} Premium Extended!",
                    description=f"This server's premium subscription has been extended by {days} days!",
                    color=tier_info["color"],
                    timestamp=datetime.now()
                )
                
                if status and status.expires_at:
                    announce_embed.add_field(
                        name="New Expiration Date",
                        value=status.expires_at.strftime("%Y-%m-%d"),
                        inline=True
                    )
                
                # Send in a different channel if possible
                system_channel = ctx.guild.system_channel
                if system_channel and system_channel.permissions_for(ctx.guild.me).send_messages:
                    await system_channel.send(embed=announce_embed)
        else:
            await ctx.send(f"❌ Failed to extend premium for guild {guild_id}.")
    
    @commands.command(name="premiumlist")
    @commands.is_owner()
    async def premium_list(self, ctx):
        """
        List all servers with premium status (Bot owner only).
        
        Usage: !premiumlist
        """
        premium_manager = await self._get_premium_manager()
        if not premium_manager:
            await ctx.send("⚠️ Premium manager is not available.")
            return
        
        # Check if premium_guilds is available
        if not hasattr(premium_manager, 'premium_guilds'):
            await ctx.send("⚠️ Premium guild list is not available.")
            return
        
        # Get premium guilds
        premium_guilds = premium_manager.premium_guilds
        
        if not premium_guilds:
            await ctx.send("No servers have premium status.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="📜 Premium Servers",
            description=f"There are {len(premium_guilds)} servers with premium status.",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Add each server to the embed
        # Create a list of (guild_id, tier, expires_at) tuples
        guild_list = []
        
        for guild_id, guild_data in premium_guilds.items():
            tier = guild_data.get("tier", "basic")
            expires_at = guild_data.get("expires_at")
            
            # Convert guild_id to int if it's a string
            if isinstance(guild_id, str) and guild_id.isdigit():
                guild_id = int(guild_id)
            
            guild_list.append((guild_id, tier, expires_at))
        
        # Sort by expiration date
        guild_list.sort(key=lambda x: x[2] if x[2] else datetime.max)
        
        # Add fields for each guild (up to 25 to stay within embed limits)
        for i, (guild_id, tier, expires_at) in enumerate(guild_list[:25]):
            # Try to get guild name
            guild = self.bot.get_guild(guild_id)
            guild_name = guild.name if guild else "Unknown"
            
            # Format expiration date
            expires_str = expires_at.strftime("%Y-%m-%d") if expires_at else "Never"
            
            # Get tier emoji
            tier_emoji = PREMIUM_TIERS.get(tier, {}).get("emoji", "✨")
            
            # Calculate days left
            days_left = "∞"
            if expires_at:
                now = datetime.now()
                if expires_at > now:
                    days_left = (expires_at - now).days
                else:
                    days_left = "Expired"
            
            # Add field
            embed.add_field(
                name=f"{i+1}. {guild_name} ({guild_id})",
                value=f"Tier: {tier_emoji} {tier.title()}\nExpires: {expires_str}\nDays Left: {days_left}",
                inline=True
            )
        
        # If there are too many guilds, add a note
        if len(guild_list) > 25:
            embed.set_footer(text=f"Showing 25/{len(guild_list)} premium servers. Use !premiuminfo <guild_id> for details.")
        else:
            embed.set_footer(text=f"Use !premiuminfo <guild_id> for detailed information about a specific server.")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="premiuminfo")
    @commands.is_owner()
    async def premium_info(self, ctx, guild_id: int):
        """
        Show detailed premium information for a server (Bot owner only).
        
        Usage: !premiuminfo <guild_id>
        Example: !premiuminfo 123456789
        """
        premium_manager = await self._get_premium_manager()
        if not premium_manager:
            await ctx.send("⚠️ Premium manager is not available.")
            return
        
        # Get premium status
        status = await premium_manager.get_premium_status(guild_id)
        
        # Get guild info
        guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else "Unknown"
        
        # Create embed
        if status.is_premium:
            # Get tier info
            tier_info = PREMIUM_TIERS.get(status.tier, {
                "emoji": "✨", 
                "color": discord.Color.blue(),
                "description": "Custom premium tier."
            })
            
            embed = discord.Embed(
                title=f"{tier_info['emoji']} Premium Info: {guild_name}",
                description=f"Detailed premium information for guild {guild_id}.",
                color=tier_info["color"],
                timestamp=datetime.now()
            )
            
            # Add guild info
            embed.add_field(name="Guild ID", value=str(guild_id), inline=True)
            embed.add_field(name="Guild Name", value=guild_name, inline=True)
            
            # Add premium info
            embed.add_field(name="Tier", value=status.tier.title(), inline=True)
            
            # Add expiration info
            if status.expires_at:
                embed.add_field(
                    name="Expires",
                    value=status.expires_at.strftime("%Y-%m-%d"),
                    inline=True
                )
                embed.add_field(
                    name="Days Left",
                    value=str(status.days_left),
                    inline=True
                )
            
            # Add feature list
            if status.features:
                features_str = "\n".join(f"✅ {feature.replace('_', ' ').title()}" for feature in status.features)
                embed.add_field(
                    name="Features",
                    value=features_str[:1024],  # Limit to Discord's field size
                    inline=False
                )
            
            # Add limits if any
            if status.limits:
                limits_str = "\n".join(f"• {key.replace('max_', '').replace('_', ' ').title()}: {value}" 
                                     for key, value in status.limits.items())
                embed.add_field(
                    name="Limits",
                    value=limits_str[:1024],  # Limit to Discord's field size
                    inline=False
                )
            
            # If the guild object is available, add member count
            if guild:
                embed.add_field(name="Members", value=str(guild.member_count), inline=True)
                
                # Add server owner
                if guild.owner:
                    embed.add_field(name="Owner", value=str(guild.owner), inline=True)
            
            # Add commands
            embed.add_field(
                name="Management Commands",
                value=(
                    f"`!extendpremium {guild_id} [days]` - Extend premium\n"
                    f"`!removepremium {guild_id}` - Remove premium"
                ),
                inline=False
            )
            
            # Add guild icon as thumbnail if available
            if guild and guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
        else:
            embed = discord.Embed(
                title=f"❌ Premium Info: {guild_name}",
                description=f"Guild {guild_id} does not have premium status.",
                color=discord.Color.dark_grey(),
                timestamp=datetime.now()
            )
            
            # Add guild info
            embed.add_field(name="Guild ID", value=str(guild_id), inline=True)
            embed.add_field(name="Guild Name", value=guild_name, inline=True)
            
            # If the guild object is available, add member count
            if guild:
                embed.add_field(name="Members", value=str(guild.member_count), inline=True)
                
                # Add server owner
                if guild.owner:
                    embed.add_field(name="Owner", value=str(guild.owner), inline=True)
            
            # Add command to add premium
            embed.add_field(
                name="Add Premium",
                value=(
                    f"`!addpremium {guild_id} [tier] [days]` - Add premium\n"
                    f"Available tiers: basic, standard, premium"
                ),
                inline=False
            )
            
            # Add guild icon as thumbnail if available
            if guild and guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the premium cog to the bot"""
    await bot.add_cog(PremiumCog(bot))
    logger.info("PremiumCog loaded")