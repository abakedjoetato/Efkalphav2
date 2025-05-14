"""
MongoDB Adapter Module

This module provides a robust interface for interacting with MongoDB,
with enhanced error handling and connection management.
"""

import os
import re
import json
import logging
import asyncio
import datetime
from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Generic

# Use motor for async MongoDB operations
import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("mongodb_adapter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Type variable for database operations
T = TypeVar('T')

class MongoDBAdapter:
    """
    Enhanced MongoDB adapter with improved error handling and connection management.
    
    This class provides a robust interface for interacting with MongoDB,
    handling connection issues, retries, and providing detailed error reporting.
    """
    
    _instance = None
    
    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        """
        Initialize the MongoDB adapter.
        
        Args:
            uri: MongoDB connection URI (default: from MONGODB_URI env var)
            db_name: Database name (default: from URI or 'discord_bot')
        """
        # Get URI from environment variable if not provided
        self.uri = uri or os.environ.get('MONGODB_URI')
        
        # Extract database name from URI if not provided
        if not db_name and self.uri:
            db_match = re.search(r'/([^/?]+)(\?|$)', self.uri)
            self.db_name = db_match.group(1) if db_match else 'discord_bot'
        else:
            self.db_name = db_name or 'discord_bot'
        
        # Initialize connections as None
        self.client = None
        self.db = None
        
        # Connection state
        self.connected = False
        self.connection_attempts = 0
        self.last_connection_attempt = None
        self.max_retries = 5
        self.retry_delay = 5  # seconds
        
        logger.info(f"MongoDB adapter initialized with database '{self.db_name}'")
    
    async def connect(self, max_retries: int = 5, retry_delay: int = 5) -> bool:
        """
        Connect to MongoDB with retries.
        
        Args:
            max_retries: Maximum number of connection attempts (default: 5)
            retry_delay: Seconds to wait between retries (default: 5)
            
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if self.connected and self.client and self.db:
            logger.info("Already connected to MongoDB")
            return True
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        if not self.uri:
            logger.error("MongoDB URI not provided and MONGODB_URI environment variable not set")
            return False
        
        # Sanitize URI for logging
        safe_uri = re.sub(r'mongodb(\+srv)?://[^:]+:[^@]+@', 'mongodb\\1://[username]:[password]@', self.uri)
        logger.info(f"Connecting to MongoDB: {safe_uri}")
        
        self.connection_attempts = 0
        while self.connection_attempts < self.max_retries:
            try:
                self.connection_attempts += 1
                self.last_connection_attempt = datetime.datetime.now()
                
                # Create client
                self.client = AsyncIOMotorClient(self.uri, serverSelectionTimeoutMS=5000)
                
                # Test connection
                await self.client.admin.command('ping')
                
                # Get database
                self.db = self.client[self.db_name]
                
                self.connected = True
                logger.info(f"Connected to MongoDB database '{self.db_name}' (Attempt {self.connection_attempts}/{self.max_retries})")
                return True
            
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB (Attempt {self.connection_attempts}/{self.max_retries}): {e}")
                
                if self.connection_attempts >= self.max_retries:
                    logger.error("Maximum connection attempts reached, giving up")
                    self.connected = False
                    return False
                
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                await asyncio.sleep(self.retry_delay)
    
    async def disconnect(self) -> bool:
        """
        Disconnect from MongoDB.
        
        Returns:
            bool: True if disconnected successfully, False if already disconnected
        """
        if not self.connected or not self.client:
            logger.info("Not connected to MongoDB")
            return False
        
        try:
            self.client.close()
            self.connected = False
            self.client = None
            self.db = None
            logger.info("Disconnected from MongoDB")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from MongoDB: {e}")
            return False
    
    async def get_collection(self, collection_name: str) -> Optional[AsyncIOMotorCollection]:
        """
        Get a collection with connection checks.
        
        Args:
            collection_name: Name of the collection to get
            
        Returns:
            AsyncIOMotorCollection: The collection object, or None if not connected
        """
        if not self.connected or not self.db:
            logger.warning(f"Not connected to MongoDB, attempting to reconnect before accessing collection '{collection_name}'")
            if not await self.connect():
                logger.error(f"Failed to reconnect to MongoDB, cannot access collection '{collection_name}'")
                return None
        
        return self.db[collection_name]
    
    async def find_one(self, collection_name: str, query: Dict[str, Any], 
                      projection: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Find a single document with error handling.
        
        Args:
            collection_name: Name of the collection to query
            query: Query filter
            projection: Fields to include or exclude
            
        Returns:
            Dict: The found document, or None if not found or error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            result = await collection.find_one(query, projection)
            return result
        except Exception as e:
            logger.error(f"Error in find_one operation on '{collection_name}': {e}")
            return None
    
    async def find(self, collection_name: str, query: Dict[str, Any], 
                  projection: Optional[Dict[str, Any]] = None,
                  sort: Optional[List[tuple]] = None, 
                  limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Find multiple documents with error handling.
        
        Args:
            collection_name: Name of the collection to query
            query: Query filter
            projection: Fields to include or exclude
            sort: Sorting parameters (list of (field, direction) tuples)
            limit: Maximum number of documents to return
            
        Returns:
            List[Dict]: List of found documents, or empty list if none found or error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return []
            
            cursor = collection.find(query, projection)
            
            if sort:
                cursor = cursor.sort(sort)
            
            if limit:
                cursor = cursor.limit(limit)
            
            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"Error in find operation on '{collection_name}': {e}")
            return []
    
    async def insert_one(self, collection_name: str, document: Dict[str, Any]) -> Optional[str]:
        """
        Insert a single document with error handling.
        
        Args:
            collection_name: Name of the collection to insert into
            document: Document to insert
            
        Returns:
            str: ID of the inserted document, or None if error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            result = await collection.insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error in insert_one operation on '{collection_name}': {e}")
            return None
    
    async def insert_many(self, collection_name: str, documents: List[Dict[str, Any]]) -> Optional[List[str]]:
        """
        Insert multiple documents with error handling.
        
        Args:
            collection_name: Name of the collection to insert into
            documents: List of documents to insert
            
        Returns:
            List[str]: List of IDs of the inserted documents, or None if error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            result = await collection.insert_many(documents)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            logger.error(f"Error in insert_many operation on '{collection_name}': {e}")
            return None
    
    async def update_one(self, collection_name: str, query: Dict[str, Any], 
                        update: Dict[str, Any], upsert: bool = False) -> Optional[int]:
        """
        Update a single document with error handling.
        
        Args:
            collection_name: Name of the collection to update
            query: Query filter
            update: Update operations
            upsert: Whether to insert if document doesn't exist
            
        Returns:
            int: Number of documents modified, or None if error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            result = await collection.update_one(query, update, upsert=upsert)
            return result.modified_count
        except Exception as e:
            logger.error(f"Error in update_one operation on '{collection_name}': {e}")
            return None
    
    async def update_many(self, collection_name: str, query: Dict[str, Any], 
                         update: Dict[str, Any], upsert: bool = False) -> Optional[int]:
        """
        Update multiple documents with error handling.
        
        Args:
            collection_name: Name of the collection to update
            query: Query filter
            update: Update operations
            upsert: Whether to insert if documents don't exist
            
        Returns:
            int: Number of documents modified, or None if error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            result = await collection.update_many(query, update, upsert=upsert)
            return result.modified_count
        except Exception as e:
            logger.error(f"Error in update_many operation on '{collection_name}': {e}")
            return None
    
    async def delete_one(self, collection_name: str, query: Dict[str, Any]) -> Optional[int]:
        """
        Delete a single document with error handling.
        
        Args:
            collection_name: Name of the collection to delete from
            query: Query filter
            
        Returns:
            int: Number of documents deleted, or None if error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            result = await collection.delete_one(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error in delete_one operation on '{collection_name}': {e}")
            return None
    
    async def delete_many(self, collection_name: str, query: Dict[str, Any]) -> Optional[int]:
        """
        Delete multiple documents with error handling.
        
        Args:
            collection_name: Name of the collection to delete from
            query: Query filter
            
        Returns:
            int: Number of documents deleted, or None if error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            result = await collection.delete_many(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error in delete_many operation on '{collection_name}': {e}")
            return None
    
    async def count_documents(self, collection_name: str, query: Dict[str, Any]) -> Optional[int]:
        """
        Count documents with error handling.
        
        Args:
            collection_name: Name of the collection to count from
            query: Query filter
            
        Returns:
            int: Number of documents matching the query, or None if error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            return await collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error in count_documents operation on '{collection_name}': {e}")
            return None
    
    async def aggregate(self, collection_name: str, pipeline: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        Perform an aggregation with error handling.
        
        Args:
            collection_name: Name of the collection to aggregate
            pipeline: Aggregation pipeline
            
        Returns:
            List[Dict]: List of documents from the aggregation, or None if error occurred
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return None
            
            result = await collection.aggregate(pipeline).to_list(length=None)
            return result
        except Exception as e:
            logger.error(f"Error in aggregate operation on '{collection_name}': {e}")
            return None
    
    async def create_index(self, collection_name: str, keys: Union[str, List[tuple]], 
                          unique: bool = False) -> bool:
        """
        Create an index with error handling.
        
        Args:
            collection_name: Name of the collection to create an index on
            keys: Keys to index (either a string or list of (key, direction) tuples)
            unique: Whether the index should enforce uniqueness
            
        Returns:
            bool: True if index was created successfully, False otherwise
        """
        try:
            collection = await self.get_collection(collection_name)
            if not collection:
                return False
            
            await collection.create_index(keys, unique=unique)
            return True
        except Exception as e:
            logger.error(f"Error in create_index operation on '{collection_name}': {e}")
            return False

# Singleton instance
_mongodb_adapter_instance = None

def get_mongodb_adapter(uri: Optional[str] = None, db_name: Optional[str] = None) -> MongoDBAdapter:
    """
    Get the global MongoDB adapter instance.
    
    Args:
        uri: MongoDB connection URI (optional)
        db_name: Database name (optional)
        
    Returns:
        MongoDBAdapter: Global MongoDB adapter instance
    """
    global _mongodb_adapter_instance
    
    if _mongodb_adapter_instance is None:
        _mongodb_adapter_instance = MongoDBAdapter(uri, db_name)
    
    return _mongodb_adapter_instance