"""
Premium Models

This module provides models for premium features and subscription management.
"""

import enum
import logging
import datetime
from typing import Any, Dict, List, Optional, Set, ClassVar, Type, Union, cast
from utils.mongodb_models import MongoModel

# Configure logger
logger = logging.getLogger("premium_models")

class PremiumTier(enum.Enum):
    """
    Premium tier levels for users and guilds.
    """
    NONE = 0
    BASIC = 1
    STANDARD = 2
    PRO = 3
    ENTERPRISE = 4
    
    @classmethod
    def from_str(cls, tier_str: str) -> 'PremiumTier':
        """Convert a string to a PremiumTier."""
        tier_str = tier_str.upper()
        for tier in cls:
            if tier.name == tier_str:
                return tier
        return cls.NONE
    
    @classmethod
    def from_int(cls, tier_int: int) -> 'PremiumTier':
        """Convert an integer to a PremiumTier."""
        for tier in cls:
            if tier.value == tier_int:
                return tier
        return cls.NONE
    
    def __lt__(self, other: 'PremiumTier') -> bool:
        """Compare tiers."""
        return self.value < other.value
    
    def __gt__(self, other: 'PremiumTier') -> bool:
        """Compare tiers."""
        return self.value > other.value
    
    def __le__(self, other: 'PremiumTier') -> bool:
        """Compare tiers."""
        return self.value <= other.value
    
    def __ge__(self, other: 'PremiumTier') -> bool:
        """Compare tiers."""
        return self.value >= other.value

class PremiumGuild(MongoModel):
    """
    Premium guild model for guild-based premium features.
    
    Attributes:
        guild_id: Discord guild ID
        tier: Premium tier level
        expires_at: When the premium subscription expires
        enabled_features: List of enabled premium features
        settings: Custom settings for premium features
    """
    
    collection_name = "premium_guilds"
    indexes = [
        {
            "keys": {"guild_id": 1},
            "options": {"unique": True}
        }
    ]
    
    # Feature availability by tier
    TIER_FEATURES = {
        PremiumTier.NONE: [],
        PremiumTier.BASIC: ["basic_analytics", "extended_logs"],
        PremiumTier.STANDARD: ["basic_analytics", "extended_logs", "custom_commands", "advanced_logging"],
        PremiumTier.PRO: ["basic_analytics", "extended_logs", "custom_commands", "advanced_logging", 
                          "auto_moderation", "scheduled_messages", "role_management"],
        PremiumTier.ENTERPRISE: ["basic_analytics", "extended_logs", "custom_commands", "advanced_logging", 
                                "auto_moderation", "scheduled_messages", "role_management", 
                                "audit_logs", "message_filtering", "custom_welcome", "advanced_stats"]
    }
    
    def __init__(self, **kwargs):
        """
        Initialize a premium guild.
        
        Args:
            **kwargs: Model attributes
        """
        super().__init__(**kwargs)
        self.guild_id = kwargs.get("guild_id")
        self.tier = kwargs.get("tier", PremiumTier.NONE.value)
        self.expires_at = kwargs.get("expires_at")
        self.enabled_features = kwargs.get("enabled_features", [])
        self.settings = kwargs.get("settings", {})
    
    def get_tier(self) -> PremiumTier:
        """Get the premium tier as an enum."""
        return PremiumTier.from_int(self.tier)
    
    def is_premium(self) -> bool:
        """Check if the guild has premium access."""
        if self.tier == PremiumTier.NONE.value:
            return False
        
        if self.expires_at and self.expires_at < datetime.datetime.utcnow():
            return False
        
        return True
    
    def get_available_features(self) -> List[str]:
        """Get the list of available features for the guild's tier."""
        tier = self.get_tier()
        return self.TIER_FEATURES.get(tier, [])
    
    def has_feature(self, feature: str) -> bool:
        """
        Check if a feature is enabled for this guild.
        
        Args:
            feature: Feature to check
            
        Returns:
            Whether the feature is available and enabled
        """
        if not self.is_premium():
            return False
        
        if feature not in self.get_available_features():
            return False
        
        if feature not in self.enabled_features:
            return False
        
        return True
    
    def extend_subscription(self, days: int) -> datetime.datetime:
        """
        Extend the guild's premium subscription.
        
        Args:
            days: Number of days to extend
            
        Returns:
            New expiration date
        """
        if not self.expires_at or self.expires_at < datetime.datetime.utcnow():
            self.expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        else:
            self.expires_at = self.expires_at + datetime.timedelta(days=days)
        
        return self.expires_at
    
    def upgrade_tier(self, tier: Union[int, str, PremiumTier]) -> PremiumTier:
        """
        Upgrade the guild's premium tier.
        
        Args:
            tier: New tier level
            
        Returns:
            New premium tier
        """
        if isinstance(tier, str):
            tier_enum = PremiumTier.from_str(tier)
        elif isinstance(tier, int):
            tier_enum = PremiumTier.from_int(tier)
        else:
            tier_enum = tier
        
        if tier_enum.value > self.tier:
            self.tier = tier_enum.value
        
        return self.get_tier()
    
    def add_feature(self, feature: str) -> bool:
        """
        Enable a premium feature for the guild.
        
        Args:
            feature: Feature to enable
            
        Returns:
            Whether the feature was added
        """
        if not self.is_premium():
            return False
        
        if feature not in self.get_available_features():
            return False
        
        if feature not in self.enabled_features:
            self.enabled_features.append(feature)
        
        return True
    
    def remove_feature(self, feature: str) -> bool:
        """
        Disable a premium feature for the guild.
        
        Args:
            feature: Feature to disable
            
        Returns:
            Whether the feature was removed
        """
        if feature in self.enabled_features:
            self.enabled_features.remove(feature)
            return True
        
        return False
    
    def set_setting(self, setting: str, value: Any) -> None:
        """
        Set a premium feature setting.
        
        Args:
            setting: Setting name
            value: Setting value
        """
        self.settings[setting] = value
    
    def get_setting(self, setting: str, default: Any = None) -> Any:
        """
        Get a premium feature setting.
        
        Args:
            setting: Setting name
            default: Default value
            
        Returns:
            Setting value
        """
        return self.settings.get(setting, default)
    
    @classmethod
    async def get_by_guild_id(cls, db_client: 'SafeMongoDBClient', guild_id: int) -> Optional['PremiumGuild']:
        """
        Get a premium guild by guild ID.
        
        Args:
            db_client: MongoDB client
            guild_id: Discord guild ID
            
        Returns:
            Premium guild or None if not found
        """
        return await cls.find_one(db_client, {"guild_id": guild_id})

class PremiumUser(MongoModel):
    """
    Premium user model for user-based premium features.
    
    Attributes:
        user_id: Discord user ID
        tier: Premium tier level
        expires_at: When the premium subscription expires
        credits: Premium credits that can be used to purchase features
        guilds: List of guild IDs that this user has granted premium to
    """
    
    collection_name = "premium_users"
    indexes = [
        {
            "keys": {"user_id": 1},
            "options": {"unique": True}
        }
    ]
    
    def __init__(self, **kwargs):
        """
        Initialize a premium user.
        
        Args:
            **kwargs: Model attributes
        """
        super().__init__(**kwargs)
        self.user_id = kwargs.get("user_id")
        self.tier = kwargs.get("tier", PremiumTier.NONE.value)
        self.expires_at = kwargs.get("expires_at")
        self.credits = kwargs.get("credits", 0)
        self.guilds = kwargs.get("guilds", [])
    
    def get_tier(self) -> PremiumTier:
        """Get the premium tier as an enum."""
        return PremiumTier.from_int(self.tier)
    
    def is_premium(self) -> bool:
        """Check if the user has premium access."""
        if self.tier == PremiumTier.NONE.value:
            return False
        
        if self.expires_at and self.expires_at < datetime.datetime.utcnow():
            return False
        
        return True
    
    def extend_subscription(self, days: int) -> datetime.datetime:
        """
        Extend the user's premium subscription.
        
        Args:
            days: Number of days to extend
            
        Returns:
            New expiration date
        """
        if not self.expires_at or self.expires_at < datetime.datetime.utcnow():
            self.expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        else:
            self.expires_at = self.expires_at + datetime.timedelta(days=days)
        
        return self.expires_at
    
    def upgrade_tier(self, tier: Union[int, str, PremiumTier]) -> PremiumTier:
        """
        Upgrade the user's premium tier.
        
        Args:
            tier: New tier level
            
        Returns:
            New premium tier
        """
        if isinstance(tier, str):
            tier_enum = PremiumTier.from_str(tier)
        elif isinstance(tier, int):
            tier_enum = PremiumTier.from_int(tier)
        else:
            tier_enum = tier
        
        if tier_enum.value > self.tier:
            self.tier = tier_enum.value
        
        return self.get_tier()
    
    def add_credits(self, amount: int) -> int:
        """
        Add premium credits to the user.
        
        Args:
            amount: Number of credits to add
            
        Returns:
            New credit balance
        """
        self.credits += amount
        return self.credits
    
    def use_credits(self, amount: int) -> bool:
        """
        Use premium credits.
        
        Args:
            amount: Number of credits to use
            
        Returns:
            Whether the credits were used
        """
        if self.credits < amount:
            return False
        
        self.credits -= amount
        return True
    
    def add_guild(self, guild_id: int) -> bool:
        """
        Add a guild to the user's premium list.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Whether the guild was added
        """
        if guild_id not in self.guilds:
            self.guilds.append(guild_id)
            return True
        
        return False
    
    def remove_guild(self, guild_id: int) -> bool:
        """
        Remove a guild from the user's premium list.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Whether the guild was removed
        """
        if guild_id in self.guilds:
            self.guilds.remove(guild_id)
            return True
        
        return False
    
    def can_add_guild(self) -> bool:
        """
        Check if the user can add another guild to their premium list.
        
        Returns:
            Whether the user can add another guild
        """
        tier = self.get_tier()
        max_guilds = {
            PremiumTier.NONE: 0,
            PremiumTier.BASIC: 1,
            PremiumTier.STANDARD: 3,
            PremiumTier.PRO: 5,
            PremiumTier.ENTERPRISE: 10
        }
        
        return len(self.guilds) < max_guilds.get(tier, 0)
    
    @classmethod
    async def get_by_user_id(cls, db_client: 'SafeMongoDBClient', user_id: int) -> Optional['PremiumUser']:
        """
        Get a premium user by user ID.
        
        Args:
            db_client: MongoDB client
            user_id: Discord user ID
            
        Returns:
            Premium user or None if not found
        """
        return await cls.find_one(db_client, {"user_id": user_id})