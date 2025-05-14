"""
Database Connection Utility

Handles connections to MongoDB with proper error handling and retry logic.
"""

import os
import asyncio
import logging
import traceback
from typing import Optional, Dict, Any, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Configure logging
logger = logging.getLogger(__name__)

# Global database connection
_db_client = None
_db = None

async def get_db_connection(
    connection_string: Optional[str] = None,
    database_name: Optional[str] = None,
    max_retries: int = 3,
    retry_delay: float = 2.0
) -> Optional[AsyncIOMotorDatabase]:
    """
    Get a connection to the MongoDB database with retry logic.
    
    Args:
        connection_string: MongoDB connection string (defaults to MONGODB_URI env var)
        database_name: Database name (defaults to parsing from connection string)
        max_retries: Maximum number of connection attempts
        retry_delay: Seconds to wait between retries
        
    Returns:
        MongoDB database connection or None if connection fails
    """
    global _db_client, _db
    
    # If we already have a connection, return it
    if _db is not None:
        return _db
    
    # Get connection string from environment if not provided
    if connection_string is None:
        connection_string = os.environ.get("MONGODB_URI")
        if not connection_string:
            logger.error("No MongoDB connection string provided and MONGODB_URI not set in environment")
            return None
    
    # Determine database name if not provided
    if database_name is None:
        # Try to parse database name from connection string
        # Format is typically: mongodb://user:pass@host:port/database
        try:
            # Extract database name from connection string
            parts = connection_string.split("/")
            if len(parts) >= 4:
                database_name = parts[3].split("?")[0]  # Remove query parameters if present
            else:
                database_name = "discord_bot"  # Default database name
        except Exception as e:
            logger.error(f"Error parsing database name from connection string: {e}")
            database_name = "discord_bot"  # Default database name
    
    # Attempt to connect with retries
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Connecting to MongoDB (attempt {attempt}/{max_retries})...")
            
            # Create client with appropriate options
            _db_client = AsyncIOMotorClient(
                connection_string,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                maxPoolSize=10
            )
            
            # Verify the connection
            await _db_client.admin.command("ping")
            
            # Get database
            _db = _db_client[database_name]
            
            logger.info(f"Successfully connected to MongoDB database '{database_name}'")
            return _db
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Maximum retry attempts reached. Could not connect to MongoDB.")
                return None
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            logger.error(traceback.format_exc())
            return None
    
    return None

async def close_db_connection():
    """Close the database connection if it exists"""
    global _db_client, _db
    
    if _db_client is not None:
        logger.info("Closing MongoDB connection...")
        _db_client.close()
        _db_client = None
        _db = None
        logger.info("MongoDB connection closed")

async def ensure_indexes():
    """
    Ensure that all required indexes exist in the database.
    This improves query performance significantly.
    """
    global _db
    
    if _db is None:
        logger.error("Cannot ensure indexes: No database connection")
        return
    
    try:
        # Example indexes for common collections
        # These should be customized based on your specific collections and query patterns
        
        # Guild settings collection
        await _db.guild_settings.create_index("guild_id", unique=True)
        
        # Player data collection
        await _db.players.create_index("user_id")
        await _db.players.create_index("guild_id")
        await _db.players.create_index([("guild_id", 1), ("user_id", 1)], unique=True)
        
        # Premium features collection
        await _db.premium.create_index("guild_id", unique=True)
        
        logger.info("Database indexes ensured")
    except Exception as e:
        logger.error(f"Error ensuring database indexes: {e}")
        logger.error(traceback.format_exc())

async def get_guild_settings(guild_id: int) -> Dict[str, Any]:
    """
    Get settings for a specific guild.
    
    Args:
        guild_id: Discord guild ID
        
    Returns:
        Guild settings dictionary or default settings if not found
    """
    global _db
    
    if _db is None:
        logger.error("Cannot get guild settings: No database connection")
        return {"guild_id": guild_id, "prefix": "!", "error": "No database connection"}
    
    try:
        # Get guild settings from database
        settings = await _db.guild_settings.find_one({"guild_id": guild_id})
        
        # If no settings found, create default settings
        if settings is None:
            default_settings = {
                "guild_id": guild_id,
                "prefix": "!",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "premium": False,
                "enabled_features": [],
                "disabled_commands": [],
                "custom_roles": {},
                "welcome_channel": None,
                "welcome_message": "Welcome {user} to {server}!",
                "log_channel": None
            }
            
            # Insert default settings
            await _db.guild_settings.insert_one(default_settings)
            return default_settings
        
        return settings
    except Exception as e:
        logger.error(f"Error getting guild settings for guild {guild_id}: {e}")
        logger.error(traceback.format_exc())
        return {"guild_id": guild_id, "prefix": "!", "error": str(e)}

async def update_guild_settings(guild_id: int, settings: Dict[str, Any]) -> bool:
    """
    Update settings for a specific guild.
    
    Args:
        guild_id: Discord guild ID
        settings: Dictionary of settings to update
        
    Returns:
        True if update successful, False otherwise
    """
    global _db
    
    if _db is None:
        logger.error("Cannot update guild settings: No database connection")
        return False
    
    try:
        # Add updated_at timestamp
        settings["updated_at"] = datetime.utcnow()
        
        # Update guild settings
        result = await _db.guild_settings.update_one(
            {"guild_id": guild_id},
            {"$set": settings},
            upsert=True
        )
        
        return result.acknowledged
    except Exception as e:
        logger.error(f"Error updating guild settings for guild {guild_id}: {e}")
        logger.error(traceback.format_exc())
        return False

async def get_player_data(guild_id: int, user_id: int) -> Dict[str, Any]:
    """
    Get player data for a specific user in a guild.
    
    Args:
        guild_id: Discord guild ID
        user_id: Discord user ID
        
    Returns:
        Player data dictionary or default player data if not found
    """
    global _db
    
    if _db is None:
        logger.error("Cannot get player data: No database connection")
        return {"guild_id": guild_id, "user_id": user_id, "error": "No database connection"}
    
    try:
        # Get player data from database
        player = await _db.players.find_one({"guild_id": guild_id, "user_id": user_id})
        
        # If no player data found, create default player data
        if player is None:
            default_player = {
                "guild_id": guild_id,
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "experience": 0,
                "level": 1,
                "currency": 0,
                "inventory": [],
                "statistics": {},
                "last_daily": None,
                "streaks": {"daily": 0},
                "settings": {}
            }
            
            # Insert default player data
            await _db.players.insert_one(default_player)
            return default_player
        
        return player
    except Exception as e:
        logger.error(f"Error getting player data for user {user_id} in guild {guild_id}: {e}")
        logger.error(traceback.format_exc())
        return {"guild_id": guild_id, "user_id": user_id, "error": str(e)}

async def update_player_data(guild_id: int, user_id: int, data: Dict[str, Any]) -> bool:
    """
    Update player data for a specific user in a guild.
    
    Args:
        guild_id: Discord guild ID
        user_id: Discord user ID
        data: Dictionary of player data to update
        
    Returns:
        True if update successful, False otherwise
    """
    global _db
    
    if _db is None:
        logger.error("Cannot update player data: No database connection")
        return False
    
    try:
        # Add updated_at timestamp
        data["updated_at"] = datetime.utcnow()
        
        # Update player data
        result = await _db.players.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {"$set": data},
            upsert=True
        )
        
        return result.acknowledged
    except Exception as e:
        logger.error(f"Error updating player data for user {user_id} in guild {guild_id}: {e}")
        logger.error(traceback.format_exc())
        return False

async def check_premium(guild_id: int) -> bool:
    """
    Check if a guild has premium status.
    
    Args:
        guild_id: Discord guild ID
        
    Returns:
        True if the guild has premium status, False otherwise
    """
    global _db
    
    if _db is None:
        logger.error("Cannot check premium status: No database connection")
        return False
    
    try:
        # Get premium data from database
        premium_data = await _db.premium.find_one({"guild_id": guild_id})
        
        # Check if premium and if premium is still valid
        if premium_data and "expires_at" in premium_data:
            now = datetime.utcnow()
            expires_at = premium_data["expires_at"]
            
            # Check if premium has expired
            if expires_at and now > expires_at:
                return False
            
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking premium status for guild {guild_id}: {e}")
        logger.error(traceback.format_exc())
        return False