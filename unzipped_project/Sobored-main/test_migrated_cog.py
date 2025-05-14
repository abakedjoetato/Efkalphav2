#!/usr/bin/env python3
"""
Test Harness for Migrated Cogs

This script loads and tests a specific migrated cog to ensure it works correctly
with py-cord 2.6.1 and the compatibility layers.

Usage:
    python test_migrated_cog.py --cog=cog_name [--verbose] [--skip-db] [--token TOKEN]
"""

import argparse
import asyncio
import importlib
import inspect
import logging
import os
import sys
import time
import traceback
from typing import Dict, List, Optional, Set, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_migrated_cog")

# Import Discord compatibility layer
try:
    from utils.discord_compat import discord, commands, is_pycord, is_pycord_261
except ImportError:
    logger.error("Could not import discord_compat module. Make sure it exists in utils/")
    sys.exit(1)


class MockContext:
    """Mock Context for testing command responses"""
    
    def __init__(self, bot, guild_id=123456789, user_id=987654321):
        self.bot = bot
        self._guild_id = guild_id
        self._user_id = user_id
        self.responses = []
        
    @property
    def guild(self):
        return MockGuild(self._guild_id)
        
    @property
    def author(self):
        return MockUser(self._user_id)
        
    @property
    def user(self):
        return MockUser(self._user_id)
        
    async def respond(self, content=None, embed=None, embeds=None, ephemeral=False, **kwargs):
        response = {"content": content, "embed": embed, "embeds": embeds, "ephemeral": ephemeral}
        self.responses.append(response)
        logger.info(f"Response received: {content[:50] if content else 'No content'}")
        if embed:
            logger.info(f"Embed: {embed.title}")
        return MockMessage()
        
    async def send(self, content=None, embed=None, embeds=None, **kwargs):
        response = {"content": content, "embed": embed, "embeds": embeds}
        self.responses.append(response)
        logger.info(f"Message sent: {content[:50] if content else 'No content'}")
        if embed:
            logger.info(f"Embed: {embed.title}")
        return MockMessage()
        
    async def defer(self, ephemeral=False):
        logger.info(f"Response deferred (ephemeral={ephemeral})")


class MockGuild:
    """Mock Guild for testing"""
    
    def __init__(self, guild_id):
        self.id = guild_id
        self.name = f"Test Guild {guild_id}"


class MockUser:
    """Mock User for testing"""
    
    def __init__(self, user_id):
        self.id = user_id
        self.name = f"Test User {user_id}"
        self.discriminator = "0000"


class MockMessage:
    """Mock Message for testing"""
    
    def __init__(self):
        self.id = 123456789
        

class MockDatabase:
    """Mock MongoDB database for testing cogs"""
    
    def __init__(self):
        self.collections = {}
        
    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]
        
    def list_collection_names(self):
        return list(self.collections.keys())


class MockCollection:
    """Mock MongoDB collection for testing"""
    
    def __init__(self, name):
        self.name = name
        self.documents = {}
        
    async def insert_one(self, document):
        # Generate a document ID if not provided
        if "_id" not in document:
            document["_id"] = f"mock_id_{len(self.documents) + 1}"
            
        # Store the document
        self.documents[document["_id"]] = document.copy()
        
        logger.debug(f"Inserted document into {self.name}: {document['_id']}")
        return MockInsertResult(document["_id"])
        
    async def find_one(self, filter):
        # Apply simple filter matching
        for doc_id, doc in self.documents.items():
            match = True
            for key, value in filter.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
                    
            if match:
                logger.debug(f"Found document in {self.name}: {doc_id}")
                return doc.copy()
                
        logger.debug(f"No document found in {self.name} matching {filter}")
        return None
        
    async def update_one(self, filter, update):
        count = 0
        
        # Apply simple filter matching
        for doc_id, doc in self.documents.items():
            match = True
            for key, value in filter.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
                    
            if match:
                # Apply updates
                if "$set" in update:
                    for key, value in update["$set"].items():
                        doc[key] = value
                        
                if "$inc" in update:
                    for key, value in update["$inc"].items():
                        if key not in doc:
                            doc[key] = value
                        else:
                            doc[key] += value
                            
                count = 1
                break
                
        logger.debug(f"Updated {count} document(s) in {self.name}")
        return MockUpdateResult(count)
        
    async def delete_one(self, filter):
        # Apply simple filter matching
        for doc_id, doc in list(self.documents.items()):
            match = True
            for key, value in filter.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
                    
            if match:
                del self.documents[doc_id]
                logger.debug(f"Deleted document from {self.name}: {doc_id}")
                return MockDeleteResult(1)
                
        logger.debug(f"No document found to delete in {self.name}")
        return MockDeleteResult(0)
        
    async def count_documents(self, filter):
        count = 0
        
        # Apply simple filter matching
        for doc in self.documents.values():
            match = True
            for key, value in filter.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
                    
            if match:
                count += 1
                
        logger.debug(f"Counted {count} document(s) in {self.name}")
        return count


class MockInsertResult:
    """Mock insert result for testing"""
    
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id
        self.acknowledged = True


class MockUpdateResult:
    """Mock update result for testing"""
    
    def __init__(self, modified_count):
        self.modified_count = modified_count
        self.matched_count = modified_count
        self.acknowledged = True


class MockDeleteResult:
    """Mock delete result for testing"""
    
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count
        self.acknowledged = True


class MockBot:
    """Mock Bot for testing migrated cogs"""
    
    def __init__(self, skip_db=False):
        self.intents = discord.Intents.default()
        self.cogs = {}
        self.commands = []
        self.event_listeners = {}
        self.skip_db = skip_db
        
        # Create a mock database
        if not skip_db:
            self.db = MockDatabase()
            self.db_client = None
        
    def add_cog(self, cog):
        """Add a cog to the bot"""
        cog_name = cog.__class__.__name__
        self.cogs[cog_name] = cog
        logger.info(f"Added cog: {cog_name}")
        
        # Register commands from the cog
        for attr_name, attr_value in inspect.getmembers(cog.__class__):
            if isinstance(attr_value, discord.SlashCommandGroup):
                logger.info(f"Found SlashCommandGroup: {attr_name}")
        
    def add_listener(self, func, name=None):
        """Add an event listener"""
        if name is None:
            name = func.__name__
            
        if name not in self.event_listeners:
            self.event_listeners[name] = []
            
        self.event_listeners[name].append(func)
        logger.debug(f"Added listener: {name}")
        
    def event(self, func):
        """Register an event listener"""
        self.add_listener(func)
        return func
        
    def get_cog(self, name):
        """Get a cog by name"""
        return self.cogs.get(name)


class CogTester:
    """Test harness for py-cord 2.6.1 compatible cogs"""
    
    def __init__(self, args):
        self.cog_name = args.cog
        self.verbose = args.verbose
        self.skip_db = args.skip_db
        self.token = args.token
        
        # Configure logging level
        if self.verbose:
            logger.setLevel(logging.DEBUG)
            
        # Create a mock bot
        self.bot = MockBot(skip_db=self.skip_db)
        
        # Track loaded cogs
        self.loaded_cogs = {}
        
    async def load_cog(self):
        """Load the specified cog"""
        try:
            logger.info(f"Loading cog: {self.cog_name}")
            
            # Import the cog module
            cog_path = f"cogs.{self.cog_name}"
            cog_module = importlib.import_module(cog_path)
            
            # Call the setup function
            if hasattr(cog_module, "setup"):
                cog_module.setup(self.bot)
                logger.info(f"Successfully loaded {self.cog_name}")
                return True
            else:
                logger.error(f"Cog {self.cog_name} has no setup function")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load cog {self.cog_name}: {e}")
            traceback.print_exc()
            return False
            
    def get_command_groups(self):
        """Get all command groups in the loaded cog"""
        command_groups = []
        
        for cog_name, cog_instance in self.bot.cogs.items():
            for attr_name, attr_value in inspect.getmembers(cog_instance.__class__):
                if isinstance(attr_value, discord.SlashCommandGroup):
                    command_groups.append((attr_name, attr_value))
                    
        return command_groups
        
    def get_commands(self):
        """Get all commands in the loaded cog"""
        commands = []
        
        # Get commands from command groups
        command_groups = self.get_command_groups()
        for group_name, group in command_groups:
            for cmd_name, cmd in inspect.getmembers(group):
                if callable(cmd) and not cmd_name.startswith("_"):
                    commands.append((f"{group_name} {cmd_name}", cmd))
                    
        return commands
        
    async def test_command(self, command_path, command_handler, ctx):
        """Test a command with mock context"""
        try:
            logger.info(f"Testing command: {command_path}")
            
            # Call the command handler
            await command_handler(ctx)
            
            # Check responses
            if ctx.responses:
                logger.info(f"Command {command_path} produced {len(ctx.responses)} responses")
                return True
            else:
                logger.warning(f"Command {command_path} did not produce any responses")
                return False
                
        except Exception as e:
            logger.error(f"Error testing command {command_path}: {e}")
            traceback.print_exc()
            return False
            
    async def test_all_commands(self):
        """Test all commands in the loaded cog"""
        commands = self.get_commands()
        
        if not commands:
            logger.warning(f"No commands found in cog {self.cog_name}")
            return False
            
        logger.info(f"Found {len(commands)} commands to test")
        
        # Create a mock context
        ctx = MockContext(self.bot)
        
        # Test each command
        success_count = 0
        
        for command_path, command_handler in commands:
            if await self.test_command(command_path, command_handler, ctx):
                success_count += 1
                
        logger.info(f"Successfully tested {success_count}/{len(commands)} commands")
        
        return success_count > 0
        
    async def run(self):
        """Run the cog tester"""
        logger.info(f"Starting test for cog: {self.cog_name}")
        
        # Load the cog
        if not await self.load_cog():
            logger.error("Failed to load cog. Aborting tests.")
            return False
            
        # Check that the cog is properly registered
        if not self.bot.cogs:
            logger.error("No cogs registered with the bot. Make sure the cog is adding itself properly.")
            return False
            
        logger.info(f"Successfully loaded {len(self.bot.cogs)} cogs")
        
        # Check for command groups
        command_groups = self.get_command_groups()
        if not command_groups:
            logger.warning("No command groups found in the cog. Make sure the cog is using SlashCommandGroup correctly.")
            
        # Test commands
        commands_ok = await self.test_all_commands()
        
        logger.info("Test completed")
        
        return commands_ok


async def main():
    parser = argparse.ArgumentParser(
        description="Test Harness for Migrated Cogs"
    )
    parser.add_argument(
        "--cog", 
        type=str,
        required=True,
        help="Name of the cog to test (without .py extension)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--skip-db", 
        action="store_true", 
        help="Skip database initialization"
    )
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("DISCORD_TOKEN"),
        help="Discord bot token (default: DISCORD_TOKEN environment variable)"
    )
    
    args = parser.parse_args()
    tester = CogTester(args)
    
    # Run tests
    success = await tester.run()
    
    # Return exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())