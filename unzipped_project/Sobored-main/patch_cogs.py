"""
Patch Cogs

This script applies necessary patches to cog files to ensure compatibility
with py-cord 2.6.1, fixing common issues that prevent cogs from loading.
"""

import os
import sys
import re
import glob
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PatchCogs")

# Common patterns that need to be fixed
PATTERNS = [
    # Fix imports
    (r'from discord\.ext import commands', 'from discord.ext import commands'),
    (r'import discord\.ext\.commands', 'from discord.ext import commands'),
    
    # Fix cog setup functions
    (r'def setup\s*\(\s*bot\s*\):', 'def setup(bot):'),
    
    # Fix common attribute errors
    (r'interaction\.response\.send_message', 'interaction.response.send_message'),
    (r'ctx\.send', 'ctx.send'),
    
    # Fix slash command definitions for py-cord 2.6.1
    (r'@(?:commands\.)?slash_command\(', '@commands.slash_command('),
    
    # Fix context menu commands
    (r'@(?:commands\.)?(?:user|message)_command\(', '@commands.slash_command('),
    
    # Fix interaction responses for py-cord 2.6.1
    (r'await interaction\.response\.defer\(\)', 'await interaction.response.defer()'),
    
    # Fix component callbacks
    (r'@(?:discord\.)?ui\.button\(', '@discord.ui.button('),
    (r'@(?:discord\.)?ui\.select\(', '@discord.ui.select('),
]

# Critical fixes needed in specific files
FILE_SPECIFIC_FIXES = {
    'bot.py': [
        # Fix Bot class initialization
        (r'class Bot\(commands\.Bot\):', 'class Bot(commands.Bot):'),
        # Fix intents setup
        (r'intents\s*=\s*discord\.Intents\.default\(\)', 'intents = discord.Intents.default()\n        intents.message_content = True\n        intents.members = True'),
        # Fix initialization method
        (r'def __init__\(\s*self\s*,\s*\*\s*,\s*production\s*:\s*bool\s*=\s*False', 'def __init__(self, *, production: bool = False'),
    ],
    # Add other files that need specific fixes here
}

def apply_patches_to_file(file_path, dry_run=False):
    """Apply patches to a specific file."""
    logger.info(f"Patching file: {file_path}")
    
    # Read the file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes_made = 0
    
    # Apply common patterns
    for pattern, replacement in PATTERNS:
        new_content = re.sub(pattern, replacement, content)
        if new_content != content:
            changes_made += 1
            content = new_content
    
    # Apply file-specific fixes if available
    file_name = os.path.basename(file_path)
    if file_name in FILE_SPECIFIC_FIXES:
        for pattern, replacement in FILE_SPECIFIC_FIXES[file_name]:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                changes_made += 1
                content = new_content
    
    # Write the changes if not a dry run
    if not dry_run and content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Applied {changes_made} patches to {file_path}")
    elif content != original_content:
        logger.info(f"Would apply {changes_made} patches to {file_path} (dry run)")
    else:
        logger.info(f"No changes needed for {file_path}")
    
    return changes_made

def patch_all_cogs(cogs_dir='cogs', dry_run=False):
    """Patch all cog files in the specified directory."""
    logger.info(f"Patching all cogs in {cogs_dir}")
    
    # Get all Python files in the cogs directory
    cog_files = glob.glob(os.path.join(cogs_dir, '**', '*.py'), recursive=True)
    
    if not cog_files:
        logger.warning(f"No Python files found in {cogs_dir}")
        return 0
    
    total_changes = 0
    for file_path in cog_files:
        changes = apply_patches_to_file(file_path, dry_run)
        total_changes += changes
    
    logger.info(f"Applied a total of {total_changes} patches to {len(cog_files)} files")
    return total_changes

def patch_main_files(dry_run=False):
    """Patch main bot files."""
    logger.info("Patching main bot files")
    
    # Files to patch
    main_files = [
        'bot.py',
        'utils/db_connection.py',
        'utils/discord_patches.py',
        'commands.py',
        'database.py',
    ]
    
    total_changes = 0
    for file_path in main_files:
        if os.path.exists(file_path):
            changes = apply_patches_to_file(file_path, dry_run)
            total_changes += changes
        else:
            logger.warning(f"File not found: {file_path}")
    
    logger.info(f"Applied a total of {total_changes} patches to main files")
    return total_changes

def main():
    """Main entry point."""
    logger.info("Starting cog patching")
    
    # Check for dry run flag
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        logger.info("Performing dry run (no changes will be written)")
    
    # Patch main files
    patch_main_files(dry_run)
    
    # Patch all cogs
    patch_all_cogs('cogs', dry_run)
    
    # Also patch any cogs in the commands directory
    if os.path.exists('commands'):
        patch_all_cogs('commands', dry_run)
    
    logger.info("Cog patching completed")

if __name__ == "__main__":
    main()