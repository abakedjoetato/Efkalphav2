"""
Safe MongoDB Compatibility Layer

This module provides a safe interface for MongoDB operations with proper error
handling and type checking. It ensures that all database operations are wrapped
in appropriate error handling and return consistent result objects.

Key features:
1. Unified error handling across all MongoDB operations
2. Type-safe result objects
3. Consistent API for different MongoDB operations
4. Support for retries and timeouts
5. Thread-safe connection handling with SafeMongoDBConnection
"""

import logging
import asyncio
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union, cast

# Import MongoDB modules carefully to handle different versions
try:
    import pymongo
    import motor.motor_asyncio
    from pymongo.errors import PyMongoError, ConnectionFailure, NetworkTimeout, WTimeoutError
    HAS_MONGODB = True
except ImportError:
    HAS_MONGODB = False
    # Create placeholder error types for type checking
    class PyMongoError(Exception): pass
    class ConnectionFailure(PyMongoError): pass
    class NetworkTimeout(PyMongoError): pass
    class WTimeoutError(PyMongoError): pass

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for generic typing
T = TypeVar('T')

# Global MongoDB client and database
_mongo_client = None
_mongo_db = None

# Default collection names
DEFAULT_CONFIG_COLLECTION = "bot_config"
DEFAULT_USER_COLLECTION = "users"
DEFAULT_GUILD_COLLECTION = "guilds"
DEFAULT_ECONOMY_COLLECTION = "economy"
DEFAULT_PREMIUM_COLLECTION = "premium"


class MongoDBErrorType(Enum):
    """Enum for categorizing MongoDB error types."""
    CONNECTION = "connection"
    TIMEOUT = "timeout"
    AUTHORIZATION = "authorization"
    INVALID_OPERATION = "invalid_operation"
    DOCUMENT_VALIDATION = "document_validation"
    DATA_CORRUPTION = "data_corruption"
    UNKNOWN = "unknown"


class SafeMongoDBResult(Generic[T]):
    """
    Type-safe result class for MongoDB operations.
    
    This class encapsulates the result of a MongoDB operation, including
    success/failure status, data, and error information.
    
    Attributes:
        success: Whether the operation was successful
        data: The result data if successful (typed as T)
        error: Error message if not successful
        error_type: Type of error if not successful
        exception: Original exception if an error occurred
    """
    
    def __init__(
        self,
        success: bool,
        data: Optional[T] = None,
        error: Optional[str] = None,
        error_type: Optional[MongoDBErrorType] = None,
        exception: Optional[Exception] = None
    ):
        """
        Initialize a MongoDB result.
        
        Args:
            success: Whether the operation was successful
            data: The result data if successful
            error: Error message if not successful
            error_type: Type of error if not successful
            exception: Original exception if an error occurred
        """
        self.success = success
        self.data = data
        self.error = error
        self.error_type = error_type or MongoDBErrorType.UNKNOWN
        self.exception = exception
    
    def __str__(self) -> str:
        """Get string representation of the result."""
        if self.success:
            return f"Success: {self.data}"
        return f"Error ({self.error_type.value}): {self.error}"
    
    def __bool__(self) -> bool:
        """Boolean evaluation of the result (success/failure)."""
        return self.success
    
    # Class methods to create results (for backward compatibility with code that uses class methods)
    @classmethod
    def success_result(cls, data: T) -> 'SafeMongoDBResult[T]':
        """Create a successful result."""
        return cls(success=True, data=data)
    
    @classmethod
    def error_result(cls, error: str, error_type: MongoDBErrorType = MongoDBErrorType.UNKNOWN, 
                   exception: Optional[Exception] = None) -> 'SafeMongoDBResult[Any]':
        """Create an error result."""
        return cls(success=False, error=error, error_type=error_type, exception=exception)


# Function versions of result creators (preferred method)
def success_result(data: T) -> SafeMongoDBResult[T]:
    """
    Create a successful result.
    
    Args:
        data: The result data
        
    Returns:
        SafeMongoDBResult with success=True
    """
    return SafeMongoDBResult(success=True, data=data)


def error_result(
    error: str,
    error_type: MongoDBErrorType = MongoDBErrorType.UNKNOWN,
    exception: Optional[Exception] = None
) -> SafeMongoDBResult[Any]:
    """
    Create an error result.
    
    Args:
        error: Error message
        error_type: Type of error
        exception: Original exception
        
    Returns:
        SafeMongoDBResult with success=False
    """
    return SafeMongoDBResult(
        success=False,
        error=error,
        error_type=error_type,
        exception=exception
    )


async def init_mongodb(
    connection_string: str,
    db_name: str,
    max_pool_size: int = 10
) -> SafeMongoDBResult[bool]:
    """
    Initialize MongoDB connection with error handling.
    
    Args:
        connection_string: MongoDB connection string
        db_name: Database name
        max_pool_size: Maximum connection pool size
        
    Returns:
        SafeMongoDBResult indicating success or failure
    """
    global _mongo_client, _mongo_db
    
    # Check if MongoDB modules are available
    if not HAS_MONGODB:
        return error_result(
            "MongoDB modules (pymongo/motor) are not installed",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        # Create the MongoDB client
        _mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            connection_string,
            maxPoolSize=max_pool_size,
            serverSelectionTimeoutMS=5000,  # 5 seconds timeout
            connectTimeoutMS=5000,
            socketTimeoutMS=30000  # 30 seconds for operations
        )
        
        # Simple ping to verify that the server is running
        await _mongo_client.admin.command('ping')
        
        # Set the database
        _mongo_db = _mongo_client[db_name]
        
        logger.info(f"Connected to MongoDB database '{db_name}'")
        return success_result(True)
    
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failure: {e}", exc_info=True)
        return error_result(
            f"Failed to connect to MongoDB: {str(e)}",
            MongoDBErrorType.CONNECTION,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error: {e}", exc_info=True)
        return error_result(
            f"MongoDB error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error initializing MongoDB: {e}", exc_info=True)
        return error_result(
            f"Unexpected error initializing MongoDB: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


class SafeMongoDBConnection:
    """Thread-safe MongoDB connection wrapper with error handling"""
    
    def __init__(self, uri=None, db_name=None, client=None, database=None):
        """
        Initialize a safe MongoDB connection.
        
        Args:
            uri: MongoDB connection URI
            db_name: Database name
            client: Existing MongoDB client
            database: Existing MongoDB database
        """
        self.logger = logging.getLogger("mongodb.safe")
        self.uri = uri
        self.db_name = db_name
        self._client = client
        self._db = database
        self._initialized = False
        self._lock = asyncio.Lock()
        
    async def init_db(self, max_retries=3, retry_delay=2):
        """
        Initialize the database connection with error handling.
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Seconds to wait between retries
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        if self._initialized:
            return True
            
        async with self._lock:
            if self._initialized:
                return True
                
            retries = 0
            while retries < max_retries:
                try:
                    if self._client is None and self.uri:
                        import motor.motor_asyncio
                        self._client = motor.motor_asyncio.AsyncIOMotorClient(self.uri)
                        
                    if self._db is None and self.db_name and self._client:
                        self._db = self._client[self.db_name]
                        
                    if self._db is None:
                        raise RuntimeError("Database not initialized - no URI or database name provided")
                        
                    # Test connection
                    await self._db.command("ping")
                    
                    self._initialized = True
                    self.logger.info("Successfully connected to MongoDB")
                    return True
                    
                except Exception as e:
                    retries += 1
                    self.logger.error(f"MongoDB connection error (attempt {retries}/{max_retries}): {e}")
                    
                    if retries < max_retries:
                        await asyncio.sleep(retry_delay)
                    else:
                        self.logger.error("Failed to connect to MongoDB after multiple attempts")
                        return False
                        
    async def get_collection(self, collection_name):
        """
        Get a collection with connection validation.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection or None if not initialized
        """
        if not self._initialized:
            if not await self.init_db():
                return None
                
        return self._db[collection_name]
        
    async def execute_operation(self, operation_func, *args, **kwargs):
        """
        Execute a database operation with error handling.
        
        Args:
            operation_func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            SafeMongoDBResult with the operation result
        """
        if not self._initialized:
            if not await self.init_db():
                return error_result("Database not initialized")
                
        try:
            result = await operation_func(*args, **kwargs)
            return success_result(result)
        except Exception as e:
            self.logger.error(f"Database operation error: {e}")
            return error_result(str(e))
            
    def close(self):
        """Close the database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._initialized = False
            self.logger.info("Closed MongoDB connection")


def close_mongodb() -> None:
    """Close MongoDB connection."""
    global _mongo_client, _mongo_db
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        logger.info("Closed MongoDB connection")


def get_db():
    """
    Get the MongoDB database instance.
    
    Returns:
        MongoDB database instance or None if not initialized
    """
    return _mongo_db


def get_collection(collection_name: str):
    """
    Get a MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        MongoDB collection or None if not initialized
    """
    if _mongo_db:
        return _mongo_db[collection_name]
    return None


async def find_one(
    collection_name: str,
    filter: Dict[str, Any],
    **kwargs
) -> SafeMongoDBResult[Optional[Dict[str, Any]]]:
    """
    Find a single document in a collection.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        **kwargs: Additional arguments for find_one
        
    Returns:
        SafeMongoDBResult with the found document or error
    """
    collection = get_collection(collection_name)
    if not collection:
        return error_result(
            f"MongoDB not initialized or collection '{collection_name}' not found",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        doc = await collection.find_one(filter, **kwargs)
        return success_result(doc)
    
    except NetworkTimeout as e:
        logger.error(f"MongoDB timeout in find_one: {e}", exc_info=True)
        return error_result(
            f"Database operation timed out: {str(e)}",
            MongoDBErrorType.TIMEOUT,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error in find_one: {e}", exc_info=True)
        return error_result(
            f"Database error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error in find_one: {e}", exc_info=True)
        return error_result(
            f"Unexpected error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


async def find(
    collection_name: str,
    filter: Dict[str, Any],
    **kwargs
) -> SafeMongoDBResult[List[Dict[str, Any]]]:
    """
    Find documents in a collection.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        **kwargs: Additional arguments for find
        
    Returns:
        SafeMongoDBResult with the found documents or error
    """
    collection = get_collection(collection_name)
    if not collection:
        return error_result(
            f"MongoDB not initialized or collection '{collection_name}' not found",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        cursor = collection.find(filter, **kwargs)
        result = await cursor.to_list(length=None)
        return success_result(result)
    
    except NetworkTimeout as e:
        logger.error(f"MongoDB timeout in find: {e}", exc_info=True)
        return error_result(
            f"Database operation timed out: {str(e)}",
            MongoDBErrorType.TIMEOUT,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error in find: {e}", exc_info=True)
        return error_result(
            f"Database error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error in find: {e}", exc_info=True)
        return error_result(
            f"Unexpected error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


async def insert_one(
    collection_name: str,
    document: Dict[str, Any],
    **kwargs
) -> SafeMongoDBResult[Any]:
    """
    Insert a document into a collection.
    
    Args:
        collection_name: Name of the collection
        document: Document to insert
        **kwargs: Additional arguments for insert_one
        
    Returns:
        SafeMongoDBResult with the inserted ID or error
    """
    collection = get_collection(collection_name)
    if not collection:
        return error_result(
            f"MongoDB not initialized or collection '{collection_name}' not found",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        result = await collection.insert_one(document, **kwargs)
        return success_result(result.inserted_id)
    
    except NetworkTimeout as e:
        logger.error(f"MongoDB timeout in insert_one: {e}", exc_info=True)
        return error_result(
            f"Database operation timed out: {str(e)}",
            MongoDBErrorType.TIMEOUT,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error in insert_one: {e}", exc_info=True)
        return error_result(
            f"Database error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error in insert_one: {e}", exc_info=True)
        return error_result(
            f"Unexpected error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


async def update_one(
    collection_name: str,
    filter: Dict[str, Any],
    update: Dict[str, Any],
    **kwargs
) -> SafeMongoDBResult[Dict[str, Any]]:
    """
    Update a document in a collection.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        update: Update to apply
        **kwargs: Additional arguments for update_one
        
    Returns:
        SafeMongoDBResult with the update result or error
    """
    collection = get_collection(collection_name)
    if not collection:
        return error_result(
            f"MongoDB not initialized or collection '{collection_name}' not found",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        result = await collection.update_one(filter, update, **kwargs)
        return success_result({
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": result.upserted_id
        })
    
    except NetworkTimeout as e:
        logger.error(f"MongoDB timeout in update_one: {e}", exc_info=True)
        return error_result(
            f"Database operation timed out: {str(e)}",
            MongoDBErrorType.TIMEOUT,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error in update_one: {e}", exc_info=True)
        return error_result(
            f"Database error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error in update_one: {e}", exc_info=True)
        return error_result(
            f"Unexpected error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


async def update_many(
    collection_name: str,
    filter: Dict[str, Any],
    update: Dict[str, Any],
    **kwargs
) -> SafeMongoDBResult[Dict[str, Any]]:
    """
    Update multiple documents in a collection.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        update: Update to apply
        **kwargs: Additional arguments for update_many
        
    Returns:
        SafeMongoDBResult with the update result or error
    """
    collection = get_collection(collection_name)
    if not collection:
        return error_result(
            f"MongoDB not initialized or collection '{collection_name}' not found",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        result = await collection.update_many(filter, update, **kwargs)
        return success_result({
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": result.upserted_id
        })
    
    except NetworkTimeout as e:
        logger.error(f"MongoDB timeout in update_many: {e}", exc_info=True)
        return error_result(
            f"Database operation timed out: {str(e)}",
            MongoDBErrorType.TIMEOUT,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error in update_many: {e}", exc_info=True)
        return error_result(
            f"Database error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error in update_many: {e}", exc_info=True)
        return error_result(
            f"Unexpected error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


async def delete_one(
    collection_name: str,
    filter: Dict[str, Any],
    **kwargs
) -> SafeMongoDBResult[int]:
    """
    Delete a document from a collection.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        **kwargs: Additional arguments for delete_one
        
    Returns:
        SafeMongoDBResult with the number of deleted documents or error
    """
    collection = get_collection(collection_name)
    if not collection:
        return error_result(
            f"MongoDB not initialized or collection '{collection_name}' not found",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        result = await collection.delete_one(filter, **kwargs)
        return success_result(result.deleted_count)
    
    except NetworkTimeout as e:
        logger.error(f"MongoDB timeout in delete_one: {e}", exc_info=True)
        return error_result(
            f"Database operation timed out: {str(e)}",
            MongoDBErrorType.TIMEOUT,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error in delete_one: {e}", exc_info=True)
        return error_result(
            f"Database error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error in delete_one: {e}", exc_info=True)
        return error_result(
            f"Unexpected error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


async def delete_many(
    collection_name: str,
    filter: Dict[str, Any],
    **kwargs
) -> SafeMongoDBResult[int]:
    """
    Delete multiple documents from a collection.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        **kwargs: Additional arguments for delete_many
        
    Returns:
        SafeMongoDBResult with the number of deleted documents or error
    """
    collection = get_collection(collection_name)
    if not collection:
        return error_result(
            f"MongoDB not initialized or collection '{collection_name}' not found",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        result = await collection.delete_many(filter, **kwargs)
        return success_result(result.deleted_count)
    
    except NetworkTimeout as e:
        logger.error(f"MongoDB timeout in delete_many: {e}", exc_info=True)
        return error_result(
            f"Database operation timed out: {str(e)}",
            MongoDBErrorType.TIMEOUT,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error in delete_many: {e}", exc_info=True)
        return error_result(
            f"Database error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error in delete_many: {e}", exc_info=True)
        return error_result(
            f"Unexpected error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


async def count_documents(
    collection_name: str,
    filter: Optional[Dict[str, Any]] = None,
    **kwargs
) -> SafeMongoDBResult[int]:
    """
    Count documents in a collection.
    
    Args:
        collection_name: Name of the collection
        filter: Filter to apply
        **kwargs: Additional arguments for count_documents
        
    Returns:
        SafeMongoDBResult with the count or error
    """
    collection = get_collection(collection_name)
    if not collection:
        return error_result(
            f"MongoDB not initialized or collection '{collection_name}' not found",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        if filter is None:
            filter = {}
        count = await collection.count_documents(filter, **kwargs)
        return success_result(count)
    
    except NetworkTimeout as e:
        logger.error(f"MongoDB timeout in count_documents: {e}", exc_info=True)
        return error_result(
            f"Database operation timed out: {str(e)}",
            MongoDBErrorType.TIMEOUT,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error in count_documents: {e}", exc_info=True)
        return error_result(
            f"Database error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error in count_documents: {e}", exc_info=True)
        return error_result(
            f"Unexpected error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


async def aggregate(
    collection_name: str,
    pipeline: List[Dict[str, Any]],
    **kwargs
) -> SafeMongoDBResult[List[Dict[str, Any]]]:
    """
    Perform an aggregation pipeline on a collection.
    
    Args:
        collection_name: Name of the collection
        pipeline: Aggregation pipeline
        **kwargs: Additional arguments for aggregate
        
    Returns:
        SafeMongoDBResult with the aggregation result or error
    """
    collection = get_collection(collection_name)
    if not collection:
        return error_result(
            f"MongoDB not initialized or collection '{collection_name}' not found",
            MongoDBErrorType.CONNECTION
        )
    
    try:
        cursor = collection.aggregate(pipeline, **kwargs)
        result = await cursor.to_list(length=None)
        return success_result(result)
    
    except NetworkTimeout as e:
        logger.error(f"MongoDB timeout in aggregate: {e}", exc_info=True)
        return error_result(
            f"Database operation timed out: {str(e)}",
            MongoDBErrorType.TIMEOUT,
            e
        )
    except PyMongoError as e:
        logger.error(f"MongoDB error in aggregate: {e}", exc_info=True)
        return error_result(
            f"Database error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )
    except Exception as e:
        logger.error(f"Unexpected error in aggregate: {e}", exc_info=True)
        return error_result(
            f"Unexpected error: {str(e)}",
            MongoDBErrorType.UNKNOWN,
            e
        )


# Retry decorator for database operations
def with_retry(max_retries: int = 3, retry_delay: float = 1.0):
    """
    Decorator to retry a MongoDB operation a specified number of times.
    
    Args:
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                result = await func(*args, **kwargs)
                
                # If successful or not a connection/timeout error, return immediately
                if result.success or (
                    result.error_type != MongoDBErrorType.CONNECTION and
                    result.error_type != MongoDBErrorType.TIMEOUT
                ):
                    return result
                
                # If we've reached max retries, return the last error result
                if retries >= max_retries:
                    return result
                
                # Exponential backoff
                wait_time = retry_delay * (2 ** retries)
                logger.warning(
                    f"Retrying MongoDB operation after {wait_time:.2f}s "
                    f"(retry {retries+1}/{max_retries})"
                )
                await asyncio.sleep(wait_time)
                retries += 1
                
        return wrapper
    return decorator