"""
Database Connection Test Script

This script tests the connection to MongoDB and basic database operations
using the SafeMongoDBClient.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("test_db")

# Add parent directory to path
sys.path.insert(0, os.path.abspath("."))

async def test_db_connection():
    """
    Test the connection to MongoDB
    """
    try:
        # Import the MongoDB client
        from utils.safe_mongodb import SafeMongoDBClient, SafeMongoDBResult
        
        # Load environment variables
        load_dotenv()
        
        # Get MongoDB URI
        mongodb_uri = os.environ.get("MONGODB_URI")
        if not mongodb_uri:
            logger.error("MONGODB_URI environment variable is not set")
            return False
        
        # Create the client
        db_client = SafeMongoDBClient(mongodb_uri, "test_db")
        
        # Connect to the database
        logger.info("Connecting to MongoDB...")
        result = await db_client.connect()
        
        if not result.success:
            logger.error(f"Failed to connect to MongoDB: {result.error}")
            return False
        
        logger.info("Connected to MongoDB successfully")
        
        # Test basic operations
        await test_basic_operations(db_client)
        
        # Close the connection
        await db_client.close()
        logger.info("Connection closed")
        
        return True
    except Exception as e:
        logger.error(f"Error testing database connection: {e}")
        return False

async def test_basic_operations(db_client):
    """
    Test basic database operations
    
    Args:
        db_client: MongoDB client
    """
    collection_name = "test_collection"
    
    # Test insert one
    logger.info("Testing insert_one...")
    test_doc = {
        "name": "Test Document",
        "value": 42,
        "tags": ["test", "mongo", "python"]
    }
    
    insert_result = await db_client.insert_one(collection_name, test_doc)
    
    if not insert_result.success:
        logger.error(f"Failed to insert document: {insert_result.error}")
        return
    
    inserted_id = insert_result.data.inserted_id
    logger.info(f"Document inserted with ID: {inserted_id}")
    
    # Test find one
    logger.info("Testing find_one...")
    find_result = await db_client.find_one(collection_name, {"_id": inserted_id})
    
    if not find_result.success:
        logger.error(f"Failed to find document: {find_result.error}")
        return
    
    logger.info(f"Found document: {find_result.data}")
    
    # Test delete one
    logger.info("Testing delete_one...")
    delete_result = await db_client.delete_one(collection_name, {"_id": inserted_id})
    
    if not delete_result.success:
        logger.error(f"Failed to delete document: {delete_result.error}")
        return
    
    logger.info(f"Deleted {delete_result.data.deleted_count} document(s)")
    
    # Test collection exists
    logger.info("Testing collection_exists...")
    exists_result = await db_client.collection_exists(collection_name)
    
    if not exists_result.success:
        logger.error(f"Failed to check if collection exists: {exists_result.error}")
        return
    
    logger.info(f"Collection '{collection_name}' exists: {exists_result.data}")
    
    logger.info("Basic operations test completed successfully")

async def main():
    """
    Main entry point
    """
    success = await test_db_connection()
    
    if success:
        logger.info("All tests passed")
    else:
        logger.error("Tests failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())