# Cog Compliance Requirements

This document outlines the compliance requirements for cogs in the Tower of Temptation Discord bot. All cogs must adhere to these requirements to ensure system-wide integrity and compatibility.

## Table of Contents

1. [Command Structure Compliance](#command-structure-compliance)
2. [Error Handling Compliance](#error-handling-compliance)
3. [Database Access Compliance](#database-access-compliance)
4. [Interaction Handling Compliance](#interaction-handling-compliance)
5. [Premium Feature Compliance](#premium-feature-compliance)
6. [Multi-Guild Compliance](#multi-guild-compliance)
7. [Async/Await Compliance](#asyncawait-compliance)
8. [Compliance Verification](#compliance-verification)

## Command Structure Compliance

All cogs must follow the standardized command structure:

1. **SlashCommandGroup Definition**:
   - Define all command groups as class variables using `discord.SlashCommandGroup`
   - Do not use the `@commands.slash_command` + `@command_name.command()` pattern

2. **Command Parameters**:
   - Use `discord.Option` for all parameter definitions
   - Do not use `@option` or `@describe` decorators
   - Provide descriptive help text for all parameters

3. **Command Registration**:
   - Implement a `setup(bot)` function that adds the cog to the bot
   - Properly register all commands with appropriate permissions

## Error Handling Compliance

All cogs must follow the standardized error handling approach:

1. **Explicit Error Checking**:
   - Check the result of all operations explicitly before accessing results
   - Use safe accessors for attributes and dictionary keys
   - Provide user-friendly error messages

2. **Error Propagation**:
   - Do not silence exceptions unless absolutely necessary
   - Log all errors with appropriate context
   - Return appropriate error responses to users

3. **Retry Logic**:
   - Implement retry logic for network operations
   - Use exponential backoff for retries
   - Limit the number of retries to prevent resource exhaustion

## Database Access Compliance

All cogs must follow the standardized database access patterns:

1. **Safe Access Functions**:
   - Use the functions from `utils.safe_mongodb_compat` for all database operations
   - Do not directly call MongoDB methods
   - Properly handle the result object returned by safe functions

2. **Data Validation**:
   - Validate all data before inserting or updating
   - Check that required fields are present and of correct types
   - Sanitize user input to prevent injection attacks

3. **Document Structure**:
   - Use consistent document structure across collections
   - Include metadata fields (creator, creation time, etc.)
   - Use safe getters to access document fields

## Interaction Handling Compliance

All cogs must follow the standardized interaction handling approach:

1. **Response Functions**:
   - Use the functions from `utils.interaction_handlers` for all responses
   - Do not directly call `ctx.respond()`, `ctx.send()`, or similar methods
   - Use the appropriate response type (message, ephemeral, etc.)

2. **Deferred Responses**:
   - Use `defer_response()` for operations that may take time
   - Provide progress updates for long-running operations
   - Use ephemeral responses for user-specific information

3. **Message Components**:
   - Use standardized components (buttons, select menus, etc.)
   - Implement proper timeout handling for components
   - Provide fallback methods for users who can't use components

## Premium Feature Compliance

All cogs must follow the standardized premium feature verification:

1. **Feature Gating**:
   - Check for premium status before allowing access to premium features
   - Use the premium verification utilities from `utils.premium_verification`
   - Provide clear messages for users without premium access

2. **Guild Scope**:
   - Premium features must be scoped to guilds, not users
   - Check guild premium status, not user premium status
   - Use the functions from `utils.interaction_handlers` to get guild IDs

3. **Premium Feature Definition**:
   - Clearly document which features are premium
   - Define premium feature flags in a centralized location
   - Use consistent naming for premium features

## Multi-Guild Compliance

All cogs must follow the standardized multi-guild approach:

1. **Guild Isolation**:
   - All data must be scoped to guilds using guild IDs
   - Do not assume single-guild context
   - Use the functions from `utils.interaction_handlers` to get guild IDs

2. **Guild Verification**:
   - Verify that commands are used in a guild context
   - Provide appropriate error messages for DM contexts
   - Check that the user has appropriate permissions in the guild

3. **Cross-Guild Data**:
   - Do not share data between guilds unless explicitly designed to do so
   - Use guild-specific configurations
   - Implement proper access controls for cross-guild features

## Async/Await Compliance

All cogs must follow the standardized async/await patterns:

1. **Proper Async Usage**:
   - Use `async`/`await` correctly for all asynchronous operations
   - Do not block the event loop with synchronous operations
   - Use `asyncio.to_thread()` for CPU-bound operations

2. **Background Tasks**:
   - Register background tasks with the bot's task system
   - Implement proper error handling in background tasks
   - Ensure tasks clean up resources properly

3. **Cancellation Handling**:
   - Handle task cancellation gracefully
   - Release resources when tasks are cancelled
   - Do not suppress CancelledError

## Compliance Verification

To verify compliance of a cog, use the following tools:

1. **Compatibility Checker**:
   ```bash
   python verify_compatibility.py --cog=your_cog_name --verbose
   ```

2. **Test Harness**:
   ```bash
   python test_migrated_cog.py --cog=your_cog_name --verbose
   ```

3. **Integration Test**:
   ```bash
   python integration_test.py --cogs=your_cog_name --verbose
   ```

A cog is considered compliant when:
1. All compatibility checks pass
2. All test harness checks pass
3. All integration tests pass
4. The cog meets all the requirements in this document

Cogs that are not compliant will not be loaded by the bot in production mode.