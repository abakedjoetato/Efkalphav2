# Cog Migration Guide

This guide explains the recent changes to the cog system in the Discord bot. We've cleaned up the codebase by removing redundant and duplicate cogs, while keeping only the most up-to-date and compatible versions.

## Changes Made

1. Created a backup directory `cogs_backup/` to store redundant cogs
2. Moved all redundant and duplicate cogs to the backup directory
3. Updated the cog loading logic in `replit_run.py` to explicitly load only the necessary cogs
4. Improved the cog loading order to ensure critical cogs are loaded first

## Cogs Retained

The following cogs have been retained in the `cogs/` directory:

### Critical/Infrastructure Cogs
- `error_handling_cog.py` - Error handling system
- `general.py` - Basic bot commands
- `admin.py` - Admin commands
- `help.py` - Help system

### Feature Cogs
- `setup_fixed.py` - Server setup commands
- `bounties_fixed.py` - Bounty system
- `premium_new_updated_fixed.py` - Premium features
- `stats_fixed.py` - Player statistics
- `rivalries_fixed.py` - Player rivalries
- `new_csv_processor.py` - CSV processing
- `events.py` - Event handling
- `economy.py` - Economy system
- `factions.py` - Faction management
- `guild_settings.py` - Guild settings
- `killfeed.py` - Kill feed
- `log_processor.py` - Log processing
- `player_links.py` - Player linking
- `sftp_commands.py` - SFTP commands

### Optional/Template Cogs
- `cog_template_fixed.py` - Template for new cogs

## Cogs Moved to Backup

The following cogs have been backed up to `cogs_backup/`:

1. Redundant Bounty Cogs:
   - `bounties.py` - Original implementation
   - `bounties_group.py` - Alternative implementation
   - `bounties_updated.py` - Partial update
   - `simple_bounties.py` - Simplified version

2. Redundant Premium Cogs:
   - `premium.py` - Original implementation
   - `premium_new_fixed.py` - Fixed version
   - `premium_new_updated.py` - Updated version

3. Redundant Stats Cogs:
   - `stats.py` - Original implementation
   - `stats_premium_fix.py` - Premium feature fix
   - `stats_premium_fix_compat.py` - Compatible premium feature fix

4. Redundant Setup Cogs:
   - `setup.py` - Original implementation

5. Redundant CSV Processor Cogs:
   - `csv_processor.py` - Original implementation

6. Redundant Rivalries Cogs:
   - `rivalries.py` - Original implementation

7. Backup Files:
   - All `.bak` files for every cog

## Updated Cog Loading Logic

The cog loading logic in `replit_run.py` has been updated to:

1. Load critical infrastructure cogs first
2. Load feature cogs in a specific order
3. Load optional/template cogs last

This ensures proper initialization and dependency resolution.

## How to Add New Cogs

When adding a new cog:

1. Use `cog_template_fixed.py` as a starting point
2. Add the cog to the appropriate section in `replit_run.py`
3. Follow the naming convention: use `_fixed` suffix for cogs with py-cord 2.6.1 compatibility fixes

## Troubleshooting

If a cog fails to load:

1. Check the error message in the logs
2. Ensure the cog is compatible with py-cord 2.6.1
3. If necessary, apply the compatibility patches from `utils/discord_patches.py`

For assistance, refer to the compatibility fixes in the existing cogs.