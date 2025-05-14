"""
Test Database Operations

This script tests the database operation safety improvements.
"""

import asyncio
import logging
import os
from typing import Optional

from utils.safe_mongodb import SafeMongoDBResult
from utils.safe_mongodb_compat import SafeMongoDBConnection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_db")

async def test_safe_mongodb_connection():
    """Test the SafeMongoDBConnection class"""
    logger.info("Testing SafeMongoDBConnection...")
    
    # Get MongoDB URI from environment
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        logger.warning("MONGODB_URI not found in environment. Using test connection string.")
        uri = "mongodb://localhost:27017"
    
    # Create a safe connection
    db_conn = SafeMongoDBConnection(uri=uri, db_name="bot_test_db")
    
    # Initialize database
    logger.info("Initializing database connection...")
    success = await db_conn.init_db(max_retries=2, retry_delay=1)
    
    if success:
        logger.info("Successfully connected to MongoDB")
        
        # Test collection access
        collection = await db_conn.get_collection("test_collection")
        if collection:
            logger.info("Successfully accessed test_collection")
            
            # Test document insertion
            doc = {"test_key": "test_value", "timestamp": asyncio.get_event_loop().time()}
            result = await db_conn.execute_operation(
                collection.insert_one, doc
            )
            
            if result and result.success:
                logger.info(f"Successfully inserted document: {result.data}")
                
                # Test document query
                query_result = await db_conn.execute_operation(
                    collection.find_one, {"test_key": "test_value"}
                )
                
                if query_result and query_result.success:
                    logger.info(f"Successfully retrieved document: {query_result.data}")
                else:
                    logger.error(f"Failed to retrieve document: {query_result.error if query_result else 'Unknown error'}")
            else:
                logger.error(f"Failed to insert document: {result.error if result else 'Unknown error'}")
        else:
            logger.error("Failed to access test_collection")
    else:
        logger.error("Failed to connect to MongoDB")
    
    # Close connection
    db_conn.close()
    logger.info("Connection closed")
    
    return success

async def test_safe_mongodb_result():
    """Test the SafeMongoDBResult class"""
    logger.info("Testing SafeMongoDBResult...")
    
    # Create a success result
    success_result = SafeMongoDBResult(
        success=True,
        result={"id": "test123"},
        collection_name="test_collection",
        operation="test_operation"
    )
    
    # Create an error result
    error_result = SafeMongoDBResult(
        success=False,
        error="Test error message",
        collection_name="test_collection",
        operation="test_operation"
    )
    
    # Test boolean evaluation
    assert bool(success_result) is True, "Success result should evaluate to True"
    assert bool(error_result) is False, "Error result should evaluate to False"
    
    # Test failed property
    assert success_result.failed is False, "Success result failed property should be False"
    assert error_result.failed is True, "Error result failed property should be True"
    
    # Test string representation
    logger.info(f"Success result string: {str(success_result)}")
    logger.info(f"Error result string: {str(error_result)}")
    
    return True

async def main():
    """Run all tests"""
    try:
        # Test SafeMongoDBResult
        result_test_success = await test_safe_mongodb_result()
        
        # Test SafeMongoDBConnection
        connection_test_success = await test_safe_mongodb_connection()
        
        if result_test_success and connection_test_success:
            logger.info("All tests passed successfully!")
        else:
            logger.warning("Some tests failed. Check the logs for details.")
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())