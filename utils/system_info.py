"""
System Information Module

This module provides utilities for gathering system information and statistics.
"""

import logging
import platform
import os
import sys
import datetime
import psutil
from typing import Dict, Any, List, Optional

# Configure logger
logger = logging.getLogger("utils.system_info")

class SystemInfo:
    """
    System information manager
    
    This class provides methods for gathering system information and statistics.
    """
    
    @staticmethod
    def get_basic_info() -> Dict[str, Any]:
        """
        Get basic system information
        
        Returns:
            Dict[str, Any]: Basic system information
        """
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "python_build": platform.python_build(),
            "python_compiler": platform.python_compiler()
        }
        
        return info
        
    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        """
        Get CPU information
        
        Returns:
            Dict[str, Any]: CPU information
        """
        try:
            info = {
                "cpu_count_physical": psutil.cpu_count(logical=False),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "cpu_usage_percent": psutil.cpu_percent(interval=0.5),
                "cpu_freq": None
            }
            
            try:
                freq = psutil.cpu_freq()
                if freq:
                    info["cpu_freq"] = {
                        "current": freq.current,
                        "min": freq.min,
                        "max": freq.max
                    }
            except:
                pass
                
            return info
        except:
            logger.error("Failed to get CPU information", exc_info=True)
            return {"error": "Failed to get CPU information"}
            
    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """
        Get memory information
        
        Returns:
            Dict[str, Any]: Memory information
        """
        try:
            # Get virtual memory
            vm = psutil.virtual_memory()
            
            # Get swap memory
            swap = psutil.swap_memory()
            
            info = {
                "virtual_memory": {
                    "total": vm.total,
                    "available": vm.available,
                    "used": vm.used,
                    "free": vm.free,
                    "percent": vm.percent
                },
                "swap_memory": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent
                }
            }
            
            return info
        except:
            logger.error("Failed to get memory information", exc_info=True)
            return {"error": "Failed to get memory information"}
            
    @staticmethod
    def get_disk_info() -> Dict[str, Any]:
        """
        Get disk information
        
        Returns:
            Dict[str, Any]: Disk information
        """
        try:
            # Get all disk partitions
            partitions = psutil.disk_partitions()
            
            # Get disk usage for each partition
            partition_info = []
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    partition_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "opts": partition.opts,
                        "usage": {
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": usage.percent
                        }
                    })
                except:
                    # Skip partitions that can't be accessed
                    pass
                    
            # Get disk IO
            try:
                io = psutil.disk_io_counters()
                
                io_info = {
                    "read_count": io.read_count,
                    "write_count": io.write_count,
                    "read_bytes": io.read_bytes,
                    "write_bytes": io.write_bytes,
                    "read_time": io.read_time,
                    "write_time": io.write_time
                }
            except:
                io_info = None
                
            info = {
                "partitions": partition_info,
                "io": io_info
            }
            
            return info
        except:
            logger.error("Failed to get disk information", exc_info=True)
            return {"error": "Failed to get disk information"}
            
    @staticmethod
    def get_network_info() -> Dict[str, Any]:
        """
        Get network information
        
        Returns:
            Dict[str, Any]: Network information
        """
        try:
            # Get network interfaces
            interfaces = psutil.net_if_addrs()
            
            # Get network IO
            io = psutil.net_io_counters()
            
            info = {
                "interfaces": {},
                "io": {
                    "bytes_sent": io.bytes_sent,
                    "bytes_recv": io.bytes_recv,
                    "packets_sent": io.packets_sent,
                    "packets_recv": io.packets_recv,
                    "errin": io.errin,
                    "errout": io.errout,
                    "dropin": io.dropin,
                    "dropout": io.dropout
                }
            }
            
            # Format interface information
            for interface, addrs in interfaces.items():
                info["interfaces"][interface] = []
                
                for addr in addrs:
                    addr_info = {
                        "family": str(addr.family),
                        "address": addr.address
                    }
                    
                    if hasattr(addr, "netmask") and addr.netmask:
                        addr_info["netmask"] = addr.netmask
                        
                    if hasattr(addr, "broadcast") and addr.broadcast:
                        addr_info["broadcast"] = addr.broadcast
                        
                    info["interfaces"][interface].append(addr_info)
                    
            return info
        except:
            logger.error("Failed to get network information", exc_info=True)
            return {"error": "Failed to get network information"}
            
    @staticmethod
    def get_process_info(pid: Optional[int] = None) -> Dict[str, Any]:
        """
        Get process information
        
        Args:
            pid: Process ID (default: current process)
            
        Returns:
            Dict[str, Any]: Process information
        """
        try:
            # Get the process
            if pid is None:
                pid = os.getpid()
                
            process = psutil.Process(pid)
            
            # Get process information
            info = {
                "pid": process.pid,
                "name": process.name(),
                "status": process.status(),
                "create_time": datetime.datetime.fromtimestamp(process.create_time()).isoformat(),
                "username": process.username(),
                "terminal": process.terminal(),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_info": {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms
                },
                "memory_percent": process.memory_percent(),
                "num_threads": process.num_threads(),
                "num_fds": process.num_fds() if hasattr(process, "num_fds") else None,
                "connections": len(process.connections()),
                "io_counters": None
            }
            
            # Get IO counters if available
            try:
                io = process.io_counters()
                
                info["io_counters"] = {
                    "read_count": io.read_count,
                    "write_count": io.write_count,
                    "read_bytes": io.read_bytes,
                    "write_bytes": io.write_bytes
                }
            except:
                pass
                
            return info
        except:
            logger.error(f"Failed to get process information for PID {pid}", exc_info=True)
            return {"error": f"Failed to get process information for PID {pid}"}
            
    @staticmethod
    def get_all_info() -> Dict[str, Any]:
        """
        Get all system information
        
        Returns:
            Dict[str, Any]: All system information
        """
        return {
            "basic": SystemInfo.get_basic_info(),
            "cpu": SystemInfo.get_cpu_info(),
            "memory": SystemInfo.get_memory_info(),
            "disk": SystemInfo.get_disk_info(),
            "network": SystemInfo.get_network_info(),
            "process": SystemInfo.get_process_info()
        }
        
    @staticmethod
    def get_module_versions() -> Dict[str, str]:
        """
        Get versions of installed modules
        
        Returns:
            Dict[str, str]: Module versions
        """
        try:
            import pkg_resources
            
            modules = {}
            for module in pkg_resources.working_set:
                modules[module.key] = module.version
                
            return modules
        except:
            logger.error("Failed to get module versions", exc_info=True)
            return {"error": "Failed to get module versions"}