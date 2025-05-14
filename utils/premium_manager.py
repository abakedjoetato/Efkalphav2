"""
Premium Manager

This module provides functionality for managing premium features in the Discord bot.
"""

import os
import logging
import datetime
from typing import Any, Dict, List, Optional, Set, Union, Tuple, Callable, Awaitable

# Configure logger
logger = logging.getLogger("premium_manager")

try:
    from utils.safe_mongodb import SafeMongoDBClient
    from utils.premium_models import PremiumGuild, PremiumUser, PremiumTier
except ImportError:
    logger.error("Failed to import required modules for PremiumManager")

# Type hints
DiscordUser = Any  # Discord User object
DiscordMember = Any  # Discord Member object
DiscordGuild = Any  # Discord Guild object

class PremiumManager:
    """
    Manager for premium features.
    
    This class provides functionality for checking premium status and
    applying premium features to guilds and users.
    
    Attributes:
        db_client: MongoDB client
        premium_guilds: Cache of premium guild IDs
        premium_users: Cache of premium user IDs
        default_duration: Default duration for premium subscriptions in days
    """
    
    def __init__(self, db_client: 'SafeMongoDBClient', default_duration: int = 30):
        """
        Initialize the premium manager.
        
        Args:
            db_client: MongoDB client
            default_duration: Default duration for premium subscriptions in days
        """
        self.db_client = db_client
        self.premium_guilds: Set[int] = set()
        self.premium_users: Set[int] = set()
        self.feature_cache: Dict[int, List[str]] = {}
        self.default_duration = default_duration
        
        # Initialize feature handlers
        self.feature_handlers: Dict[str, Callable[[DiscordGuild], Awaitable[bool]]] = {}
    
    async def initialize(self) -> bool:
        """
        Initialize the premium manager.
        
        This method loads premium guilds and users from the database.
        
        Returns:
            Whether the initialization was successful
        """
        try:
            # Load premium guilds
            guilds = await PremiumGuild.find(self.db_client, {})
            
            for guild in guilds:
                if guild.is_premium():
                    self.premium_guilds.add(guild.guild_id)
                    self.feature_cache[guild.guild_id] = guild.enabled_features
            
            # Load premium users
            users = await PremiumUser.find(self.db_client, {})
            
            for user in users:
                if user.is_premium():
                    self.premium_users.add(user.user_id)
            
            logger.info(f"Loaded {len(self.premium_guilds)} premium guilds and {len(self.premium_users)} premium users")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize premium manager: {e}")
            return False
    
    def register_feature_handler(self, feature_name: str, handler: Callable[[DiscordGuild], Awaitable[bool]]) -> None:
        """
        Register a handler for a premium feature.
        
        Args:
            feature_name: Name of the feature
            handler: Function to handle the feature
        """
        self.feature_handlers[feature_name] = handler
        logger.debug(f"Registered handler for feature: {feature_name}")
    
    async def is_guild_premium(self, guild_id: int) -> bool:
        """
        Check if a guild has premium access.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Whether the guild has premium access
        """
        # Check cache first
        if guild_id in self.premium_guilds:
            return True
        
        # Check database
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if guild and guild.is_premium():
            self.premium_guilds.add(guild_id)
            self.feature_cache[guild_id] = guild.enabled_features
            return True
        
        return False
    
    async def is_user_premium(self, user_id: int) -> bool:
        """
        Check if a user has premium access.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Whether the user has premium access
        """
        # Check cache first
        if user_id in self.premium_users:
            return True
        
        # Check database
        user = await PremiumUser.get_by_user_id(self.db_client, user_id)
        
        if user and user.is_premium():
            self.premium_users.add(user_id)
            return True
        
        return False
    
    async def get_guild_tier(self, guild_id: int) -> PremiumTier:
        """
        Get the premium tier of a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Premium tier of the guild
        """
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if guild:
            return guild.get_tier()
        
        return PremiumTier.NONE
    
    async def get_user_tier(self, user_id: int) -> PremiumTier:
        """
        Get the premium tier of a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Premium tier of the user
        """
        user = await PremiumUser.get_by_user_id(self.db_client, user_id)
        
        if user:
            return user.get_tier()
        
        return PremiumTier.NONE
    
    async def can_use_feature(self, guild_id: int, feature: str) -> bool:
        """
        Check if a guild can use a premium feature.
        
        Args:
            guild_id: Discord guild ID
            feature: Feature to check
            
        Returns:
            Whether the guild can use the feature
        """
        # Check cache first
        if guild_id in self.premium_guilds and guild_id in self.feature_cache:
            if feature in self.feature_cache[guild_id]:
                return True
        
        # Check database
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if guild and guild.has_feature(feature):
            self.premium_guilds.add(guild_id)
            self.feature_cache[guild_id] = guild.enabled_features
            return True
        
        return False
    
    async def add_guild_premium(self, guild_id: int, tier: Union[int, str, PremiumTier] = PremiumTier.STANDARD, 
                               duration_days: Optional[int] = None) -> Tuple[bool, Optional[PremiumGuild]]:
        """
        Add premium access to a guild.
        
        Args:
            guild_id: Discord guild ID
            tier: Premium tier level
            duration_days: Duration of the premium subscription in days
            
        Returns:
            Tuple of (success, premium guild)
        """
        if duration_days is None:
            duration_days = self.default_duration
        
        # Get or create the guild
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if not guild:
            guild = PremiumGuild(guild_id=guild_id)
        
        # Set the tier
        guild.upgrade_tier(tier)
        
        # Set the expiration date
        expiry = guild.extend_subscription(duration_days)
        
        # Enable default features for the tier
        available_features = guild.get_available_features()
        guild.enabled_features = available_features
        
        # Save the guild
        success = await guild.save(self.db_client)
        
        if success:
            self.premium_guilds.add(guild_id)
            self.feature_cache[guild_id] = guild.enabled_features
            logger.info(f"Added premium to guild {guild_id} at tier {guild.tier} until {expiry}")
            return True, guild
        
        logger.error(f"Failed to add premium to guild {guild_id}")
        return False, None
    
    async def add_user_premium(self, user_id: int, tier: Union[int, str, PremiumTier] = PremiumTier.STANDARD,
                              duration_days: Optional[int] = None, credits: int = 0) -> Tuple[bool, Optional[PremiumUser]]:
        """
        Add premium access to a user.
        
        Args:
            user_id: Discord user ID
            tier: Premium tier level
            duration_days: Duration of the premium subscription in days
            credits: Premium credits to add
            
        Returns:
            Tuple of (success, premium user)
        """
        if duration_days is None:
            duration_days = self.default_duration
        
        # Get or create the user
        user = await PremiumUser.get_by_user_id(self.db_client, user_id)
        
        if not user:
            user = PremiumUser(user_id=user_id)
        
        # Set the tier
        user.upgrade_tier(tier)
        
        # Set the expiration date
        expiry = user.extend_subscription(duration_days)
        
        # Add credits
        if credits > 0:
            user.add_credits(credits)
        
        # Save the user
        success = await user.save(self.db_client)
        
        if success:
            self.premium_users.add(user_id)
            logger.info(f"Added premium to user {user_id} at tier {user.tier} until {expiry}")
            return True, user
        
        logger.error(f"Failed to add premium to user {user_id}")
        return False, None
    
    async def remove_guild_premium(self, guild_id: int) -> bool:
        """
        Remove premium access from a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Whether the premium access was removed
        """
        # Get the guild
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if not guild:
            logger.warning(f"Guild {guild_id} not found in premium database")
            return False
        
        # Set tier to none
        guild.tier = PremiumTier.NONE.value
        
        # Clear expiration date
        guild.expires_at = None
        
        # Clear enabled features
        guild.enabled_features = []
        
        # Save the guild
        success = await guild.save(self.db_client)
        
        if success:
            if guild_id in self.premium_guilds:
                self.premium_guilds.remove(guild_id)
            
            if guild_id in self.feature_cache:
                del self.feature_cache[guild_id]
                
            logger.info(f"Removed premium from guild {guild_id}")
            return True
        
        logger.error(f"Failed to remove premium from guild {guild_id}")
        return False
    
    async def remove_user_premium(self, user_id: int) -> bool:
        """
        Remove premium access from a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Whether the premium access was removed
        """
        # Get the user
        user = await PremiumUser.get_by_user_id(self.db_client, user_id)
        
        if not user:
            logger.warning(f"User {user_id} not found in premium database")
            return False
        
        # Set tier to none
        user.tier = PremiumTier.NONE.value
        
        # Clear expiration date
        user.expires_at = None
        
        # Save the user
        success = await user.save(self.db_client)
        
        if success:
            if user_id in self.premium_users:
                self.premium_users.remove(user_id)
                
            logger.info(f"Removed premium from user {user_id}")
            return True
        
        logger.error(f"Failed to remove premium from user {user_id}")
        return False
    
    async def enable_feature(self, guild_id: int, feature: str) -> bool:
        """
        Enable a premium feature for a guild.
        
        Args:
            guild_id: Discord guild ID
            feature: Feature to enable
            
        Returns:
            Whether the feature was enabled
        """
        # Get the guild
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if not guild:
            logger.warning(f"Guild {guild_id} not found in premium database")
            return False
        
        # Check if the guild can use the feature
        if not guild.is_premium():
            logger.warning(f"Guild {guild_id} is not premium")
            return False
        
        # Add the feature
        success = guild.add_feature(feature)
        
        if not success:
            logger.warning(f"Feature {feature} not available for guild {guild_id}")
            return False
        
        # Save the guild
        success = await guild.save(self.db_client)
        
        if success:
            if guild_id in self.feature_cache:
                self.feature_cache[guild_id] = guild.enabled_features
                
            logger.info(f"Enabled feature {feature} for guild {guild_id}")
            
            # Call the feature handler if available
            if feature in self.feature_handlers:
                try:
                    await self.feature_handlers[feature](guild_id)
                except Exception as e:
                    logger.error(f"Error in feature handler for {feature}: {e}")
            
            return True
        
        logger.error(f"Failed to enable feature {feature} for guild {guild_id}")
        return False
    
    async def disable_feature(self, guild_id: int, feature: str) -> bool:
        """
        Disable a premium feature for a guild.
        
        Args:
            guild_id: Discord guild ID
            feature: Feature to disable
            
        Returns:
            Whether the feature was disabled
        """
        # Get the guild
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if not guild:
            logger.warning(f"Guild {guild_id} not found in premium database")
            return False
        
        # Remove the feature
        success = guild.remove_feature(feature)
        
        if not success:
            logger.warning(f"Feature {feature} not enabled for guild {guild_id}")
            return False
        
        # Save the guild
        success = await guild.save(self.db_client)
        
        if success:
            if guild_id in self.feature_cache:
                self.feature_cache[guild_id] = guild.enabled_features
                
            logger.info(f"Disabled feature {feature} for guild {guild_id}")
            return True
        
        logger.error(f"Failed to disable feature {feature} for guild {guild_id}")
        return False
    
    async def get_guild_features(self, guild_id: int) -> List[str]:
        """
        Get the enabled premium features for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            List of enabled features
        """
        # Check cache first
        if guild_id in self.feature_cache:
            return self.feature_cache[guild_id]
        
        # Get the guild
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if guild:
            self.feature_cache[guild_id] = guild.enabled_features
            return guild.enabled_features
        
        return []
    
    async def get_available_features(self, guild_id: int) -> List[str]:
        """
        Get the available premium features for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            List of available features
        """
        # Get the guild
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if guild and guild.is_premium():
            return guild.get_available_features()
        
        return []
    
    async def check_and_remove_expired(self) -> Tuple[int, int]:
        """
        Check for expired premium subscriptions and remove them.
        
        Returns:
            Tuple of (expired guilds, expired users)
        """
        now = datetime.datetime.utcnow()
        expired_guilds = 0
        expired_users = 0
        
        # Check guilds
        guilds = await PremiumGuild.find(self.db_client, {"expires_at": {"$lt": now}})
        
        for guild in guilds:
            if guild.tier != PremiumTier.NONE.value:
                guild.tier = PremiumTier.NONE.value
                guild.enabled_features = []
                await guild.save(self.db_client)
                
                if guild.guild_id in self.premium_guilds:
                    self.premium_guilds.remove(guild.guild_id)
                
                if guild.guild_id in self.feature_cache:
                    del self.feature_cache[guild.guild_id]
                
                expired_guilds += 1
        
        # Check users
        users = await PremiumUser.find(self.db_client, {"expires_at": {"$lt": now}})
        
        for user in users:
            if user.tier != PremiumTier.NONE.value:
                user.tier = PremiumTier.NONE.value
                await user.save(self.db_client)
                
                if user.user_id in self.premium_users:
                    self.premium_users.remove(user.user_id)
                
                expired_users += 1
        
        if expired_guilds > 0 or expired_users > 0:
            logger.info(f"Removed premium from {expired_guilds} expired guilds and {expired_users} expired users")
        
        return expired_guilds, expired_users
    
    async def get_subscription_status(self, guild_id: int) -> Dict[str, Any]:
        """
        Get the premium subscription status for a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary with subscription status information
        """
        guild = await PremiumGuild.get_by_guild_id(self.db_client, guild_id)
        
        if not guild:
            return {
                "is_premium": False,
                "tier": PremiumTier.NONE.value,
                "tier_name": PremiumTier.NONE.name,
                "expires_at": None,
                "days_left": 0,
                "enabled_features": [],
                "available_features": []
            }
        
        days_left = 0
        
        if guild.expires_at and guild.expires_at > datetime.datetime.utcnow():
            delta = guild.expires_at - datetime.datetime.utcnow()
            days_left = delta.days
        
        return {
            "is_premium": guild.is_premium(),
            "tier": guild.tier,
            "tier_name": PremiumTier.from_int(guild.tier).name,
            "expires_at": guild.expires_at,
            "days_left": days_left,
            "enabled_features": guild.enabled_features,
            "available_features": guild.get_available_features()
        }
    
    async def get_user_subscription_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get the premium subscription status for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Dictionary with subscription status information
        """
        user = await PremiumUser.get_by_user_id(self.db_client, user_id)
        
        if not user:
            return {
                "is_premium": False,
                "tier": PremiumTier.NONE.value,
                "tier_name": PremiumTier.NONE.name,
                "expires_at": None,
                "days_left": 0,
                "credits": 0,
                "guilds": []
            }
        
        days_left = 0
        
        if user.expires_at and user.expires_at > datetime.datetime.utcnow():
            delta = user.expires_at - datetime.datetime.utcnow()
            days_left = delta.days
        
        return {
            "is_premium": user.is_premium(),
            "tier": user.tier,
            "tier_name": PremiumTier.from_int(user.tier).name,
            "expires_at": user.expires_at,
            "days_left": days_left,
            "credits": user.credits,
            "guilds": user.guilds
        }
    
    async def user_can_add_guild(self, user_id: int, guild_id: int) -> bool:
        """
        Check if a user can add a guild to their premium list.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            
        Returns:
            Whether the user can add the guild
        """
        user = await PremiumUser.get_by_user_id(self.db_client, user_id)
        
        if not user:
            return False
        
        if not user.is_premium():
            return False
        
        if guild_id in user.guilds:
            return True
        
        return user.can_add_guild()