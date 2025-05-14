"""
Database Cog

This cog provides commands for database operations and management.
"""

import logging
import discord
from discord.ext import commands
import os
import io
import asyncio
from typing import Optional, Union
from datetime import datetime

# Import MongoDB models
from utils.mongodb_models import Guild, User
from utils.premium_feature_access import requires_premium_feature

# Configure logger
logger = logging.getLogger("cogs.database")

class Database(commands.Cog):
    """
    Database operations cog
    
    This cog provides commands for database operations.
    """
    
    def __init__(self, bot):
        """
        Initialize the cog
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        
    @property
    def db_client(self):
        """
        Get the MongoDB client
        
        Returns:
            SafeMongoDBClient: MongoDB client
        """
        return getattr(self.bot, '_db_client', None)
        
    @commands.group(name="db", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def db_group(self, ctx):
        """
        Database commands
        
        This command group provides access to database operations.
        Use a subcommand to perform specific operations.
        """
        if ctx.invoked_subcommand is None:
            # Show help for the group
            await ctx.send_help(ctx.command)
            
    @db_group.command(name="guild")
    @commands.has_permissions(administrator=True)
    async def guild_info(self, ctx):
        """
        View guild database info
        
        This command shows information about the guild in the database.
        """
        if not self.db_client:
            await ctx.send("❌ Database not connected")
            return
            
        try:
            # Get the guild from the database
            guild = await Guild.get_by_guild_id(self.db_client, ctx.guild.id)
            
            if guild:
                # Format the guild information
                embed = discord.Embed(
                    title="Guild Database Info",
                    description=f"Information for guild {ctx.guild.name} in the database",
                    color=0x00a8ff
                )
                
                embed.add_field(
                    name="ID",
                    value=str(guild._id),
                    inline=True
                )
                
                embed.add_field(
                    name="Guild ID",
                    value=str(guild.guild_id),
                    inline=True
                )
                
                embed.add_field(
                    name="Name",
                    value=guild.name,
                    inline=True
                )
                
                embed.add_field(
                    name="Owner ID",
                    value=str(guild.owner_id),
                    inline=True
                )
                
                embed.add_field(
                    name="Prefix",
                    value=guild.prefix,
                    inline=True
                )
                
                # Format settings
                settings_str = "\n".join([f"**{k}**: {v}" for k, v in guild.settings.items()]) or "No custom settings"
                
                embed.add_field(
                    name="Settings",
                    value=settings_str,
                    inline=False
                )
                
                # Format timestamps
                embed.add_field(
                    name="Created At",
                    value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
                
                embed.add_field(
                    name="Updated At",
                    value=guild.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
                
                await ctx.send(embed=embed)
            else:
                # Guild not found in database
                await ctx.send("❓ Guild not found in database. Creating new entry...")
                
                # Create a new guild entry
                guild = Guild(
                    guild_id=ctx.guild.id,
                    name=ctx.guild.name,
                    owner_id=ctx.guild.owner_id,
                    prefix="!",
                    settings={}
                )
                
                # Save the guild
                if await guild.save(self.db_client):
                    await ctx.send("✅ Guild entry created in database")
                else:
                    await ctx.send("❌ Failed to create guild entry in database")
        except Exception as e:
            logger.error(f"Error getting guild info: {e}")
            await ctx.send(f"❌ Error: {e}")
            
    @db_group.command(name="prefix")
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, prefix: str):
        """
        Set custom command prefix
        
        This command sets a custom command prefix for the guild.
        
        Args:
            prefix: New command prefix
        """
        if not self.db_client:
            await ctx.send("❌ Database not connected")
            return
            
        try:
            # Get the guild from the database
            guild = await Guild.get_by_guild_id(self.db_client, ctx.guild.id)
            
            if not guild:
                # Guild not found in database, create it
                guild = Guild(
                    guild_id=ctx.guild.id,
                    name=ctx.guild.name,
                    owner_id=ctx.guild.owner_id,
                    prefix=prefix,
                    settings={}
                )
            else:
                # Update the prefix
                guild.prefix = prefix
                
            # Save the guild
            if await guild.save(self.db_client):
                await ctx.send(f"✅ Command prefix set to `{prefix}`")
            else:
                await ctx.send("❌ Failed to set command prefix")
        except Exception as e:
            logger.error(f"Error setting prefix: {e}")
            await ctx.send(f"❌ Error: {e}")
            
    @db_group.command(name="setting")
    @commands.has_permissions(administrator=True)
    async def set_setting(self, ctx, key: str, value: str):
        """
        Set a guild setting
        
        This command sets a custom setting for the guild.
        
        Args:
            key: Setting key
            value: Setting value
        """
        if not self.db_client:
            await ctx.send("❌ Database not connected")
            return
            
        try:
            # Get the guild from the database
            guild = await Guild.get_by_guild_id(self.db_client, ctx.guild.id)
            
            if not guild:
                # Guild not found in database, create it
                guild = Guild(
                    guild_id=ctx.guild.id,
                    name=ctx.guild.name,
                    owner_id=ctx.guild.owner_id,
                    prefix="!",
                    settings={key: value}
                )
            else:
                # Update the setting
                if not hasattr(guild, 'settings') or not guild.settings:
                    guild.settings = {}
                    
                guild.settings[key] = value
                
            # Save the guild
            if await guild.save(self.db_client):
                await ctx.send(f"✅ Setting `{key}` set to `{value}`")
            else:
                await ctx.send(f"❌ Failed to set setting `{key}`")
        except Exception as e:
            logger.error(f"Error setting guild setting: {e}")
            await ctx.send(f"❌ Error: {e}")
            
    @db_group.command(name="user")
    @commands.has_permissions(administrator=True)
    async def user_info(self, ctx, user: Optional[discord.Member] = None):
        """
        View user database info
        
        This command shows information about a user in the database.
        
        Args:
            user: User to show info for (default: command author)
        """
        if not self.db_client:
            await ctx.send("❌ Database not connected")
            return
            
        # Default to command author
        if user is None:
            user = ctx.author
            
        try:
            # Get the user from the database
            db_user = await User.get_by_user_id(self.db_client, user.id)
            
            if db_user:
                # Format the user information
                embed = discord.Embed(
                    title="User Database Info",
                    description=f"Information for user {user.display_name} in the database",
                    color=0x00a8ff
                )
                
                embed.add_field(
                    name="ID",
                    value=str(db_user._id),
                    inline=True
                )
                
                embed.add_field(
                    name="User ID",
                    value=str(db_user.user_id),
                    inline=True
                )
                
                embed.add_field(
                    name="Username",
                    value=db_user.username,
                    inline=True
                )
                
                embed.add_field(
                    name="Premium",
                    value="Yes" if db_user.is_premium else "No",
                    inline=True
                )
                
                # Format settings
                settings_str = "\n".join([f"**{k}**: {v}" for k, v in db_user.settings.items()]) or "No custom settings"
                
                embed.add_field(
                    name="Settings",
                    value=settings_str,
                    inline=False
                )
                
                # Format timestamps
                embed.add_field(
                    name="Created At",
                    value=db_user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
                
                embed.add_field(
                    name="Updated At",
                    value=db_user.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                    inline=True
                )
                
                await ctx.send(embed=embed)
            else:
                # User not found in database
                await ctx.send("❓ User not found in database. Creating new entry...")
                
                # Create a new user entry
                db_user = User(
                    user_id=user.id,
                    username=user.name,
                    is_premium=False,
                    settings={}
                )
                
                # Save the user
                if await db_user.save(self.db_client):
                    await ctx.send("✅ User entry created in database")
                else:
                    await ctx.send("❌ Failed to create user entry in database")
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            await ctx.send(f"❌ Error: {e}")
            
    @db_group.command(name="premium")
    @commands.has_permissions(administrator=True)
    @requires_premium_feature("advanced_analytics")
    async def set_premium(self, ctx, user: discord.Member, premium: bool):
        """
        Set user premium status
        
        This command sets a user's premium status in the database.
        
        Args:
            user: User to set premium status for
            premium: Premium status (True/False)
        """
        if not self.db_client:
            await ctx.send("❌ Database not connected")
            return
            
        try:
            # Get the user from the database
            db_user = await User.get_by_user_id(self.db_client, user.id)
            
            if not db_user:
                # User not found in database, create it
                db_user = User(
                    user_id=user.id,
                    username=user.name,
                    is_premium=premium,
                    settings={}
                )
            else:
                # Update the premium status
                db_user.is_premium = premium
                
            # Save the user
            if await db_user.save(self.db_client):
                status = "enabled" if premium else "disabled"
                await ctx.send(f"✅ Premium status for {user.mention} {status}")
            else:
                await ctx.send(f"❌ Failed to set premium status for {user.mention}")
        except Exception as e:
            logger.error(f"Error setting premium status: {e}")
            await ctx.send(f"❌ Error: {e}")
            
    @db_group.command(name="stats")
    @commands.has_permissions(administrator=True)
    @requires_premium_feature("advanced_analytics")
    async def db_stats(self, ctx):
        """
        View database statistics
        
        This command shows statistics about the database.
        """
        if not self.db_client:
            await ctx.send("❌ Database not connected")
            return
            
        try:
            # Get collection statistics
            collections = {
                "Guilds": "guilds",
                "Users": "users",
                "Premium Guilds": "premium_guilds"
            }
            
            # Format the statistics
            embed = discord.Embed(
                title="Database Statistics",
                description="Statistics about the database collections",
                color=0x00a8ff
            )
            
            for name, collection in collections.items():
                # Count documents in each collection
                result = await self.db_client.count_documents(collection, {})
                
                if result.success:
                    count = result.data
                else:
                    count = "Error"
                    
                embed.add_field(
                    name=name,
                    value=str(count),
                    inline=True
                )
                
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            await ctx.send(f"❌ Error: {e}")
            
def setup(bot):
    """
    Set up the database cog
    
    Args:
        bot: The Discord bot instance
    """
    bot.add_cog(Database(bot))
    logger.info("Database cog loaded")