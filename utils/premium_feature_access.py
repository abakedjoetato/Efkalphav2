"""
Premium Feature Access Module

This module provides functionality to check and manage premium feature access
for the Discord bot. It integrates with the MongoDB database to store and
retrieve premium status information.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Set, Tuple
from datetime import datetime, timedelta
import discord
from discord.ext import commands

# Import our safe MongoDB client
from utils.safe_mongodb import SafeMongoDBClient, SafeMongoDBResult

# Configure logger
logger = logging.getLogger("utils.premium_feature_access")

# Collection name for premium guild data
PREMIUM_GUILDS_COLLECTION = "premium_guilds"

# Feature access levels
class FeatureAccessLevel:
    """
    Enum for feature access levels
    """
    FREE = 0
    BASIC = 1
    STANDARD = 2
    PRO = 3
    ENTERPRISE = 4
    
    @classmethod
    def get_name(cls, level: int) -> str:
        """
        Get the name of a feature access level
        
        Args:
            level: Feature access level
            
        Returns:
            str: Name of the level
        """
        level_names = {
            cls.FREE: "Free",
            cls.BASIC: "Basic",
            cls.STANDARD: "Standard",
            cls.PRO: "Pro",
            cls.ENTERPRISE: "Enterprise"
        }
        return level_names.get(level, "Unknown")

class PremiumFeature:
    """
    Premium feature definition
    
    This class defines a premium feature with its name, description,
    required access level, and any other metadata.
    
    Attributes:
        name: Feature name
        description: Feature description
        required_level: Required access level
        category: Feature category
    """
    
    def __init__(self, name: str, description: str, required_level: int, category: str = "General"):
        """
        Initialize the premium feature
        
        Args:
            name: Feature name
            description: Feature description
            required_level: Required access level
            category: Feature category
        """
        self.name = name
        self.description = description
        self.required_level = required_level
        self.category = category
        
    def __str__(self) -> str:
        """
        String representation
        
        Returns:
            str: String representation
        """
        level_name = FeatureAccessLevel.get_name(self.required_level)
        return f"{self.name} ({level_name}): {self.description}"
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary
        
        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {
            "name": self.name,
            "description": self.description,
            "required_level": self.required_level,
            "category": self.category
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PremiumFeature':
        """
        Create from dictionary
        
        Args:
            data: Dictionary representation
            
        Returns:
            PremiumFeature: Premium feature
        """
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            required_level=data.get("required_level", FeatureAccessLevel.FREE),
            category=data.get("category", "General")
        )

class PremiumFeatureRegistry:
    """
    Registry for premium features
    
    This class manages the registry of premium features and provides
    methods to check access and get feature information.
    
    Attributes:
        features: Dictionary of feature names to feature objects
    """
    
    def __init__(self):
        """Initialize the feature registry"""
        self.features: Dict[str, PremiumFeature] = {}
        
    def register_feature(self, feature: PremiumFeature) -> None:
        """
        Register a premium feature
        
        Args:
            feature: Premium feature to register
        """
        self.features[feature.name] = feature
        logger.debug(f"Registered premium feature: {feature.name}")
        
    def get_feature(self, feature_name: str) -> Optional[PremiumFeature]:
        """
        Get a premium feature by name
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            Optional[PremiumFeature]: Premium feature or None if not found
        """
        return self.features.get(feature_name)
        
    def get_all_features(self) -> List[PremiumFeature]:
        """
        Get all registered premium features
        
        Returns:
            List[PremiumFeature]: List of all premium features
        """
        return list(self.features.values())
        
    def get_features_by_level(self, level: int) -> List[PremiumFeature]:
        """
        Get all features available at a specific level
        
        Args:
            level: Access level
            
        Returns:
            List[PremiumFeature]: List of features available at the level
        """
        return [feature for feature in self.features.values() if feature.required_level <= level]
        
    def get_features_by_category(self, category: str) -> List[PremiumFeature]:
        """
        Get all features in a specific category
        
        Args:
            category: Feature category
            
        Returns:
            List[PremiumFeature]: List of features in the category
        """
        return [feature for feature in self.features.values() if feature.category == category]

class PremiumManager:
    """
    Manager for premium features and access control
    
    This class manages premium features and access control for guilds.
    It provides methods to check if a guild has access to a specific feature.
    
    Attributes:
        db_client: Safe MongoDB client
        registry: Premium feature registry
        cache: Cache of guild premium status
        cache_ttl: Cache time-to-live in seconds
        cache_last_updated: Last cache update time
    """
    
    def __init__(self, db_client: SafeMongoDBClient):
        """
        Initialize the premium manager
        
        Args:
            db_client: Safe MongoDB client
        """
        self.db_client = db_client
        self.registry = PremiumFeatureRegistry()
        
        # Cache of guild premium status
        self.cache: Dict[int, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_last_updated = {}
        
        # Register default features
        self._register_default_features()
        
    def _register_default_features(self) -> None:
        """Register default premium features"""
        # General features
        self.registry.register_feature(PremiumFeature(
            name="advanced_logging",
            description="Advanced logging and analytics features",
            required_level=FeatureAccessLevel.BASIC,
            category="Logging"
        ))
        
        self.registry.register_feature(PremiumFeature(
            name="custom_commands",
            description="Create custom commands with dynamic responses",
            required_level=FeatureAccessLevel.STANDARD,
            category="Commands"
        ))
        
        self.registry.register_feature(PremiumFeature(
            name="auto_moderation",
            description="Automatic moderation based on rules",
            required_level=FeatureAccessLevel.STANDARD,
            category="Moderation"
        ))
        
        self.registry.register_feature(PremiumFeature(
            name="advanced_analytics",
            description="Advanced analytics and statistics",
            required_level=FeatureAccessLevel.PRO,
            category="Analytics"
        ))
        
        self.registry.register_feature(PremiumFeature(
            name="custom_integrations",
            description="Custom integrations with external services",
            required_level=FeatureAccessLevel.ENTERPRISE,
            category="Integrations"
        ))
        
        logger.info("Registered default premium features")
        
    async def get_guild_premium_level(self, guild_id: int) -> int:
        """
        Get the premium level for a guild
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            int: Premium level for the guild
        """
        # Check cache first
        if guild_id in self.cache:
            cache_time = self.cache_last_updated.get(guild_id, datetime.min)
            if datetime.now() - cache_time < timedelta(seconds=self.cache_ttl):
                return self.cache[guild_id].get("level", FeatureAccessLevel.FREE)
                
        # Get from database
        result = await self.db_client.find_one(
            PREMIUM_GUILDS_COLLECTION,
            {"guild_id": guild_id}
        )
        
        if result.success and result.data:
            # Cache the result
            self.cache[guild_id] = result.data
            self.cache_last_updated[guild_id] = datetime.now()
            return result.data.get("level", FeatureAccessLevel.FREE)
        else:
            # Default to free
            return FeatureAccessLevel.FREE
            
    async def has_feature_access(self, guild_id: int, feature_name: str) -> bool:
        """
        Check if a guild has access to a feature
        
        Args:
            guild_id: Discord guild ID
            feature_name: Feature name
            
        Returns:
            bool: True if the guild has access to the feature, False otherwise
        """
        # Get the feature
        feature = self.registry.get_feature(feature_name)
        if not feature:
            logger.warning(f"Feature not found: {feature_name}")
            return False
            
        # Get the guild's premium level
        guild_level = await self.get_guild_premium_level(guild_id)
        
        # Check if the guild has access to the feature
        return guild_level >= feature.required_level
        
    async def set_guild_premium_level(self, guild_id: int, level: int) -> bool:
        """
        Set the premium level for a guild
        
        Args:
            guild_id: Discord guild ID
            level: Premium level
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Update or insert the document
        result = await self.db_client.update_one(
            PREMIUM_GUILDS_COLLECTION,
            {"guild_id": guild_id},
            {"$set": {"level": level, "updated_at": datetime.now()}},
            upsert=True
        )
        
        if result.success:
            # Update cache
            if guild_id in self.cache:
                self.cache[guild_id]["level"] = level
            else:
                self.cache[guild_id] = {"guild_id": guild_id, "level": level}
            self.cache_last_updated[guild_id] = datetime.now()
            
            logger.info(f"Set premium level for guild {guild_id} to {level} ({FeatureAccessLevel.get_name(level)})")
            return True
        else:
            logger.error(f"Failed to set premium level for guild {guild_id}: {result.error}")
            return False
            
    def get_premium_info_embed(self, guild_id: Optional[int] = None) -> discord.Embed:
        """
        Create an embed with premium feature information
        
        Args:
            guild_id: Optional Discord guild ID to check feature access
            
        Returns:
            discord.Embed: Embed with premium feature information
        """
        embed = discord.Embed(
            title="Premium Features",
            description="The following premium features are available:",
            color=0x00a8ff
        )
        
        # Group features by category
        categories = {}
        for feature in self.registry.get_all_features():
            category = feature.category
            if category not in categories:
                categories[category] = []
            categories[category].append(feature)
            
        # Add fields for each category
        for category, features in categories.items():
            # Sort features by level
            features.sort(key=lambda f: f.required_level)
            
            # Create field value
            field_value = ""
            for feature in features:
                level_name = FeatureAccessLevel.get_name(feature.required_level)
                field_value += f"**{feature.name}** ({level_name})\n{feature.description}\n\n"
                
            embed.add_field(
                name=category,
                value=field_value,
                inline=False
            )
            
        return embed
        
    async def get_guild_features_embed(self, guild_id: int) -> discord.Embed:
        """
        Create an embed with information about a guild's premium features
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            discord.Embed: Embed with guild premium feature information
        """
        # Get the guild's premium level
        guild_level = await self.get_guild_premium_level(guild_id)
        level_name = FeatureAccessLevel.get_name(guild_level)
        
        embed = discord.Embed(
            title="Guild Premium Features",
            description=f"Your guild has the **{level_name}** subscription tier.",
            color=0x00a8ff
        )
        
        # Get available features
        available_features = self.registry.get_features_by_level(guild_level)
        
        # Group by category
        categories = {}
        for feature in available_features:
            category = feature.category
            if category not in categories:
                categories[category] = []
            categories[category].append(feature)
            
        # Add fields for each category
        for category, features in categories.items():
            # Create field value
            field_value = ""
            for feature in features:
                field_value += f"✅ **{feature.name}**\n{feature.description}\n\n"
                
            embed.add_field(
                name=category,
                value=field_value,
                inline=False
            )
            
        # Add unavailable features
        unavailable_features = [
            feature for feature in self.registry.get_all_features()
            if feature.required_level > guild_level
        ]
        
        if unavailable_features:
            upgrade_value = ""
            for feature in unavailable_features:
                level_name = FeatureAccessLevel.get_name(feature.required_level)
                upgrade_value += f"⭐ **{feature.name}** ({level_name} tier)\n{feature.description}\n\n"
                
            embed.add_field(
                name="Upgrade to Access",
                value=upgrade_value,
                inline=False
            )
            
        return embed

def has_premium_feature():
    """
    Decorator to check if a guild has access to a premium feature
    
    This decorator can be used on commands to check if the guild has
    access to a specific premium feature.
    
    Example:
        @commands.command()
        @has_premium_feature("advanced_logging")
        async def logs(self, ctx):
            await ctx.send("Advanced logging command")
    
    Returns:
        Callable: Command check decorator
    """
    async def predicate(ctx):
        # Get the premium manager from the bot
        premium_manager = getattr(ctx.bot, "premium_manager", None)
        if not premium_manager:
            # If no premium manager is available, default to deny
            return False
            
        # Get the feature name from the command
        feature_name = ctx.command.name
        
        # Check if the guild has access to the feature
        return await premium_manager.has_feature_access(ctx.guild.id, feature_name)
        
    return commands.check(predicate)

def requires_premium_feature(feature_name: str):
    """
    Decorator to check if a guild has access to a specific premium feature
    
    This decorator can be used on commands to check if the guild has
    access to a specific premium feature.
    
    Args:
        feature_name: Name of the required feature
    
    Example:
        @commands.command()
        @requires_premium_feature("advanced_logging")
        async def logs(self, ctx):
            await ctx.send("Advanced logging command")
    
    Returns:
        Callable: Command check decorator
    """
    async def predicate(ctx):
        # Get the premium manager from the bot
        premium_manager = getattr(ctx.bot, "premium_manager", None)
        if not premium_manager:
            # If no premium manager is available, default to deny
            return False
            
        # Check if the guild has access to the feature
        has_access = await premium_manager.has_feature_access(ctx.guild.id, feature_name)
        
        if not has_access:
            # Send a message about the premium feature
            level_name = "premium"
            feature = premium_manager.registry.get_feature(feature_name)
            if feature:
                level_name = FeatureAccessLevel.get_name(feature.required_level)
                
            await ctx.send(
                f"⭐ This command requires the **{feature_name}** feature, "
                f"which is available in the **{level_name}** subscription tier.\n"
                f"Use the `premium` command to learn more about premium features."
            )
            
        return has_access
        
    return commands.check(predicate)