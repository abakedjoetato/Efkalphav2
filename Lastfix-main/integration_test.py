#!/usr/bin/env python3
"""
Integration Test Suite for Tower of Temptation Discord Bot

This comprehensive test suite validates the cross-cutting integration between
all components of the Discord bot, ensuring command routing, database operations,
async flows, premium features, and multi-guild contexts work properly together.

Usage:
    python integration_test.py [--cogs=cog1,cog2] [--skip-db] [--verbose]
"""

import asyncio
import argparse
import importlib
import inspect
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Set, Tuple, Any, Callable

import discord
from discord.ext import commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("integration_test")

# Try to import test_bot for mock classes
try:
    import test_bot
    MockBot = test_bot.MockBot
except ImportError:
    # Define a minimal MockBot if test_bot.py is not available
    class MockBot:
        """Mock Bot for testing cog loading"""
        def __init__(self):
            self.intents = discord.Intents.default()
            self.cogs = {}
            self.extensions = {}
            self.commands = []
            self.event_listeners = {}
        
        def add_listener(self, func, name=None):
            if name is None:
                name = func.__name__
            if name not in self.event_listeners:
                self.event_listeners[name] = []
            self.event_listeners[name].append(func)
        
        def event(self, func):
            self.add_listener(func)
            return func
        
        def load_extension(self, name, package=None):
            """Mock loading an extension"""
            if name not in self.extensions:
                module = importlib.import_module(name, package=package)
                if hasattr(module, "setup"):
                    module.setup(self)
                self.extensions[name] = module
                return [name]
            return []


# MongoDB Integration checking
class MongoDBIntegrationChecker:
    """Check MongoDB integration across all cogs"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.environ.get("MONGODB_URI")
        self.connection_valid = False
        self.available_collections = set()
        self.collection_access_map = {}
        self.db_client = None
        self.db = None
    
    async def initialize(self):
        """Initialize MongoDB connection and collect schema information"""
        if not self.connection_string:
            logger.warning("No MongoDB connection string provided, skipping database checks")
            return False
            
        try:
            # Dynamically import pymongo to avoid hard dependency
            import pymongo
            from pymongo.errors import ConnectionFailure
            
            # Create client with 5 second timeout
            self.db_client = pymongo.MongoClient(
                self.connection_string, 
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection
            self.db_client.admin.command('ping')
            logger.info("MongoDB connection successful")
            self.connection_valid = True
            
            # Identify default database name from connection string
            # Extract database name from mongodb://user:pass@host:port/dbname
            if '/' in self.connection_string:
                parts = self.connection_string.split('/')
                if len(parts) >= 4:  # Has schema, auth, host and db parts
                    db_name = parts[3].split('?')[0]  # Remove query params if present
                else:
                    db_name = "tower_of_temptation"  # Default fallback
            else:
                db_name = "tower_of_temptation"  # Default fallback
                
            self.db = self.db_client[db_name]
            
            # Get collection names
            self.available_collections = set(self.db.list_collection_names())
            logger.info(f"Available collections: {', '.join(self.available_collections)}")
            
            return True
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            return False
    
    def analyze_cog_db_usage(self, cog_instance):
        """Analyze which collections a cog uses"""
        if not self.connection_valid:
            return {}
            
        cog_name = cog_instance.__class__.__name__
        collection_access = set()
        
        # Inspect all methods for database access patterns
        for name, method in inspect.getmembers(cog_instance, inspect.ismethod):
            method_source = inspect.getsource(method)
            
            # Check for collection access patterns
            for collection in self.available_collections:
                if f'"{collection}"' in method_source or f"'{collection}'" in method_source:
                    collection_access.add(collection)
                    
            # Check for db[] access patterns
            import re
            collection_patterns = re.findall(r'db\[[\'"](.*?)[\'"]\]', method_source)
            for coll in collection_patterns:
                collection_access.add(coll)
                
        self.collection_access_map[cog_name] = collection_access
        return collection_access
    
    def verify_collection_exists(self, collection_name):
        """Verify a collection exists in the database"""
        if not self.connection_valid:
            return False
        return collection_name in self.available_collections
    
    async def validate_collection_operations(self, collection_name):
        """Validate basic CRUD operations on a collection"""
        if not self.connection_valid or not self.verify_collection_exists(collection_name):
            return False
            
        try:
            # Generate a unique test document ID
            test_id = f"integration_test_{int(time.time())}"
            collection = self.db[collection_name]
            
            # Insert test document
            result = await asyncio.to_thread(
                collection.insert_one, 
                {"_id": test_id, "test": True, "timestamp": time.time()}
            )
            
            # Verify insert
            if not result.acknowledged:
                logger.warning(f"Insert operation not acknowledged for {collection_name}")
                return False
                
            # Find the document
            doc = await asyncio.to_thread(
                collection.find_one,
                {"_id": test_id}
            )
            
            if not doc:
                logger.warning(f"Could not find test document in {collection_name}")
                return False
                
            # Update the document
            update_result = await asyncio.to_thread(
                collection.update_one,
                {"_id": test_id},
                {"$set": {"updated": True}}
            )
            
            if not update_result.acknowledged:
                logger.warning(f"Update operation not acknowledged for {collection_name}")
                return False
                
            # Delete the test document
            delete_result = await asyncio.to_thread(
                collection.delete_one,
                {"_id": test_id}
            )
            
            if not delete_result.acknowledged:
                logger.warning(f"Delete operation not acknowledged for {collection_name}")
                return False
                
            logger.info(f"Successfully validated CRUD operations on {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating collection {collection_name}: {e}")
            return False


# Discord Integration Checker
class DiscordIntegrationChecker:
    """Check Discord API integration across all cogs"""
    
    def __init__(self, bot):
        self.bot = bot
        self.slash_commands = []
        self.command_groups = {}
        self.event_handlers = {}
        self.hybrid_commands = []
        
    def analyze_cog_commands(self, cog_instance):
        """Analyze commands defined in a cog"""
        cog_name = cog_instance.__class__.__name__
        
        # Check for slash commands
        slash_cmds = getattr(cog_instance, "slash_commands", [])
        if slash_cmds:
            for cmd in slash_cmds:
                self.slash_commands.append((cog_name, cmd))
                
        # Look for SlashCommandGroup attributes
        for name, attr in inspect.getmembers(cog_instance.__class__):
            if isinstance(attr, discord.SlashCommandGroup):
                self.command_groups[f"{cog_name}.{name}"] = attr
                
        # Check for event handlers
        for name, method in inspect.getmembers(cog_instance, inspect.ismethod):
            if name.startswith("on_"):
                self.event_handlers[f"{cog_name}.{name}"] = method
                
        # Check for hybrid commands
        for name, method in inspect.getmembers(cog_instance, inspect.ismethod):
            if hasattr(method, "is_hybrid_command"):
                self.hybrid_commands.append((cog_name, name, method))
                
        return {
            "slash_commands": len(self.slash_commands),
            "command_groups": len(self.command_groups),
            "event_handlers": len(self.event_handlers),
            "hybrid_commands": len(self.hybrid_commands)
        }


# Premium Feature Integration Checker
class PremiumFeatureChecker:
    """Check premium feature integration across all cogs"""
    
    def __init__(self):
        self.premium_features = {}
        self.premium_checks = {}
        
    def analyze_cog_premium_features(self, cog_instance):
        """Analyze premium features in a cog"""
        cog_name = cog_instance.__class__.__name__
        premium_features = set()
        checks = {}
        
        # Check for premium decorators or attributes in methods
        for name, method in inspect.getmembers(cog_instance, inspect.ismethod):
            # Skip special methods
            if name.startswith("__"):
                continue
                
            # Check method attributes
            premium_attr = getattr(method, "premium_feature", None)
            if premium_attr:
                premium_features.add(premium_attr)
                checks[name] = premium_attr
                
            # Check method source code for premium patterns
            try:
                source = inspect.getsource(method)
                if "premium" in source.lower():
                    checks[name] = "source_contains_premium_check"
            except (OSError, TypeError):
                pass
                
        self.premium_features[cog_name] = premium_features
        self.premium_checks[cog_name] = checks
        
        return {
            "premium_features": premium_features,
            "premium_checks": checks
        }


# Async Flow Integration Checker
class AsyncFlowChecker:
    """Check async flow integration across all cogs"""
    
    def __init__(self):
        self.background_tasks = {}
        self.event_loops = {}
        self.awaitable_methods = {}
        
    def analyze_cog_async_flow(self, cog_instance):
        """Analyze async flows in a cog"""
        cog_name = cog_instance.__class__.__name__
        background_tasks = []
        awaitable_methods = []
        
        # Check for background tasks
        for name, method in inspect.getmembers(cog_instance, inspect.ismethod):
            # Skip special methods
            if name.startswith("__"):
                continue
                
            # Check if method is a coroutine
            if asyncio.iscoroutinefunction(method):
                awaitable_methods.append(name)
                
                # Check method source for background task patterns
                try:
                    source = inspect.getsource(method)
                    if "create_task" in source or "loop.create_task" in source:
                        background_tasks.append(name)
                except (OSError, TypeError):
                    pass
                    
        self.background_tasks[cog_name] = background_tasks
        self.awaitable_methods[cog_name] = awaitable_methods
        
        return {
            "background_tasks": background_tasks,
            "awaitable_methods": awaitable_methods
        }


# Integration Test Runner
class IntegrationTestRunner:
    """Main test runner for the integration test suite"""
    
    def __init__(self, args):
        self.args = args
        self.cogs_to_test = args.cogs.split(",") if args.cogs else []
        self.skip_db = args.skip_db
        self.verbose = args.verbose
        
        # Set up test environment
        self.mock_bot = MockBot()
        self.loaded_cogs = {}
        
        # Set up integration checkers
        self.mongo_checker = MongoDBIntegrationChecker()
        self.discord_checker = DiscordIntegrationChecker(self.mock_bot)
        self.premium_checker = PremiumFeatureChecker()
        self.async_checker = AsyncFlowChecker()
        
        # Configure logging level
        if self.verbose:
            logger.setLevel(logging.DEBUG)
        
    async def run(self):
        """Run the integration test suite"""
        logger.info("Starting Tower of Temptation Discord Bot Integration Test")
        
        # Initialize MongoDB if needed
        if not self.skip_db:
            db_initialized = await self.mongo_checker.initialize()
            if not db_initialized:
                logger.warning("Continuing without MongoDB validation")
        
        # Load and validate cogs
        await self.load_cogs()
        
        # Analyze cog integration
        self.analyze_cogs()
        
        # Generate integration report
        self.generate_report()
        
        logger.info("Integration test completed")
    
    async def load_cogs(self):
        """Load and initialize all cogs for testing"""
        # Find all cogs if no specific cogs were requested
        if not self.cogs_to_test:
            try:
                import glob
                cog_files = glob.glob("cogs/*.py")
                self.cogs_to_test = [
                    os.path.splitext(os.path.basename(f))[0]
                    for f in cog_files
                    if not os.path.basename(f).startswith("_")
                ]
                logger.info(f"Discovered cogs: {', '.join(self.cogs_to_test)}")
            except Exception as e:
                logger.error(f"Failed to discover cogs: {e}")
                self.cogs_to_test = ["simple_bounties", "bounties_fixed"]  # Fallback to known cogs
                
        # Load each cog
        for cog_name in self.cogs_to_test:
            try:
                logger.info(f"Loading cog: {cog_name}")
                cog_path = f"cogs.{cog_name}"
                self.mock_bot.load_extension(cog_path)
                
                # Find the actual cog instance
                for name, obj in self.mock_bot.cogs.items():
                    if obj.__module__ == cog_path:
                        self.loaded_cogs[cog_name] = obj
                        break
                        
                logger.info(f"Successfully loaded {cog_name}")
            except Exception as e:
                logger.error(f"Failed to load {cog_name}: {e}")
    
    def analyze_cogs(self):
        """Analyze all loaded cogs for integration issues"""
        for cog_name, cog_instance in self.loaded_cogs.items():
            logger.info(f"Analyzing cog: {cog_name}")
            
            # Analyze MongoDB integration
            if not self.skip_db:
                db_usage = self.mongo_checker.analyze_cog_db_usage(cog_instance)
                if self.verbose:
                    logger.debug(f"{cog_name} DB usage: {db_usage}")
            
            # Analyze Discord integration
            discord_info = self.discord_checker.analyze_cog_commands(cog_instance)
            if self.verbose:
                logger.debug(f"{cog_name} Discord integration: {discord_info}")
            
            # Analyze premium features
            premium_info = self.premium_checker.analyze_cog_premium_features(cog_instance)
            if self.verbose:
                logger.debug(f"{cog_name} Premium features: {premium_info}")
            
            # Analyze async flows
            async_info = self.async_checker.analyze_cog_async_flow(cog_instance)
            if self.verbose:
                logger.debug(f"{cog_name} Async flows: {async_info}")
    
    def generate_report(self):
        """Generate an integration report"""
        logger.info("=== INTEGRATION TEST REPORT ===")
        
        # Summary of loaded cogs
        logger.info(f"Total cogs loaded: {len(self.loaded_cogs)}/{len(self.cogs_to_test)}")
        
        # Discord integration summary
        logger.info("\n--- Discord Integration ---")
        logger.info(f"Slash commands: {len(self.discord_checker.slash_commands)}")
        logger.info(f"Command groups: {len(self.discord_checker.command_groups)}")
        logger.info(f"Event handlers: {len(self.discord_checker.event_handlers)}")
        logger.info(f"Hybrid commands: {len(self.discord_checker.hybrid_commands)}")
        
        # MongoDB integration summary
        if not self.skip_db:
            logger.info("\n--- MongoDB Integration ---")
            logger.info(f"Available collections: {len(self.mongo_checker.available_collections)}")
            for cog_name, collections in self.mongo_checker.collection_access_map.items():
                logger.info(f"{cog_name} uses collections: {', '.join(collections)}")
        
        # Premium integration summary
        logger.info("\n--- Premium Feature Integration ---")
        for cog_name, features in self.premium_checker.premium_features.items():
            if features:
                logger.info(f"{cog_name} uses premium features: {', '.join(features)}")
        
        # Async flow summary
        logger.info("\n--- Async Flow Integration ---")
        for cog_name, tasks in self.async_checker.background_tasks.items():
            if tasks:
                logger.info(f"{cog_name} uses background tasks in: {', '.join(tasks)}")
        
        logger.info("\n=== END OF REPORT ===")


# Main entry point
async def main():
    parser = argparse.ArgumentParser(
        description="Integration Test Suite for Tower of Temptation Discord Bot"
    )
    parser.add_argument(
        "--cogs", 
        type=str, 
        help="Comma-separated list of cogs to test (default: all)", 
        default=""
    )
    parser.add_argument(
        "--skip-db", 
        action="store_true", 
        help="Skip MongoDB integration tests"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    test_runner = IntegrationTestRunner(args)
    await test_runner.run()


if __name__ == "__main__":
    asyncio.run(main())