"""
SFTP Cog

This cog provides commands for SFTP operations, used for log processing
and other file operations.
"""

import logging
import discord
from discord.ext import commands
import os
import io
import asyncio
from typing import Optional
from datetime import datetime

# Import SFTP connection manager
from utils.sftp_connection import SFTPConnectionManager
from utils.premium_feature_access import requires_premium_feature

# Import config
from config import config

# Configure logger
logger = logging.getLogger("cogs.sftp")

class SFTP(commands.Cog):
    """
    SFTP operations cog
    
    This cog provides commands for SFTP operations.
    """
    
    def __init__(self, bot):
        """
        Initialize the cog
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.connections = {}
        
    async def cog_check(self, ctx):
        """
        Check if the cog is enabled
        
        Args:
            ctx: Command context
            
        Returns:
            bool: True if enabled, False otherwise
        """
        # Check if SFTP is enabled in the configuration
        return config.sftp_enabled
        
    @commands.group(name="sftp", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def sftp_group(self, ctx):
        """
        SFTP commands
        
        This command group provides access to SFTP operations.
        Use a subcommand to perform specific operations.
        """
        if ctx.invoked_subcommand is None:
            # Show help for the group
            await ctx.send_help(ctx.command)
            
    @sftp_group.command(name="connect")
    @commands.has_permissions(administrator=True)
    @requires_premium_feature("custom_integrations")
    async def connect(self, ctx, host: str, port: Optional[int] = 22, username: str = None):
        """
        Connect to an SFTP server
        
        This command connects to an SFTP server with the specified parameters.
        The password should be sent in a direct message for security.
        
        Args:
            host: SFTP server hostname
            port: SFTP server port (default: 22)
            username: SFTP username
        """
        # Check if already connected
        if ctx.guild.id in self.connections:
            await ctx.send("❌ Already connected to an SFTP server. Disconnect first.")
            return
            
        # Send a DM to ask for the password
        try:
            # Create a temporary connection object
            connection = {
                'host': host,
                'port': port,
                'username': username,
                'guild_id': ctx.guild.id
            }
            
            # Store connection in temporary storage
            self.connections[ctx.guild.id] = connection
            
            # Send a DM to the user
            await ctx.author.send(f"Please reply with the SFTP password for {username}@{host}:{port}")
            
            # Send a message in the channel
            await ctx.send(f"✅ Connecting to SFTP server {host}:{port}. Please check your DMs for further instructions.")
            
            # Wait for response in DM
            def check(m):
                return m.author == ctx.author and not m.guild
                
            try:
                # Wait for a response in DM
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                
                # Get the password from the message
                password = msg.content.strip()
                
                # Delete the message with the password
                await msg.delete()
                
                # Create the SFTP connection
                sftp_manager = SFTPConnectionManager(
                    host=host,
                    port=port,
                    username=username,
                    password=password
                )
                
                # Try to connect
                if await sftp_manager.connect():
                    # Store the connection
                    connection['manager'] = sftp_manager
                    
                    # Send a success message
                    await ctx.author.send(f"✅ Successfully connected to SFTP server {host}:{port}")
                    await ctx.send(f"✅ Successfully connected to SFTP server {host}:{port}")
                else:
                    # Failed to connect
                    await ctx.author.send(f"❌ Failed to connect to SFTP server {host}:{port}")
                    await ctx.send(f"❌ Failed to connect to SFTP server {host}:{port}")
                    
                    # Remove the connection
                    if ctx.guild.id in self.connections:
                        del self.connections[ctx.guild.id]
            except asyncio.TimeoutError:
                # Timeout waiting for password
                await ctx.author.send("❌ Timed out waiting for password")
                await ctx.send("❌ Timed out waiting for password")
                
                # Remove the connection
                if ctx.guild.id in self.connections:
                    del self.connections[ctx.guild.id]
        except Exception as e:
            logger.error(f"Error connecting to SFTP server: {e}")
            await ctx.send(f"❌ Error connecting to SFTP server: {e}")
            
            # Remove the connection
            if ctx.guild.id in self.connections:
                del self.connections[ctx.guild.id]
                
    @sftp_group.command(name="disconnect")
    @commands.has_permissions(administrator=True)
    @requires_premium_feature("custom_integrations")
    async def disconnect(self, ctx):
        """
        Disconnect from the SFTP server
        
        This command disconnects from the current SFTP server.
        """
        # Check if connected
        if ctx.guild.id not in self.connections:
            await ctx.send("❌ Not connected to an SFTP server")
            return
            
        try:
            # Get the connection
            connection = self.connections[ctx.guild.id]
            
            # Disconnect
            if 'manager' in connection:
                await connection['manager'].disconnect()
                
            # Remove the connection
            del self.connections[ctx.guild.id]
            
            # Send a success message
            await ctx.send(f"✅ Disconnected from SFTP server")
        except Exception as e:
            logger.error(f"Error disconnecting from SFTP server: {e}")
            await ctx.send(f"❌ Error disconnecting from SFTP server: {e}")
            
    @sftp_group.command(name="list")
    @commands.has_permissions(administrator=True)
    @requires_premium_feature("custom_integrations")
    async def list_files(self, ctx, path: str = "."):
        """
        List files on the SFTP server
        
        This command lists files in a directory on the SFTP server.
        
        Args:
            path: Directory path (default: current directory)
        """
        # Check if connected
        if ctx.guild.id not in self.connections or 'manager' not in self.connections[ctx.guild.id]:
            await ctx.send("❌ Not connected to an SFTP server")
            return
            
        try:
            # Get the connection
            manager = self.connections[ctx.guild.id]['manager']
            
            # List files
            files = await manager.list_directory(path)
            
            # Send the file list
            if files:
                # Format the file list
                file_list = "\n".join(files)
                
                # Create an embed
                embed = discord.Embed(
                    title=f"Files in {path}",
                    description=f"```\n{file_list}\n```",
                    color=0x00a8ff
                )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"📁 Directory {path} is empty")
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            await ctx.send(f"❌ Error listing files: {e}")
            
    @sftp_group.command(name="download")
    @commands.has_permissions(administrator=True)
    @requires_premium_feature("custom_integrations")
    async def download_file(self, ctx, remote_path: str):
        """
        Download a file from the SFTP server
        
        This command downloads a file from the SFTP server and
        sends it as an attachment.
        
        Args:
            remote_path: Remote file path
        """
        # Check if connected
        if ctx.guild.id not in self.connections or 'manager' not in self.connections[ctx.guild.id]:
            await ctx.send("❌ Not connected to an SFTP server")
            return
            
        try:
            # Get the connection
            manager = self.connections[ctx.guild.id]['manager']
            
            # Check if the file exists
            if not await manager.file_exists(remote_path):
                await ctx.send(f"❌ File {remote_path} not found")
                return
                
            # Send a message indicating that the download is in progress
            message = await ctx.send(f"⏳ Downloading {remote_path}...")
            
            # Download the file
            file_data = await manager.download_file_object(remote_path)
            
            if file_data:
                # Get the file name from the path
                file_name = os.path.basename(remote_path)
                
                # Create a file object
                file = discord.File(io.BytesIO(file_data), filename=file_name)
                
                # Send the file
                await ctx.send(f"✅ Downloaded {remote_path}", file=file)
                
                # Delete the progress message
                await message.delete()
            else:
                await message.edit(content=f"❌ Failed to download {remote_path}")
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            await ctx.send(f"❌ Error downloading file: {e}")
            
    @sftp_group.command(name="upload")
    @commands.has_permissions(administrator=True)
    @requires_premium_feature("custom_integrations")
    async def upload_file(self, ctx, remote_path: str):
        """
        Upload a file to the SFTP server
        
        This command uploads an attached file to the SFTP server.
        
        Args:
            remote_path: Remote file path
        """
        # Check if connected
        if ctx.guild.id not in self.connections or 'manager' not in self.connections[ctx.guild.id]:
            await ctx.send("❌ Not connected to an SFTP server")
            return
            
        # Check if a file is attached
        if not ctx.message.attachments:
            await ctx.send("❌ No file attached")
            return
            
        try:
            # Get the connection
            manager = self.connections[ctx.guild.id]['manager']
            
            # Get the attached file
            attachment = ctx.message.attachments[0]
            
            # Send a message indicating that the upload is in progress
            message = await ctx.send(f"⏳ Uploading {attachment.filename} to {remote_path}...")
            
            # Download the attachment
            file_data = await attachment.read()
            
            # Upload the file
            if await manager.upload_file_object(file_data, remote_path):
                await message.edit(content=f"✅ Uploaded {attachment.filename} to {remote_path}")
            else:
                await message.edit(content=f"❌ Failed to upload {attachment.filename} to {remote_path}")
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            await ctx.send(f"❌ Error uploading file: {e}")
            
    @sftp_group.command(name="delete")
    @commands.has_permissions(administrator=True)
    @requires_premium_feature("custom_integrations")
    async def delete_file(self, ctx, remote_path: str):
        """
        Delete a file on the SFTP server
        
        This command deletes a file on the SFTP server.
        
        Args:
            remote_path: Remote file path
        """
        # Check if connected
        if ctx.guild.id not in self.connections or 'manager' not in self.connections[ctx.guild.id]:
            await ctx.send("❌ Not connected to an SFTP server")
            return
            
        try:
            # Get the connection
            manager = self.connections[ctx.guild.id]['manager']
            
            # Check if the file exists
            if not await manager.file_exists(remote_path):
                await ctx.send(f"❌ File {remote_path} not found")
                return
                
            # Ask for confirmation
            confirm_message = await ctx.send(f"⚠️ Are you sure you want to delete {remote_path}? Reply with 'yes' to confirm.")
            
            # Wait for confirmation
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() == 'yes'
                
            try:
                # Wait for confirmation
                await self.bot.wait_for('message', check=check, timeout=30.0)
                
                # Delete the file
                if await manager.remove(remote_path):
                    await ctx.send(f"✅ Deleted {remote_path}")
                else:
                    await ctx.send(f"❌ Failed to delete {remote_path}")
            except asyncio.TimeoutError:
                # Timeout waiting for confirmation
                await confirm_message.edit(content="❌ Deletion cancelled due to timeout")
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            await ctx.send(f"❌ Error deleting file: {e}")
            
def setup(bot):
    """
    Set up the SFTP cog
    
    Args:
        bot: The Discord bot instance
    """
    bot.add_cog(SFTP(bot))
    logger.info("SFTP cog loaded")