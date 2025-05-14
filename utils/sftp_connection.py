"""
SFTP Connection Module

This module provides utilities for connecting to SFTP servers and transferring files.
It's used for log processing and other file operations.
"""

import logging
import asyncio
import os
import io
import paramiko
from typing import Dict, List, Optional, Union, BinaryIO, Tuple, Any
import aiofiles
import tempfile
import functools
import concurrent.futures

# Configure logger
logger = logging.getLogger("utils.sftp_connection")

class SFTPConnectionManager:
    """
    SFTP connection manager
    
    This class manages connections to SFTP servers and provides
    methods for file operations.
    
    Attributes:
        host: SFTP server hostname
        port: SFTP server port
        username: SFTP username
        password: SFTP password
        private_key_path: Path to private key file
        private_key_passphrase: Passphrase for private key
        connected: Whether the connection is established
    """
    
    def __init__(self, host: str, port: int = 22, username: str = None, 
                password: str = None, private_key_path: str = None,
                private_key_passphrase: str = None):
        """
        Initialize the SFTP connection manager
        
        Args:
            host: SFTP server hostname
            port: SFTP server port
            username: SFTP username
            password: SFTP password
            private_key_path: Path to private key file
            private_key_passphrase: Passphrase for private key
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key_path = private_key_path
        self.private_key_passphrase = private_key_passphrase
        
        self.connected = False
        self._client = None
        self._sftp = None
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
    async def connect(self) -> bool:
        """
        Connect to the SFTP server
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if self.connected:
            return True
            
        try:
            # Create a new SSH client
            transport = paramiko.Transport((self.host, self.port))
            
            # Authenticate
            if self.private_key_path:
                # Use private key authentication
                private_key = paramiko.RSAKey.from_private_key_file(
                    self.private_key_path,
                    password=self.private_key_passphrase
                )
                transport.connect(username=self.username, pkey=private_key)
            else:
                # Use password authentication
                transport.connect(username=self.username, password=self.password)
                
            # Create SFTP client
            self._sftp = paramiko.SFTPClient.from_transport(transport)
            self._client = transport
            
            self.connected = True
            logger.info(f"Connected to SFTP server at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SFTP server: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from the SFTP server"""
        if not self.connected:
            return
            
        if self._sftp:
            self._sftp.close()
            self._sftp = None
            
        if self._client:
            self._client.close()
            self._client = None
            
        self.connected = False
        logger.info("Disconnected from SFTP server")
        
    async def __aenter__(self):
        """
        Async context manager entry
        
        Returns:
            SFTPConnectionManager: Self
        """
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
        
    def _ensure_connected(func):
        """
        Decorator to ensure the connection is established
        
        Args:
            func: Function to wrap
            
        Returns:
            Function: Wrapped function
        """
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not self.connected:
                if not await self.connect():
                    raise ConnectionError("Not connected to SFTP server")
            return await func(self, *args, **kwargs)
        return wrapper
        
    @_ensure_connected
    async def list_directory(self, path: str) -> List[str]:
        """
        List files in a directory
        
        Args:
            path: Directory path
            
        Returns:
            List[str]: List of file names
        """
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._pool,
                lambda: self._sftp.listdir(path)
            )
            return result
        except Exception as e:
            logger.error(f"Failed to list directory {path}: {e}")
            raise
            
    @_ensure_connected
    async def file_exists(self, path: str) -> bool:
        """
        Check if a file exists
        
        Args:
            path: File path
            
        Returns:
            bool: True if the file exists, False otherwise
        """
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            # Try to get file stats
            await loop.run_in_executor(
                self._pool,
                lambda: self._sftp.stat(path)
            )
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking if file exists {path}: {e}")
            return False
            
    @_ensure_connected
    async def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download a file from the SFTP server
        
        Args:
            remote_path: Remote file path
            local_path: Local file path
            
        Returns:
            bool: True if downloaded successfully, False otherwise
        """
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._pool,
                lambda: self._sftp.get(remote_path, local_path)
            )
            logger.info(f"Downloaded file from {remote_path} to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file {remote_path}: {e}")
            return False
            
    @_ensure_connected
    async def download_file_object(self, remote_path: str) -> Optional[bytes]:
        """
        Download a file from the SFTP server to a bytes object
        
        Args:
            remote_path: Remote file path
            
        Returns:
            Optional[bytes]: File contents or None if download failed
        """
        try:
            # Use a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
                
            # Download to the temporary file
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._pool,
                lambda: self._sftp.get(remote_path, temp_path)
            )
            
            # Read the file
            async with aiofiles.open(temp_path, 'rb') as f:
                data = await f.read()
                
            # Delete the temporary file
            os.unlink(temp_path)
            
            logger.info(f"Downloaded file from {remote_path} to memory")
            return data
        except Exception as e:
            logger.error(f"Failed to download file {remote_path} to memory: {e}")
            return None
            
    @_ensure_connected
    async def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Upload a file to the SFTP server
        
        Args:
            local_path: Local file path
            remote_path: Remote file path
            
        Returns:
            bool: True if uploaded successfully, False otherwise
        """
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._pool,
                lambda: self._sftp.put(local_path, remote_path)
            )
            logger.info(f"Uploaded file from {local_path} to {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file {local_path}: {e}")
            return False
            
    @_ensure_connected
    async def upload_file_object(self, data: bytes, remote_path: str) -> bool:
        """
        Upload a bytes object to the SFTP server
        
        Args:
            data: File contents
            remote_path: Remote file path
            
        Returns:
            bool: True if uploaded successfully, False otherwise
        """
        try:
            # Use a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
                
            # Write the data to the temporary file
            async with aiofiles.open(temp_path, 'wb') as f:
                await f.write(data)
                
            # Upload the temporary file
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._pool,
                lambda: self._sftp.put(temp_path, remote_path)
            )
            
            # Delete the temporary file
            os.unlink(temp_path)
            
            logger.info(f"Uploaded file from memory to {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload file from memory to {remote_path}: {e}")
            return False
            
    @_ensure_connected
    async def mkdir(self, path: str, mode: int = 0o777) -> bool:
        """
        Create a directory
        
        Args:
            path: Directory path
            mode: Directory permissions
            
        Returns:
            bool: True if created successfully, False otherwise
        """
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._pool,
                lambda: self._sftp.mkdir(path, mode)
            )
            logger.info(f"Created directory {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
            
    @_ensure_connected
    async def rmdir(self, path: str) -> bool:
        """
        Remove a directory
        
        Args:
            path: Directory path
            
        Returns:
            bool: True if removed successfully, False otherwise
        """
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._pool,
                lambda: self._sftp.rmdir(path)
            )
            logger.info(f"Removed directory {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove directory {path}: {e}")
            return False
            
    @_ensure_connected
    async def remove(self, path: str) -> bool:
        """
        Remove a file
        
        Args:
            path: File path
            
        Returns:
            bool: True if removed successfully, False otherwise
        """
        try:
            # Run in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._pool,
                lambda: self._sftp.remove(path)
            )
            logger.info(f"Removed file {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove file {path}: {e}")
            return False