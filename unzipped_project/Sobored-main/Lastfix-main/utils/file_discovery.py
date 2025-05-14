"""
File discovery utilities for handling CSV files and directory structures
with robust error handling and path normalization.
"""
import os
import logging
import re
import time
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any, Union, Set

logger = logging.getLogger("file_discovery")

class FileDiscovery:
    """
    Class for discovering and managing files with advanced caching and monitoring.
    
    Features:
    - Directory monitoring for file changes
    - File categorization and filtering
    - Cache management for performance
    - Batch processing capabilities
    """
    
    def __init__(self, base_directory: str, recursive: bool = False, 
                cache_timeout: int = 300, auto_refresh: bool = True):
        """
        Initialize a FileDiscovery instance.
        
        Args:
            base_directory: The base directory to search in
            recursive: Whether to search recursively
            cache_timeout: Seconds before cache is invalidated
            auto_refresh: Whether to auto-refresh cache when stale
        """
        self.base_directory = normalize_path(base_directory)
        self.recursive = recursive
        self.cache_timeout = cache_timeout
        self.auto_refresh = auto_refresh
        
        # Initialize caches
        self._file_cache: List[str] = []
        self._cache_timestamp: float = 0
        self._known_directories: Set[str] = set()
        self._last_refresh_time: float = 0
        
        # File categorization
        self.categories: Dict[str, List[str]] = {
            "map": [],
            "standard": [],
            "unknown": []
        }
        
        # Statistics
        self.stats = {
            "total_files": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "last_refresh_duration": 0
        }
        
        # Validate and initialize
        if not ensure_directory_exists(self.base_directory):
            create_directory_if_not_exists(self.base_directory)
            
    def refresh_cache(self, force: bool = False) -> bool:
        """
        Refresh the file cache if needed or forced.
        
        Args:
            force: Force cache refresh even if not expired
            
        Returns:
            Whether the cache was refreshed
        """
        now = time.time()
        
        # Check if cache needs refreshing
        if (not force and 
            self._cache_timestamp > 0 and 
            now - self._cache_timestamp < self.cache_timeout):
            self.stats["cache_hits"] += 1
            return False
            
        self.stats["cache_misses"] += 1
        start_time = time.time()
        
        try:
            # Discover files and categorize them
            self._file_cache = discover_csv_files(
                self.base_directory, 
                recursive=self.recursive,
                max_files=5000
            )
            
            # Update categories
            self.categories = {"map": [], "standard": [], "unknown": []}
            for file in self._file_cache:
                category = get_csv_file_category(file)
                self.categories[category].append(file)
                
            # Update stats and cache timestamp
            self.stats["total_files"] = len(self._file_cache)
            self._cache_timestamp = now
            self._last_refresh_time = now
            self.stats["last_refresh_duration"] = time.time() - start_time
            
            # Track directories
            self._known_directories = {os.path.dirname(f) for f in self._file_cache}
            
            return True
        except Exception as e:
            logger.error(f"Error refreshing file cache: {e}")
            return False
            
    def get_files(self, category: Optional[str] = None, 
                 refresh: bool = None, max_files: int = 1000,
                 sort_reverse: bool = True) -> List[str]:
        """
        Get files from cache, optionally filtering by category.
        
        Args:
            category: Filter by category (map, standard, unknown)
            refresh: Whether to refresh cache (None=auto)
            max_files: Maximum number of files to return
            sort_reverse: Sort in reverse order (newest first)
            
        Returns:
            List of matching file paths
        """
        # Determine if we should refresh
        should_refresh = refresh if refresh is not None else (
            self.auto_refresh and 
            (time.time() - self._cache_timestamp > self.cache_timeout)
        )
        
        if should_refresh:
            self.refresh_cache()
            
        # Filter and return files
        if category and category in self.categories:
            files = self.categories[category][:max_files]
        else:
            files = self._file_cache[:max_files]
            
        # Sort (usually by timestamp in filename)
        if sort_reverse:
            return sorted(files, reverse=True)
        return sorted(files)
        
    def get_latest_file(self, category: Optional[str] = None) -> Optional[str]:
        """
        Get the latest file from a specific category.
        
        Args:
            category: File category (map, standard, unknown)
            
        Returns:
            Path to the latest file or None if not found
        """
        files = self.get_files(category=category, max_files=1, sort_reverse=True)
        return files[0] if files else None
        
    def file_exists(self, filename: str) -> bool:
        """
        Check if a specific file exists in the monitored directories.
        
        Args:
            filename: Filename to check
            
        Returns:
            Whether the file exists
        """
        # Ensure the cache is fresh
        if self.auto_refresh and (time.time() - self._cache_timestamp > self.cache_timeout):
            self.refresh_cache()
            
        # Check if the exact path is in the cache
        if filename in self._file_cache:
            return True
            
        # Check if it's just the basename we're looking for
        basename = os.path.basename(filename)
        for cached_file in self._file_cache:
            if os.path.basename(cached_file) == basename:
                return True
                
        # Direct filesystem check as fallback
        return os.path.exists(filename) and os.path.isfile(filename)

# Regex patterns for file matching
CSV_TIMESTAMP_PATTERN = re.compile(r'(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2})\.csv$')
CSV_FILENAME_PATTERN = re.compile(r'^(.*?)(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2})\.csv$')
MAP_FILENAME_PATTERN = re.compile(r'^map_(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2})\.csv$')

class FileDiscoveryError(Exception):
    """Base exception for file discovery errors"""
    pass

class DirectoryNotFoundError(FileDiscoveryError):
    """Exception raised when a directory doesn't exist"""
    pass

class NoFilesFoundError(FileDiscoveryError):
    """Exception raised when no files match the criteria"""
    pass

def normalize_path(path: str) -> str:
    """Normalize a path for consistent handling

    Args:
        path: Path to normalize

    Returns:
        Normalized path
    """
    # Convert path separators to OS-specific format
    normalized = os.path.normpath(path)

    # Ensure path doesn't end with separator unless it's the root
    if normalized.endswith(os.path.sep) and normalized != os.path.sep:
        normalized = normalized[:-1]

    return normalized

def ensure_directory_exists(directory: str) -> bool:
    """Check if directory exists and is actually a directory

    Args:
        directory: Directory path to check

    Returns:
        True if directory exists, False otherwise
    """
    normalized_dir = normalize_path(directory)
    return os.path.exists(normalized_dir) and os.path.isdir(normalized_dir)

def create_directory_if_not_exists(directory: str) -> None:
    """Create directory if it doesn't exist

    Args:
        directory: Directory path to create

    Raises:
        FileDiscoveryError: If directory creation fails
    """
    normalized_dir = normalize_path(directory)
    if not os.path.exists(normalized_dir):
        try:
            os.makedirs(normalized_dir, exist_ok=True)
            logger.info(f"Created directory: {normalized_dir}")
        except Exception as e:
            raise FileDiscoveryError(f"Failed to create directory {normalized_dir}: {e}f")

def discover_csv_files(
    base_directory: str,
    recursive: bool = False,
    include_pattern: Optional[str] = None,
    exclude_pattern: Optional[str] = None,
    max_files: int = 1000
) -> List[str]:
    """Discover CSV files in a directory with robust error handling

    Args:
        base_directory: Base directory to search in
        recursive: Whether to search recursively in subdirectories
        include_pattern: Regex pattern for files to include
        exclude_pattern: Regex pattern for files to exclude
        max_files: Maximum number of files to return

    Returns:
        List of file paths

    Raises:
        DirectoryNotFoundError: If directory doesn't exist
        NoFilesFoundError: If no matching files are found
    """
    # Normalize and check base directory
    base_dir = normalize_path(base_directory)

    # Check if directory exists
    if not ensure_directory_exists(base_dir):
        raise DirectoryNotFoundError(f"Directory not found: {base_dir}")

    # Compile regex patterns if provided
    include_regex = re.compile(include_pattern) if include_pattern else None
    exclude_regex = re.compile(exclude_pattern) if exclude_pattern else None

    # Find all files
    found_files = []
    start_time = time.time()

    # Log discovery start
    logger.debug(f"Starting CSV file discovery in {base_dir} (recursive={recursive})")

    try:
        if recursive:
            # Recursive search with os.walk
            for root, _, files in os.walk(base_dir):
                _process_directory_files(root, files, found_files, include_regex, exclude_regex, max_files)
                if len(found_files) >= max_files:
                    logger.warning(f"Max file limit ({max_files}) reached during discovery")
                    break
        else:
            # Non-recursive - just look in the base directory
            if os.path.exists(base_dir) and os.path.isdir(base_dir):
                files = [f for f in os.listdir(base_dir) if os.path.isfile(os.path.join(base_dir, f))]
                _process_directory_files(base_dir, files, found_files, include_regex, exclude_regex, max_files)
    except Exception as e:
        logger.error(f"Error during file discovery: {e}f")
        raise FileDiscoveryError(f"Error during file discovery: {e}f")

    # Sort files by name (which typically sorts by timestamp for our CSV files)
    found_files.sort()

    # Log discovery results
    logger.debug(f"Found {len(found_files)} files in {time.time() - start_time:.2f}s")

    if not found_files:
        raise NoFilesFoundError(f"No matching CSV files found in {base_dir}")

    return found_files

def _process_directory_files(
    directory: str,
    files: List[str],
    found_files: List[str],
    include_regex: Optional[re.Pattern],
    exclude_regex: Optional[re.Pattern],
    max_files: int
) -> None:
    """Process files in a directory and add matching ones to found_files

    Args:
        directory: Directory containing the files
        files: List of filenames
        found_files: List to add matching files to
        include_regex: Regex pattern for files to include
        exclude_regex: Regex pattern for files to exclude
        max_files: Maximum number of files to find
    """
    for filename in files:
        # Skip if we've reached the maximum
        if len(found_files) >= max_files:
            return

        # Only process .csv files
        if not filename.lower().endswith('.csv'):
            continue

        # Check against include/exclude patterns
        if include_regex and not include_regex.search(filename):
            continue
        if exclude_regex and exclude_regex.search(filename):
            continue

        # Add the full path to the results
        full_path = os.path.join(directory, filename)
        found_files.append(full_path)

def discover_map_csv_files(base_directory: str, max_files: int = 1000) -> List[str]:
    """Discover map-specific CSV files

    Args:
        base_directory: Base directory to search in
        max_files: Maximum number of files to return

    Returns:
        List of map CSV file paths

    Raises:
        DirectoryNotFoundError: If directory doesn't exist
        NoFilesFoundError: If no matching files are found
    """
    # Check for maps subdirectory
    maps_dir = os.path.join(normalize_path(base_directory), "maps")

    # If maps directory exists, search there
    if ensure_directory_exists(maps_dir):
        try:
            # Specifically look for map files in the maps directory
            return discover_csv_files(
                maps_dir,
                recursive=False,
                include_pattern=r'^map_\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}\.csv$',
                max_files=max_files
            )
        except NoFilesFoundError:
            logger.info(f"No map CSV files found in dedicated maps directory: {maps_dir}")
    else:
        logger.info(f"Maps directory not found: {maps_dir}")

    # Fallback: search for map files in the main directory
    try:
        return discover_csv_files(
            base_directory,
            recursive=False,
            include_pattern=r'^map_\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}\.csv$',
            max_files=max_files
        )
    except NoFilesFoundError:
        logger.info(f"No map CSV files found in base directory: {base_directory}")
        return []  # Return empty list instead of raising - maps may not exist

def get_latest_csv_file(directory: str, is_map_file: bool = False) -> Optional[str]:
    """Get the latest CSV file from a directory

    Args:
        directory: Directory to search in
        is_map_file: Whether to look for map-specific CSV files

    Returns:
        Path to the latest CSV file, or None if no files found
    """
    try:
        if is_map_file:
            files = discover_map_csv_files(directory)
        else:
            files = discover_csv_files(directory)

        if not files:
            return None

        # Sort files to find the latest one (assuming timestamp in filename)
        files.sort(reverse=True)
        return files[0]
    except FileDiscoveryError:
        return None

def extract_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """Extract timestamp from a CSV filename

    Args:
        filename: Filename to extract timestamp from

    Returns:
        Extracted timestamp or None if not found
    """
    basename = os.path.basename(filename)

    # Try standard pattern first
    match = CSV_TIMESTAMP_PATTERN.search(basename)
    if match:
        timestamp_str = match.group(1)
        try:
            # Convert from "yyyy.mm.dd-hh.mm.ss" format
            dt = datetime.strptime(timestamp_str, "%Y.%m.%d-%H.%M.%S")
            return dt
        except ValueError:
            pass

    return None

def is_map_csv_file(filename: str) -> bool:
    """Check if a file is a map-specific CSV file

    Args:
        filename: Filename to check

    Returns:
        True if it's a map CSV file, False otherwise
    """
    basename = os.path.basename(filename)
    return bool(MAP_FILENAME_PATTERN.match(basename))

def get_csv_file_category(filename: str) -> str:
    """Determine the category of a CSV file based on its name and location

    Args:
        filename: Full path to the CSV file

    Returns:
        Category of the file: "map", "standard", or "unknown"
    """
    basename = os.path.basename(filename)

    # Check if it's in a maps directory
    if "maps" in os.path.normpath(filename).split(os.path.sep):
        return "map"

    # Check filename pattern for map files
    if MAP_FILENAME_PATTERN.match(basename):
        return "map"

    # Check for standard CSV pattern
    if CSV_FILENAME_PATTERN.match(basename):
        return "standard"

    return "unknown"