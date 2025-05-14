"""
Safe MongoDB Client

This module provides a safe MongoDB client with error handling and 
automatic reconnection capabilities. It wraps the motor.motor_asyncio 
client to ensure reliable database operations, even in unreliable network conditions.
"""

import os
import logging
import asyncio
import datetime
from typing import Dict, List, Any, Optional, Union, TypeVar, Generic, Mapping, Iterable

# Import pymongo and motor for MongoDB interactions
try:
    import pymongo
    from pymongo.database import Database
    from pymongo.collection import Collection
    from pymongo.results import InsertOneResult, InsertManyResult, UpdateResult, DeleteResult
    from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError
    import motor.motor_asyncio
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
except ImportError as e:
    print(f"Error importing MongoDB libraries: {e}")
    print("Make sure you have installed pymongo and motor.")
    raise

# Configure logger
logger = logging.getLogger("mongodb")

# Result class for database operations
class SafeMongoDBResult:
    """
    Result class for database operations
    
    This class encapsulates the result of a database operation,
    including success status, data, and error information.
    
    Attributes:
        success: Whether the operation was successful
        data: The data returned by the operation (if any)
        error: Error information (if any)
        error_type: Type of error (if any)
        timestamp: When the operation was performed
    """
    
    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None, error_type: Optional[str] = None):
        """
        Initialize the result
        
        Args:
            success: Whether the operation was successful
            data: The data returned by the operation (if any)
            error: Error information (if any)
            error_type: Type of error (if any)
        """
        self.success = success
        self.data = data
        self.error = error
        self.error_type = error_type
        self.timestamp = datetime.datetime.utcnow()
    
    def __bool__(self) -> bool:
        """Boolean conversion for the result"""
        return self.success
    
    def __str__(self) -> str:
        """String representation for the result"""
        if self.success:
            return f"Success: {self.data}"
        else:
            return f"Error ({self.error_type}): {self.error}"
    
    @classmethod
    def success_result(cls, data: Any = None) -> 'SafeMongoDBResult':
        """
        Create a success result
        
        Args:
            data: The data to include in the result
            
        Returns:
            Success result
        """
        return cls(True, data=data)
    
    @classmethod
    def error_result(cls, error: str, error_type: Optional[str] = None, data: Any = None) -> 'SafeMongoDBResult':
        """
        Create an error result
        
        Args:
            error: Error message
            error_type: Type of error
            data: Any data to include
            
        Returns:
            Error result
        """
        return cls(False, data=data, error=error, error_type=error_type)

# Type variable for database operations
T = TypeVar('T')

class SafeMongoDBClient(Generic[T]):
    """
    Safe MongoDB client with error handling and reconnection
    
    This class wraps the MongoDB client to provide error handling,
    automatic reconnection, and other safety features.
    
    Attributes:
        uri: MongoDB connection URI
        db_name: Name of the database
        client: Motor AsyncIO MongoDB client
        database: AsyncIO Motor database
    """
    
    def __init__(self, uri: str, db_name: str):
        """
        Initialize the client
        
        Args:
            uri: MongoDB connection URI
            db_name: Name of the database
        """
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self._database = None
        self._connected = False
        self._max_reconnect_attempts = 3
        self._reconnect_delay = 2  # seconds
    
    @property
    def database(self) -> AsyncIOMotorDatabase:
        """
        Get the database instance
        
        Returns:
            AsyncIO Motor database
        
        Raises:
            RuntimeError: If not connected to the database
        """
        if not self._database:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        
        return self._database
    
    async def connect(self) -> SafeMongoDBResult:
        """
        Connect to MongoDB
        
        Returns:
            Result of the connection attempt
        """
        try:
            logger.info(f"Connecting to MongoDB: {self.db_name}")
            
            # Create the client
            self.client = AsyncIOMotorClient(
                self.uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                maxPoolSize=10
            )
            
            # Get the database
            self._database = self.client[self.db_name]
            
            # Verify the connection by listing collections
            await self._database.list_collection_names()
            
            self._connected = True
            logger.info(f"Connected to MongoDB: {self.db_name}")
            
            return SafeMongoDBResult.success_result()
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type="ConnectionFailure"
            )
        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB server selection timeout: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type="ServerSelectionTimeoutError"
            )
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
    
    async def close(self) -> None:
        """Close the connection"""
        if self.client:
            self.client.close()
            self._connected = False
            self._database = None
            logger.info("Closed MongoDB connection")
    
    async def _ensure_connected(self) -> SafeMongoDBResult:
        """
        Ensure the client is connected and reconnect if necessary
        
        Returns:
            Result of the connection check
        """
        if self._connected and self.client and self._database:
            return SafeMongoDBResult.success_result()
        
        for attempt in range(self._max_reconnect_attempts):
            result = await self.connect()
            if result.success:
                return result
            
            if attempt < self._max_reconnect_attempts - 1:
                logger.info(f"Reconnection attempt {attempt + 1} failed, retrying in {self._reconnect_delay} seconds...")
                await asyncio.sleep(self._reconnect_delay)
        
        return SafeMongoDBResult.error_result(
            "Failed to reconnect to MongoDB after multiple attempts",
            error_type="ReconnectionFailure"
        )
    
    async def get_collection(self, collection_name: str) -> SafeMongoDBResult[Collection]:
        """
        Get a collection safely
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Result with the collection or error
        """
        # Ensure connected
        connect_result = await self._ensure_connected()
        if not connect_result.success:
            return connect_result
        
        try:
            collection = self._database[collection_name]
            return SafeMongoDBResult.success_result(collection)
        except Exception as e:
            logger.error(f"Error getting collection {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
    
    async def insert_one(self, collection_name: str, document: Dict[str, Any]) -> SafeMongoDBResult[InsertOneResult]:
        """
        Insert a document safely
        
        Args:
            collection_name: Name of the collection
            document: Document to insert
            
        Returns:
            Result with the insert result or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            result = await collection.insert_one(document)
            return SafeMongoDBResult.success_result(result)
        except PyMongoError as e:
            logger.error(f"Error inserting document into {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data=document
            )
        except Exception as e:
            logger.error(f"Unexpected error inserting document: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data=document
            )
    
    async def insert_many(self, collection_name: str, documents: List[Dict[str, Any]]) -> SafeMongoDBResult[InsertManyResult]:
        """
        Insert multiple documents safely
        
        Args:
            collection_name: Name of the collection
            documents: Documents to insert
            
        Returns:
            Result with the insert result or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            result = await collection.insert_many(documents)
            return SafeMongoDBResult.success_result(result)
        except PyMongoError as e:
            logger.error(f"Error inserting multiple documents into {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data=documents
            )
        except Exception as e:
            logger.error(f"Unexpected error inserting multiple documents: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data=documents
            )
    
    async def find_one(self, collection_name: str, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None) -> SafeMongoDBResult[Optional[Dict[str, Any]]]:
        """
        Find a single document safely
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            projection: Projection to apply
            
        Returns:
            Result with the found document or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            result = await collection.find_one(query, projection)
            return SafeMongoDBResult.success_result(result)
        except PyMongoError as e:
            logger.error(f"Error finding document in {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
        except Exception as e:
            logger.error(f"Unexpected error finding document: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
    
    async def find_many(self, collection_name: str, query: Dict[str, Any], 
                        projection: Optional[Dict[str, Any]] = None,
                        sort: Optional[List[tuple]] = None,
                        limit: Optional[int] = None,
                        skip: Optional[int] = None) -> SafeMongoDBResult[List[Dict[str, Any]]]:
        """
        Find multiple documents safely
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            projection: Projection to apply
            sort: Sort specification
            limit: Maximum number of documents to return
            skip: Number of documents to skip
            
        Returns:
            Result with the found documents or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            cursor = collection.find(query, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            
            if skip:
                cursor = cursor.skip(skip)
                
            if limit:
                cursor = cursor.limit(limit)
            
            documents = await cursor.to_list(length=None)
            return SafeMongoDBResult.success_result(documents)
        except PyMongoError as e:
            logger.error(f"Error finding documents in {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
        except Exception as e:
            logger.error(f"Unexpected error finding documents: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
    
    async def update_one(self, collection_name: str, query: Dict[str, Any], 
                        update: Dict[str, Any],
                        upsert: bool = False) -> SafeMongoDBResult[UpdateResult]:
        """
        Update a single document safely
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            update: Update specification
            upsert: Whether to insert a new document if no match is found
            
        Returns:
            Result with the update result or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            result = await collection.update_one(query, update, upsert=upsert)
            return SafeMongoDBResult.success_result(result)
        except PyMongoError as e:
            logger.error(f"Error updating document in {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data={"query": query, "update": update}
            )
        except Exception as e:
            logger.error(f"Unexpected error updating document: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data={"query": query, "update": update}
            )
    
    async def update_many(self, collection_name: str, query: Dict[str, Any], 
                         update: Dict[str, Any],
                         upsert: bool = False) -> SafeMongoDBResult[UpdateResult]:
        """
        Update multiple documents safely
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            update: Update specification
            upsert: Whether to insert a new document if no match is found
            
        Returns:
            Result with the update result or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            result = await collection.update_many(query, update, upsert=upsert)
            return SafeMongoDBResult.success_result(result)
        except PyMongoError as e:
            logger.error(f"Error updating multiple documents in {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data={"query": query, "update": update}
            )
        except Exception as e:
            logger.error(f"Unexpected error updating multiple documents: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data={"query": query, "update": update}
            )
    
    async def delete_one(self, collection_name: str, query: Dict[str, Any]) -> SafeMongoDBResult[DeleteResult]:
        """
        Delete a single document safely
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            
        Returns:
            Result with the delete result or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            result = await collection.delete_one(query)
            return SafeMongoDBResult.success_result(result)
        except PyMongoError as e:
            logger.error(f"Error deleting document from {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data=query
            )
        except Exception as e:
            logger.error(f"Unexpected error deleting document: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data=query
            )
    
    async def delete_many(self, collection_name: str, query: Dict[str, Any]) -> SafeMongoDBResult[DeleteResult]:
        """
        Delete multiple documents safely
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            
        Returns:
            Result with the delete result or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            result = await collection.delete_many(query)
            return SafeMongoDBResult.success_result(result)
        except PyMongoError as e:
            logger.error(f"Error deleting multiple documents from {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data=query
            )
        except Exception as e:
            logger.error(f"Unexpected error deleting multiple documents: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__,
                data=query
            )
    
    async def count_documents(self, collection_name: str, query: Dict[str, Any]) -> SafeMongoDBResult[int]:
        """
        Count documents safely
        
        Args:
            collection_name: Name of the collection
            query: Query filter
            
        Returns:
            Result with the count or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            count = await collection.count_documents(query)
            return SafeMongoDBResult.success_result(count)
        except PyMongoError as e:
            logger.error(f"Error counting documents in {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
        except Exception as e:
            logger.error(f"Unexpected error counting documents: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
    
    async def collection_exists(self, collection_name: str) -> SafeMongoDBResult[bool]:
        """
        Check if a collection exists safely
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Result with true/false or error
        """
        # Ensure connected
        connect_result = await self._ensure_connected()
        if not connect_result.success:
            return connect_result
        
        try:
            collections = await self._database.list_collection_names()
            exists = collection_name in collections
            return SafeMongoDBResult.success_result(exists)
        except PyMongoError as e:
            logger.error(f"Error checking if collection {collection_name} exists: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
        except Exception as e:
            logger.error(f"Unexpected error checking if collection exists: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
    
    async def aggregate(self, collection_name: str, pipeline: List[Dict[str, Any]]) -> SafeMongoDBResult[List[Dict[str, Any]]]:
        """
        Run an aggregation pipeline safely
        
        Args:
            collection_name: Name of the collection
            pipeline: Aggregation pipeline
            
        Returns:
            Result with the aggregation results or error
        """
        # Get the collection
        collection_result = await self.get_collection(collection_name)
        if not collection_result.success:
            return collection_result
        
        collection = collection_result.data
        
        try:
            cursor = collection.aggregate(pipeline)
            documents = await cursor.to_list(length=None)
            return SafeMongoDBResult.success_result(documents)
        except PyMongoError as e:
            logger.error(f"Error running aggregation pipeline on {collection_name}: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )
        except Exception as e:
            logger.error(f"Unexpected error running aggregation pipeline: {e}")
            return SafeMongoDBResult.error_result(
                str(e),
                error_type=type(e).__name__
            )