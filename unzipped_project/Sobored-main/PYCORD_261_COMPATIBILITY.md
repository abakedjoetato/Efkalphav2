# py-cord 2.6.1 Compatibility Guide

This document details the specific breaking changes in py-cord 2.6.1 and how our compatibility layers address them.

## Breaking Changes in py-cord 2.6.1

### 1. SlashCommandGroup Implementation Changes

py-cord 2.6.1 significantly changed how `SlashCommandGroup` works:

- The initialization signature changed, particularly affecting `guild_ids` handling
- Subgroups must be created differently
- Parent-child relationships between command groups need to be managed manually
- Adding commands to groups works differently

### 2. Interaction Response Handling

Interaction response handling is stricter in 2.6.1:

- Interactions must be responded to within 3 seconds or deferred
- The library throws specific errors when an interaction is responded to more than once
- Original response access requires different patterns

### 3. Command Context Differences

The context object for commands has changed:

- Some attributes are accessed differently
- Permission checking mechanisms changed
- Interaction handling between slash commands and UI components differs

### 4. MongoDB Operation Changes

While not directly related to py-cord, we've addressed common MongoDB issues:

- Better handling of server selection timeout errors
- Proper operation retries for transient failures
- Consistent error handling across all database operations

## Compatibility Solutions

### Compatibility Modules

We've created dedicated compatibility modules to address these issues:

1. `utils/discord_compat.py` - Discord API compatibility layer
2. `utils/interaction_handlers.py` - Interaction handling utilities
3. `utils/safe_mongodb_compat.py` - Safe MongoDB operations
4. `cogs/cog_template_fixed.py` - Example cog with proper implementations

### SlashCommandGroup Compatibility

The `create_slash_group` and `create_subgroup` functions in `discord_compat.py` handle the differences in initialization and parent-child relationships between command groups:

```python
def create_slash_group(
    name: str,
    description: str,
    parent: Optional[Any] = None,
    guild_ids: Optional[List[int]] = None,
    guild_only: bool = False
) -> discord.SlashCommandGroup:
    # Compatibility implementation...
    
def create_subgroup(
    parent: discord.SlashCommandGroup,
    name: str,
    description: str,
    guild_only: bool = False
) -> discord.SlashCommandGroup:
    # Compatibility implementation...
```

These functions check for the availability of certain methods and attributes in the current py-cord version and use appropriate fallbacks when necessary.

### Interaction Response Compatibility

The `safely_respond_to_interaction` function in `interaction_handlers.py` handles the differences in interaction response handling:

```python
async def safely_respond_to_interaction(
    interaction: discord.Interaction,
    content: Optional[str] = None,
    *,
    embed: Optional[discord.Embed] = None,
    # other parameters...
) -> bool:
    # Check if we need to use followup or not
    if interaction.response.is_done():
        # Use followup
        # ...
    else:
        # Initial response
        # ...
```

This function handles different edge cases like:
- Already responded interactions
- Timed-out interactions
- Network errors
- Response chunking for large content

### Safe Database Operations

The `safe_mongodb_compat.py` module provides a consistent interface for MongoDB operations with proper error handling:

```python
async def find_one(
    collection_name: str,
    filter: Dict[str, Any],
    database_name: Optional[str] = None,
    **kwargs
) -> SafeMongoDBResult[Optional[Dict[str, Any]]]:
    # Safe implementation that handles errors consistently
```

The `SafeMongoDBResult` class wraps all database operation results with proper error information, making error handling consistent across the codebase.

## Version Detection and Adaptive Behavior

The compatibility layer detects the version of py-cord being used and adapts its behavior accordingly:

```python
# Version detection
discord_version = getattr(discord, "__version__", "unknown")
is_pycord = hasattr(discord, "__version__") and discord.__version__.startswith("2.")
is_pycord_261 = is_pycord and discord.__version__.startswith("2.6.1")
```

This allows the compatibility functions to use different implementations based on the detected version.

## Common Issues and Solutions

### 1. SlashCommand "command" Attribute Missing

**Issue**: In py-cord 2.6.1, the `SlashCommand` object no longer has a `command` attribute, which breaks code that accesses it.

**Solution**: The compatibility layer avoids using the `.command` attribute and provides alternative ways to access command information.

### 2. Interaction Already Responded To

**Issue**: py-cord 2.6.1 throws `InteractionResponded` errors if you try to respond to an interaction more than once.

**Solution**: `safely_respond_to_interaction` function handles this by checking if the interaction has already been responded to and using followup messages in that case.

### 3. Defer Timing Issues

**Issue**: py-cord 2.6.1 is stricter about deferring interactions within the 3-second window.

**Solution**: `safe_defer` function handles this with proper error management and logging.

### 4. MongoDB Connection Issues

**Issue**: MongoDB connections can fail in various ways, especially in production environments.

**Solution**: `SafeMongoDBClient` includes retry logic, connection pooling, and consistent error handling.

## Testing Your Cog Compatibility

After migrating your cogs, test them thoroughly with both interactive users and programmatically:

1. Check all slash commands work with proper responses
2. Verify error handling shows user-friendly messages
3. Test database operations with both valid and invalid data
4. Test interaction timeouts and response limits

## Debugging Tips

When debugging compatibility issues, look for these common patterns:

1. Check for direct attribute access that might have changed in 2.6.1
2. Look for interaction response patterns that might need to use the safe response helpers
3. Verify MongoDB operations use the safe versions with proper error handling
4. Ensure slash command groups are created with the compatibility helpers

## Performance Considerations

The compatibility layers add minimal overhead while ensuring that your code works reliably. Some specific optimizations include:

1. Lazy imports to reduce startup time
2. Caching of version detection results
3. Efficient error handling that avoids excessive logging
4. Connection pooling for MongoDB operations

## Future Compatibility

The compatibility layers are designed to support future versions of py-cord with minimal changes:

1. Version detection allows for version-specific behavior
2. Abstract interfaces that can adapt to future API changes
3. Comprehensive error handling that can accommodate new error types
4. Modular design that allows for targeted updates