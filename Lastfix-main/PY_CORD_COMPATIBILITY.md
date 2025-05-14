# py-cord 2.6.1 Compatibility Guide

This document outlines the changes made to ensure compatibility with py-cord 2.6.1 when using slash commands and SlashCommandGroups.

## Issue Overview

In py-cord 2.6.1, there are several changes to how slash commands work compared to earlier versions or discord.py:

1. The `SlashCommandGroup` object's functionality has changed and no longer has `.command()` in some contexts
2. The `@option` decorator approach has been replaced with a different parameter style
3. The `describe` decorator may not be available 
4. Command handler decorators may not properly apply to slash commands

## Solution Approach

### SlashCommandGroup Usage

Use the direct class rather than decorator approach:

```python
# INCORRECT for py-cord 2.6.1
@commands.slash_command(name="bounty", description="...")
async def bounty(self, ctx):
    pass

@bounty.command() # This fails in py-cord 2.6.1
async def place(self, ctx, ...):
    # command implementation
```

```python
# CORRECT for py-cord 2.6.1
# Define the command group as a class variable
bounty = discord.SlashCommandGroup(name="bounty", description="...")

# Define commands within the group
@bounty.command(name="place", description="...")
async def bounty_place(self, ctx, ...):
    # command implementation
```

### Parameter Definitions

Use `discord.Option` for parameters instead of `@option` decorator:

```python
# INCORRECT for py-cord 2.6.1
@bounty.command()
@option("player_name", str, description="Name of the player")
@option("amount", int, description="Amount of currency")
async def place(self, ctx, player_name, amount):
    # command implementation
```

```python
# CORRECT for py-cord 2.6.1
@bounty.command()
async def place(
    self, 
    ctx,
    player_name: discord.Option(str, "Name of the player"),
    amount: discord.Option(int, "Amount of currency")
):
    # command implementation
```

### Response Handling

Use the most appropriate response method based on available objects:

```python
# Check for 'respond' method (most common in py-cord 2.6.1)
if hasattr(ctx, 'respond'):
    await ctx.respond("Message")
# Fallback to 'send' for ApplicationContext
elif hasattr(ctx, 'send'):
    await ctx.send("Message")
# Final fallback to channel send
elif hasattr(ctx, 'channel'):
    await ctx.channel.send("Message")
```

## Fixed Files

We have created fixed versions of the cogs with py-cord 2.6.1 compatibility:

- **cogs/bounties_fixed.py**: The bounties cog with proper SlashCommandGroup implementation
- **utils/safe_mongodb.py**: Safe MongoDB result handling
- **utils/interaction_handlers.py**: Helper functions for interaction handling

## Testing

You can test the fixed commands by running:

```bash
python test_bot.py
```

This will load the fixed bounties cog and register the commands with Discord.

## Remaining Work

Additional cogs in the codebase will need similar fixes:

1. Replace `@commands.slash_command` + `@command` approach with `SlashCommandGroup` class
2. Update parameter definitions to use `discord.Option`
3. Update response handling to use context-appropriate methods

By applying these changes consistently, the bot will be fully compatible with py-cord 2.6.1.