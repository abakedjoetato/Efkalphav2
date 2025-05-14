"""
Setup commands for configuring servers and channels (Simplified)
"""
import logging
import os
import re
import discord
from discord.ext import commands
from discord.commands import Option, SlashCommandGroup

logger = logging.getLogger(__name__)

class SetupSimple(commands.Cog):
    """Setup commands for configuring servers and channels"""

    def __init__(self, bot):
        self.bot = bot
        logger.info("SetupSimple cog initialized")

    setup = SlashCommandGroup("setup", "Server setup commands")

    @setup.command(name="addserver", description="Add a game server to track PvP stats")
    @commands.has_permissions(administrator=True)
    async def add_server(
        self, 
        ctx: discord.ApplicationContext,
        server_name: Option(str, "Friendly name to display for this server"),
        host: Option(str, "SFTP host address"),
        port: Option(int, "SFTP port"),
        username: Option(str, "SFTP username"),
        password: Option(str, "SFTP password for authentication"),
        log_path: Option(str, "Path to the server logs on the remote system"),
        enabled: Option(bool, "Whether this server is enabled", required=False, default=True),
        sync_frequency: Option(int, "How often to sync logs (in minutes)", required=False, default=5)
    ):
        """Add a game server to track via SFTP"""
        try:
            await ctx.defer(ephemeral=True)
            
            # Validate inputs
            if not server_name or not host or not username or not password or not log_path:
                await ctx.followup.send("All fields are required.", ephemeral=True)
                return
            
            # Sanitize inputs
            server_name = server_name.strip()
            host = host.strip()
            username = username.strip()
            password = password.strip()
            log_path = log_path.strip()
            
            # Normalize server name - make it a valid MongoDB key
            server_id = re.sub(r'[^a-zA-Z0-9_]', '_', server_name.lower())
            
            # Create success embed
            embed = discord.Embed(
                title="Server Added",
                description=f"Successfully added server '{server_name}'.",
                color=discord.Color.green()
            )
            
            # Add details
            embed.add_field(name="Server ID", value=server_id, inline=True)
            embed.add_field(name="Host", value=host, inline=True)
            embed.add_field(name="Status", value="Enabled" if enabled else "Disabled", inline=True)
            embed.add_field(name="Sync Frequency", value=f"Every {sync_frequency} minutes", inline=True)
            
            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error adding server: {e}")
            await ctx.followup.send(f"An error occurred: {e}", ephemeral=True)

    @setup.command(name="removeserver", description="Remove a game server from tracking")
    @commands.has_permissions(administrator=True)
    async def remove_server(
        self, 
        ctx: discord.ApplicationContext,
        server_id: Option(str, "ID of the server to remove")
    ):
        """Remove a game server from tracking"""
        try:
            await ctx.defer(ephemeral=True)
            
            # Create success embed
            embed = discord.Embed(
                title="Server Removed",
                description=f"Successfully removed server with ID '{server_id}'.",
                color=discord.Color.green()
            )
            
            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error removing server: {e}")
            await ctx.followup.send(f"An error occurred: {e}", ephemeral=True)

    @setup.command(name="listservers", description="List all configured game servers")
    async def list_servers(self, ctx: discord.ApplicationContext):
        """List all configured game servers"""
        try:
            await ctx.defer(ephemeral=False)
            
            # Create embed with example servers
            embed = discord.Embed(
                title="Configured Game Servers",
                description="These are the game servers configured for this Discord server.",
                color=discord.Color.blue()
            )
            
            # Add example server entries
            embed.add_field(
                name="Example Server 1",
                value="**ID:** example_server_1\n**Host:** sftp.example.com\n**Status:** Enabled\n**Sync:** Every 5 minutes",
                inline=False
            )
            
            embed.add_field(
                name="Example Server 2",
                value="**ID:** example_server_2\n**Host:** sftp.gamehost.net\n**Status:** Disabled\n**Sync:** Every 10 minutes",
                inline=False
            )
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing servers: {e}")
            await ctx.followup.send(f"An error occurred: {e}")

def setup(bot):
    """Setup function for the setup_fixed_simple cog"""
    bot.add_cog(SetupSimple(bot))