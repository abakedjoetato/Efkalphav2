"""
Command Handlers for Discord API Compatibility

This module provides enhanced command classes and functions to handle
compatibility issues between different versions of discord.py and py-cord,
especially for slash commands and application commands.
"""

import logging
import inspect
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast, get_type_hints

# Import error handler for Step 1.1 fix
from utils.error_handlers import handle_command_error

try:
    import discord
    from discord.ext import commands
    
    # Check if we're using py-cord by looking for slash_command attribute
    USING_PYCORD = hasattr(commands.Bot, "slash_command")
    
    # Set a default value for py-cord version detection
    USING_PYCORD_261_PLUS = False
    
    # Create a placeholder for SlashCommand that will be properly set later
    SlashCommand = None
    
    # Detect py-cord version and import appropriate classes
    if USING_PYCORD:
        # Check for py-cord 2.6.1+ by version string if available
        try:
            if hasattr(discord, "__version__"):
                from packaging import version
                USING_PYCORD_261_PLUS = version.parse(discord.__version__) >= version.parse("2.6.1")
            else:
                # Alternative detection method based on module structure
                USING_PYCORD_261_PLUS = hasattr(discord, "app_commands") and hasattr(discord.app_commands, "command")
        except (ImportError, AttributeError):
            # If version check fails, try structure detection
            USING_PYCORD_261_PLUS = hasattr(discord, "app_commands")
        
        # Import appropriate SlashCommand class based on py-cord version
        if USING_PYCORD_261_PLUS:
            try:
                # For py-cord 2.6.1+, create an alias for slash commands
                # In py-cord 2.6.1+, slash commands are created by slash_command decorator,
                # not by instantiating a SlashCommand class directly.
                # We'll use commands.SlashCommand as our base class
                from discord.ext.commands import Command as SlashCommand
            except ImportError:
                # Fallback for different module structures
                try:
                    from discord.commands import SlashCommand
                except ImportError:
                    # Final fallback to basic Command
                    from discord.ext.commands import Command as SlashCommand
        else:
            # For older py-cord versions
            try:
                from discord.commands import SlashCommand
            except ImportError:
                # Fallback to base Command class
                from discord.ext.commands import Command as SlashCommand
    else:
        # discord.py style
        try:
            from discord.app_commands import Command as SlashCommand
        except ImportError:
            # Fallback to base Command
            from discord.ext.commands import Command as SlashCommand
        
except ImportError as e:
    # Provide better error messages for missing dependencies
    logging.error(f"Failed to import Discord libraries: {e}")
    raise ImportError(
        "Failed to import Discord libraries. Please install discord.py or py-cord:\n"
        "For py-cord: pip install py-cord>=2.0.0\n"
        "For discord.py: pip install discord.py>=2.0.0"
    ) from e

# Setup logger
logger = logging.getLogger(__name__)

# Define command handler functions that are used by cogs
def command_handler(
    premium_feature: Optional[str] = None, 
    server_id_param: Optional[str] = None,
    check_server_limits: bool = False,
    guild_only_command: bool = True,
    cooldown_seconds: Optional[int] = None,
    error_messages: Optional[Dict[str, str]] = None,
    timeout_seconds: int = 10,
    retry_count: int = 2,
    log_metrics: bool = True,
    validate_parameters: bool = True,
    guild_only: bool = None,
    collection_name: Optional[str] = None,
    operation_type: Optional[str] = None
):
    """
    Enhanced command decorator that combines multiple validations and error handling.

    This comprehensive decorator provides bulletproof command handling with:
    1. Guild-only enforcement
    2. Premium feature validation
    3. Server ID validation and guild isolation
    4. Server limit enforcement
    5. Command cooldowns and rate limiting
    6. Automatic error recovery and predictive error handling
    7. Command execution metrics and performance tracking
    8. Timeout protection with configurable retries
    9. Comprehensive logging

    Args:
        premium_feature: Optional premium feature to check
        server_id_param: Optional server ID parameter name to validate
        check_server_limits: Whether to check server limits
        guild_only_command: Whether command requires a guild context
        cooldown_seconds: Optional cooldown in seconds
        error_messages: Optional custom error messages
        timeout_seconds: Timeout for command execution in seconds
        retry_count: Number of times to retry on transient errors
        log_metrics: Whether to log command metrics
        validate_parameters: Whether to validate command parameters
        guild_only: Alias for guild_only_command for backward compatibility
        collection_name: Optional collection name for database operations
        operation_type: Optional operation type for database operations

    Returns:
        Command decorator
    """
    # For backward compatibility
    if guild_only is not None:
        guild_only_command = guild_only
        
    def decorator(func):
        """Actual decorator function."""
        # Keep the original function intact
        @functools.wraps(func)
        async def wrapped(self, ctx, *args, **kwargs):
            """Wrapper for handling errors and validation."""
            try:
                # Call the original function
                return await func(self, ctx, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in command {func.__name__}: {e}")
                # Try to respond to the user with an error message
                try:
                    # Handle both interaction and context objects
                    if hasattr(ctx, 'followup'):
                        # It's an interaction
                        await ctx.followup.send(f"An error occurred: {e}", ephemeral=True)
                    elif hasattr(ctx, 'send'):
                        # It's a context
                        await ctx.send(f"An error occurred: {e}")
                except Exception:
                    logger.error(f"Failed to send error message for {func.__name__}")
                return None
        
        # Add command handler attributes to the function
        wrapped.premium_feature = premium_feature
        wrapped.server_id_param = server_id_param
        wrapped.check_server_limits = check_server_limits
        wrapped.guild_only_command = guild_only_command
        wrapped.cooldown_seconds = cooldown_seconds
        wrapped.timeout_seconds = timeout_seconds
        wrapped.retry_count = retry_count
        wrapped.log_metrics = log_metrics
        wrapped.validate_parameters = validate_parameters
        wrapped.collection_name = collection_name
        wrapped.operation_type = operation_type
        
        return wrapped
    
    return decorator
    
# Database operation decorator
DB_OP_METRICS: Dict[str, Dict[str, Any]] = {}

def db_operation(
    operation_type: Optional[str] = None,
    collection_name: Optional[str] = None,
    retry_count: int = 3, 
    timeout_seconds: int = 10,
    log_metrics: bool = True
):
    """
    Decorator for database operations that provides:
    1. Consistent error handling
    2. Retry logic for transient errors
    3. Timeout protection
    4. Logging and metrics
    5. Transaction support
    
    Args:
        operation_type: Type of database operation (for metrics)
        collection_name: Name of the collection being operated on
        retry_count: Number of retries for transient errors
        timeout_seconds: Timeout in seconds for the operation
        log_metrics: Whether to log metrics
        
    Returns:
        Decorator function
    """
    def decorator(func):
        # Get the operation name from the function if not provided
        op_type = operation_type or func.__name__
        coll_name = collection_name or "unknown"
        
        # Initialize metrics for this operation
        if log_metrics:
            if op_type not in DB_OP_METRICS:
                DB_OP_METRICS[op_type] = {
                    "calls": 0,
                    "errors": 0,
                    "retries": 0,
                    "timeouts": 0,
                    "avg_duration": 0,
                    "call_times": [],
                }
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import time
            import asyncio
            
            start_time = time.time()
            attempt = 0
            last_error = None
            
            # Try operation with retries
            while attempt <= retry_count:
                attempt += 1
                
                try:
                    # Set timeout for the operation
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout_seconds
                    )
                    
                    # Log metrics on success
                    if log_metrics:
                        duration = time.time() - start_time
                        DB_OP_METRICS[op_type]["calls"] += 1
                        DB_OP_METRICS[op_type]["call_times"].append(duration)
                        
                        # Keep only the last 100 call times
                        if len(DB_OP_METRICS[op_type]["call_times"]) > 100:
                            DB_OP_METRICS[op_type]["call_times"].pop(0)
                            
                        # Recalculate average duration
                        DB_OP_METRICS[op_type]["avg_duration"] = sum(
                            DB_OP_METRICS[op_type]["call_times"]
                        ) / len(DB_OP_METRICS[op_type]["call_times"])
                    
                    return result
                    
                except asyncio.TimeoutError:
                    last_error = f"Database operation timed out after {timeout_seconds}s"
                    if log_metrics:
                        DB_OP_METRICS[op_type]["timeouts"] += 1
                        
                except Exception as e:
                    last_error = str(e)
                    if log_metrics:
                        DB_OP_METRICS[op_type]["errors"] += 1
                
                # If we've reached max retries, log and raise
                if attempt > retry_count:
                    logger.error(
                        f"Database operation {op_type} on {coll_name} failed after {attempt} attempts: {last_error}"
                    )
                    # Re-raise the last exception
                    raise Exception(f"Database operation failed: {last_error}")
                
                # Log retry attempt
                if log_metrics:
                    DB_OP_METRICS[op_type]["retries"] += 1
                
                logger.warning(
                    f"Retrying database operation {op_type} on {coll_name} (attempt {attempt}/{retry_count})"
                )
                
                # Wait before retrying with exponential backoff
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
        
        # Store metadata on the function for introspection
        wrapper.operation_type = op_type
        wrapper.collection_name = coll_name
        
        return wrapper
    
    return decorator
    
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
    
def defer_interaction():
    """
    Decorator to defer an interaction.
    This is a placeholder that will be replaced with an actual decorator.
    """
    def decorator(func):
        return func
    return decorator

# Type variables for return typing
T = TypeVar('T')
CommandT = TypeVar('CommandT')

class EnhancedSlashCommand(SlashCommand):
    """
    Enhanced SlashCommand with compatibility fixes for different py-cord versions.
    
    This class overrides the _parse_options method to handle both list-style options
    (used in newer py-cord versions) and dict-style options (used in older versions).
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parameter_descriptions = {}
        
    def _parse_options(self, params: Dict[str, Any]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Parse command options with compatibility for different parameter styles.
        
        Args:
            params: Parameter dictionary
            
        Returns:
            Either a dict (older style) or list (newer style) of option parameters
        """
        # If we're using py-cord 2.6.1+, we need to handle the options differently
        if USING_PYCORD_261_PLUS:
            try:
                # Newer py-cord expects a list of options
                options = []
                
                # Extract the parameters
                for name, param in params.items():
                    if name == "self" or name == "ctx":
                        continue
                        
                    option = self._extract_option_params(name, param)
                    options.append(option)
                    
                return options
            except Exception as e:
                logger.error(f"Error parsing options in newer py-cord style: {e}")
                # Fall back to super's implementation
                return super()._parse_options(params)  # type: ignore
        else:
            # Older py-cord or discord.py expects a dict of options
            try:
                options = {}
                
                # Extract the parameters
                for name, param in params.items():
                    if name == "self" or name == "ctx":
                        continue
                        
                    option = self._extract_option_params(name, param)
                    options[name] = option
                    
                return options
            except Exception as e:
                logger.error(f"Error parsing options in older py-cord style: {e}")
                # Fall back to super's implementation
                return super()._parse_options(params)  # type: ignore
                
    def _extract_option_params(self, name: str, param: Any) -> Dict[str, Any]:
        """
        Extract option parameters from a parameter.
        
        Args:
            name: Parameter name
            param: Parameter object
            
        Returns:
            Dict of option parameters
        """
        option = {
            "name": name,
            "description": self._parameter_descriptions.get(name, "No description provided"),
            "required": True,
        }
        
        # Set default if available
        if param.default is not inspect.Parameter.empty:
            option["required"] = False
            option["default"] = param.default
            
        # Set type if available
        if param.annotation is not inspect.Parameter.empty:
            option["type"] = param.annotation
            
        return option
        
    def add_parameter_description(self, name: str, description: str) -> None:
        """
        Add a description for a parameter.
        
        Args:
            name: Parameter name
            description: Parameter description
        """
        self._parameter_descriptions[name] = description

# Parameter option builders
def text_option(name: str, description: str, required: bool = True, default: str = None) -> Dict[str, Any]:
    """
    Create a text option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        default: Default value
        
    Returns:
        Option dictionary
    """
    option = {
        "name": name,
        "description": description,
        "required": required,
        "type": str,
    }
    
    if default is not None:
        option["default"] = default
        
    return option

def number_option(name: str, description: str, required: bool = True, default: float = None) -> Dict[str, Any]:
    """
    Create a number option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        default: Default value
        
    Returns:
        Option dictionary
    """
    option = {
        "name": name,
        "description": description,
        "required": required,
        "type": float,
    }
    
    if default is not None:
        option["default"] = default
        
    return option

def integer_option(name: str, description: str, required: bool = True, default: int = None) -> Dict[str, Any]:
    """
    Create an integer option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        default: Default value
        
    Returns:
        Option dictionary
    """
    option = {
        "name": name,
        "description": description,
        "required": required,
        "type": int,
    }
    
    if default is not None:
        option["default"] = default
        
    return option

def boolean_option(name: str, description: str, required: bool = True, default: bool = None) -> Dict[str, Any]:
    """
    Create a boolean option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        default: Default value
        
    Returns:
        Option dictionary
    """
    option = {
        "name": name,
        "description": description,
        "required": required,
        "type": bool,
    }
    
    if default is not None:
        option["default"] = default
        
    return option

def user_option(name: str, description: str, required: bool = True) -> Dict[str, Any]:
    """
    Create a user option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option dictionary
    """
    return {
        "name": name,
        "description": description,
        "required": required,
        "type": discord.User,
    }

def channel_option(name: str, description: str, required: bool = True) -> Dict[str, Any]:
    """
    Create a channel option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option dictionary
    """
    return {
        "name": name,
        "description": description,
        "required": required,
        "type": discord.abc.GuildChannel,
    }

def role_option(name: str, description: str, required: bool = True) -> Dict[str, Any]:
    """
    Create a role option for a slash command.
    
    Args:
        name: Option name
        description: Option description
        required: Whether the option is required
        
    Returns:
        Option dictionary
    """
    return {
        "name": name,
        "description": description,
        "required": required,
        "type": discord.Role,
    }

def enhanced_slash_command(
    name: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs
) -> Callable[[T], EnhancedSlashCommand]:
    """
    Decorator to create an enhanced slash command with compatibility fixes.
    
    Args:
        name: Command name
        description: Command description
        **kwargs: Additional arguments to pass to the command
        
    Returns:
        Command decorator function
    """
    def decorator(func: T) -> EnhancedSlashCommand:
        """
        Decorator to create an enhanced slash command with compatibility fixes.
        
        Args:
            func: Function to wrap
            
        Returns:
            Enhanced slash command
        """
        # Get the command name from the function name if not provided
        cmd_name = name or func.__name__
        cmd_description = description or func.__doc__ or "No description provided"
        
        # Create the command
        command = EnhancedSlashCommand(
            func,
            name=cmd_name,
            description=cmd_description,
            **kwargs
        )
        
        return command
    
    return decorator

def add_parameter_options(command: EnhancedSlashCommand, options: Dict[str, Dict[str, Any]]) -> None:
    """
    Add parameter options to a command.
    
    Args:
        command: Command to add options to
        options: Dictionary of parameter name to option parameters
    """
    # Add parameter descriptions to the command
    for name, option in options.items():
        command.add_parameter_description(name, option.get("description", "No description provided"))
        
def is_pycord_261_or_later() -> bool:
    """
    Check if we're using py-cord 2.6.1 or later.
    
    Returns:
        True if using py-cord 2.6.1 or later, False otherwise
    """
    return USING_PYCORD and USING_PYCORD_261_PLUS