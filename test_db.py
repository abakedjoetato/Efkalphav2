"""
Test MongoDB Connection

This script tests the MongoDB connection to ensure it works properly.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("test_db.log")
    ]
)

logger = logging.getLogger(__name__)

async def test_database():
    """Test MongoDB connection and basic operations"""
    try:
        # Import database connection utilities
        from utils.db_connection import get_db_connection, close_db_connection
        
        # Get MongoDB URI from environment
        mongodb_uri = os.environ.get("MONGODB_URI")
        if not mongodb_uri:
            logger.error("MONGODB_URI environment variable not set")
            return False
            
        logger.info(f"Connecting to MongoDB: {mongodb_uri[:20]}...")
        
        # Try to connect to the database
        db = await get_db_connection()
        if db is None:
            logger.error("Failed to connect to MongoDB")
            return False
        
        # Test listing collections
        collections = await db.list_collection_names()
        logger.info(f"Found {len(collections)} collections: {', '.join(collections) if collections else 'none'}")
        
        # Try to create a test document
        logger.info("Inserting test document...")
        result = await db.test_connection.insert_one({
            "test": True,
            "message": "MongoDB connection test"
        })
        
        # Verify document was inserted
        doc_id = result.inserted_id
        logger.info(f"Test document inserted with ID: {doc_id}")
        
        # Try to retrieve the document
        logger.info("Finding test document...")
        doc = await db.test_connection.find_one({"_id": doc_id})
        
        if doc:
            logger.info(f"Found test document: {doc}")
            
            # Delete the test document
            logger.info("Deleting test document...")
            await db.test_connection.delete_one({"_id": doc_id})
            
            # Close connection
            await close_db_connection()
            
            logger.info("MongoDB connection test successful!")
            return True
        else:
            logger.error("Test document not found")
            await close_db_connection()
            return False
            
    except Exception as e:
        logger.error(f"Error testing database: {e}")
        return False

async def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    # Test database connection
    success = await test_database()
    
    if success:
        logger.info("Database connection test passed")
        return 0
    else:
        logger.error("Database connection test failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)