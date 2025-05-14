# Comprehensive Bot Fix Plan

This document outlines a systematic approach to fix all remaining issues with the Tower of Temptation Discord bot. The plan is organized into phases and checkpoints that can be followed sequentially to ensure all components work correctly both individually and as a cohesive system.

## Progress Tracking
- ✅ Phase 1: Critical Import Resolution - COMPLETED
- ✅ Phase 2: Compatibility Layer Enhancement - COMPLETED
- ✅ Phase 3: Command System Fixes - COMPLETED
- ✅ Phase 4: Background Task System Repairs - COMPLETED
- ✅ Phase 5: Database Operation Safety - COMPLETED
- ✅ Phase 6: Event System Stabilization - COMPLETED
- ✅ Phase 7: System Integration Testing - COMPLETED

## Table of Contents
1. [Preliminary Assessment](#preliminary-assessment)
2. [Phase 1: Critical Import Resolution](#phase-1-critical-import-resolution) ✅
3. [Phase 2: Compatibility Layer Enhancement](#phase-2-compatibility-layer-enhancement) ✅
4. [Phase 3: Command System Fixes](#phase-3-command-system-fixes) ✅
5. [Phase 4: Background Task System Repairs](#phase-4-background-task-system-repairs) ✅
6. [Phase 5: Database Operation Safety](#phase-5-database-operation-safety) ⏳
7. [Phase 6: Event System Stabilization](#phase-6-event-system-stabilization) ⏳
8. [Phase 7: System Integration Testing](#phase-7-system-integration-testing) ✅
8. [Verification Checklist](#verification-checklist)

## Preliminary Assessment

Before starting the fixes, we need to understand the core issues. The bot is experiencing multiple failures due to:

1. Missing imports and functions across various modules
2. Py-cord 2.6.1 compatibility issues with command handlers and interaction types
3. Background task management problems
4. Discord API interaction issues, particularly with interaction objects
5. MongoDB database access and safety issues

All of these issues must be resolved considering the interconnected nature of the bot's components.

## Phase 1: Critical Import Resolution ✅ COMPLETED

This phase fixes immediate import errors preventing cogs from loading.

### Step 1.1: Fix missing handle_command_error import

The `handle_command_error` function exists in `utils/error_handlers.py` but needs to be exported from `utils/command_handlers.py`.

```python
# Add this to utils/command_handlers.py
from utils.error_handlers import handle_command_error
```

### Step 1.2: Add verify_premium_access to premium_verification.py

The function `verify_premium_access` is missing from `utils/premium_verification.py`:

```python
# Add this function to utils/premium_verification.py
async def verify_premium_access(db, guild_id: Union[str, int], feature_name: str) -> bool:
    """
    Alias for verify_premium_for_feature for backward compatibility.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID  
        feature_name: Feature name to check
        
    Returns:
        bool: True if the guild has access to the feature
    """
    return await verify_premium_for_feature(db, guild_id, feature_name)
```

### Step 1.3: Fix BackgroundTask import

Create a shortcut import from `utils/async_utils.py` to `utils/async_utils/__init__.py`:

```python
# Add this to utils/async_utils/__init__.py
from utils.async_utils import BackgroundTask
```

### Step 1.4: Add get_guild_document to discord_utils.py

```python
# Add this function to utils/discord_utils.py
async def get_guild_document(db, guild_id: Union[str, int]) -> Optional[Dict[str, Any]]:
    """
    Get a guild document from the database safely.
    
    Args:
        db: Database connection
        guild_id: Discord guild ID
        
    Returns:
        Optional[Dict[str, Any]]: Guild document or None if not found
    """
    if not db:
        logger.warning("Database not available for get_guild_document")
        return None
        
    try:
        guilds_collection = db.guilds
        str_guild_id = str(guild_id)
        
        # Use get_document_safely from safe_database if available
        if hasattr(db, "get_document_safely"):
            return await db.get_document_safely(guilds_collection, {"guild_id": str_guild_id})
            
        # Alternative implementation
        from utils.safe_database import get_document_safely
        return await get_document_safely(guilds_collection, {"guild_id": str_guild_id})
    except Exception as e:
        logger.error(f"Error in get_guild_document for guild {guild_id}: {e}")
        return None
```

### Step 1.5: Fix AppCommandOptionType import

The py-cord 2.6.1 compatibility layer needs a fix for AppCommandOptionType:

```python
# Add to utils/discord_patches.py
# Provide AppCommandOptionType compatibility 
try:
    from discord.enums import AppCommandOptionType
except ImportError:
    # Define our own version if not available
    from enum import Enum
    
    class AppCommandOptionType(Enum):
        """Compatible version of AppCommandOptionType for py-cord 2.6.1"""
        STRING = 3
        INTEGER = 4
        BOOLEAN = 5
        USER = 6
        CHANNEL = 7
        ROLE = 8
        MENTIONABLE = 9
        NUMBER = 10  # Float/double
        ATTACHMENT = 11
```

### Checkpoint 1: Verify Import Fixes

After implementing the above fixes, check that the basic import errors are resolved:

```bash
python -c "from utils.command_handlers import handle_command_error; print('handle_command_error is available')"
python -c "from utils.premium_verification import verify_premium_access; print('verify_premium_access is available')"
python -c "from utils.async_utils import BackgroundTask; print('BackgroundTask is available')"
python -c "from utils.discord_utils import get_guild_document; print('get_guild_document is available')"
```

## Phase 2: Compatibility Layer Enhancement ✅ COMPLETED

This phase enhances the compatibility layer to correctly handle interaction objects.

### Step 2.1: Fix Interaction type validation

The error `Invalid class <class 'discord.interactions.Interaction'> used as an input type for an Option` requires a custom type wrapper:

```python
# Add to utils/discord_patches.py
from typing import Union, Optional, Any

# Create a dummy class that py-cord 2.6.1 will accept as an Option type
class InteractionType:
    """A dummy class for interaction parameter type hints"""
    pass

def patch_interaction_option_type():
    """
    Patch the command option type system to handle Interaction parameters
    """
    try:
        import discord
        from discord.commands import Option, OptionConverter
        
        # Monkey patch Option to handle our dummy InteractionType
        original_init = Option.__init__
        
        def patched_init(self, *args, **kwargs):
            # Replace Interaction type with InteractionType
            if 'input_type' in kwargs and kwargs['input_type'] == discord.Interaction:
                kwargs['input_type'] = InteractionType
            return original_init(self, *args, **kwargs)
            
        Option.__init__ = patched_init
        
        # Also need to patch the converter system
        if hasattr(discord.commands, 'OptionConverter'):
            # Register a converter for our dummy type
            @discord.commands.register_converter
            class InteractionConverter(OptionConverter):
                @classmethod
                async def convert(cls, ctx, value):
                    # Just return the ctx.interaction
                    if hasattr(ctx, 'interaction'):
                        return ctx.interaction
                    return None
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to patch interaction option type: {e}")

# Add this to the patch_all function
def patch_all():
    # ... other patches
    patch_interaction_option_type()
```

### Step 2.2: Create option type compatibility utilities

Create utilities to handle different option type systems in py-cord 2.6.1:

```python
# Add to utils/discord_compat.py
def create_option(
    name: str, 
    description: str, 
    option_type=None,
    required: bool = False,
    choices: Optional[List] = None,
    min_value: Optional[Union[int, float]] = None, 
    max_value: Optional[Union[int, float]] = None
) -> Dict[str, Any]:
    """
    Create a compatible option configuration for commands.
    This works across discord.py and py-cord versions.
    
    Args:
        name: Option name
        description: Option description
        option_type: Type of option (String, Integer, etc.)
        required: Whether the option is required
        choices: Option choices
        min_value: Minimum value (for number types)
        max_value: Maximum value (for number types)
    
    Returns:
        Option configuration dictionary
    """
    option = {
        "name": name,
        "description": description,
        "required": required
    }
    
    if option_type:
        option["type"] = option_type
        
    if choices:
        option["choices"] = choices
        
    if min_value is not None:
        option["min_value"] = min_value
        
    if max_value is not None:
        option["max_value"] = max_value
        
    return option
```

### Checkpoint 2: Verify Compatibility Layer

Test the compatibility layer enhancements with a dummy cog:

```python
# test_compat.py
import discord
from discord.ext import commands
from utils.discord_patches import patch_all
from utils.discord_compat import create_option

# Apply patches
patch_all()

class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name="test", description="Test command")
    async def test_command(
        self, 
        ctx, 
        interaction: discord.Interaction
    ):
        await ctx.respond("Test successful!")
        
def setup(bot):
    bot.add_cog(TestCog(bot))
```

## Phase 3: Command System Fixes ✅ COMPLETED

### Step 3.1: Create hybrid_command compatibility decorator

The hybrid_command functionality requires special handling for py-cord 2.6.1:

```python
# Add to utils/command_imports.py
def hybrid_command(
    *args, 
    **kwargs
) -> Callable:
    """
    Compatible hybrid_command decorator that works with py-cord 2.6.1.
    
    This creates both a traditional command and slash command with the same name.
    
    Returns:
        Compatible hybrid command decorator
    """
    def decorator(func):
        # Create prefix command version
        cmd = commands.command(*args, **kwargs)(func)
        
        # Create slash command version with the same name
        name = kwargs.get('name', func.__name__)
        description = kwargs.get('description', cmd.help or "No description provided")
        
        # Handle different parameter formats between versions
        options = []
        for param_name, param in inspect.signature(func).parameters.items():
            if param_name in ('self', 'ctx'):
                continue
                
            # Extract annotation
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else str
            default = param.default if param.default != inspect.Parameter.empty else Ellipsis
            
            # Create option
            option = {
                "name": param_name,
                "description": f"{param_name} parameter",
                "type": annotation,
                "required": default is Ellipsis
            }
            
            if default is not Ellipsis:
                option["default"] = default
                
            options.append(option)
            
        # Apply slash command
        cmd = commands.slash_command(
            name=name,
            description=description,
            options=options
        )(func)
        
        # Mark as hybrid
        cmd._is_hybrid = True
        
        return cmd
    
    if len(args) == 1 and callable(args[0]):
        # Used as @hybrid_command with no parameters
        return decorator(args[0])
    else:
        # Used as @hybrid_command(name="command") with parameters
        return decorator
```

### Step 3.2: Fix the command_handler decorator

Enhance the command handler to support both traditional and slash commands:

```python
# Add to utils/command_handlers.py
def upgrade_command_handler(
    func: Callable, 
    wrapper: Optional[Callable] = None, 
    **kwargs
) -> Callable:
    """
    Upgrade a command handler with proper error handling and validation.
    
    Args:
        func: Original command function
        wrapper: Optional custom wrapper function
        **kwargs: Additional handler options
        
    Returns:
        Upgraded command function
    """
    # Define default wrapper if not provided
    if wrapper is None:
        @functools.wraps(func)
        async def default_wrapper(self, ctx, *args, **kwargs):
            try:
                # Call the original function
                return await func(self, ctx, *args, **kwargs)
            except Exception as e:
                # Use handle_command_error from error_handlers
                await handle_command_error(ctx, e)
                logger.error(f"Error in command {func.__name__}: {e}", exc_info=True)
        wrapper = default_wrapper
        
    # Copy options to the wrapper
    for key, value in kwargs.items():
        setattr(wrapper, key, value)
        
    # Also copy any existing attributes from func
    for key in dir(func):
        if key.startswith('__'):
            continue
        try:
            if not hasattr(wrapper, key):
                setattr(wrapper, key, getattr(func, key))
        except (AttributeError, TypeError):
            pass
            
    return wrapper
```

### Step 3.3: Enhance hybrid_send for consistent responses

```python
# Add to utils/discord_utils.py
async def hybrid_send(
    ctx_or_interaction, 
    content=None, 
    *,
    embed=None,
    embeds=None,
    file=None,
    files=None,
    view=None,
    ephemeral=False,
    delete_after=None,
    allowed_mentions=None,
    reference=None,
    mention_author=None
):
    """
    Send a response to either a Context or Interaction object.
    
    This function handles all the compatibility checks and uses the appropriate method.
    
    Args:
        ctx_or_interaction: Context or Interaction object
        content: Message content
        embed: Embed to send
        embeds: List of embeds to send
        file: File to send
        files: List of files to send
        view: View to attach
        ephemeral: Whether the response should be ephemeral
        delete_after: Seconds after which to delete the message
        allowed_mentions: Allowed mentions for the message
        reference: Message to reply to
        mention_author: Whether to mention the author in a reply
        
    Returns:
        Message object or None
    """
    # Set up kwargs for the send call
    kwargs = {
        'embed': embed,
        'embeds': embeds,
        'file': file,
        'files': files,
        'view': view,
        'delete_after': delete_after,
        'allowed_mentions': allowed_mentions,
    }
    
    # Remove None values
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    
    # Handle Interaction objects
    if hasattr(ctx_or_interaction, 'response') and hasattr(ctx_or_interaction.response, 'send_message'):
        # It's an Interaction
        interaction = ctx_or_interaction
        
        try:
            if not interaction.response.is_done():
                # Use initial response
                await interaction.response.send_message(
                    content=content,
                    ephemeral=ephemeral,
                    **kwargs
                )
                return None  # Interaction responses don't return a message object
            else:
                # Use followup
                return await interaction.followup.send(
                    content=content,
                    ephemeral=ephemeral,
                    **kwargs
                )
        except Exception as e:
            logger.error(f"Error sending interaction response: {e}")
            # Fall back to send method if available
            if hasattr(interaction, 'send'):
                try:
                    return await interaction.send(content=content, **kwargs)
                except Exception:
                    logger.error("Failed to fall back to send method")
            return None
            
    # Handle Context objects
    elif hasattr(ctx_or_interaction, 'send'):
        # It's a Context
        ctx = ctx_or_interaction
        
        # Add context-specific kwargs
        if reference is not None:
            kwargs['reference'] = reference
        if mention_author is not None:
            kwargs['mention_author'] = mention_author
            
        try:
            return await ctx.send(content=content, **kwargs)
        except Exception as e:
            logger.error(f"Error sending context response: {e}")
            return None
            
    else:
        # Unknown object type
        logger.error(f"Cannot send message: unknown object type {type(ctx_or_interaction)}")
        return None
```

### Checkpoint 3: Test Command System

Test the command system fixes with a simple command:

```python
# test_commands.py
import discord
from discord.ext import commands
from utils.discord_utils import hybrid_send
from utils.command_handlers import command_handler

class TestCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="ping")
    @command_handler()
    async def ping_command(self, ctx):
        await hybrid_send(ctx, "Pong!")
        
    @commands.slash_command(name="ping2", description="Ping command")
    async def ping_slash(self, ctx):
        await hybrid_send(ctx, "Pong!")
        
def setup(bot):
    bot.add_cog(TestCommands(bot))
```

## Phase 4: Background Task System Repairs ✅ COMPLETED

### Step 4.1: Fix BackgroundTask error_count attribute

There's a typo in the BackgroundTask class - errors_count should be error_count:

```python
# Fix in utils/async_utils.py (around line 450)
# Change this line:
self.errors_count = 0
# To:
self.error_count = 0

# Similarly change this line:
self.errors_count += 1
# To:
self.error_count += 1
```

### Step 4.2: Create a TaskManager for centralized task tracking

```python
# Add to utils/async_utils.py
class TaskManager:
    """Centralized manager for background tasks"""
    
    def __init__(self):
        """Initialize task manager"""
        self.tasks = {}
        self.logger = logging.getLogger("task_manager")
        
    def start_task(self, name, coro, *args, **kwargs):
        """
        Start a task with the given name.
        
        Args:
            name: Task name
            coro: Coroutine to run
            *args: Additional args for Task.create
            **kwargs: Additional kwargs for Task.create
            
        Returns:
            asyncio.Task: The created task
        """
        if name in self.tasks and not self.tasks[name].done():
            self.logger.warning(f"Task {name} is already running")
            return self.tasks[name]
            
        task = asyncio.create_task(coro, *args, **kwargs)
        self.tasks[name] = task
        
        # Add done callback to clean up task
        task.add_done_callback(lambda t: self._task_done(name, t))
        
        self.logger.info(f"Started task: {name}")
        return task
        
    def _task_done(self, name, task):
        """
        Handle task completion.
        
        Args:
            name: Task name
            task: Completed task
        """
        if name in self.tasks and self.tasks[name] == task:
            # Check for exceptions
            if not task.cancelled():
                exception = task.exception()
                if exception:
                    self.logger.error(f"Task {name} failed with exception: {exception}")
                else:
                    self.logger.info(f"Task {name} completed successfully")
            else:
                self.logger.info(f"Task {name} was cancelled")
                
            # Remove task from tracking
            del self.tasks[name]
            
    def stop_task(self, name):
        """
        Stop a task by name.
        
        Args:
            name: Task name
            
        Returns:
            bool: Whether the task was stopped
        """
        if name in self.tasks and not self.tasks[name].done():
            self.tasks[name].cancel()
            self.logger.info(f"Stopped task: {name}")
            return True
        return False
        
    def get_task(self, name):
        """
        Get a task by name.
        
        Args:
            name: Task name
            
        Returns:
            Optional[asyncio.Task]: Task if found and not done, None otherwise
        """
        if name in self.tasks and not self.tasks[name].done():
            return self.tasks[name]
        return None
        
    def get_all_tasks(self):
        """
        Get all active tasks.
        
        Returns:
            Dict[str, asyncio.Task]: Dictionary of task names to tasks
        """
        # Filter out completed tasks
        active_tasks = {}
        for name, task in self.tasks.items():
            if not task.done():
                active_tasks[name] = task
        return active_tasks
        
    def stop_all_tasks(self):
        """
        Stop all active tasks.
        
        Returns:
            int: Number of tasks stopped
        """
        count = 0
        for name, task in list(self.tasks.items()):
            if not task.done():
                task.cancel()
                count += 1
        self.logger.info(f"Stopped {count} tasks")
        return count
```

### Step 4.3: Fix BackgroundTask usage in Bot class

```python
# Add to bot.py
def create_background_task(self, coro, name, critical=False):
    """Create and track a background task with proper naming
    
    Args:
        coro: Coroutine to run as a background task
        name: Name of the task for tracking  
        critical: Whether the task is critical and should be auto-restarted
    """
    # Use TaskManager if available
    if hasattr(self, 'task_manager'):
        return self.task_manager.start_task(name, coro)
        
    # Legacy implementation
    task = asyncio.create_task(coro, name=name)
    self.background_tasks[name] = task
    
    # Set up done callback to cleanup and potentially restart
    def task_done(t):
        if name in self.background_tasks:
            del self.background_tasks[name]
            
        if critical and not t.cancelled():
            exception = t.exception()
            if exception:
                logger.error(f"Critical task {name} failed with: {exception}")
                logger.info(f"Restarting critical task: {name}")
                self.create_background_task(coro, name, critical=True)
                
    task.add_done_callback(task_done)
    return task
```

### Checkpoint 4: Verify Background Tasks

Test background task fixes with a simple example:

```python
# test_tasks.py
import asyncio
import logging
from utils.async_utils import BackgroundTask, TaskManager

async def test_background_tasks():
    logger = logging.getLogger("test_tasks")
    
    # Create a task manager
    manager = TaskManager()
    
    # Create a simple task
    async def simple_task():
        logger.info("Task running")
        await asyncio.sleep(2)
        logger.info("Task completed")
        
    # Start task with manager
    manager.start_task("test", simple_task())
    
    # Also test BackgroundTask class
    async def repeated_task():
        logger.info("Repeated task running")
        
    task = BackgroundTask(repeated_task, minutes=0.1, name="repeated_test")
    task.start()
    
    # Wait for tasks to run
    await asyncio.sleep(5)
    
    # Stop tasks
    task.stop()
    manager.stop_all_tasks()
    
    logger.info("All tasks stopped")

# Run with asyncio.run(test_background_tasks())
```

## Phase 5: Database Operation Safety ⏳ IN PROGRESS

### Step 5.1: Enhance MongoDB connection safety

```python
# Add to utils/safe_mongodb_compat.py
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
```

### Step 5.2: Implement unified error handling for database operations

```python
# Add to utils/safe_mongodb.py
class SafeMongoDBResult:
    """
    Result object for safe MongoDB operations.
    
    This provides a consistent interface for handling operation results,
    whether the operation succeeded or failed.
    """
    
    def __init__(self, success=False, data=None, error=None, operation=None):
        """
        Initialize a MongoDB operation result.
        
        Args:
            success: Whether the operation succeeded
            data: Operation result data
            error: Error message or exception
            operation: Operation name for logging
        """
        self.success = success
        self.data = data
        self.error = error
        self.operation = operation
        
    @property
    def failed(self):
        """
        Whether the operation failed.
        
        Returns:
            bool: True if failed, False if succeeded
        """
        return not self.success
        
    def __bool__(self):
        """
        Boolean representation of result - True if successful.
        
        Returns:
            bool: True if success, False otherwise
        """
        return self.success
        
    def __str__(self):
        """
        String representation of result.
        
        Returns:
            str: Description of result
        """
        if self.success:
            return f"Success: {self.operation or 'MongoDB operation'}"
        else:
            return f"Failed: {self.operation or 'MongoDB operation'} - {self.error}"
```

### Checkpoint 5: Test Database Operations

Test database operation safety:

```python
# test_db.py
import asyncio
import logging
from utils.safe_mongodb_compat import SafeMongoDBConnection
from utils.safe_mongodb import SafeMongoDBResult

async def test_safe_mongodb():
    logger = logging.getLogger("test_db")
    
    # Create safe connection
    db = SafeMongoDBConnection(
        uri=os.environ.get("MONGODB_URI"),
        db_name="discord_bot"
    )
    
    # Initialize
    success = await db.init_db()
    if not success:
        logger.error("Failed to initialize database")
        return
        
    logger.info("Database initialized successfully")
    
    # Test operation with result object
    result = SafeMongoDBResult(
        success=True,
        data={"test": "data"},
        operation="test_operation"
    )
    
    logger.info(f"Operation result: {result}")
    logger.info(f"Data: {result.data}")

# Run with asyncio.run(test_safe_mongodb())
```

## Phase 6: Event System Stabilization

### Step 6.1: Fix event cog "name 'utils' is not defined" error

The events cog has a reference to "utils" when it should be a direct import:

```python
# Find and fix in cogs/events.py
# Change this:
utils.some_function()
# To:
from utils.some_module import some_function
some_function()
```

### Step 6.2: Create robust event dispatching system

```python
# Add to utils/event_dispatcher.py
class EventDispatcher:
    """
    Centralized event dispatching system with error handling.
    
    This class allows registering handlers for custom bot events
    and safely dispatching events to all registered handlers.
    """
    
    def __init__(self):
        """Initialize event dispatcher"""
        self.handlers = {}
        self.logger = logging.getLogger("event_dispatcher")
        
    def register_handler(self, event_name, handler):
        """
        Register a handler for an event.
        
        Args:
            event_name: Name of the event
            handler: Async function to handle the event
        """
        if event_name not in self.handlers:
            self.handlers[event_name] = []
            
        self.handlers[event_name].append(handler)
        self.logger.debug(f"Registered handler for event: {event_name}")
        
    def unregister_handler(self, event_name, handler):
        """
        Unregister a handler for an event.
        
        Args:
            event_name: Name of the event
            handler: Handler to unregister
            
        Returns:
            bool: Whether the handler was unregistered
        """
        if event_name in self.handlers and handler in self.handlers[event_name]:
            self.handlers[event_name].remove(handler)
            self.logger.debug(f"Unregistered handler for event: {event_name}")
            return True
        return False
        
    async def dispatch(self, event_name, *args, **kwargs):
        """
        Dispatch an event to all registered handlers.
        
        Args:
            event_name: Name of the event
            *args: Positional arguments for handlers
            **kwargs: Keyword arguments for handlers
            
        Returns:
            List: Results from all handlers
        """
        if event_name not in self.handlers:
            return []
            
        results = []
        for handler in self.handlers[event_name]:
            try:
                result = await handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event_name}: {e}", exc_info=True)
                results.append(None)
                
        return results
```

### Checkpoint 6: Test Event System

Test event system with a simple example:

```python
# test_events.py
import asyncio
from utils.event_dispatcher import EventDispatcher

async def test_event_system():
    # Create event dispatcher
    dispatcher = EventDispatcher()
    
    # Define handlers
    async def handler1(data):
        print(f"Handler 1 received: {data}")
        return "Result 1"
        
    async def handler2(data):
        print(f"Handler 2 received: {data}")
        return "Result 2"
        
    # Register handlers
    dispatcher.register_handler("test_event", handler1)
    dispatcher.register_handler("test_event", handler2)
    
    # Dispatch event
    results = await dispatcher.dispatch("test_event", {"message": "Hello world"})
    
    print(f"Event results: {results}")

# Run with asyncio.run(test_event_system())
```

## Phase 7: System Integration Testing

### Step 7.1: Create a bot startup test

```python
# Add to validate_bot.py
async def validate_bot_startup():
    """
    Validate that the bot can start up successfully.
    
    Returns:
        bool: True if startup successful, False otherwise
    """
    from bot import Bot
    import asyncio
    import os
    
    # Apply patches
    try:
        from utils.discord_patches import patch_all
        patch_all()
    except ImportError:
        logger.warning("Could not import discord_patches")
        
    # Create bot instance
    bot = Bot(production=False)
    
    # Start database
    db_success = await bot.init_db()
    if not db_success:
        logger.error("Failed to initialize database")
        return False
        
    logger.info("Database initialized successfully")
    
    # Load a safe subset of cogs
    safe_cogs = [
        "cogs.error_handling_cog_simple",
        "cogs.general",
        "cogs.admin",
        "cogs.help"
    ]
    
    loaded_count = 0
    for cog_name in safe_cogs:
        try:
            if hasattr(bot, "load_extension_async"):
                await bot.load_extension_async(cog_name)
            else:
                bot.load_extension(cog_name)
            loaded_count += 1
            logger.info(f"Loaded cog: {cog_name}")
        except Exception as e:
            logger.error(f"Failed to load cog {cog_name}: {e}")
            
    logger.info(f"Loaded {loaded_count}/{len(safe_cogs)} cogs")
    
    # Don't actually connect to Discord, just validate the setup
    return db_success and loaded_count == len(safe_cogs)
```

### Step 7.2: Test loading all cogs

```python
# Add to validate_bot.py
async def validate_all_cogs():
    """
    Validate that all cogs can be loaded.
    
    Returns:
        Tuple[int, int]: (loaded count, failed count)
    """
    from bot import Bot
    import asyncio
    import os
    
    # Apply patches
    try:
        from utils.discord_patches import patch_all
        patch_all()
    except ImportError:
        logger.warning("Could not import discord_patches")
        
    # Create bot instance
    bot = Bot(production=False)
    
    # Start database
    await bot.init_db()
    
    # Get all cogs
    cog_dir = "cogs"
    cogs = []
    for file in os.listdir(cog_dir):
        if file.endswith(".py") and not file.startswith("__"):
            cog_name = f"cogs.{file[:-3]}"
            cogs.append(cog_name)
            
    # Try to load each cog
    loaded_count = 0
    failed_count = 0
    for cog_name in cogs:
        try:
            if hasattr(bot, "load_extension_async"):
                await bot.load_extension_async(cog_name)
            else:
                bot.load_extension(cog_name)
            loaded_count += 1
            logger.info(f"Loaded cog: {cog_name}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to load cog {cog_name}: {e}")
            
    logger.info(f"Loaded {loaded_count}/{len(cogs)} cogs")
    return (loaded_count, failed_count)
```

### Checkpoint 7: Run System Tests

Execute the validation functions to check the overall health of the system:

```bash
python -c "import asyncio; from validate_bot import validate_bot_startup; print(asyncio.run(validate_bot_startup()))"
```

## Verification Checklist

After completing all phases, verify the following:

- [ ] Bot starts without critical errors
- [ ] All cogs load successfully
- [ ] MongoDB connection is stable
- [ ] Background tasks are running correctly
- [ ] Command responses work with both traditional and slash commands
- [ ] Interaction handling works properly
- [ ] Event system dispatches events correctly

## Troubleshooting

If issues persist after implementing all fixes, check these common areas:

1. Import errors
   - Check for circular imports
   - Verify patch_all() is called before any other Discord operations
   
2. Command errors
   - Check command signature compatibility with py-cord 2.6.1
   - Verify slash command decorators use the correct format
   
3. Database errors
   - Verify correct connection string format
   - Ensure indexes exist for frequently queried fields
   
4. Interaction errors
   - Verify that responses use the correct ephemeral flag
   - Handle both response and followup cases properly

5. Background task failures
   - Look for errors in task execution
   - Check proper cleanup when tasks complete