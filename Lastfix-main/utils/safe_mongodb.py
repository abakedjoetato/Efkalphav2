"""
Safe MongoDB Operations Module

This module provides classes and utilities for safely interacting with MongoDB,
with proper error handling and type safety.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

T = TypeVar('T')

class SafeMongoDBResult(Generic[T]):
    """
    Wrapper for MongoDB operation results with error handling.
    
    This class encapsulates the result of MongoDB operations, including
    success/failure information, error details, and the result data.
    
    Attributes:
        success: Whether the operation was successful
        result: The result data (if successful)
        error: Error message (if unsuccessful)
        collection_name: Name of the collection involved in the operation
    """
    
    def __init__(
        self, 
        success: bool = False, 
        result: Optional[T] = None, 
        error: Optional[str] = None, 
        collection_name: Optional[str] = None
    ):
        """
        Initialize a SafeMongoDBResult.
        
        Args:
            success: Whether the operation was successful
            result: The result data (if successful)
            error: Error message (if unsuccessful)
            collection_name: Name of the collection involved in the operation
        """
        self.success = success
        self.result = result
        self.error = error
        self.collection_name = collection_name

class SafeDocument(Dict[str, Any]):
    """
    Safe wrapper for MongoDB documents with additional helper methods.
    
    This class provides a safer way to access document fields with
    proper error handling and default values.
    """
    
    def __init__(self, document: Optional[Dict[str, Any]] = None):
        """
        Initialize a SafeDocument.
        
        Args:
            document: The MongoDB document to wrap
        """
        super().__init__()
        if document:
            self.update(document)
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the document with a default.
        
        Args:
            key: The key to look up
            default: Default value if the key is not found
            
        Returns:
            The value at the key or the default
        """
        return super().get(key, default)
        
    def get_string(self, key: str, default: str = "") -> str:
        """
        Get a string value from the document with a default.
        
        Args:
            key: The key to look up
            default: Default value if the key is not found or not a string
            
        Returns:
            The string value at the key or the default
        """
        value = self.get(key, default)
        if not isinstance(value, str):
            return default
        return value
        
    def get_int(self, key: str, default: int = 0) -> int:
        """
        Get an integer value from the document with a default.
        
        Args:
            key: The key to look up
            default: Default value if the key is not found or not an integer
            
        Returns:
            The integer value at the key or the default
        """
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
            
    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean value from the document with a default.
        
        Args:
            key: The key to look up
            default: Default value if the key is not found or not a boolean
            
        Returns:
            The boolean value at the key or the default
        """
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("yes", "true", "t", "1")
        if isinstance(value, int):
            return value != 0
        return default


# Global MongoDB database instance
_db = None

def set_database(db):
    """
    Set the global MongoDB database instance.
    
    Args:
        db: The MongoDB database instance to use
    """
    global _db
    _db = db
    
def get_database():
    """
    Get the global MongoDB database instance.
    
    Returns:
        The MongoDB database instance or None if not set
    """
    return _db

def is_db_available(db=None):
    """
    Check if the database appears to be available.
    
    Args:
        db: The database instance to check, or None to use the global instance
        
    Returns:
        bool: True if the database appears to be available, False otherwise
    """
    try:
        db_to_check = db if db is not None else _db
        return db_to_check is not None
    except Exception:
        return False