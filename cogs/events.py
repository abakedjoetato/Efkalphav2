"""
Events commands and background tasks for monitoring server events
"""
import logging
import asyncio
import traceback
import time
import discord
from discord.ext import commands
from utils.discord_patches import app_commands
from datetime import datetime, timedelta
from typing import Union,  Dict, List, Any, Optional

from models.guild import Guild
from models.server import Server
from models.event import Event, Connection
from utils.sftp import SFTPClient
from utils.parsers import LogParser
from utils.embed_builder import EmbedBuilder
from utils.helpers import has_admin_permission, update_voice_channel_name
from utils.premium_verification import premium_feature_required
from utils.discord_utils import server_id_autocomplete

logger = logging.getLogger(__name__)

class Events(commands.Cog):
    """Events commands and background tasks"""

    
    async def verify_premium(self, guild_id: Union[str, int], feature_name: str = None) -> bool:
        """
        Verify premium access for a feature
        
        Args:
            guild_id: Discord guild ID
            feature_name: The feature name to check
            
        Returns:
            bool: Whether access is granted
        """
        # Default feature name to cog name if not provided
        if feature_name is None:
            feature_name = self.__class__.__name__.lower()
            
        # Standardize guild_id to string
        guild_id_str = str(guild_id)
        
        # Fixed: Removed undefined ctx reference
        logger.info(f"Events premium verification for guild {guild_id_str}, feature {feature_name}")
        
        try:
            # Import premium utils
            from utils import premium_utils
            
            # Use standardized premium check
            has_access = await premium_utils.verify_premium_for_feature(
                self.bot.db, guild_id_str, feature_name
            )
            
            # Log the result
            logger.info(f"Premium verification for {feature_name}: access={has_access}")
            return has_access
            
        except Exception as e:
            logger.error(f"Error verifying premium: {e}")
            traceback.print_exc()
            # Default to allowing access if there's an error
            return True
            
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="events", description="Server events commands")
    @commands.guild_only()
    async def events(self, ctx):
        """Events command group"""
        if ctx.invoked_subcommand is None:
            from utils.discord_utils import hybrid_send
            await hybrid_send(ctx, "Please specify a subcommand.")

    @events.command(name="help", description="Get help with events commands")
    async def events_help(self, ctx):
        """Show help for events commands"""
        try:
            # Get guild model for themed embed
            guild_data = None
            guild_model = None
            try:
                # Get guild data with enhanced lookup
                guild_id = ctx.guild.id
                
                # Try string conversion of guild ID first
                guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
                if guild_data is None:
                    # Try with integer ID
                    guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
                
                if guild_data is not None:
                    # Use create_from_db_document to ensure proper conversion of premium_tier
                    guild_model = Guild.create_from_db_document(guild_data, self.bot.db)
            except Exception as e:
                logger.warning(f"Error getting guild model: {e}")

            embed = await EmbedBuilder.create_base_embed(
                "Events Commands Help",
                "Use these commands to manage event monitoring and notifications for your servers."
            , guild=guild_model)

            # Basic commands
            basic_commands = [
                "`/events start server:<name>` - Start monitoring events for a server",
                "`/events stop server:<name>` - Stop monitoring events for a server",
                "`/events status` - Check the status of all event monitors",
                "`/events list server:<name> [event_type:all] [limit:10]` - List recent events",
                "`/events online server:<name>` - List online players"
            ]

            embed.add_field(
                name="📊 Basic Commands",
                value="\n".join(basic_commands),
                inline=False
            )

            # Notification configuration commands
            config_commands = [
                "`/events config server:<name> ...` - Configure game event notifications",
                "  ↳ Set which game events (missions, airdrops, etc.) trigger notifications",
                "`/events conn_config server:<name> ...` - Configure connection notifications",
                "  ↳ Enable/disable player connect and disconnect notifications",
                "`/events suicide_config server:<name> ...` - Configure suicide notifications",
                "  ↳ Enable/disable different types of suicide notifications"
            ]

            embed.add_field(
                name="⚙️ Notification Configuration",
                value="\n".join(config_commands),
                inline=False
            )

            # Customization tips
            tips = [
                "**Reduce Channel Spam**: Disable notifications for common events",
                "**Focus on Important Events**: Keep rare events like airdrops enabled",
                "**Silence Suicides**: Disable menu/fall suicides if they happen too often",
                "**Admin Only**: These commands require administrator permissions"
            ]

            embed.add_field(
                name="💡 Tips",
                value="\n".join(tips),
                inline=False
            )

            from utils.discord_utils import hybrid_send
            await hybrid_send(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error displaying events help: {e}", exc_info=True)
            embed = await EmbedBuilder.create_error_embed(
                "Error",
                f"An error occurred: {e}"
            , guild=guild_model)
            from utils.discord_utils import hybrid_send
            await hybrid_send(ctx, embed=embed)

    @events.command(name="start", description="Start monitoring events for a server")
    @app_commands.describe(server_id="Select a server by name to monitor")
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    @premium_feature_required(feature_name="events", min_tier=1)  # Events monitoring requires premium tier 1+
    async def start(self, ctx, server_id: str):
        """Start the events monitor for a server"""

        try:
            # Get guild model for themed embed
            guild_data = None
            guild_model = None
            try:
                # Get guild data with enhanced lookup
                guild_id = ctx.guild.id
                
                # Try string conversion of guild ID first
                guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
                if guild_data is None:
                    # Try with integer ID
                    guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
                
                if guild_data is not None:
                    # Use create_from_db_document to ensure proper conversion of premium_tier
                    guild_model = Guild.create_from_db_document(guild_data, self.bot.db)
            except Exception as e:
                logger.warning(f"Error getting guild model: {e}")

            # Check permissions
            if await self._check_permission(ctx):
                return

            # Get guild data
            # Get guild data with enhanced lookup
            guild_id = ctx.guild.id
            
            # Try string conversion of guild ID first
            guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
            if guild_data is None:
                # Try with integer ID
                guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
            
            if guild_data is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    "This guild is not set up. Please use the setup commands first.",
                    guild=guild_model
                )
                from utils.discord_utils import hybrid_send
                await hybrid_send(ctx, embed=embed)
                return

            # Check if server is not None exists in this guild
            server_exists = False
            for server in guild_data.get("servers", []):
                if server.get('server_id') == server_id:
                    server_exists = True
                    break

            if server_exists is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    f"Server '{server_id}' not found in this guild. Please use an existing server name.",
                    guild=guild_model
                )
                from utils.discord_utils import hybrid_send
                await hybrid_send(ctx, embed=embed)
                return

            # Start events monitor
            task_name = f"events_{ctx.guild.id}_{server_id}"

            # Check if task is already running
            if task_name in self.bot.background_tasks:
                # If task exists but is done, remove it
                if self.bot.background_tasks[task_name].done():
                    self.bot.background_tasks.pop(task_name)
                else:
                    embed = await EmbedBuilder.create_error_embed(
                        "Already Running",
                        f"Events monitor for server {server_id} is already running.",
                        guild=guild_model
                    )
                    from utils.discord_utils import hybrid_send
                    await hybrid_send(ctx, embed=embed)
                    return

            # Create initial response
            embed = await EmbedBuilder.create_base_embed(
                "Starting Events Monitor",
                f"Starting events monitor for server {server_id}..."
            , guild=guild_model)
            from utils.discord_utils import hybrid_send
            message = await hybrid_send(ctx, embed=embed)

            # Start the task
            task = asyncio.create_task(
                self.start_events_monitor(ctx.guild.id, server_id)
            )
            self.bot.background_tasks[task_name] = task

            # Add callback to handle completion
            task.add_done_callback(
                lambda t: asyncio.create_task(
                    self._handle_task_completion(t, ctx.guild.id, server_id, message)
                )
            )

            # Update response after a short delay
            await asyncio.sleep(2)
            embed = await EmbedBuilder.create_success_embed(
                "Events Monitor Started",
                f"Events monitor for server {server_id} has been started successfully."
            , guild=guild_model)
            await message.edit(embed=embed)

        except Exception as e:
            logger.error(f"Error starting events monitor: {e}", exc_info=True)
            embed = await EmbedBuilder.create_error_embed(
                "Error",
                f"An error occurred while starting the events monitor: {e}",
                guild=guild_model
            )
            await ctx.send(embed=embed)

    @events.command(name="stop", description="Stop monitoring events for a server")
    @app_commands.describe(server_id="Select a server by name to stop monitoring")
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    async def stop(self, ctx, server_id: str):
        """Stop the events monitor for a server"""

        try:
            # Get guild model for themed embed
            guild_data = None
            guild_model = None
            try:
                # Get guild data with enhanced lookup
                guild_id = ctx.guild.id
                
                # Try string conversion of guild ID first
                guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
                if guild_data is None:
                    # Try with integer ID
                    guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
                
                if guild_data is not None:
                    # Use create_from_db_document to ensure proper conversion of premium_tier
                    guild_model = Guild.create_from_db_document(guild_data, self.bot.db)
            except Exception as e:
                logger.warning(f"Error getting guild model: {e}")

            # Check permissions
            if await self._check_permission(ctx):
                return

            # Check if task is running
            task_name = f"events_{ctx.guild.id}_{server_id}"
            if task_name not in self.bot.background_tasks:
                embed = await EmbedBuilder.create_error_embed(
                    "Not Running",
                    f"Events monitor for server {server_id} is not running.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Cancel the task
            task = self.bot.background_tasks[task_name]
            task.cancel()

            # Remove the task
            self.bot.background_tasks.pop(task_name)

            # Send success message
            embed = await EmbedBuilder.create_success_embed(
                "Events Monitor Stopped",
                f"Events monitor for server {server_id} has been stopped successfully."
            , guild=guild_model)
            from utils.discord_utils import hybrid_send
            await hybrid_send(ctx, embed=embed)

        except Exception as e:
            logger.error(f"Error stopping events monitor: {e}", exc_info=True)
            embed = await EmbedBuilder.create_error_embed(
                "Error",
                f"An error occurred while stopping the events monitor: {e}",
                guild=guild_model
            )
            await ctx.send(embed=embed)

    @events.command(name="status", description="Check events monitor status")
    @premium_feature_required(feature_name="events", min_tier=1)  # Events monitoring requires premium tier 1+
    async def status(self, ctx):
        """Check the status of events monitors for this guild"""

        try:
            # Get guild model for themed embed
            guild_data = None
            guild_model = None
            try:
                # Get guild data with enhanced lookup
                guild_id = ctx.guild.id
                
                # Try string conversion of guild ID first
                guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
                if guild_data is None:
                    # Try with integer ID
                    guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
                
                if guild_data is not None:
                    # Use create_from_db_document to ensure proper conversion of premium_tier
                    guild_model = Guild.create_from_db_document(guild_data, self.bot.db)
            except Exception as e:
                logger.warning(f"Error getting guild model: {e}")

            # Get guild data
            # Get guild data with enhanced lookup
            guild_id = ctx.guild.id
            
            # Try string conversion of guild ID first
            guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
            if guild_data is None:
                # Try with integer ID
                guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
            
            if guild_data is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    "This guild is not set up. Please use the setup commands first.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Check running tasks for this guild
            running_monitors = []
            for task_name, task in self.bot.background_tasks.items():
                if task_name.startswith(f"events_{ctx.guild.id}_"):
                    parts = task_name.split("_")
                    if len(parts) >= 3:
                        server_id = parts[2]

                        # Find server name
                        server_name = server_id
                        for server in guild_data.get("servers", []):
                            if server.get('server_id') == server_id:
                                server_name = server.get("server_name", server_id)
                                break

                        running_monitors.append({
                            "server_id": server_id,
                            "server_name": server_name,
                            "status": "Running" if not task.done() else "Completed"
                        })

            # Create embed
            if running_monitors is not None:
                embed = await EmbedBuilder.create_base_embed(
                    "Events Monitor Status",
                    f"Currently running events monitors for {ctx.guild.name}"
                , guild=guild_model)

                for monitor in running_monitors:
                    embed.add_field(
                        name=f"{monitor['server_name']} ({monitor['server_id']})",
                        value=f"Status: {monitor['status']}",
                        inline=False
                    )
            else:
                embed = await EmbedBuilder.create_base_embed(
                    "Events Monitor Status",
                    f"No events monitors are currently running for {ctx.guild.name}."
                , guild=guild_model)

                # Add instructions
                embed.add_field(
                    name="How to Start",
                    value="Use `/events start server:<server_name>` to start monitoring a server.",
                    inline=False
                )

                # Add premium notice if needed
                guild = Guild(self.bot.db, guild_data)
                if not guild.check_feature_access("events"):
                    embed.add_field(
                        name="Premium Feature",
                        value="Events monitoring is a premium feature. Please upgrade to access this feature.",
                        inline=False
                    )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error checking events status: {e}", exc_info=True)
            embed = await EmbedBuilder.create_error_embed(
                "Error",
                f"An error occurred while checking events status: {e}",
                guild=guild_model
            )
            await ctx.send(embed=embed)

    @events.command(name="list", description="List recent events for a server")
    @app_commands.describe(
        server_id="Select a server by name to list events for",
        event_type="Filter events by type",
        limit="Number of events to show (max 20)"
    )
    @app_commands.choices(event_type=[
        app_commands.Choice(name="All Events", value="all"),
        app_commands.Choice(name="Missions", value="mission"),
        app_commands.Choice(name="Airdrops", value="airdrop"),
        app_commands.Choice(name="Helicopter Crashes", value="crash"),
        app_commands.Choice(name="Traders", value="trader"),
        app_commands.Choice(name="Convoys", value="convoy"),
        app_commands.Choice(name="Special Encounters", value="encounter"),
        app_commands.Choice(name="Server Restarts", value="server_restart")
    ])
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    @premium_feature_required(feature_name="events", min_tier=1)  # Events monitoring requires premium tier 1+
    async def list_events(self, ctx, server_id: str, event_type: str = "all", limit: int = 10):
        """List recent events for a server"""

        try:
            # Get guild model for themed embed
            guild_data = None
            guild_model = None
            try:
                # Get guild data with enhanced lookup
                guild_id = ctx.guild.id
                
                # Try string conversion of guild ID first
                guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
                if guild_data is None:
                    # Try with integer ID
                    guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
                
                if guild_data is not None:
                    # Use create_from_db_document to ensure proper conversion of premium_tier
                    guild_model = Guild.create_from_db_document(guild_data, self.bot.db)
            except Exception as e:
                logger.warning(f"Error getting guild model: {e}")

            # Validate limit
            if limit < 1:
                limit = 10
            elif limit > 20:
                limit = 20

            # Get guild data
            # Get guild data with enhanced lookup
            guild_id = ctx.guild.id
            
            # Try string conversion of guild ID first
            guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
            if guild_data is None:
                # Try with integer ID
                guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
            
            if guild_data is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    "This guild is not set up. Please use the setup commands first.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Check if the guild has access to events feature
            guild = Guild(self.bot.db, guild_data)
            if not guild.check_feature_access("events"):
                embed = await EmbedBuilder.create_error_embed(
                    "Premium Feature",
                    "Events monitoring is a premium feature. Please upgrade to access this feature.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Find the server
            server = None
            server_name = server_id
            for s in guild_data.get("servers", []):
                if s.get("server_id") == server_id:
                    server = Server(self.bot.db, s)
                    server_name = s.get("server_name", server_id)
                    break

            if server is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Server Not Found",
                    f"Server '{server_id}' not found in this guild. Please use an existing server name.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Get events
            if event_type == "all":
                events = await Event.get_by_server(self.bot.db, server_id, limit)
            else:
                events = await Event.get_by_server(self.bot.db, server_id, limit, event_type)

            if events is None or len(events) == 0:
                embed = await EmbedBuilder.create_error_embed(
                    "No Events",
                    f"No events found for server {server_name}" +
                    (f" for {event_type} events" if event_type != "all" else "")
                )
                await ctx.send(embed=embed)
                return

            # Create embed
            embed = await EmbedBuilder.create_base_embed(
                "Recent Events",
                f"Recent events for {server_name}" +
                (f" (Type: {event_type})" if event_type != "all" else "")
            )

            # Add events to embed
            for i, event in enumerate(events):
                # Format timestamp
                timestamp_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")

                # Format details based on event type
                if event.event_type == "server_restart":
                    details = "Server restarted"
                elif event.event_type == "convoy":
                    start, end = event.details
                    details = f"From {start} to {end}"
                elif event.event_type == "encounter":
                    encounter_type, location = event.details
                    details = f"Event Type: {event_type} | Map: {event.get('map', 'Unknown')}"
                else:
                    details = event.details[0] if event.details else "No details"

                # Get event emoji
                event_emoji = {
                    "mission": "🎯",
                    "airdrop": "🛩️",
                    "crash": "🚁",
                    "trader": "💰",
                    "convoy": "🚚",
                    "encounter": "⚠️",
                    "server_restart": "🔄"
                }.get(event.event_type, "🔔")

                # Add to embed
                name = f"{event_emoji} {event.event_type.title()} ({timestamp_str})"
                embed.add_field(name=name, value=details, inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error listing events: {e}", exc_info=True)
            embed = await EmbedBuilder.create_error_embed(
                "Error",
                f"An error occurred while listing events: {e}",
                guild=guild_model
            )
            await ctx.send(embed=embed)

    @events.command(name="players", description="List online players for a server")
    @app_commands.describe(server_id="Select a server by name to list players for")
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    @premium_feature_required(feature_name="events", min_tier=1)  # Player connections requires premium tier 1+
    async def online_players(self, ctx, server_id: str):
        """List online players for a server"""

        try:
            # Get guild model for themed embed
            guild_data = None
            guild_model = None
            try:
                # Get guild data with enhanced lookup
                guild_id = ctx.guild.id
                
                # Try string conversion of guild ID first
                guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
                if guild_data is None:
                    # Try with integer ID
                    guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
                
                if guild_data is not None:
                    # Use create_from_db_document to ensure proper conversion of premium_tier
                    guild_model = Guild.create_from_db_document(guild_data, self.bot.db)
            except Exception as e:
                logger.warning(f"Error getting guild model: {e}")

            # Get guild data
            # Get guild data with enhanced lookup
            guild_id = ctx.guild.id
            
            # Try string conversion of guild ID first
            guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
            if guild_data is None:
                # Try with integer ID
                guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
            
            if guild_data is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    "This guild is not set up. Please use the setup commands first.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Check if the guild has access to connections feature
            guild = Guild(self.bot.db, guild_data)
            if not guild.check_feature_access("connections"):
                embed = await EmbedBuilder.create_error_embed(
                    "Premium Feature",
                    "Player connections is a premium feature. Please upgrade to access this feature.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Find the server
            server = None
            server_name = server_id
            for s in guild_data.get("servers", []):
                if s.get("server_id") == server_id:
                    server = Server(self.bot.db, s)
                    server_name = s.get("server_name", server_id)
                    break

            if server is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Server Not Found",
                    f"Server '{server_id}' not found in this guild. Please use an existing server name.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Get online players
            player_count, online_players = await server.get_online_player_count()

            # Create embed
            embed = await EmbedBuilder.create_base_embed(
                "Online Players",
                f"Currently {player_count} player(s) online on {server_name}"
            , guild=guild_model)

            # Add players to embed
            if player_count > 0:
                # Convert to list and sort by name
                players_list = [
                    {"id": player_id, "name": player_name}
                    for player_id, player_name in online_players.items()
                ]
                players_list.sort(key=lambda p: p["name"])

                # Format player list
                players_text = "\n".join([
                    f"{i+1}. {player['name']}"
                    for i, player in enumerate(players_list)
                ])

                embed.add_field(name="Players", value=players_text, inline=False)
            else:
                embed.add_field(name="Players", value="No players currently online", inline=False)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error listing online players: {e}", exc_info=True)
            embed = await EmbedBuilder.create_error_embed(
                "Error",
                f"An error occurred while listing online players: {e}",
                guild=guild_model
            )
            await ctx.send(embed=embed)

    @events.command(name="config", description="Configure event notifications")
    @app_commands.describe(
        server_id="Select a server by name to configure",
        mission="Enable mission event notifications (True/False)",
        airdrop="Enable airdrop event notifications (True/False)",
        crash="Enable crash event notifications (True/False)",
        trader="Enable trader event notifications (True/False)",
        convoy="Enable convoy event notifications (True/False)",
        encounter="Enable encounter event notifications (True/False)",
        server_restart="Enable server restart notifications (True/False)"
    )
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    @premium_feature_required(feature_name="events", min_tier=1)  # Events configuration requires premium tier 1+
    async def configure_events(self, ctx, server_id: str, 
                             mission: Optional[bool] = None,
                             airdrop: Optional[bool] = None,
                             crash: Optional[bool] = None,
                             trader: Optional[bool] = None,
                             convoy: Optional[bool] = None,
                             encounter: Optional[bool] = None,
                             server_restart: Optional[bool] = None):
        """Configure which event notifications are enabled"""

        try:
            # Get guild model for themed embed
            guild_data = None
            guild_model = None
            try:
                # Get guild data with enhanced lookup
                guild_id = ctx.guild.id
                
                # Try string conversion of guild ID first
                guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
                if guild_data is None:
                    # Try with integer ID
                    guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
                
                if guild_data is not None:
                    # Use create_from_db_document to ensure proper conversion of premium_tier
                    guild_model = Guild.create_from_db_document(guild_data, self.bot.db)
            except Exception as e:
                logger.warning(f"Error getting guild model: {e}")

            # Check permissions
            if await self._check_permission(ctx):
                return

            # Get server
            server = await Server.get_by_id(self.bot.db, server_id, ctx.guild.id)
            if server is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    f"Could not find server with ID {server_id} for this guild.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Build settings dictionary from provided arguments
            settings = {}
            if mission is not None:
                settings["mission"] = mission
            if airdrop is not None:
                settings["airdrop"] = airdrop
            if crash is not None:
                settings["crash"] = crash
            if trader is not None:
                settings["trader"] = trader
            if convoy is not None:
                settings["convoy"] = convoy
            if encounter is not None:
                settings["encounter"] = encounter
            if server_restart is not None:
                settings["server_restart"] = server_restart

            # If no settings were provided, show current settings
            if settings is not None is None:
                embed = await EmbedBuilder.create_base_embed(
                    "Event Notification Settings",
                    f"Current event notification settings for {server.name}"
                , guild=guild_model)

                # Add current settings to embed
                notification_settings = []
                for event_type, enabled in server.event_notifications.items():
                    status = "✅ Enabled" if enabled is not None else "❌ Disabled"
                    notification_settings.append(f"{event_type.replace('_', ' ').title()}: {status}")

                embed.add_field(
                    name="Event Types",
                    value="\n".join(notification_settings) or "No event types configured",
                    inline=False
                )

                embed.add_field(
                    name="How to Configure",
                    value="Use `/events config server:<server_name> event_type:<true/false>` to enable or disable notifications. " \
                          "For example, `/events config server:my_server mission:true airdrop:false`.",
                    inline=False
                )

                await ctx.send(embed=embed)
                return

            # Update settings
            success = await server.update_event_notifications(settings)
            if success is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    "Failed to update event notification settings. Please try again later.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Create success embed
            embed = await EmbedBuilder.create_success_embed(
                "Event Notifications Updated",
                f"Successfully updated event notification settings for {server.name}."
            , guild=guild_model)

            # Add updated settings to embed
            updated_settings = []
            for event_type, enabled in settings.items():
                status = "✅ Enabled" if enabled is not None else "❌ Disabled"
                updated_settings.append(f"{event_type.replace('_', ' ').title()}: {status}")

            embed.add_field(
                name="Updated Settings",
                value="\n".join(updated_settings),
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error configuring event notifications: {e}", exc_info=True)
            embed = await EmbedBuilder.create_error_embed(
                "Error",
                f"An error occurred: {e}",
                guild=guild_model
            )
            await ctx.send(embed=embed)

    @events.command(name="conn_config", description="Configure connection notifications")
    @app_commands.describe(
        server_id="Select a server by name to configure",
        connect="Enable player connection notifications (True/False)",
        disconnect="Enable player disconnection notifications (True/False)"
    )
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    @premium_feature_required(feature_name="events", min_tier=1)  # Connection configuration requires premium tier 1+
    async def configure_connections(self, ctx, server_id: str, 
                                connect: Optional[bool] = None,
                                disconnect: Optional[bool] = None):
        """Configure which connection notifications are enabled"""

        try:
            # Get guild model for themed embed
            guild_data = None
            guild_model = None
            try:
                # Get guild data with enhanced lookup
                guild_id = ctx.guild.id
                
                # Try string conversion of guild ID first
                guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
                if guild_data is None:
                    # Try with integer ID
                    guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
                
                if guild_data is not None:
                    # Use create_from_db_document to ensure proper conversion of premium_tier
                    guild_model = Guild.create_from_db_document(guild_data, self.bot.db)
            except Exception as e:
                logger.warning(f"Error getting guild model: {e}")

            # Check permissions
            if await self._check_permission(ctx):
                return

            # Get server
            server = await Server.get_by_id(self.bot.db, server_id, ctx.guild.id)
            if server is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    f"Could not find server with ID {server_id} for this guild.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Build settings dictionary from provided arguments
            settings = {}
            if connect is not None:
                settings["connect"] = connect
            if disconnect is not None:
                settings["disconnect"] = disconnect

            # If no settings were provided, show current settings
            if settings is None:
                embed = await EmbedBuilder.create_base_embed(
                    "Connection Notification Settings",
                    f"Current connection notification settings for {server.name}"
                , guild=guild_model)

                # Add current settings to embed
                notification_settings = []
                for conn_type, enabled in server.connection_notifications.items():
                    status = "✅ Enabled" if enabled is not None else "❌ Disabled"
                    notification_settings.append(f"{conn_type.replace('_', ' ').title()}: {status}")

                embed.add_field(
                    name="Connection Types",
                    value="\n".join(notification_settings) or "No connection types configured",
                    inline=False
                )

                embed.add_field(
                    name="How to Configure",
                    value="Use `/eventsconn_config server:<server_name> connect:<true/false> disconnect:<true/false>` to enable or disable notifications.",
                    inline=False
                )

                await ctx.send(embed=embed)
                return

            # Update settings
            success = await server.update_connection_notifications(settings)
            if success is None:
                embed = await EmbedBuilder.create_error_error_embed(
                    "Error",
                    "Failed to update connection notification settings. Please try again later.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Create success embed
            embed = await EmbedBuilder.create_success_embed(
                "Connection Notifications Updated",
                f"Successfully updated connection notification settings for {server.name}."
            , guild=guild_model)

            # Add updated settings to embed
            updated_settings = []
            for conn_type, enabled in settings.items():
                status = "✅ Enabled" if enabled is not None else "❌ Disabled"
                updated_settings.append(f"{conn_type.replace('_', ' ').title()}: {status}")

            embed.add_field(
                name="Updated Settings",
                value="\n".join(updated_settings),
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error configuring connection notifications: {e}", exc_info=True)
            embed = await EmbedBuilder.create_error_embed(
                "Error",
                f"An error occurred: {e}",
                guild=guild_model
            )
            await ctx.send(embed=embed)

    @events.command(name="suicide_config", description="Configure suicide notifications")
    @app_commands.describe(
        server_id="Select a server by name to configure",
        menu="Enable menu suicide notifications (True/False)",
        fall="Enable fall damage suicide notifications (True/False)",
        other="Enable other suicide notifications (True/False)"
    )
    @app_commands.autocomplete(server_id=server_id_autocomplete)
    @premium_feature_required(feature_name="events", min_tier=1)  # Suicide notification configuration requires premium tier 1+
    async def configure_suicides(self, ctx, server_id: str, 
                               menu: Optional[bool] = None,
                               fall: Optional[bool] = None,
                               other: Optional[bool] = None):
        """Configure which suicide notifications are enabled"""

        try:
            # Get guild model for themed embed
            guild_data = None
            guild_model = None
            try:
                # Get guild data with enhanced lookup
                guild_id = ctx.guild.id
                
                # Try string conversion of guild ID first
                guild_data = await self.bot.db.guilds.find_one({"guild_id": str(guild_id)})
                if guild_data is None:
                    # Try with integer ID
                    guild_data = await self.bot.db.guilds.find_one({"guild_id": int(guild_id)})
                
                if guild_data is not None:
                    # Use create_from_db_document to ensure proper conversion of premium_tier
                    guild_model = Guild.create_from_db_document(guild_data, self.bot.db)
            except Exception as e:
                logger.warning(f"Error getting guild model: {e}")

            # Check permissions
            if await self._check_permission(ctx):
                return

            # Get server
            server = await Server.get_by_id(self.bot.db, server_id, ctx.guild.id)
            if server is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    f"Could not find server with ID {server_id} for this guild.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Build settings dictionary from provided arguments
            settings = {}
            if menu is not None:
                settings["menu"] = menu
            if fall is not None:
                settings["fall"] = fall
            if other is not None:
                settings["other"] = other

            # If no settings were provided, show current settings
            if settings is None:
                embed = await EmbedBuilder.create_base_embed(
                    "Suicide Notification Settings",
                    f"Current suicide notification settings for {server.name}"
                , guild=guild_model)

                # Add current settings to embed
                notification_settings = []
                for suicide_type, enabled in server.suicide_notifications.items():
                    status = "✅ Enabled" if enabled is not None else "❌ Disabled"
                    notification_settings.append(f"{suicide_type.replace('_', ' ').title()}: {status}")

                embed.add_field(
                    name="Suicide Types",
                    value="\n".join(notification_settings) or "No suicide types configured",
                    inline=False
                )

                embed.add_field(
                    name="How to Configure",
                    value="Use `/events suicide_config server:<server_name> menu:<true/false> fall:<true/false> other:<true/false>` " \
                          "to enable or disable notifications.",
                    inline=False
                )

                await ctx.send(embed=embed)
                return

            # Update settings
            success = await server.update_suicide_notifications(settings)
            if success is None:
                embed = await EmbedBuilder.create_error_embed(
                    "Error",
                    "Failed to update suicide notification settings. Please try again later.",
                    guild=guild_model
                )
                await ctx.send(embed=embed)
                return

            # Create success embed
            embed = await EmbedBuilder.create_success_embed(
                "Suicide Notifications Updated",
                f"Successfully updated suicide notification settings for {server.name}."
            , guild=guild_model)

            # Add updated settings to embed
            updated_settings = []
            for suicide_type, enabled in settings.items():
                status = "✅ Enabled" if enabled is not None else "❌ Disabled"
                updated_settings.append(f"{suicide_type.replace('_', ' ').title()}: {status}")

            embed.add_field(
                name="Updated Settings",
                value="\n".join(updated_settings),
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error configuring suicide notifications: {e}", exc_info=True)
            embed = await EmbedBuilder.create_error_embed(
                "Error",
                f"An error occurred: {e}",
                guild=guild_model
            )
            await ctx.send(embed=embed)

    async def _check_permission(self, ctx) -> bool:
        """Check if user is not None has permission to use the command"""
        # Initialize guild_model to None first to avoid UnboundLocalError
        guild_model = None

        # Check if user has admin permission
        if has_admin_permission(ctx):
            return True

        # If not, send error message
        # Get the guild model for theme
        try:
            guild_model = await Guild.get_by_id(self.bot.db, ctx.guild.id)
        except Exception as e:
            logger.warning(f"Error getting guild model in permission check: {e}")

        embed = await EmbedBuilder.create_error_embed(
            "Permission Denied",
            "You need administrator permission or the designated admin role to use this command.",
            guild=guild_model
        )
        await ctx.send(embed=embed, ephemeral=True)
        return False

    async def _handle_task_completion(self, task, guild_id, server_id, message):
        """Handle completion of a background task"""
        try:
            # Check if task was cancelled
            if task is not None and task.cancelled():
                logger.info(f"Events monitor for server {server_id} was cancelled.")
                return

            # Check if task completed with an exception
            if task is not None and task.exception():
                logger.error(
                    f"Events monitor for server {server_id} failed: {task.exception()}", 
                    exc_info=task.exception()
                )

                # Update message if still exists
                try:
                    # Find the guild for the server
                    try:
                        # Use MongoDB array element matching syntax for server_id
                        guild_data = await self.bot.db.guilds.find_one({"servers.server_id": server_id})
                        guild_model = None
                        if guild_data is not None:
                            # Use create_from_db_document to ensure proper conversion of premium_tier
                            guild_model = Guild.create_from_db_document(guild_data, self.bot.db)

                        embed = await EmbedBuilder.create_error_embed(
                            "Events Monitor Failed",
                            f"The events monitor for server {server_id} has failed: {task.exception()}",
                            guild=guild_model
                        )
                    except Exception as ex:
                        # Fallback to simple error embed
                        logger.error(f"Error creating themed embed: {ex}")
                        embed = await EmbedBuilder.create_error_embed(
                            "Events Monitor Failed",
                            f"The events monitor for server {server_id} has failed: {task.exception()}"
                        )
                    await message.edit(embed=embed)
                except:
                    pass

                return

            # Task completed normally
            logger.info(f"Events monitor for server {server_id} completed successfully.")

        except Exception as e:
            logger.error(f"Error handling task completion: {e}", exc_info=True)


    async def start_events_monitor(self, guild_id: int, server_id: str):
        """Background task to monitor events for a server"""
        from config import EVENTS_REFRESH_INTERVAL
    
        try:
            # Initialize reconnection tracking
            reconnect_attempts = 0
            max_reconnect_attempts = 10
            backoff_time = 5  # Start with 5 seconds
            last_successful_connection = time.time()

            # Check if we actually have server data in the database
            # This prevents errors when the bot starts up with empty database
            if await self.bot.db.guilds.count_documents({"guild_id": guild_id, "servers": {"$exists": True, "$ne": []}}) == 0:
                logger.warning(f"No servers found for guild {guild_id} - skipping events monitor")
                return

            # Check if guild exists in bot's cache
            discord_guild = self.bot.get_guild(int(guild_id))
            if discord_guild is None:
                logger.error(f"Guild {guild_id} not found in bot's cache - will continue processing data without sending Discord messages")
            # Don't return here, we'll still process data for when the guild is available later

            logger.info(f"Starting events monitor for server {server_id} in guild {guild_id}")
            # Get server data
            try:
                server = await Server.get_by_id(self.bot.db, server_id, str(guild_id))
                if server is None:
                    logger.error(f"Server {server_id} not found in guild {guild_id}")
                    return
                    
                # Verify channel configuration
                events_channel_id = server.events_channel_id
            except Exception as e:
                logger.error(f"Error getting server data: {e}")
                return
                
            channel_configured = True
            if events_channel_id is None:
                logger.warning(f"No events channel configured for server {server_id} in guild {guild_id}")

                # Send a direct message to administrators about missing configuration
                try:
                    guild_model = await Guild.get_by_id(self.bot.db, guild_id)
                    if guild_model is not None and guild_model.admin_role_id:
                        # Try to get admin role
                        guild = self.bot.get_guild(guild_id)
                        if guild is not None:
                            admin_role = guild.get_role(guild_model.admin_role_id)
                            if admin_role is not None and admin_role.members:
                                admin = admin_role.members[0]  # Get first admin
                                await admin.send(f"⚠️ Event notifications for server {server.name} cannot be sent because no events channel is configured. Please use `/setup setup_channels` to set one up.")
                except Exception as notify_e:
                    logger.error(f"Error notifying admin about missing channel configuration: {notify_e}")
                
                # We'll still continue the events monitor to process events but we won't send Discord messages
                channel_configured = False
                
            # Set up SFTP client
            # We need to connect to SFTP to get logs with event data
            
            sftp_key = f"{guild_id}_{server_id}_events"
            sftp_connected = None  # Track whether we are connected or not
            
            # Check if we already have a connection in the bot's connection pool
            if hasattr(self.bot, 'sftp_connections') and sftp_key in self.bot.sftp_connections:
                sftp_client = self.bot.sftp_connections[sftp_key]
                # Check if still connected (does not guarantee a working connection)
                if sftp_client.is_connected():
                    sftp_connected = True
                    logger.info(f"Reusing existing SFTP connection for server {server_id}")
            
            # If not connected, create new connection
            if not hasattr(self.bot, 'sftp_connections'):
                self.bot.sftp_connections = {}
                
            if sftp_key not in self.bot.sftp_connections or not sftp_connected:
                # Construct path to log file based on server ID for this provider
                path_prefix = None
                
                # Get the original server ID for path construction
                original_server_id = server_id
                
                # First try to get from original_server_id attribute if it exists
                if hasattr(server, 'original_server_id') and server.original_server_id:
                    original_server_id = server.original_server_id
                # Then try dictionary-style access if supported
                elif hasattr(server, 'get') and callable(server.get) and server.get('original_server_id'):
                    original_server_id = server.get('original_server_id')
                # Then try server_data if it exists
                elif hasattr(server, 'server_data') and isinstance(server.server_data, dict) and 'original_server_id' in server.server_data:
                    original_server_id = server.server_data['original_server_id']
                # If still not found but we have a numeric ID, use that
                elif server_id.isdigit():
                    logger.info(f"Using numeric server ID for path construction: {server_id}")
                    original_server_id = server_id
                else:
                    logger.info(f"Checking for numeric server ID in server properties")
                    
                    # Try to find a numeric ID in server name or other properties
                    server_name = getattr(server, 'server_name', '') if hasattr(server, 'server_name') else ''
                    if server_name:
                        # Try to extract a numeric ID from the server name
                        for word in str(server_name).split():
                            if word.isdigit() and len(word) >= 4:
                                logger.info(f"Found potential numeric server ID in server_name: {word}")
                                original_server_id = word
                                break
            
                logger.info(f"Using original_server_id: {original_server_id} for path construction")
                
                # Create SFTP client
                from utils.sftp_client import DayzServerSFTPClient
                sftp_client = DayzServerSFTPClient(
                    server_id=server_id,
                    server=server,
                    path_prefix=path_prefix,
                    provider="default",  # or check server.provider if available
                    original_server_id=original_server_id
                )
                
                # Connect to SFTP server
                try:
                    sftp_connected = await sftp_client.connect()
                    if not sftp_connected:
                        logger.error(f"Failed to connect to SFTP for server {server_id}")
                        # We'll try to reconnect later, don't return here
                except Exception as e:
                    logger.error(f"Error connecting to SFTP for server {server_id}: {e}")
                    sftp_connected = None
                
                # Store client for later use, even if connected is None
                self.bot.sftp_connections[sftp_key] = sftp_client

            # If not connected, we'll log it and try to reconnect periodically
            if sftp_connected is None:
                logger.warning(f"Not connected to SFTP for server {server_id}, will attempt periodic reconnection")

            # Get channels
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                logger.error(f"Guild {guild_id} not found - will continue processing data without sending Discord messages")
                # Don't return here, we'll still process data for when the guild is available later

            events_channel_id = server.events_channel_id
            events_channel = None
            connections_channel_id = server.connections_channel_id
            connections_channel = None

            # Log channel ID details for diagnosis
            logger.info(f"Retrieved events_channel_id: {events_channel_id} (type: {type(events_channel_id).__name__})")
            logger.info(f"Retrieved connections_channel_id: {connections_channel_id} (type: {type(connections_channel_id).__name__} if connections_channel_id is not None else None)")

            # Only try to get channels if guild is not None exists
            if guild is not None:
                # Try to get events channel
                if events_channel_id is not None:
                    try:
                        # Ensure channel ID is an integer
                        if not isinstance(events_channel_id, int):
                            events_channel_id = int(events_channel_id)
                            logger.info(f"Converted events_channel_id to int: {events_channel_id}")

                        # Try to get the channel
                        events_channel = guild.get_channel(events_channel_id)
                        logger.info(f"Attempted to get events channel: {events_channel_id}, result: {events_channel is not None}")

                        if events_channel is None:
                            try:
                                # Try to fetch channel through HTTP API in case it's not in cache
                                logger.info(f"Events channel not in cache, trying HTTP fetch for: {events_channel_id}")
                                events_channel = await guild.fetch_channel(events_channel_id)
                                logger.info(f"HTTP fetch successful for events channel: {events_channel.name if events_channel is not None else None}")
                            except discord.NotFound:
                                logger.error(f"Events channel {events_channel_id} not found in guild {guild_id}")
                                channel_configured = False
                                logger.info(f"Channel not found, continuing without events channel for server {server_id}")
                    except Exception as fetch_e:
                        logger.error(f"Error fetching events channel: {fetch_e}")
                        channel_configured = False
                        logger.info(f"Error fetching channel, continuing without events channel for server {server_id}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting events_channel_id to int: {e}")
                        channel_configured = False

                # Try to get connections channel
                if connections_channel_id is not None:
                    try:
                        # Ensure channel ID is an integer
                        if not isinstance(connections_channel_id, int):
                            connections_channel_id = int(connections_channel_id)
                            logger.info(f"Converted connections_channel_id to int: {connections_channel_id}")
                        
                        # Try to get the channel
                        connections_channel = guild.get_channel(connections_channel_id)
                        logger.info(f"Attempted to get connections channel: {connections_channel_id}, result: {connections_channel is not None}")
                        
                        if connections_channel is None:
                            try:
                                # Try to fetch channel through HTTP API in case it's not in cache
                                logger.info(f"Connections channel not in cache, trying HTTP fetch for: {connections_channel_id}")
                                connections_channel = await guild.fetch_channel(connections_channel_id)
                                logger.info(f"HTTP fetch successful for connections channel: {connections_channel.name}")
                            except discord.NotFound:
                                logger.error(f"Connections channel {connections_channel_id} not found in guild {guild_id}")
                                logger.info(f"Connection channel not found, continuing without connections channel for server {server_id}")
                                # We'll still have events channel potentially
                            except Exception as fetch_e:
                                logger.error(f"Error fetching connections channel: {fetch_e}")
                                logger.info(f"Error fetching connections channel, continuing without connections channel for server {server_id}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting connections_channel_id to int: {e}")
            
            # Log what channels we have
            logger.info(f"Events channel: {events_channel.name if events_channel else None}")
            logger.info(f"Connections channel: {connections_channel.name if connections_channel else None}")
            
            # Verify permissions if channels are found
            for channel_type, channel in [("Events", events_channel), ("Connections", connections_channel)]:
                if channel is not None:
                    try:
                        # Check if the bot has permission to send messages
                        permissions = channel.permissions_for(guild.me)
                        if not permissions.send_messages:
                            logger.warning(f"{channel_type} channel {channel.name} ({channel.id}) - Bot does not have permission to send messages")
                            if channel_type == "Events":
                                channel_configured = False
                        elif not permissions.embed_links:
                            logger.warning(f"{channel_type} channel {channel.name} ({channel.id}) - Bot does not have permission to embed links")
                    except Exception as e:
                        logger.error(f"Error checking permissions for {channel_type.lower()} channel: {e}")
                        if channel_type == "Events":
                            channel_configured = False
                else:
                    if channel_type == "Events" and events_channel_id is not None:
                        logger.warning(f"{channel_type} channel configured but not found: {events_channel_id}")
                        channel_configured = False
            
            # Initialize monitoring status in database
            try:
                # Mark as running in database
                await self.bot.db.monitoring.update_one(
                    {"guild_id": guild_id, "server_id": server_id, "type": "events"},
                    {"$set": {
                        "running": True,
                        "last_updated": datetime.datetime.utcnow(),
                        "channel_id": events_channel_id,
                        "error": None
                    }},
                    upsert=True
                )
            except Exception as db_e:
                logger.error(f"Error updating monitoring status in database: {db_e}")
                # Continue anyway

            # Main monitoring loop
            while True:
                try:
                    # Get log file
                    log_file = await sftp_client.get_log_file()
                    if log_file is None:
                        logger.warning(f"No log file found for server {server_id}")
                        # If we haven't found a log file for a while, try reconnecting
                        if time.time() - last_successful_connection > 300:  # 5 minutes
                            logger.info(f"No log file found for 5 minutes, reconnecting SFTP for server {server_id}")
                            await sftp_client.disconnect()
                            
                            reconnect_attempts += 1
                            if reconnect_attempts > max_reconnect_attempts:
                                logger.error(f"Maximum reconnection attempts ({max_reconnect_attempts}) reached for server {server_id}")
                                break
                                
                            # Exponential backoff
                            backoff_time = min(backoff_time * 2, 60)  # Max 60 seconds
                            logger.info(f"Waiting {backoff_time} seconds before reconnecting (attempt {reconnect_attempts}/{max_reconnect_attempts})")
                            await asyncio.sleep(backoff_time)
                            
                            try:
                                logger.info(f"Attempting to reconnect SFTP for server {server_id}")
                                sftp_connected = await sftp_client.connect()
                                if sftp_connected:
                                    logger.info(f"Successfully reconnected SFTP for server {server_id}")
                                    # Reset backoff and reconnect attempts on successful connection
                                    backoff_time = 5
                                    reconnect_attempts = 0
                                    last_successful_connection = time.time()
                                else:
                                    logger.error(f"Failed to reconnect SFTP for server {server_id}")
                            except Exception as reconnect_e:
                                logger.error(f"Error reconnecting SFTP for server {server_id}: {reconnect_e}")
                                
                        # Wait before trying again
                        await asyncio.sleep(EVENTS_REFRESH_INTERVAL)
                        continue
                        
                    # Process log file for events and connection messages
                    if log_file:
                        last_successful_connection = time.time()
                        
                        # Reset backoff and reconnect attempts on successful connection
                        backoff_time = 5
                        reconnect_attempts = 0
                        
                        # Parse log entries
                        for entry in log_file:
                            message = entry.get('message', '')
                            timestamp = entry.get('timestamp')
                            
                            # Check for event messages
                            try:
                                # Process events
                                # Check if the message contains event data
                                event_data = None
                                for event_type in ['mission', 'airdrop', 'crash', 'heli crash', 'trader', 'convoy', 'encounter', 'server restart']:
                                    if event_type.lower() in message.lower():
                                        event_data = {
                                            'type': event_type,
                                            'message': message,
                                            'timestamp': timestamp
                                        }
                                        break
                                
                                if event_data:
                                    # Process event
                                    await process_event(self.bot, server, event_data, events_channel if channel_configured else None)
                            except Exception as event_e:
                                logger.error(f"Error processing event message: {event_e}")
                                logger.error(f"Message was: {message}")
                                continue  # Skip this message and continue with the next
                                
                            # Check for connection messages
                            try:
                                # Process connections (player joins/leaves)
                                connection_data = None
                                if "connected" in message.lower() or "disconnected" in message.lower():
                                    # Extract player name and connection status
                                    connection_data = {
                                        'message': message,
                                        'timestamp': timestamp
                                    }
                                
                                if connection_data:
                                    # Process connection
                                    await process_connection(self.bot, server, connection_data, connections_channel)
                            except Exception as conn_e:
                                logger.error(f"Error processing connection message: {conn_e}")
                                logger.error(f"Message was: {message}")
                                continue  # Skip this message and continue with the next
                                
                            # Check for voice calls
                            try:
                                # This is custom handling for voice communications events
                                # Only enable if server supports it
                                if hasattr(server, 'voice_notifications_enabled') and server.voice_notifications_enabled:
                                    if "voice call" in message.lower():
                                        # Extract voice call data
                                        await process_voice_call(self.bot, server, message, timestamp, events_channel)
                            except Exception as voice_e:
                                logger.error(f"Error processing voice call message: {voice_e}")
                                logger.error(f"Message was: {message}")
                                continue  # Skip this message and continue with the next
                    
                    # Update monitoring status in database
                    try:
                        await self.bot.db.monitoring.update_one(
                            {"guild_id": guild_id, "server_id": server_id, "type": "events"},
                            {"$set": {"last_updated": datetime.datetime.utcnow()}}
                        )
                    except asyncio.CancelledError:
                        # Allow cancellation to propagate
                        raise
                    except Exception as e:
                        # Log but continue
                        logger.error(f"Error updating monitoring status in database: {e}")
                        
                    # Success, wait for next interval
                    await asyncio.sleep(EVENTS_REFRESH_INTERVAL)
                
                except asyncio.CancelledError:
                    # Task is being cancelled, clean up and exit
                    logger.info(f"Events monitor for server {server_id} in guild {guild_id} is being cancelled")
                    break
                except Exception as e:
                    # Something went wrong, log it and retry after a delay
                    logger.error(f"Error in events monitor for server {server_id}: {e}")
                    logger.error("Full traceback:", exc_info=True)
                    
                    # Update monitoring status with error
                    try:
                        await self.bot.db.monitoring.update_one(
                            {"guild_id": guild_id, "server_id": server_id, "type": "events"},
                            {"$set": {
                                "last_updated": datetime.datetime.utcnow(),
                                "error": str(e)
                            }}
                        )
                    except Exception as inner_e:
                        logger.error(f"Error updating monitoring status with error in database: {inner_e}")
                        
                    # Wait before retrying
                    try:
                        await asyncio.sleep(EVENTS_REFRESH_INTERVAL)
                    except asyncio.CancelledError:
                        # Allow cancellation to propagate during sleep
                        logger.info(f"Events monitor for server {server_id} in guild {guild_id} cancelled during error recovery")
                        break
                        
                    # Try to reconnect if it's a connection issue
                    if "ConnectionRefusedError" in str(e) or "TimeoutError" in str(e) or "EOFError" in str(e):
                        logger.info(f"Connection error detected, attempting to reconnect SFTP for server {server_id}")
                        try:
                            await sftp_client.disconnect()
                            sftp_connected = await sftp_client.connect()
                            if sftp_connected:
                                logger.info(f"Successfully reconnected SFTP for server {server_id} after connection error")
                                last_successful_connection = time.time()
                            else:
                                logger.error(f"Failed to reconnect SFTP for server {server_id} after connection error")
                        except Exception as reconnect_e:
                            logger.error(f"Error reconnecting SFTP for server {server_id} after connection error: {reconnect_e}")
                
        except Exception as e:
            logger.error(f"Unexpected error in events monitor: {e}", exc_info=True)
            
        finally:
            # No need to clean up SFTP connection as killfeed monitor might be using it
            logger.info(f"Events monitor for server {server_id} stopped")
            
            # Mark as stopped in database
            try:
                await self.bot.db.monitoring.update_one(
                    {"guild_id": guild_id, "server_id": server_id, "type": "events"},
                    {"$set": {
                        "running": False,
                        "last_updated": datetime.datetime.utcnow()
                    }}
                )
            except Exception as db_e:
                logger.error(f"Error updating monitoring status in database during shutdown: {db_e}")

async def process_event(bot, server, event_data, channel):
    """Process an event and update the database"""
    try:
        # Create timestamp object if it's a string
        if isinstance(event_data["timestamp"], str):
            event_data["timestamp"] = datetime.fromisoformat(event_data["timestamp"])

        # Add server_id to the event
        event_data["server_id"] = server.get('server_id')

        # Create event in database
        event = await Event.create(bot.db, event_data)

        # Check if this is not None type of event notification is enabled
        event_type = event_data.get("event_type") or event_data.get("type")
        if event_type in server.event_notifications and not server.event_notifications.get(event_type, True):
            logger.debug(f"Skipping notification for {event_type} event as it's disabled for server {server.get('server_id')}")
            return

        # Get guild model for themed embed
        guild_data = await bot.db.guilds.find_one({"servers.server_id": server.get('server_id')})
        guild_model = None
        if guild_data is not None:
            # Use create_from_db_document to ensure proper conversion of premium_tier
            guild_model = Guild.create_from_db_document(guild_data, bot.db)

        # Create embed for the event
        embed = await EmbedBuilder.create_event_embed(event_data, guild=guild_model)

        # Get the icon file for the specific event type
        from utils.embed_icons import create_discord_file, get_event_icon
        # Get the event icon based on the event type
        event_icon_path = get_event_icon(event_data.get("type", "unknown"))
        icon_file = create_discord_file(event_icon_path) if event_icon_path is not None else None

        # Send to channel with the event icon if channel is not None exists
        if channel is not None:
            try:
                if icon_file is not None:
                    await channel.send(embed=embed, file=icon_file)
                else:
                    # Fallback if file can't be created
                    await channel.send(embed=embed)
            except Exception as send_error:
                logger.error(f"Error sending event to channel: {send_error}")
        else:
            # No channel to send to, but we still log this and continue processing
            event_desc = event_data.get('description', 'Unknown event')
            logger.info(f"Event processed but not displayed (no channel): {event_desc}")

        # Handle server restart event specially
        if isinstance(event_data, dict) and event_data["type"] == "server_restart":
            # Reset player count tracking
            logger.info(f"Server restart detected for {server.get('server_id')}")

    except Exception as e:
        logger.error(f"Error processing event: {e}", exc_info=True)


async def process_connection(bot, server, connection_data, channel):
    """Process a connection event and update the database"""
    try:
        # Create timestamp object if it's a string
        if isinstance(connection_data["timestamp"], str):
            connection_data["timestamp"] = datetime.fromisoformat(connection_data["timestamp"])

        # Add server_id to the connection
        connection_data["server_id"] = server.get('server_id')

        # Create connection in database
        connection = await Connection.create(bot.db, connection_data)

        # Get connection action
        action = connection_data["action"]

        # Check if this is not None type of connection notification is enabled
        if action in server.connection_notifications and not server.connection_notifications.get(action, True):
            logger.debug(f"Skipping notification for {action} connection as it's disabled for server {server.get('server_id')}")
            return

        # Get guild model for themed embed
        guild_data = await bot.db.guilds.find_one({"servers.server_id": server.get('server_id')})
        guild_model = None
        if guild_data is not None:
            # Use create_from_db_document to ensure proper conversion of premium_tier
            guild_model = Guild.create_from_db_document(guild_data, bot.db)

        # Create base embed with theme
        if action == "connected":
            title = "🟢 Player Connected"
        else:
            title = "🔴 Player Disconnected"

        player_name = connection_data["player_name"]
        platform = connection_data.get("platform", "Unknown")

        # Create themed base embed
        embed = await EmbedBuilder.create_base_embed(
            title=title,
            description=f"**{player_name}** has {action} to the server",
            guild=guild_model
        )

        # Override color for connection status
        if action == "connected":
            embed.color = discord.Color.green()
        else:
            embed.color = discord.Color.red()

        embed.timestamp = connection_data["timestamp"]
        embed.add_field(name="Platform", value=platform, inline=True)

        # Get the icon file for the connection event
        from utils.embed_icons import create_discord_file, CONNECTIONS_ICON
        icon_file = create_discord_file(CONNECTIONS_ICON)

        # Send to channel with connection icon if channel is not None exists
        if channel is not None:
            try:
                if icon_file is not None:
                    await channel.send(embed=embed, file=icon_file)
                else:
                    # Fallback if file can't be created
                    await channel.send(embed=embed)
            except Exception as send_error:
                logger.error(f"Error sending connection event to channel: {send_error}")
        else:
            # No channel to send to, but we still log this and continue processing
            logger.info(f"Connection event processed but not displayed (no channel): {player_name} has {action} to the server")

    except Exception as e:
        logger.error(f"Error handling command: {ctx.command}", exc_info=True)


async def setup(bot):
    """Set up the Events cog"""
    await bot.add_cog(Events(bot))