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