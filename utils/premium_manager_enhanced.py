"""
Premium Manager (Enhanced) Module

This module provides a robust system for managing premium features and access controls,
with enhanced error handling and caching for improved performance.
"""

import os
import re
import json
import time
import logging
import asyncio
import datetime
from typing import Dict, List, Any, Optional, Union, Callable, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("premium_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PremiumManager:
    """
    Enhanced premium features management system.
    
    This class provides methods to check, grant, and revoke premium access
    for guilds and users, with caching for improved performance.
    """
    
    def __init__(self, db=None):
        """
        Initialize the premium manager.
        
        Args:
            db: Database adapter
        """
        self.db = db
        
        # Cache for premium status
        self.guild_premium_cache = {}  # {guild_id: {'status': bool, 'features': List[str], 'expires_at': datetime, 'updated_at': datetime}}
        self.user_premium_cache = {}   # {user_id: {'status': bool, 'features': List[str], 'expires_at': datetime, 'updated_at': datetime}}
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes cache TTL
        self.cache_clean_interval = 3600  # Clean cache every hour
        
        # Premium feature definitions
        self.available_features = {
            'custom_prefix': {
                'name': 'Custom Prefix',
                'description': 'Customize the bot command prefix for your server',
                'tier': 1
            },
            'extended_logs': {
                'name': 'Extended Logs',
                'description': 'Access to extended logging features and history',
                'tier': 1
            },
            'auto_responses': {
                'name': 'Auto Responses',
                'description': 'Create custom automated responses to messages',
                'tier': 2
            },
            'advanced_analytics': {
                'name': 'Advanced Analytics',
                'description': 'Access to advanced server analytics and reports',
                'tier': 2
            },
            'custom_commands': {
                'name': 'Custom Commands',
                'description': 'Create and manage custom commands',
                'tier': 3
            },
            'reaction_roles': {
                'name': 'Reaction Roles',
                'description': 'Create role assignment systems using reactions',
                'tier': 3
            }
        }
        
        # Premium tiers
        self.premium_tiers = {
            1: {
                'name': 'Basic',
                'price': '$2.99/month',
                'features': ['custom_prefix', 'extended_logs'],
                'color': 0xAAAAAA  # Light gray
            },
            2: {
                'name': 'Standard',
                'price': '$4.99/month',
                'features': ['custom_prefix', 'extended_logs', 'auto_responses', 'advanced_analytics'],
                'color': 0xC0C0C0  # Silver
            },
            3: {
                'name': 'Premium',
                'price': '$9.99/month',
                'features': ['custom_prefix', 'extended_logs', 'auto_responses', 
                             'advanced_analytics', 'custom_commands', 'reaction_roles'],
                'color': 0xFFD700  # Gold
            }
        }
        
        logger.info("Premium manager initialized")
    
    async def start_cache_cleanup_task(self):
        """Start a background task to periodically clean the cache"""
        while True:
            try:
                self._cleanup_cache()
                await asyncio.sleep(self.cache_clean_interval)
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")
                await asyncio.sleep(60)  # Wait a bit before retrying
    
    def _cleanup_cache(self):
        """Clean expired entries from the cache"""
        now = datetime.datetime.now()
        expired_guilds = []
        expired_users = []
        
        # Find expired guild entries
        for guild_id, data in self.guild_premium_cache.items():
            if 'updated_at' in data and (now - data['updated_at']).total_seconds() > self.cache_ttl:
                expired_guilds.append(guild_id)
        
        # Find expired user entries
        for user_id, data in self.user_premium_cache.items():
            if 'updated_at' in data and (now - data['updated_at']).total_seconds() > self.cache_ttl:
                expired_users.append(user_id)
        
        # Remove expired entries
        for guild_id in expired_guilds:
            del self.guild_premium_cache[guild_id]
        
        for user_id in expired_users:
            del self.user_premium_cache[user_id]
        
        if expired_guilds or expired_users:
            logger.info(f"Cleaned {len(expired_guilds)} guild entries and {len(expired_users)} user entries from cache")
    
    async def is_guild_premium(self, guild_id: int) -> bool:
        """
        Check if a guild has premium status.
        
        Args:
            guild_id: ID of the guild to check
            
        Returns:
            bool: True if the guild has premium status, False otherwise
        """
        # Check cache first
        if guild_id in self.guild_premium_cache:
            cache_entry = self.guild_premium_cache[guild_id]
            
            # If cache entry is still valid, use it
            if (datetime.datetime.now() - cache_entry['updated_at']).total_seconds() <= self.cache_ttl:
                # Check if premium has expired
                if 'expires_at' in cache_entry and cache_entry['expires_at'] and cache_entry['expires_at'] < datetime.datetime.now():
                    # Premium has expired, update cache and database
                    await self._update_guild_premium_status(guild_id, False, [], None)
                    return False
                
                return cache_entry['status']
        
        # Cache miss or expired, query database
        if self.db:
            try:
                guild_premium = await self.db.find_one('guild_premium', {'guild_id': str(guild_id)})
                
                if guild_premium:
                    # Parse expires_at from string if it exists
                    expires_at = None
                    if 'expires_at' in guild_premium and guild_premium['expires_at']:
                        try:
                            expires_at = datetime.datetime.fromisoformat(guild_premium['expires_at'])
                        except (ValueError, TypeError):
                            logger.error(f"Invalid expires_at format for guild {guild_id}: {guild_premium['expires_at']}")
                    
                    # Check if premium has expired
                    if expires_at and expires_at < datetime.datetime.now():
                        # Premium has expired, update status
                        await self._update_guild_premium_status(guild_id, False, [], None)
                        return False
                    
                    # Premium is valid, update cache
                    features = guild_premium.get('features', [])
                    await self._update_guild_premium_status(guild_id, True, features, expires_at)
                    return True
                else:
                    # No premium entry found
                    await self._update_guild_premium_status(guild_id, False, [], None)
                    return False
            
            except Exception as e:
                logger.error(f"Error checking premium status for guild {guild_id}: {e}")
                # If there's an error, assume no premium
                return False
        
        # No database available
        logger.warning(f"No database available to check premium status for guild {guild_id}")
        return False
    
    async def is_user_premium(self, user_id: int) -> bool:
        """
        Check if a user has premium status.
        
        Args:
            user_id: ID of the user to check
            
        Returns:
            bool: True if the user has premium status, False otherwise
        """
        # Check cache first
        if user_id in self.user_premium_cache:
            cache_entry = self.user_premium_cache[user_id]
            
            # If cache entry is still valid, use it
            if (datetime.datetime.now() - cache_entry['updated_at']).total_seconds() <= self.cache_ttl:
                # Check if premium has expired
                if 'expires_at' in cache_entry and cache_entry['expires_at'] and cache_entry['expires_at'] < datetime.datetime.now():
                    # Premium has expired, update cache and database
                    await self._update_user_premium_status(user_id, False, [], None)
                    return False
                
                return cache_entry['status']
        
        # Cache miss or expired, query database
        if self.db:
            try:
                user_premium = await self.db.find_one('user_premium', {'user_id': str(user_id)})
                
                if user_premium:
                    # Parse expires_at from string if it exists
                    expires_at = None
                    if 'expires_at' in user_premium and user_premium['expires_at']:
                        try:
                            expires_at = datetime.datetime.fromisoformat(user_premium['expires_at'])
                        except (ValueError, TypeError):
                            logger.error(f"Invalid expires_at format for user {user_id}: {user_premium['expires_at']}")
                    
                    # Check if premium has expired
                    if expires_at and expires_at < datetime.datetime.now():
                        # Premium has expired, update status
                        await self._update_user_premium_status(user_id, False, [], None)
                        return False
                    
                    # Premium is valid, update cache
                    features = user_premium.get('features', [])
                    await self._update_user_premium_status(user_id, True, features, expires_at)
                    return True
                else:
                    # No premium entry found
                    await self._update_user_premium_status(user_id, False, [], None)
                    return False
            
            except Exception as e:
                logger.error(f"Error checking premium status for user {user_id}: {e}")
                # If there's an error, assume no premium
                return False
        
        # No database available
        logger.warning(f"No database available to check premium status for user {user_id}")
        return False
    
    async def get_guild_premium_tier(self, guild_id: int) -> int:
        """
        Get the premium tier of a guild.
        
        Args:
            guild_id: ID of the guild to check
            
        Returns:
            int: Premium tier (0 if no premium)
        """
        # Check if guild has premium
        if not await self.is_guild_premium(guild_id):
            return 0
        
        # Get guild premium features
        features = await self.get_guild_premium_features(guild_id)
        
        # Determine tier based on features
        highest_tier = 0
        for tier_id, tier_info in self.premium_tiers.items():
            if all(feature in features for feature in tier_info['features']):
                highest_tier = max(highest_tier, tier_id)
        
        return highest_tier
    
    async def get_user_premium_tier(self, user_id: int) -> int:
        """
        Get the premium tier of a user.
        
        Args:
            user_id: ID of the user to check
            
        Returns:
            int: Premium tier (0 if no premium)
        """
        # Check if user has premium
        if not await self.is_user_premium(user_id):
            return 0
        
        # Get user premium features
        features = await self.get_user_premium_features(user_id)
        
        # Determine tier based on features
        highest_tier = 0
        for tier_id, tier_info in self.premium_tiers.items():
            if all(feature in features for feature in tier_info['features']):
                highest_tier = max(highest_tier, tier_id)
        
        return highest_tier
    
    async def get_guild_premium_features(self, guild_id: int) -> List[str]:
        """
        Get the premium features available to a guild.
        
        Args:
            guild_id: ID of the guild to check
            
        Returns:
            List[str]: List of premium feature IDs available to the guild
        """
        # Check cache first
        if guild_id in self.guild_premium_cache:
            cache_entry = self.guild_premium_cache[guild_id]
            
            # If cache entry is still valid and guild has premium, use it
            if (datetime.datetime.now() - cache_entry['updated_at']).total_seconds() <= self.cache_ttl and cache_entry['status']:
                return cache_entry.get('features', [])
        
        # Cache miss, expired, or no premium, query database
        if self.db:
            try:
                guild_premium = await self.db.find_one('guild_premium', {'guild_id': str(guild_id)})
                
                if guild_premium and guild_premium.get('status', False):
                    # Return features from database
                    return guild_premium.get('features', [])
            
            except Exception as e:
                logger.error(f"Error getting premium features for guild {guild_id}: {e}")
        
        # No premium or error
        return []
    
    async def get_user_premium_features(self, user_id: int) -> List[str]:
        """
        Get the premium features available to a user.
        
        Args:
            user_id: ID of the user to check
            
        Returns:
            List[str]: List of premium feature IDs available to the user
        """
        # Check cache first
        if user_id in self.user_premium_cache:
            cache_entry = self.user_premium_cache[user_id]
            
            # If cache entry is still valid and user has premium, use it
            if (datetime.datetime.now() - cache_entry['updated_at']).total_seconds() <= self.cache_ttl and cache_entry['status']:
                return cache_entry.get('features', [])
        
        # Cache miss, expired, or no premium, query database
        if self.db:
            try:
                user_premium = await self.db.find_one('user_premium', {'user_id': str(user_id)})
                
                if user_premium and user_premium.get('status', False):
                    # Return features from database
                    return user_premium.get('features', [])
            
            except Exception as e:
                logger.error(f"Error getting premium features for user {user_id}: {e}")
        
        # No premium or error
        return []
    
    async def has_feature(self, feature_id: str, guild_id: Optional[int] = None, user_id: Optional[int] = None) -> bool:
        """
        Check if a guild or user has access to a specific premium feature.
        
        Args:
            feature_id: ID of the feature to check
            guild_id: ID of the guild to check (optional)
            user_id: ID of the user to check (optional)
            
        Returns:
            bool: True if the guild or user has access to the feature, False otherwise
        """
        # Validate input
        if guild_id is None and user_id is None:
            logger.error("Either guild_id or user_id must be provided to has_feature()")
            return False
        
        # Check if feature exists
        if feature_id not in self.available_features:
            logger.warning(f"Feature '{feature_id}' does not exist")
            return False
        
        # Check guild premium
        if guild_id is not None:
            guild_features = await self.get_guild_premium_features(guild_id)
            if feature_id in guild_features:
                return True
        
        # Check user premium
        if user_id is not None:
            user_features = await self.get_user_premium_features(user_id)
            if feature_id in user_features:
                return True
        
        return False
    
    async def add_guild_premium(self, guild_id: int, tier: int, duration_days: int = 30) -> bool:
        """
        Add premium status to a guild.
        
        Args:
            guild_id: ID of the guild to add premium to
            tier: Premium tier to add (1-3)
            duration_days: Duration of premium in days
            
        Returns:
            bool: True if premium was added successfully, False otherwise
        """
        # Validate tier
        if tier not in self.premium_tiers:
            logger.error(f"Invalid premium tier: {tier}")
            return False
        
        # Calculate expiration date
        expires_at = datetime.datetime.now() + datetime.timedelta(days=duration_days)
        
        # Get features for tier
        features = self.premium_tiers[tier]['features']
        
        # Update database
        if self.db:
            try:
                # Check if guild already has premium
                existing = await self.db.find_one('guild_premium', {'guild_id': str(guild_id)})
                
                if existing:
                    # Update existing entry
                    await self.db.update_one(
                        'guild_premium',
                        {'guild_id': str(guild_id)},
                        {
                            '$set': {
                                'status': True,
                                'tier': tier,
                                'features': features,
                                'expires_at': expires_at.isoformat(),
                                'updated_at': datetime.datetime.now().isoformat()
                            }
                        }
                    )
                else:
                    # Create new entry
                    await self.db.insert_one(
                        'guild_premium',
                        {
                            'guild_id': str(guild_id),
                            'status': True,
                            'tier': tier,
                            'features': features,
                            'expires_at': expires_at.isoformat(),
                            'created_at': datetime.datetime.now().isoformat(),
                            'updated_at': datetime.datetime.now().isoformat()
                        }
                    )
                
                # Update cache
                await self._update_guild_premium_status(guild_id, True, features, expires_at)
                
                logger.info(f"Added tier {tier} premium to guild {guild_id} until {expires_at.isoformat()}")
                return True
            
            except Exception as e:
                logger.error(f"Error adding premium to guild {guild_id}: {e}")
                return False
        
        # No database available
        logger.warning(f"No database available to add premium to guild {guild_id}")
        return False
    
    async def add_user_premium(self, user_id: int, tier: int, duration_days: int = 30) -> bool:
        """
        Add premium status to a user.
        
        Args:
            user_id: ID of the user to add premium to
            tier: Premium tier to add (1-3)
            duration_days: Duration of premium in days
            
        Returns:
            bool: True if premium was added successfully, False otherwise
        """
        # Validate tier
        if tier not in self.premium_tiers:
            logger.error(f"Invalid premium tier: {tier}")
            return False
        
        # Calculate expiration date
        expires_at = datetime.datetime.now() + datetime.timedelta(days=duration_days)
        
        # Get features for tier
        features = self.premium_tiers[tier]['features']
        
        # Update database
        if self.db:
            try:
                # Check if user already has premium
                existing = await self.db.find_one('user_premium', {'user_id': str(user_id)})
                
                if existing:
                    # Update existing entry
                    await self.db.update_one(
                        'user_premium',
                        {'user_id': str(user_id)},
                        {
                            '$set': {
                                'status': True,
                                'tier': tier,
                                'features': features,
                                'expires_at': expires_at.isoformat(),
                                'updated_at': datetime.datetime.now().isoformat()
                            }
                        }
                    )
                else:
                    # Create new entry
                    await self.db.insert_one(
                        'user_premium',
                        {
                            'user_id': str(user_id),
                            'status': True,
                            'tier': tier,
                            'features': features,
                            'expires_at': expires_at.isoformat(),
                            'created_at': datetime.datetime.now().isoformat(),
                            'updated_at': datetime.datetime.now().isoformat()
                        }
                    )
                
                # Update cache
                await self._update_user_premium_status(user_id, True, features, expires_at)
                
                logger.info(f"Added tier {tier} premium to user {user_id} until {expires_at.isoformat()}")
                return True
            
            except Exception as e:
                logger.error(f"Error adding premium to user {user_id}: {e}")
                return False
        
        # No database available
        logger.warning(f"No database available to add premium to user {user_id}")
        return False
    
    async def remove_guild_premium(self, guild_id: int) -> bool:
        """
        Remove premium status from a guild.
        
        Args:
            guild_id: ID of the guild to remove premium from
            
        Returns:
            bool: True if premium was removed successfully, False otherwise
        """
        # Update database
        if self.db:
            try:
                # Update entry to remove premium
                await self.db.update_one(
                    'guild_premium',
                    {'guild_id': str(guild_id)},
                    {
                        '$set': {
                            'status': False,
                            'features': [],
                            'expires_at': None,
                            'updated_at': datetime.datetime.now().isoformat()
                        }
                    }
                )
                
                # Update cache
                await self._update_guild_premium_status(guild_id, False, [], None)
                
                logger.info(f"Removed premium from guild {guild_id}")
                return True
            
            except Exception as e:
                logger.error(f"Error removing premium from guild {guild_id}: {e}")
                return False
        
        # No database available
        logger.warning(f"No database available to remove premium from guild {guild_id}")
        return False
    
    async def remove_user_premium(self, user_id: int) -> bool:
        """
        Remove premium status from a user.
        
        Args:
            user_id: ID of the user to remove premium from
            
        Returns:
            bool: True if premium was removed successfully, False otherwise
        """
        # Update database
        if self.db:
            try:
                # Update entry to remove premium
                await self.db.update_one(
                    'user_premium',
                    {'user_id': str(user_id)},
                    {
                        '$set': {
                            'status': False,
                            'features': [],
                            'expires_at': None,
                            'updated_at': datetime.datetime.now().isoformat()
                        }
                    }
                )
                
                # Update cache
                await self._update_user_premium_status(user_id, False, [], None)
                
                logger.info(f"Removed premium from user {user_id}")
                return True
            
            except Exception as e:
                logger.error(f"Error removing premium from user {user_id}: {e}")
                return False
        
        # No database available
        logger.warning(f"No database available to remove premium from user {user_id}")
        return False
    
    async def _update_guild_premium_status(self, guild_id: int, status: bool, features: List[str], expires_at: Optional[datetime.datetime]):
        """
        Update guild premium status in cache and database.
        
        Args:
            guild_id: ID of the guild to update
            status: New premium status
            features: List of premium features
            expires_at: Expiration date
        """
        # Update cache
        self.guild_premium_cache[guild_id] = {
            'status': status,
            'features': features,
            'expires_at': expires_at,
            'updated_at': datetime.datetime.now()
        }
        
        # Update database if available
        if self.db:
            try:
                existing = await self.db.find_one('guild_premium', {'guild_id': str(guild_id)})
                
                if existing:
                    # Update existing entry
                    await self.db.update_one(
                        'guild_premium',
                        {'guild_id': str(guild_id)},
                        {
                            '$set': {
                                'status': status,
                                'features': features,
                                'expires_at': expires_at.isoformat() if expires_at else None,
                                'updated_at': datetime.datetime.now().isoformat()
                            }
                        }
                    )
                else:
                    # Create new entry
                    await self.db.insert_one(
                        'guild_premium',
                        {
                            'guild_id': str(guild_id),
                            'status': status,
                            'features': features,
                            'expires_at': expires_at.isoformat() if expires_at else None,
                            'created_at': datetime.datetime.now().isoformat(),
                            'updated_at': datetime.datetime.now().isoformat()
                        }
                    )
            except Exception as e:
                logger.error(f"Error updating premium status for guild {guild_id} in database: {e}")
    
    async def _update_user_premium_status(self, user_id: int, status: bool, features: List[str], expires_at: Optional[datetime.datetime]):
        """
        Update user premium status in cache and database.
        
        Args:
            user_id: ID of the user to update
            status: New premium status
            features: List of premium features
            expires_at: Expiration date
        """
        # Update cache
        self.user_premium_cache[user_id] = {
            'status': status,
            'features': features,
            'expires_at': expires_at,
            'updated_at': datetime.datetime.now()
        }
        
        # Update database if available
        if self.db:
            try:
                existing = await self.db.find_one('user_premium', {'user_id': str(user_id)})
                
                if existing:
                    # Update existing entry
                    await self.db.update_one(
                        'user_premium',
                        {'user_id': str(user_id)},
                        {
                            '$set': {
                                'status': status,
                                'features': features,
                                'expires_at': expires_at.isoformat() if expires_at else None,
                                'updated_at': datetime.datetime.now().isoformat()
                            }
                        }
                    )
                else:
                    # Create new entry
                    await self.db.insert_one(
                        'user_premium',
                        {
                            'user_id': str(user_id),
                            'status': status,
                            'features': features,
                            'expires_at': expires_at.isoformat() if expires_at else None,
                            'created_at': datetime.datetime.now().isoformat(),
                            'updated_at': datetime.datetime.now().isoformat()
                        }
                    )
            except Exception as e:
                logger.error(f"Error updating premium status for user {user_id} in database: {e}")

# Singleton instance
_premium_manager_instance = None

def get_premium_manager(db=None):
    """
    Get the global premium manager instance.
    
    Args:
        db: Database adapter (optional)
        
    Returns:
        PremiumManager: Global premium manager instance
    """
    global _premium_manager_instance
    
    if _premium_manager_instance is None:
        _premium_manager_instance = PremiumManager(db)
    elif db and _premium_manager_instance.db is None:
        _premium_manager_instance.db = db
    
    return _premium_manager_instance