"""
Test crucial Discord bot components without actually connecting to Discord.
This script verifies that all essential bot components are functional.
"""

import asyncio
import importlib
import logging
import os
import sys
import traceback
from typing import Dict, List, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('component_tester')

# Components to test
REQUIRED_MODULES = [
    'discord',
    'pymongo',
    'motor',
    'asyncio',
    'dotenv',
    'discord.ext.commands',
]

CUSTOM_MODULES = [
    'utils.discord_patches',
    'utils.discord_compat',
    'utils.command_imports',
    'utils.safe_mongodb',
    'utils.event_dispatcher',
    'bot',
]

async def test_module_imports() -> Tuple[bool, List[str]]:
    """Test that all required modules can be imported"""
    missing_modules = []
    
    # Test required packages
    logger.info("Testing required package imports...")
    for module_name in REQUIRED_MODULES:
        try:
            module = importlib.import_module(module_name)
            logger.info(f"✓ Successfully imported {module_name}")
            
            # Get version if available
            if hasattr(module, '__version__'):
                logger.info(f"  Version: {module.__version__}")
                
        except ImportError:
            logger.error(f"✗ Failed to import {module_name}")
            missing_modules.append(module_name)
    
    # Test custom modules
    logger.info("\nTesting custom module imports...")
    for module_name in CUSTOM_MODULES:
        try:
            module = importlib.import_module(module_name)
            logger.info(f"✓ Successfully imported {module_name}")
        except ImportError as e:
            logger.error(f"✗ Failed to import {module_name}: {e}")
            missing_modules.append(module_name)
    
    success = len(missing_modules) == 0
    return success, missing_modules

def test_environment_variables() -> Tuple[bool, List[str]]:
    """Test that all required environment variables are set"""
    required_vars = ['DISCORD_TOKEN', 'MONGODB_URI']
    missing_vars = []
    
    logger.info("\nTesting environment variables...")
    for var_name in required_vars:
        if var_name in os.environ and os.environ[var_name]:
            logger.info(f"✓ {var_name} is set")
        else:
            logger.error(f"✗ {var_name} is not set")
            missing_vars.append(var_name)
    
    success = len(missing_vars) == 0
    return success, missing_vars

async def test_mongodb_connection() -> bool:
    """Test that the MongoDB connection works"""
    logger.info("\nTesting MongoDB connection...")
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Get connection string
        conn_string = os.environ.get('MONGODB_URI')
        if not conn_string:
            logger.error("✗ MONGODB_URI is not set")
            return False
            
        # Try to connect
        client = AsyncIOMotorClient(conn_string, serverSelectionTimeoutMS=5000)
        
        # Test connection
        await client.admin.command('ping')
        
        logger.info("✓ Successfully connected to MongoDB")
        
        # Close connection
        client.close()
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {e}")
        return False

async def test_bot_initialization() -> bool:
    """Test that the bot can be initialized"""
    logger.info("\nTesting bot initialization (without connecting to Discord)...")
    try:
        # Apply patches if needed
        try:
            from utils.discord_patches import patch_all
            patch_all()
            logger.info("✓ Applied Discord patches")
        except ImportError:
            logger.warning("Could not import discord_patches")
        
        # Import bot class
        from bot import Bot
        
        # Create bot instance with test mode
        bot = Bot(production=False)
        logger.info("✓ Successfully created Bot instance")
        
        # Test database initialization
        try:
            db_success = await bot.init_db()
            if db_success:
                logger.info("✓ Successfully initialized database connection")
            else:
                logger.error("✗ Failed to initialize database connection")
                return False
        except Exception as e:
            logger.error(f"✗ Failed during database initialization: {e}")
            return False
            
        # Clean up
        await bot.close()
        logger.info("✓ Successfully closed Bot instance")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed during bot initialization: {e}")
        traceback.print_exc()
        return False

async def test_components() -> Dict[str, bool]:
    """Run all tests and return results"""
    results = {}
    
    # Test module imports
    modules_success, missing_modules = await test_module_imports()
    results['modules'] = modules_success
    
    # Test environment variables
    env_success, missing_vars = test_environment_variables()
    results['environment'] = env_success
    
    # Test MongoDB connection
    mongo_success = await test_mongodb_connection()
    results['mongodb'] = mongo_success
    
    # Test bot initialization
    bot_success = await test_bot_initialization()
    results['bot'] = bot_success
    
    # Print summary
    logger.info("\n===== TEST SUMMARY =====")
    for test_name, success in results.items():
        logger.info(f"{test_name}: {'✓ PASS' if success else '✗ FAIL'}")
    
    # Overall success
    overall = all(results.values())
    logger.info(f"\nOVERALL RESULT: {'✓ ALL TESTS PASSED' if overall else '✗ SOME TESTS FAILED'}")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_components())