"""
Analytics Cog

This cog provides commands for server analytics and data visualization.
"""

import logging
import discord
from discord.ext import commands
import asyncio
from typing import Optional, Dict, List, Any, Union
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io
import os
from collections import Counter, defaultdict

# Import premium utilities
from utils.premium_manager import requires_premium_feature
from utils.permissions import is_admin, is_guild_owner, is_mod_or_higher

# Configure logger
logger = logging.getLogger("cogs.analytics")

class Analytics(commands.Cog):
    """
    Analytics and data visualization
    
    This cog provides commands for server analytics and data visualization.
    """
    
    def __init__(self, bot):
        """
        Initialize the cog
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.message_cache = defaultdict(list)  # guild_id -> list of message timestamps
        self.member_join_cache = defaultdict(list)  # guild_id -> list of join timestamps
        self.cache_limit = 10000  # Maximum number of timestamps to cache per guild
        self.enabled_guilds = set()  # Set of guild IDs with analytics enabled
        
        # Start background task to periodically clean up old cache data
        self.cleanup_task = bot.loop.create_task(self._cleanup_cache())
        
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        # Cancel the background task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            
    async def _cleanup_cache(self):
        """Background task to clean up old cache data"""
        try:
            while not self.bot.is_closed():
                # Remove data older than 30 days
                cutoff = datetime.datetime.now() - datetime.timedelta(days=30)
                
                for guild_id in list(self.message_cache.keys()):
                    self.message_cache[guild_id] = [
                        timestamp for timestamp in self.message_cache[guild_id]
                        if timestamp > cutoff
                    ]
                    
                for guild_id in list(self.member_join_cache.keys()):
                    self.member_join_cache[guild_id] = [
                        timestamp for timestamp in self.member_join_cache[guild_id]
                        if timestamp > cutoff
                    ]
                    
                # Wait 1 hour before cleaning up again
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            # Task was cancelled, just exit
            pass
        except Exception as e:
            logger.error(f"Error in cache cleanup task: {e}")
            
    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Handle message events for analytics
        
        Args:
            message: The message
        """
        # Ignore bot messages
        if message.author.bot:
            return
            
        # Ignore DMs
        if not message.guild:
            return
            
        # Check if analytics are enabled for this guild
        if message.guild.id not in self.enabled_guilds:
            return
            
        # Add message timestamp to cache
        self.message_cache[message.guild.id].append(datetime.datetime.now())
        
        # Trim cache if it gets too large
        if len(self.message_cache[message.guild.id]) > self.cache_limit:
            self.message_cache[message.guild.id] = self.message_cache[message.guild.id][-self.cache_limit:]
            
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Handle member join events for analytics
        
        Args:
            member: The member that joined
        """
        # Check if analytics are enabled for this guild
        if member.guild.id not in self.enabled_guilds:
            return
            
        # Add join timestamp to cache
        self.member_join_cache[member.guild.id].append(datetime.datetime.now())
        
        # Trim cache if it gets too large
        if len(self.member_join_cache[member.guild.id]) > self.cache_limit:
            self.member_join_cache[member.guild.id] = self.member_join_cache[member.guild.id][-self.cache_limit:]
            
    @commands.group(name="analytics", invoke_without_command=True)
    @requires_premium_feature("advanced_analytics")
    @is_mod_or_higher()
    async def analytics_group(self, ctx):
        """
        Server analytics and data visualization
        
        This command group provides access to server analytics.
        Use a subcommand to view specific analytics.
        """
        if ctx.invoked_subcommand is None:
            # Show help for the group
            await ctx.send_help(ctx.command)
            
    @analytics_group.command(name="enable")
    @requires_premium_feature("advanced_analytics")
    @is_admin()
    async def enable_analytics(self, ctx):
        """
        Enable analytics for this server
        
        This command enables analytics tracking for the current server.
        """
        # Enable analytics for this guild
        self.enabled_guilds.add(ctx.guild.id)
        
        await ctx.send("✅ Analytics tracking enabled for this server.")
        
    @analytics_group.command(name="disable")
    @requires_premium_feature("advanced_analytics")
    @is_admin()
    async def disable_analytics(self, ctx):
        """
        Disable analytics for this server
        
        This command disables analytics tracking for the current server.
        """
        # Disable analytics for this guild
        if ctx.guild.id in self.enabled_guilds:
            self.enabled_guilds.remove(ctx.guild.id)
            
        await ctx.send("✅ Analytics tracking disabled for this server.")
        
    @analytics_group.command(name="activity")
    @requires_premium_feature("advanced_analytics")
    async def activity_chart(self, ctx, days: int = 7):
        """
        View server activity chart
        
        This command shows a chart of server activity over time.
        
        Args:
            days: Number of days to include (default: 7)
        """
        # Check if analytics are enabled for this guild
        if ctx.guild.id not in self.enabled_guilds:
            await ctx.send("❌ Analytics tracking is not enabled for this server. Use `!analytics enable` to enable it.")
            return
            
        # Limit days to a reasonable range
        if days < 1:
            days = 1
        elif days > 30:
            days = 30
            
        # Create chart
        start_time = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Filter message timestamps
        timestamps = [
            ts for ts in self.message_cache.get(ctx.guild.id, [])
            if ts >= start_time
        ]
        
        if not timestamps:
            await ctx.send("❌ No activity data available for the requested time period.")
            return
            
        # Create the figure
        plt.figure(figsize=(10, 6))
        
        # Create the chart
        plt.hist(timestamps, bins=min(days * 4, 50), alpha=0.7, color='blue')
        
        # Configure the chart
        plt.title(f"Server Activity - Last {days} Days")
        plt.xlabel("Date")
        plt.ylabel("Number of Messages")
        
        # Format the x-axis as dates
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator())
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save the chart to a buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Close the figure to free memory
        plt.close()
        
        # Create a file from the buffer
        file = discord.File(buf, filename='activity.png')
        
        # Send the chart
        await ctx.send(f"📊 Server Activity - Last {days} Days", file=file)
        
    @analytics_group.command(name="members")
    @requires_premium_feature("advanced_analytics")
    async def member_chart(self, ctx, days: int = 7):
        """
        View member growth chart
        
        This command shows a chart of member growth over time.
        
        Args:
            days: Number of days to include (default: 7)
        """
        # Check if analytics are enabled for this guild
        if ctx.guild.id not in self.enabled_guilds:
            await ctx.send("❌ Analytics tracking is not enabled for this server. Use `!analytics enable` to enable it.")
            return
            
        # Limit days to a reasonable range
        if days < 1:
            days = 1
        elif days > 30:
            days = 30
            
        # Create chart
        start_time = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Get member join timestamps
        timestamps = [
            ts for ts in self.member_join_cache.get(ctx.guild.id, [])
            if ts >= start_time
        ]
        
        if not timestamps:
            await ctx.send("❌ No member join data available for the requested time period.")
            return
            
        # Create the figure
        plt.figure(figsize=(10, 6))
        
        # Group joins by day
        dates = [ts.date() for ts in timestamps]
        join_counts = Counter(dates)
        
        # Generate all dates in the range
        all_dates = [start_time.date() + datetime.timedelta(days=i) for i in range(days + 1)]
        
        # Get counts for each date
        counts = [join_counts.get(date, 0) for date in all_dates]
        
        # Create a cumulative count
        cumulative_counts = np.cumsum(counts)
        
        # Create the chart
        plt.plot(all_dates, cumulative_counts, '-o', alpha=0.7, color='green')
        
        # Configure the chart
        plt.title(f"Member Growth - Last {days} Days")
        plt.xlabel("Date")
        plt.ylabel("Total New Members")
        
        # Format the x-axis as dates
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator())
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save the chart to a buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Close the figure to free memory
        plt.close()
        
        # Create a file from the buffer
        file = discord.File(buf, filename='member_growth.png')
        
        # Send the chart
        await ctx.send(f"📊 Member Growth - Last {days} Days", file=file)
        
    @analytics_group.command(name="hourly")
    @requires_premium_feature("advanced_analytics")
    async def hourly_activity(self, ctx, days: int = 7):
        """
        View hourly activity chart
        
        This command shows a chart of server activity by hour of day.
        
        Args:
            days: Number of days to include in the analysis (default: 7)
        """
        # Check if analytics are enabled for this guild
        if ctx.guild.id not in self.enabled_guilds:
            await ctx.send("❌ Analytics tracking is not enabled for this server. Use `!analytics enable` to enable it.")
            return
            
        # Limit days to a reasonable range
        if days < 1:
            days = 1
        elif days > 30:
            days = 30
            
        # Create chart
        start_time = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Filter message timestamps
        timestamps = [
            ts for ts in self.message_cache.get(ctx.guild.id, [])
            if ts >= start_time
        ]
        
        if not timestamps:
            await ctx.send("❌ No activity data available for the requested time period.")
            return
            
        # Get hours for each message
        hours = [ts.hour for ts in timestamps]
        
        # Create the figure
        plt.figure(figsize=(10, 6))
        
        # Create the chart
        bins = range(25)  # 0-24
        plt.hist(hours, bins=bins, alpha=0.7, color='purple')
        
        # Configure the chart
        plt.title(f"Hourly Activity - Last {days} Days")
        plt.xlabel("Hour of Day (UTC)")
        plt.ylabel("Number of Messages")
        plt.xticks(range(0, 24, 2))  # Show every other hour
        
        plt.tight_layout()
        
        # Save the chart to a buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Close the figure to free memory
        plt.close()
        
        # Create a file from the buffer
        file = discord.File(buf, filename='hourly_activity.png')
        
        # Send the chart
        await ctx.send(f"📊 Hourly Activity - Last {days} Days", file=file)
        
    @analytics_group.command(name="channels")
    @requires_premium_feature("advanced_analytics")
    async def channel_activity(self, ctx, limit: int = 100):
        """
        View channel activity chart
        
        This command shows a chart of activity by channel.
        
        Args:
            limit: Maximum number of messages to analyze per channel (default: 100)
        """
        # Check if analytics are enabled for this guild
        if ctx.guild.id not in self.enabled_guilds:
            await ctx.send("❌ Analytics tracking is not enabled for this server. Use `!analytics enable` to enable it.")
            return
            
        # Limit to a reasonable range
        if limit < 10:
            limit = 10
        elif limit > 500:
            limit = 500
            
        # Let the user know this might take a while
        status_message = await ctx.send("⏳ Gathering channel activity data... This might take a moment.")
        
        try:
            # Get all text channels
            text_channels = [channel for channel in ctx.guild.channels if isinstance(channel, discord.TextChannel)]
            
            # Get message counts for each channel
            channel_data = []
            
            for channel in text_channels:
                try:
                    # Check if the bot has permission to read the channel
                    if not channel.permissions_for(ctx.guild.me).read_message_history:
                        continue
                        
                    # Get the message count
                    count = 0
                    async for _ in channel.history(limit=limit):
                        count += 1
                        
                    if count > 0:
                        channel_data.append((channel.name, count))
                except:
                    # Skip channels with errors
                    pass
                    
            if not channel_data:
                await status_message.edit(content="❌ No channel activity data available.")
                return
                
            # Sort by count in descending order
            channel_data.sort(key=lambda x: x[1], reverse=True)
            
            # Limit to top 15 channels
            if len(channel_data) > 15:
                channel_data = channel_data[:15]
                
            # Create the figure
            plt.figure(figsize=(10, 6))
            
            # Extract data
            names = [item[0] for item in channel_data]
            counts = [item[1] for item in channel_data]
            
            # Create the chart
            bars = plt.barh(names, counts, alpha=0.7, color='teal')
            
            # Add count labels to bars
            for bar in bars:
                width = bar.get_width()
                plt.text(width + 1, bar.get_y() + bar.get_height()/2, f'{int(width)}', 
                        ha='left', va='center')
            
            # Configure the chart
            plt.title(f"Channel Activity (Last {limit} messages per channel)")
            plt.xlabel("Number of Messages")
            plt.ylabel("Channel")
            
            plt.tight_layout()
            
            # Save the chart to a buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            
            # Close the figure to free memory
            plt.close()
            
            # Create a file from the buffer
            file = discord.File(buf, filename='channel_activity.png')
            
            # Send the chart
            await status_message.delete()
            await ctx.send(f"📊 Channel Activity", file=file)
        except Exception as e:
            logger.error(f"Error in channel activity chart: {e}")
            await status_message.edit(content=f"❌ Error generating channel activity chart: {e}")
            
    @analytics_group.command(name="roles")
    @requires_premium_feature("advanced_analytics")
    async def role_distribution(self, ctx):
        """
        View role distribution chart
        
        This command shows a chart of member distribution by role.
        """
        # Check if analytics are enabled for this guild
        if ctx.guild.id not in self.enabled_guilds:
            await ctx.send("❌ Analytics tracking is not enabled for this server. Use `!analytics enable` to enable it.")
            return
            
        # Let the user know this might take a while
        status_message = await ctx.send("⏳ Gathering role distribution data... This might take a moment.")
        
        try:
            # Get role counts
            role_counts = {}
            
            # Skip everyone role
            roles = [role for role in ctx.guild.roles if role.name != "@everyone"]
            
            # Sort roles by position (highest to lowest)
            roles.sort(key=lambda role: role.position, reverse=True)
            
            # Count members for each role
            for role in roles:
                if len(role.members) > 0:
                    role_counts[role.name] = len(role.members)
                    
            if not role_counts:
                await status_message.edit(content="❌ No role distribution data available.")
                return
                
            # Limit to top 15 roles
            if len(role_counts) > 15:
                # Sort by count in descending order
                sorted_roles = sorted(role_counts.items(), key=lambda x: x[1], reverse=True)
                role_counts = dict(sorted_roles[:15])
                
            # Create the figure
            plt.figure(figsize=(10, 6))
            
            # Extract data
            names = list(role_counts.keys())
            counts = list(role_counts.values())
            
            # Create the chart
            bars = plt.barh(names, counts, alpha=0.7, color='orange')
            
            # Add count labels to bars
            for bar in bars:
                width = bar.get_width()
                plt.text(width + 1, bar.get_y() + bar.get_height()/2, f'{int(width)}', 
                        ha='left', va='center')
            
            # Configure the chart
            plt.title("Role Distribution")
            plt.xlabel("Number of Members")
            plt.ylabel("Role")
            
            plt.tight_layout()
            
            # Save the chart to a buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            
            # Close the figure to free memory
            plt.close()
            
            # Create a file from the buffer
            file = discord.File(buf, filename='role_distribution.png')
            
            # Send the chart
            await status_message.delete()
            await ctx.send("📊 Role Distribution", file=file)
        except Exception as e:
            logger.error(f"Error in role distribution chart: {e}")
            await status_message.edit(content=f"❌ Error generating role distribution chart: {e}")
            
    @analytics_group.command(name="weekly")
    @requires_premium_feature("advanced_analytics")
    async def weekly_activity(self, ctx, weeks: int = 4):
        """
        View weekly activity chart
        
        This command shows a chart of server activity by day of week.
        
        Args:
            weeks: Number of weeks to include in the analysis (default: 4)
        """
        # Check if analytics are enabled for this guild
        if ctx.guild.id not in self.enabled_guilds:
            await ctx.send("❌ Analytics tracking is not enabled for this server. Use `!analytics enable` to enable it.")
            return
            
        # Limit weeks to a reasonable range
        if weeks < 1:
            weeks = 1
        elif weeks > 12:
            weeks = 12
            
        # Create chart
        start_time = datetime.datetime.now() - datetime.timedelta(weeks=weeks)
        
        # Filter message timestamps
        timestamps = [
            ts for ts in self.message_cache.get(ctx.guild.id, [])
            if ts >= start_time
        ]
        
        if not timestamps:
            await ctx.send("❌ No activity data available for the requested time period.")
            return
            
        # Get weekdays for each message (0 = Monday, 6 = Sunday)
        weekdays = [ts.weekday() for ts in timestamps]
        
        # Create the figure
        plt.figure(figsize=(10, 6))
        
        # Create the chart
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        counts = [weekdays.count(i) for i in range(7)]
        
        bars = plt.bar(days, counts, alpha=0.7, color='blue')
        
        # Add count labels to bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, height + 0.5, f'{int(height)}', 
                    ha='center', va='bottom')
        
        # Configure the chart
        plt.title(f"Weekly Activity Pattern - Last {weeks} Weeks")
        plt.xlabel("Day of Week")
        plt.ylabel("Number of Messages")
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save the chart to a buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Close the figure to free memory
        plt.close()
        
        # Create a file from the buffer
        file = discord.File(buf, filename='weekly_activity.png')
        
        # Send the chart
        await ctx.send(f"📊 Weekly Activity Pattern - Last {weeks} Weeks", file=file)
        
    @analytics_group.command(name="report")
    @requires_premium_feature("advanced_analytics")
    @is_admin()
    async def analytics_report(self, ctx, days: int = 7):
        """
        Generate a comprehensive analytics report
        
        This command generates a comprehensive report of server analytics.
        
        Args:
            days: Number of days to include in the report (default: 7)
        """
        # Check if analytics are enabled for this guild
        if ctx.guild.id not in self.enabled_guilds:
            await ctx.send("❌ Analytics tracking is not enabled for this server. Use `!analytics enable` to enable it.")
            return
            
        # Limit days to a reasonable range
        if days < 1:
            days = 1
        elif days > 30:
            days = 30
            
        # Let the user know this might take a while
        status_message = await ctx.send("⏳ Generating analytics report... This might take a moment.")
        
        try:
            # Calculate the start time
            start_time = datetime.datetime.now() - datetime.timedelta(days=days)
            
            # Filter message timestamps
            message_timestamps = [
                ts for ts in self.message_cache.get(ctx.guild.id, [])
                if ts >= start_time
            ]
            
            # Filter member join timestamps
            join_timestamps = [
                ts for ts in self.member_join_cache.get(ctx.guild.id, [])
                if ts >= start_time
            ]
            
            # Create the embed
            embed = discord.Embed(
                title=f"Analytics Report - Last {days} Days",
                description=f"Comprehensive analytics report for {ctx.guild.name}",
                color=0x00a8ff,
                timestamp=datetime.datetime.now()
            )
            
            # Add guild information
            embed.add_field(
                name="Server Information",
                value=f"Members: {ctx.guild.member_count}\n"
                      f"Channels: {len(ctx.guild.channels)}\n"
                      f"Roles: {len(ctx.guild.roles)}\n"
                      f"Created: {ctx.guild.created_at.strftime('%Y-%m-%d')}\n"
                      f"Region: {ctx.guild.region if hasattr(ctx.guild, 'region') else 'Unknown'}",
                inline=False
            )
            
            # Add activity statistics
            embed.add_field(
                name="Activity Statistics",
                value=f"Messages: {len(message_timestamps)}\n"
                      f"New Members: {len(join_timestamps)}\n"
                      f"Daily Average: {len(message_timestamps) // days} messages",
                inline=False
            )
            
            # Set the server icon as the thumbnail
            if ctx.guild.icon:
                embed.set_thumbnail(url=ctx.guild.icon.url)
                
            # Set the footer
            embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
            
            # Add charts
            
            # Create a temporary directory for charts
            os.makedirs("temp", exist_ok=True)
            
            # Activity over time chart
            if message_timestamps:
                # Create the figure
                plt.figure(figsize=(10, 6))
                
                # Create the chart
                plt.hist(message_timestamps, bins=min(days * 4, 50), alpha=0.7, color='blue')
                
                # Configure the chart
                plt.title(f"Server Activity - Last {days} Days")
                plt.xlabel("Date")
                plt.ylabel("Number of Messages")
                
                # Format the x-axis as dates
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.gca().xaxis.set_major_locator(mdates.DayLocator())
                plt.xticks(rotation=45)
                
                plt.tight_layout()
                
                # Save the chart to a file
                activity_file = "temp/activity.png"
                plt.savefig(activity_file)
                
                # Close the figure to free memory
                plt.close()
                
                # Create a file from the saved chart
                file1 = discord.File(activity_file, filename='activity.png')
                
                # Send the chart
                await ctx.send(file=file1)
            
            # Member growth chart
            if join_timestamps:
                # Create the figure
                plt.figure(figsize=(10, 6))
                
                # Group joins by day
                dates = [ts.date() for ts in join_timestamps]
                join_counts = Counter(dates)
                
                # Generate all dates in the range
                all_dates = [start_time.date() + datetime.timedelta(days=i) for i in range(days + 1)]
                
                # Get counts for each date
                counts = [join_counts.get(date, 0) for date in all_dates]
                
                # Create a cumulative count
                cumulative_counts = np.cumsum(counts)
                
                # Create the chart
                plt.plot(all_dates, cumulative_counts, '-o', alpha=0.7, color='green')
                
                # Configure the chart
                plt.title(f"Member Growth - Last {days} Days")
                plt.xlabel("Date")
                plt.ylabel("Total New Members")
                
                # Format the x-axis as dates
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.gca().xaxis.set_major_locator(mdates.DayLocator())
                plt.xticks(rotation=45)
                
                plt.tight_layout()
                
                # Save the chart to a file
                members_file = "temp/member_growth.png"
                plt.savefig(members_file)
                
                # Close the figure to free memory
                plt.close()
                
                # Create a file from the saved chart
                file2 = discord.File(members_file, filename='member_growth.png')
                
                # Send the chart
                await ctx.send(file=file2)
                
            # Send the embed
            await status_message.edit(content="✅ Analytics report generated!")
            await ctx.send(embed=embed)
            
            # Clean up temporary files
            try:
                for filename in os.listdir("temp"):
                    os.remove(os.path.join("temp", filename))
                os.rmdir("temp")
            except:
                pass
        except Exception as e:
            logger.error(f"Error generating analytics report: {e}")
            await status_message.edit(content=f"❌ Error generating analytics report: {e}")
        
def setup(bot):
    """
    Set up the analytics cog
    
    Args:
        bot: The Discord bot instance
    """
    bot.add_cog(Analytics(bot))
    logger.info("Analytics cog loaded")