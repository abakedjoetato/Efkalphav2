"""
Error Telemetry Module

This module provides error tracking and reporting capabilities for the bot.
It logs errors, collects context, and can send error reports.
"""

import os
import sys
import time
import json
import logging
import asyncio
import datetime
import traceback
from typing import Dict, List, Any, Optional, Union, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("error_telemetry.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ErrorTelemetry:
    """
    Error tracking and reporting system.
    
    This class provides methods to track, log, and report errors
    that occur during the bot's operation.
    """
    
    _instance = None
    
    def __init__(self, bot=None, db=None):
        """
        Initialize the error telemetry system.
        
        Args:
            bot: Bot instance (optional)
            db: Database adapter (optional)
        """
        self.bot = bot
        self.db = db
        self.error_log = []
        self.error_counts = {}
        self.max_errors = 1000  # Maximum number of errors to store in memory
        self.error_log_file = "errors.log"
        logger.info("Error telemetry initialized")
    
    def _format_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                     command: Optional[str] = None) -> Dict[str, Any]:
        """
        Format an error with context information.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            command: Command that caused the error (if applicable)
            
        Returns:
            Dict containing error information
        """
        # Get traceback information
        tb = traceback.extract_tb(error.__traceback__)
        
        # Format traceback
        formatted_tb = []
        for frame in tb:
            formatted_tb.append({
                "filename": frame.filename,
                "lineno": frame.lineno,
                "name": frame.name,
                "line": frame.line
            })
        
        # Create error entry
        error_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "traceback": formatted_tb,
            "context": context or {},
            "command": command
        }
        
        return error_entry
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                 command: Optional[str] = None) -> bool:
        """
        Log an error with context information.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            command: Command that caused the error (if applicable)
            
        Returns:
            bool: True if error was logged successfully, False otherwise
        """
        try:
            # Format error
            error_entry = self._format_error(error, context, command)
            
            # Add to in-memory log
            self.error_log.append(error_entry)
            
            # Trim log if it gets too large
            if len(self.error_log) > self.max_errors:
                self.error_log = self.error_log[-self.max_errors:]
            
            # Update error counts
            error_type = error.__class__.__name__
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            # Log to file
            with open(self.error_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_entry) + "\n")
            
            # Log to database if available
            if self.db:
                asyncio.create_task(self._log_to_database(error_entry))
            
            logger.info(f"Logged error: {error_type}: {str(error)}")
            return True
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
            return False
    
    async def _log_to_database(self, error_entry: Dict[str, Any]) -> bool:
        """
        Log error to database.
        
        Args:
            error_entry: Formatted error information
            
        Returns:
            bool: True if error was logged to database successfully, False otherwise
        """
        try:
            if not self.db:
                logger.warning("No database available for error logging")
                return False
            
            # Insert error into database
            collection = await self.db.get_collection("errors")
            if collection:
                await collection.insert_one(error_entry)
                logger.info(f"Logged error to database: {error_entry['error_type']}")
                return True
            else:
                logger.warning("Failed to get errors collection")
                return False
        except Exception as e:
            logger.error(f"Failed to log error to database: {e}")
            return False
    
    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get error statistics.
        
        Returns:
            Dict containing error statistics
        """
        return {
            "total_errors": len(self.error_log),
            "error_types": self.error_counts,
            "recent_errors": self.error_log[-10:] if self.error_log else []
        }
    
    def clear_errors(self) -> bool:
        """
        Clear error log.
        
        Returns:
            bool: True if errors were cleared successfully, False otherwise
        """
        try:
            self.error_log = []
            self.error_counts = {}
            logger.info("Error log cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear error log: {e}")
            return False

# Singleton instance
_error_telemetry_instance = None

def get_error_telemetry(bot=None, db=None):
    """
    Get the global error telemetry instance.
    
    Args:
        bot: Bot instance (optional)
        db: Database adapter (optional)
        
    Returns:
        ErrorTelemetry: Global error telemetry instance
    """
    global _error_telemetry_instance
    
    if _error_telemetry_instance is None:
        _error_telemetry_instance = ErrorTelemetry(bot, db)
    elif bot and _error_telemetry_instance.bot is None:
        _error_telemetry_instance.bot = bot
    elif db and _error_telemetry_instance.db is None:
        _error_telemetry_instance.db = db
    
    return _error_telemetry_instance