"""
Configuration Module

This module provides configuration settings for the Discord bot and related services.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

# Configure logger
logger = logging.getLogger("config")

# Default configuration
config: Dict[str, Any] = {
    "discord": {
        "prefix": "!",
        "production": os.environ.get("PRODUCTION", "False").lower() in ("true", "1", "yes"),
        "debug_guilds": [],
        "owner_ids": []
    },
    "mongodb": {
        "uri": os.environ.get("MONGODB_URI"),
        "db_name": os.environ.get("DB_NAME", "discordbot")
    },
    "premium": {
        "default_duration_days": 30,
        "max_guilds_per_user": {
            "BASIC": 1,
            "STANDARD": 3,
            "PRO": 5,
            "ENTERPRISE": 10
        },
        "features": {
            "BASIC": ["basic_analytics", "extended_logs"],
            "STANDARD": ["basic_analytics", "extended_logs", "custom_commands", "advanced_logging"],
            "PRO": ["basic_analytics", "extended_logs", "custom_commands", "advanced_logging", 
                   "auto_moderation", "scheduled_messages", "role_management"],
            "ENTERPRISE": ["basic_analytics", "extended_logs", "custom_commands", "advanced_logging", 
                         "auto_moderation", "scheduled_messages", "role_management", 
                         "audit_logs", "message_filtering", "custom_welcome", "advanced_stats"]
        }
    },
    "logging": {
        "level": os.environ.get("LOG_LEVEL", "INFO"),
        "file": "logs/bot.log",
        "max_bytes": 10485760,  # 10 MB
        "backup_count": 5
    },
    "sftp": {
        "enabled": False,
        "host": os.environ.get("SFTP_HOST"),
        "port": int(os.environ.get("SFTP_PORT", "22")),
        "username": os.environ.get("SFTP_USERNAME"),
        "password": os.environ.get("SFTP_PASSWORD"),
        "key_file": os.environ.get("SFTP_KEY_FILE"),
        "remote_dir": os.environ.get("SFTP_REMOTE_DIR", "/logs")
    }
}

# Parse debug guild IDs from environment
debug_guilds_str = os.environ.get("DEBUG_GUILDS", "")
if debug_guilds_str:
    try:
        debug_guild_ids = [int(guild_id.strip()) for guild_id in debug_guilds_str.split(",") if guild_id.strip()]
        config["discord"]["debug_guilds"] = debug_guild_ids
    except (ValueError, TypeError) as e:
        logger.error(f"Error parsing DEBUG_GUILDS: {e}")

# Parse owner IDs from environment
owner_ids_str = os.environ.get("OWNER_IDS", "")
if owner_ids_str:
    try:
        owner_ids = [int(owner_id.strip()) for owner_id in owner_ids_str.split(",") if owner_id.strip()]
        config["discord"]["owner_ids"] = owner_ids
    except (ValueError, TypeError) as e:
        logger.error(f"Error parsing OWNER_IDS: {e}")

# Load config from file if it exists
config_file = os.environ.get("CONFIG_FILE", "config.json")
if os.path.exists(config_file):
    try:
        with open(config_file, "r") as f:
            file_config = json.load(f)
        
        # Update config with values from file
        for section, values in file_config.items():
            if section in config:
                if isinstance(config[section], dict) and isinstance(values, dict):
                    config[section].update(values)
                else:
                    config[section] = values
            else:
                config[section] = values
                
        logger.info(f"Loaded configuration from {config_file}")
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading config from {config_file}: {e}")

# Ensure required directories exist
os.makedirs("logs", exist_ok=True)

# Configure logging based on config
log_level_name = config["logging"]["level"]
log_level = getattr(logging, log_level_name.upper(), logging.INFO)

# Export a getter function for cleaner access
def get_config(section: Optional[str] = None, key: Optional[str] = None, default: Any = None) -> Any:
    """
    Get a configuration value with optional fallback
    
    Args:
        section: Configuration section (optional)
        key: Key within the section (optional)
        default: Default value if the requested config doesn't exist
        
    Returns:
        The requested configuration value or default
    """
    if section is None:
        return config
    
    if section not in config:
        return default
    
    if key is None:
        return config[section]
    
    return config[section].get(key, default)