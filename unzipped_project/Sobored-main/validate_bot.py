"""
Bot Validation Script

This script validates that the bot can start up correctly and load essential components.
"""

import asyncio
import logging
import os
import sys
import traceback
from typing import List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bot_validator')

async def validate_bot_startup():
    """
    Validate that the bot can start up successfully.
    
    Returns:
        bool: True if startup successful, False otherwise
    """
    try:
        # Import bot and apply patches
        try:
            from utils.discord_patches import patch_all
            patch_all()
            logger.info("Applied Discord patches successfully")
        except ImportError:
            logger.warning("Could not import discord_patches")
        
        # Create bot instance
        from bot import Bot
        bot = Bot(production=False)
        logger.info("Created bot instance successfully")
        
        # Start database
        db_success = await bot.init_db()
        if not db_success:
            logger.error("Failed to initialize database")
            return False
            
        logger.info("Database initialized successfully")
        
        # Load a safe subset of cogs
        safe_cogs = [
            "cogs.error_handling",
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
                logger.warning(f"Failed to load cog {cog_name}: {e}")
                
        logger.info(f"Loaded {loaded_count}/{len(safe_cogs)} cogs")
        
        # Verify event handlers
        if not hasattr(bot, "_listeners") or not bot._listeners:
            logger.warning("No event listeners registered")
        else:
            event_counts = {}
            for event_name, handlers in bot._listeners.items():
                event_counts[event_name] = len(handlers)
                
            logger.info(f"Event listeners registered: {event_counts}")
            
        # Verify command registration
        command_count = len(bot.commands) if hasattr(bot, "commands") else 0
        logger.info(f"Bot has {command_count} commands registered")
        
        # Verify intents
        intents = bot.intents if hasattr(bot, "intents") else None
        if intents:
            logger.info(f"Bot intents: {intents}")
            
        if hasattr(bot, "tree") and bot.tree:
            app_commands_count = len(bot.tree.get_commands())
            logger.info(f"Bot has {app_commands_count} application commands registered")
            
        logger.info("Bot startup validation completed successfully")
        
        # Clean up
        await bot.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Bot validation failed: {e}")
        traceback.print_exc()
        return False

async def validate_bot_components():
    """
    Validate that critical bot components exist and are properly structured.
    
    Returns:
        Tuple[bool, List[str]]: Success indicator and list of issues found
    """
    issues = []
    
    # Check for critical files
    critical_files = [
        "bot.py",
        "utils/discord_patches.py",
        "utils/discord_compat.py",
        "utils/command_imports.py",
        "utils/safe_mongodb.py",
        "utils/event_dispatcher.py"
    ]
    
    for file_path in critical_files:
        if not os.path.exists(file_path):
            issues.append(f"Missing critical file: {file_path}")
            
    # Check for critical directories
    critical_dirs = [
        "cogs",
        "utils",
        "models"
    ]
    
    for dir_path in critical_dirs:
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            issues.append(f"Missing critical directory: {dir_path}")
    
    # Validate environment variables
    if not os.environ.get("DISCORD_TOKEN"):
        issues.append("Missing DISCORD_TOKEN environment variable")
        
    if not os.environ.get("MONGODB_URI"):
        issues.append("Missing MONGODB_URI environment variable")
        
    # Check for cogs
    if os.path.exists("cogs"):
        cog_count = len([f for f in os.listdir("cogs") if f.endswith(".py") and not f.startswith("__")])
        if cog_count < 2:
            issues.append(f"Insufficient cogs found: {cog_count} (expected at least 2)")
            
    # Final validation
    if issues:
        logger.warning(f"Found {len(issues)} issues during component validation")
        for issue in issues:
            logger.warning(f"- {issue}")
        return False, issues
    
    logger.info("All critical components validated successfully")
    return True, []

async def test_command_system():
    """
    Test the command system by checking command registration and handling.
    
    Returns:
        bool: True if the command system is working properly
    """
    try:
        # Import bot and apply patches
        try:
            from utils.discord_patches import patch_all
            patch_all()
            logger.info("Applied Discord patches for command system test")
        except ImportError:
            logger.warning("Could not import discord_patches")
        
        # Create bot instance
        from bot import Bot
        bot = Bot(production=False)
        logger.info("Created bot instance for command system test")
        
        # Create a test command
        from discord.ext import commands
        
        @bot.command(name="test_validation")
        async def test_command(ctx):
            return "Test passed"
            
        # Check if the command was registered
        cmd = bot.get_command("test_validation")
        if not cmd:
            logger.error("Failed to register test command")
            return False
            
        logger.info("Test command registered successfully")
        
        # Check hybrid commands if available
        has_hybrid_commands = hasattr(bot, "tree") or hasattr(commands, "hybrid_command")
        logger.info(f"Hybrid commands available: {has_hybrid_commands}")
        
        # Check slash commands
        has_slash_commands = hasattr(commands, "slash_command") or hasattr(bot, "add_application_command")
        logger.info(f"Slash commands available: {has_slash_commands}")
        
        # Verify command tree
        if hasattr(bot, "tree"):
            logger.info("Command tree is available")
            
        # Verify command handling
        import inspect
        if not inspect.iscoroutinefunction(cmd.callback):
            logger.warning("Command callback is not a coroutine function")
            
        # Close the bot
        await bot.close()
        
        return True
    except Exception as e:
        logger.error(f"Command system test failed: {e}")
        traceback.print_exc()
        return False

async def validate_all_cogs():
    """
    Validate that all cogs can be loaded.
    
    Returns:
        Tuple[int, int]: (loaded count, failed count)
    """
    try:
        # Import bot and apply patches
        try:
            from utils.discord_patches import patch_all
            patch_all()
            logger.info("Applied Discord patches successfully")
        except ImportError:
            logger.warning("Could not import discord_patches")
        
        # Create bot instance
        from bot import Bot
        bot = Bot(production=False)
        logger.info("Created bot instance for cog validation")
        
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
        failed_cogs = []
        
        for cog_name in cogs:
            try:
                if hasattr(bot, "load_extension_async"):
                    await bot.load_extension_async(cog_name)
                else:
                    bot.load_extension(cog_name)
                loaded_count += 1
                logger.info(f"Successfully loaded cog: {cog_name}")
            except Exception as e:
                failed_count += 1
                failed_cogs.append((cog_name, str(e)))
                logger.error(f"Failed to load cog {cog_name}: {e}")
                
        # Report results
        logger.info(f"Cog validation: {loaded_count} loaded, {failed_count} failed")
        if failed_count > 0:
            logger.warning("Failed cogs:")
            for cog, error in failed_cogs:
                logger.warning(f"- {cog}: {error}")
        
        # Clean up
        await bot.close()
        
        return loaded_count, failed_count
        
    except Exception as e:
        logger.error(f"Cog validation failed with exception: {e}")
        traceback.print_exc()
        return 0, -1

async def main():
    """Run all validation tests"""
    logger.info("Starting Discord bot validation")
    
    # Validate components first
    components_valid, issues = await validate_bot_components()
    if not components_valid:
        logger.error("Component validation failed, skipping startup test")
        sys.exit(1)
        
    # Test command system
    cmd_system_valid = await test_command_system()
    if not cmd_system_valid:
        logger.error("Command system validation failed")
        logger.warning("Continuing with other tests anyway...")
    else:
        logger.info("Command system validation passed successfully")
    
    # Then validate startup
    startup_valid = await validate_bot_startup()
    if not startup_valid:
        logger.error("Startup validation failed")
        sys.exit(1)
    else:
        logger.info("Startup validation passed successfully")
    
    # Finally validate all cogs
    loaded_count, failed_count = await validate_all_cogs()
    if failed_count > 0:
        logger.warning(f"Some cogs failed to load ({failed_count} failures)")
    elif failed_count < 0:
        logger.error("Cog validation failed with an unexpected error")
        sys.exit(1)
    else:
        logger.info(f"Successfully loaded all {loaded_count} cogs")
        
    logger.info("All validation tests completed")
    
    # Overall success determination
    if cmd_system_valid and startup_valid and (failed_count == 0):
        logger.info("✅ ALL VALIDATION TESTS PASSED SUCCESSFULLY")
        return True
    else:
        logger.warning("⚠️ SOME VALIDATION TESTS FAILED - CHECK LOGS FOR DETAILS")
        return False

if __name__ == "__main__":
    asyncio.run(main())