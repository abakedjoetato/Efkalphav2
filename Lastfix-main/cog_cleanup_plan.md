# Cog Cleanup Plan

After reviewing all cogs in the `/cogs` directory, I've identified several duplicate, redundant, or obsolete cogs that can be cleaned up to improve the bot's organization and performance.

## Identified Issues

1. **Multiple versions of the same cog** - Several cogs have multiple versions with different suffixes (like `_fixed`, `_updated`, etc.)
2. **Backup files loaded as cogs** - Although `.bak` files are excluded, some files like `bounties_updated.py` appear to be backups/iterations
3. **Experimental versions** - Some cogs like `simple_bounties.py` appear to be experimental versions
4. **Conflicting implementations** - Multiple implementations of the same feature (like `bounties.py` and `bounties_group.py`)

## Redundant Cog Sets

### Bounties Cogs
- `bounties.py` - Original implementation
- `bounties_fixed.py` - Fixed version for py-cord 2.6.1
- `bounties_updated.py` - Another updated version
- `bounties_group.py` - Alternative implementation using SlashCommandGroup
- `simple_bounties.py` - Simplified version

**Recommendation**: Keep only `bounties_fixed.py` which is the most up-to-date and compatible version.

### Premium Cogs
- `premium.py` - Original implementation
- `premium_new_fixed.py` - Fixed version
- `premium_new_updated.py` - Another updated version
- `premium_new_updated_fixed.py` - Combined updates and fixes

**Recommendation**: Keep only `premium_new_updated_fixed.py` which contains all updates and fixes.

### Stats Cogs
- `stats.py` - Original implementation
- `stats_fixed.py` - Fixed version for py-cord 2.6.1
- `stats_premium_fix.py` - Premium feature fix
- `stats_premium_fix_compat.py` - Compatible premium feature fix

**Recommendation**: Keep only `stats_fixed.py` which has the proper compatibility fixes.

### Setup Cogs
- `setup.py` - Original implementation
- `setup_fixed.py` - Fixed version for py-cord 2.6.1

**Recommendation**: Keep only `setup_fixed.py`.

### CSV Processor Cogs
- `csv_processor.py` - Original implementation
- `new_csv_processor.py` - Updated version

**Recommendation**: Keep only `new_csv_processor.py` which appears to be the newer implementation.

### Rivalries Cogs
- `rivalries.py` - Original implementation
- `rivalries_fixed.py` - Fixed version for py-cord 2.6.1

**Recommendation**: Keep only `rivalries_fixed.py`.

## Implementation Plan

1. Create a backup directory: `cogs_backup/`
2. Move all redundant cogs to the backup directory
3. Update the cog loading logic in `replit_run.py` to load only the recommended cogs
4. Test to ensure all functionality works properly

## Cogs to Keep

- `admin.py`
- `bounties_fixed.py`
- `cog_template_fixed.py`
- `economy.py`
- `error_handling_cog.py`
- `events.py`
- `factions.py`
- `general.py`
- `guild_settings.py`
- `help.py`
- `killfeed.py`
- `log_processor.py`
- `new_csv_processor.py`
- `player_links.py`
- `premium_new_updated_fixed.py`
- `rivalries_fixed.py`
- `setup_fixed.py`
- `sftp_commands.py`
- `stats_fixed.py`

## Cogs to Move to Backup

- `bounties.py`
- `bounties_group.py`
- `bounties_updated.py`
- `csv_processor.py`
- `premium.py`
- `premium_new_fixed.py`
- `premium_new_updated.py`
- `rivalries.py`
- `setup.py`
- `simple_bounties.py`
- `stats.py`
- `stats_premium_fix.py`
- `stats_premium_fix_compat.py`
- All `.bak` files