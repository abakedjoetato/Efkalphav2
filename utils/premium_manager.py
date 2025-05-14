"""
Premium Features Manager

Handles premium features, subscription status, and feature access control.
"""

import os
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# Constants for premium tiers
PREMIUM_TIERS = {
    "basic": {
        "max_custom_commands": 5,
        "max_welcome_messages": 1,
        "max_auto_roles": 1,
        "features": ["custom_prefix", "basic_analytics", "auto_roles"]
    },
    "standard": {
        "max_custom_commands": 15,
        "max_welcome_messages": 3,
        "max_auto_roles": 3,
        "features": ["custom_prefix", "basic_analytics", "auto_roles", 
                    "reaction_roles", "advanced_logging", "custom_embeds"]
    },
    "premium": {
        "max_custom_commands": 50,
        "max_welcome_messages": 10,
        "max_auto_roles": 10,
        "features": ["custom_prefix", "basic_analytics", "auto_roles", 
                    "reaction_roles", "advanced_logging", "custom_embeds",
                    "advanced_analytics", "priority_support", "custom_events",
                    "scheduled_messages", "advanced_moderation"]
    }
}

# All available premium features
ALL_PREMIUM_FEATURES = {
    "custom_prefix": "Change the bot command prefix",
    "basic_analytics": "View basic server stats and activity",
    "auto_roles": "Automatically assign roles to new members",
    "reaction_roles": "Allow users to get roles by reacting to messages",
    "advanced_logging": "Detailed logging of server activities",
    "custom_embeds": "Create custom embed messages",
    "advanced_analytics": "Detailed server analytics and reports",
    "priority_support": "Priority support from the bot developers",
    "custom_events": "Create custom server events",
    "scheduled_messages": "Schedule messages to be sent at specific times",
    "advanced_moderation": "Advanced moderation tools",
    "voice_analytics": "Track voice channel usage",
    "custom_welcome_images": "Create custom welcome images",
    "member_verification": "Custom member verification systems",
    "giveaways": "Run giveaways with multiple winners",
    "polls": "Create advanced polls with multiple options",
    "server_backup": "Backup server configurations",
    "auto_moderation": "Automatic moderation based on rules",
    "custom_leveling": "Custom leveling system",
    "music_player": "Advanced music player features"
}

class PremiumManager:
    """Manager for premium features and subscription status"""
    
    def __init__(self, bot):
        """Initialize the premium manager with a bot instance"""
        self.bot = bot
        self.premium_guilds = {}  # Cache of premium guild statuses
        self.premium_features = ALL_PREMIUM_FEATURES
        self.premium_tiers = PREMIUM_TIERS
        
    async def initialize(self):
        """Initialize the premium manager by loading premium status for all guilds"""
        try:
            # Load premium status for all guilds if we have a database connection
            if hasattr(self.bot, 'db') and self.bot.db is not None:
                premium_guilds = self.bot.db.premium.find({})
                
                async for guild in premium_guilds:
                    guild_id = guild.get('guild_id')
                    if guild_id:
                        self.premium_guilds[guild_id] = guild
                
                logger.info(f"Loaded premium status for {len(self.premium_guilds)} guilds")
        except Exception as e:
            logger.error(f"Error initializing premium manager: {e}")
            logger.error(traceback.format_exc())
    
    async def is_premium(self, guild_id: int) -> bool:
        """
        Check if a guild has premium status.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if the guild has premium status, False otherwise
        """
        # Check cache first
        if guild_id in self.premium_guilds:
            premium_data = self.premium_guilds[guild_id]
            
            # Check if premium has expired
            if "expires_at" in premium_data:
                now = datetime.utcnow()
                expires_at = premium_data["expires_at"]
                
                if expires_at and now > expires_at:
                    # Premium has expired, remove from cache
                    del self.premium_guilds[guild_id]
                    return False
                
                return True
        
        # If not in cache, check database
        try:
            if hasattr(self.bot, 'db') and self.bot.db is not None:
                premium_data = await self.bot.db.premium.find_one({"guild_id": guild_id})
                
                if premium_data:
                    # Update cache
                    self.premium_guilds[guild_id] = premium_data
                    
                    # Check if premium has expired
                    if "expires_at" in premium_data:
                        now = datetime.utcnow()
                        expires_at = premium_data["expires_at"]
                        
                        if expires_at and now > expires_at:
                            return False
                        
                        return True
        except Exception as e:
            logger.error(f"Error checking premium status for guild {guild_id}: {e}")
            logger.error(traceback.format_exc())
        
        return False
    
    async def get_premium_tier(self, guild_id: int) -> str:
        """
        Get the premium tier of a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Premium tier name or "none" if not premium
        """
        try:
            # Check if guild is premium
            if await self.is_premium(guild_id):
                # Get premium data from cache or database
                premium_data = self.premium_guilds.get(guild_id)
                
                if not premium_data and hasattr(self.bot, 'db') and self.bot.db is not None:
                    premium_data = await self.bot.db.premium.find_one({"guild_id": guild_id})
                    
                    if premium_data:
                        self.premium_guilds[guild_id] = premium_data
                
                # Get tier from premium data
                if premium_data and "tier" in premium_data:
                    tier = premium_data["tier"]
                    
                    # Verify tier is valid
                    if tier in self.premium_tiers:
                        return tier
                    
                    # Default to basic if tier is invalid
                    return "basic"
                
                # Default to basic if tier not specified
                return "basic"
        except Exception as e:
            logger.error(f"Error getting premium tier for guild {guild_id}: {e}")
            logger.error(traceback.format_exc())
        
        return "none"
    
    async def has_feature(self, guild_id: int, feature: str) -> bool:
        """
        Check if a guild has access to a specific premium feature.
        
        Args:
            guild_id: Discord guild ID
            feature: Premium feature name
            
        Returns:
            True if the guild has access to the feature, False otherwise
        """
        # If feature doesn't exist, return False
        if feature not in self.premium_features:
            return False
        
        # Check if guild is premium
        tier = await self.get_premium_tier(guild_id)
        
        # If not premium, return False
        if tier == "none":
            return False
        
        # Check if feature is included in guild's premium tier
        tier_features = self.premium_tiers.get(tier, {}).get("features", [])
        
        return feature in tier_features
    
    async def get_available_features(self, guild_id: int) -> Dict[str, str]:
        """
        Get all premium features available to a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary of feature names to descriptions
        """
        # Check if guild is premium
        tier = await self.get_premium_tier(guild_id)
        
        # If not premium, return empty dict
        if tier == "none":
            return {}
        
        # Get features for the guild's premium tier
        tier_features = self.premium_tiers.get(tier, {}).get("features", [])
        
        # Create dictionary of available features
        available_features = {}
        for feature in tier_features:
            if feature in self.premium_features:
                available_features[feature] = self.premium_features[feature]
        
        return available_features
    
    async def get_feature_limit(self, guild_id: int, limit_name: str) -> int:
        """
        Get the limit for a specific feature.
        
        Args:
            guild_id: Discord guild ID
            limit_name: Name of the limit (e.g., "max_custom_commands")
            
        Returns:
            Limit value or 0 if not premium
        """
        # Check if guild is premium
        tier = await self.get_premium_tier(guild_id)
        
        # If not premium, return 0
        if tier == "none":
            return 0
        
        # Get limits for the guild's premium tier
        tier_limits = self.premium_tiers.get(tier, {})
        
        # Return the requested limit or 0 if not found
        return tier_limits.get(limit_name, 0)
    
    async def add_premium(self, guild_id: int, tier: str = "basic", duration_days: int = 30) -> bool:
        """
        Add premium status to a guild.
        
        Args:
            guild_id: Discord guild ID
            tier: Premium tier name (default: "basic")
            duration_days: Number of days to add premium for (default: 30)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify tier is valid
            if tier not in self.premium_tiers and tier != "none":
                logger.error(f"Invalid premium tier: {tier}")
                return False
            
            # If tier is "none", remove premium
            if tier == "none":
                return await self.remove_premium(guild_id)
            
            # Calculate expiration date
            now = datetime.utcnow()
            expires_at = now + timedelta(days=duration_days)
            
            # Create premium data
            premium_data = {
                "guild_id": guild_id,
                "tier": tier,
                "added_at": now,
                "expires_at": expires_at,
                "updated_at": now
            }
            
            # Update database
            if hasattr(self.bot, 'db') and self.bot.db is not None:
                result = await self.bot.db.premium.update_one(
                    {"guild_id": guild_id},
                    {"$set": premium_data},
                    upsert=True
                )
                
                if result.acknowledged:
                    # Update cache
                    self.premium_guilds[guild_id] = premium_data
                    logger.info(f"Added premium tier {tier} to guild {guild_id} for {duration_days} days")
                    return True
                else:
                    logger.error(f"Failed to add premium to guild {guild_id}")
            else:
                logger.error("Cannot add premium: No database connection")
        except Exception as e:
            logger.error(f"Error adding premium to guild {guild_id}: {e}")
            logger.error(traceback.format_exc())
        
        return False
    
    async def remove_premium(self, guild_id: int) -> bool:
        """
        Remove premium status from a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Remove from cache
            if guild_id in self.premium_guilds:
                del self.premium_guilds[guild_id]
            
            # Remove from database
            if hasattr(self.bot, 'db') and self.bot.db is not None:
                result = await self.bot.db.premium.delete_one({"guild_id": guild_id})
                
                if result.acknowledged:
                    logger.info(f"Removed premium from guild {guild_id}")
                    return True
                else:
                    logger.error(f"Failed to remove premium from guild {guild_id}")
            else:
                logger.error("Cannot remove premium: No database connection")
        except Exception as e:
            logger.error(f"Error removing premium from guild {guild_id}: {e}")
            logger.error(traceback.format_exc())
        
        return False
    
    async def extend_premium(self, guild_id: int, days: int) -> bool:
        """
        Extend premium duration for a guild.
        
        Args:
            guild_id: Discord guild ID
            days: Number of days to extend premium by
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if guild is already premium
            if not await self.is_premium(guild_id):
                logger.error(f"Cannot extend premium for non-premium guild {guild_id}")
                return False
            
            # Get premium data
            premium_data = self.premium_guilds.get(guild_id)
            
            if not premium_data and hasattr(self.bot, 'db') and self.bot.db is not None:
                premium_data = await self.bot.db.premium.find_one({"guild_id": guild_id})
            
            if not premium_data:
                logger.error(f"Premium data not found for guild {guild_id}")
                return False
            
            # Calculate new expiration date
            now = datetime.utcnow()
            current_expires_at = premium_data.get("expires_at", now)
            
            # If current expiration is in the past, use now as the base
            if current_expires_at < now:
                current_expires_at = now
            
            new_expires_at = current_expires_at + timedelta(days=days)
            
            # Update premium data
            premium_data["expires_at"] = new_expires_at
            premium_data["updated_at"] = now
            
            # Update database
            if hasattr(self.bot, 'db') and self.bot.db is not None:
                result = await self.bot.db.premium.update_one(
                    {"guild_id": guild_id},
                    {"$set": premium_data},
                    upsert=True
                )
                
                if result.acknowledged:
                    # Update cache
                    self.premium_guilds[guild_id] = premium_data
                    logger.info(f"Extended premium for guild {guild_id} by {days} days")
                    return True
                else:
                    logger.error(f"Failed to extend premium for guild {guild_id}")
            else:
                logger.error("Cannot extend premium: No database connection")
        except Exception as e:
            logger.error(f"Error extending premium for guild {guild_id}: {e}")
            logger.error(traceback.format_exc())
        
        return False
    
    async def get_premium_status(self, guild_id: int) -> Dict[str, Any]:
        """
        Get detailed premium status information for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary with premium status details
        """
        status = {
            "is_premium": False,
            "tier": "none",
            "expires_at": None,
            "days_left": 0,
            "features": [],
            "limits": {}
        }
        
        try:
            # Check if guild is premium
            is_premium = await self.is_premium(guild_id)
            status["is_premium"] = is_premium
            
            if is_premium:
                # Get premium data
                premium_data = self.premium_guilds.get(guild_id)
                
                if not premium_data and hasattr(self.bot, 'db') and self.bot.db is not None:
                    premium_data = await self.bot.db.premium.find_one({"guild_id": guild_id})
                    
                    if premium_data:
                        self.premium_guilds[guild_id] = premium_data
                
                if premium_data:
                    # Set premium tier
                    tier = premium_data.get("tier", "basic")
                    status["tier"] = tier
                    
                    # Set expiration date
                    expires_at = premium_data.get("expires_at")
                    status["expires_at"] = expires_at
                    
                    # Calculate days left
                    if expires_at:
                        now = datetime.utcnow()
                        days_left = (expires_at - now).days
                        status["days_left"] = max(0, days_left)
                    
                    # Get available features
                    tier_features = self.premium_tiers.get(tier, {}).get("features", [])
                    status["features"] = tier_features
                    
                    # Get feature limits
                    tier_limits = {}
                    for limit_name, limit_value in self.premium_tiers.get(tier, {}).items():
                        if limit_name != "features":
                            tier_limits[limit_name] = limit_value
                    
                    status["limits"] = tier_limits
        except Exception as e:
            logger.error(f"Error getting premium status for guild {guild_id}: {e}")
            logger.error(traceback.format_exc())
        
        return status

def setup(bot):
    """Add the premium manager to the bot"""
    bot.premium_manager = PremiumManager(bot)
    return bot.premium_manager