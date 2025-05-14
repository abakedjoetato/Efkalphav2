"""
Timed Events Module

This module provides utilities for working with timed events and background tasks.
It enables scheduling of tasks to run at specific intervals or times.
"""

import logging
import asyncio
import datetime
from typing import Dict, List, Callable, Awaitable, Optional, Any, Tuple, Union
import traceback

# Configure logger
logger = logging.getLogger("utils.timed_events")

class TaskScheduler:
    """
    Task scheduler for timed events
    
    This class manages scheduled tasks that run at specific intervals
    or at specific times.
    
    Attributes:
        tasks: Dictionary of scheduled tasks
        running: Whether the scheduler is running
    """
    
    def __init__(self, bot):
        """
        Initialize the task scheduler
        
        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self._shutdown_event = asyncio.Event()
        
    def start(self):
        """Start the task scheduler"""
        if self.running:
            return
            
        self.running = True
        self._shutdown_event.clear()
        logger.info("Task scheduler started")
        
    def stop(self):
        """Stop the task scheduler"""
        if not self.running:
            return
            
        self.running = False
        self._shutdown_event.set()
        
        # Cancel all tasks
        for task_id, task in list(self.tasks.items()):
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled task {task_id}")
            
        logger.info("Task scheduler stopped")
        
    def schedule_task(self, task_id: str, coroutine: Callable[..., Awaitable[Any]], 
                     interval: Optional[float] = None, 
                     when: Optional[datetime.datetime] = None,
                     run_once: bool = False,
                     **kwargs) -> asyncio.Task:
        """
        Schedule a task to run at a specific interval or time
        
        Args:
            task_id: Unique identifier for the task
            coroutine: Coroutine function to run
            interval: Interval in seconds between runs (None for one-time tasks)
            when: Specific time to run the task (None for immediate or interval tasks)
            run_once: Whether to run the task only once
            **kwargs: Additional arguments to pass to the coroutine
            
        Returns:
            asyncio.Task: Scheduled task
        """
        # Cancel existing task with the same ID
        if task_id in self.tasks and not self.tasks[task_id].done():
            self.tasks[task_id].cancel()
            logger.info(f"Cancelled existing task {task_id}")
            
        # Create and schedule the task
        task = asyncio.create_task(
            self._run_task(task_id, coroutine, interval, when, run_once, **kwargs)
        )
        
        self.tasks[task_id] = task
        logger.info(f"Scheduled task {task_id}")
        
        return task
        
    async def _run_task(self, task_id: str, coroutine: Callable[..., Awaitable[Any]],
                       interval: Optional[float], when: Optional[datetime.datetime],
                       run_once: bool, **kwargs):
        """
        Run a scheduled task
        
        Args:
            task_id: Unique identifier for the task
            coroutine: Coroutine function to run
            interval: Interval in seconds between runs
            when: Specific time to run the task
            run_once: Whether to run the task only once
            **kwargs: Additional arguments to pass to the coroutine
        """
        try:
            # Wait until the specified time
            if when is not None:
                now = datetime.datetime.now()
                if when > now:
                    # Calculate delay in seconds
                    delay = (when - now).total_seconds()
                    logger.info(f"Task {task_id} will run at {when} (in {delay:.2f} seconds)")
                    
                    # Wait until the specified time or shutdown
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=delay
                        )
                        # If we get here, shutdown was triggered
                        logger.info(f"Task {task_id} cancelled during delay due to shutdown")
                        return
                    except asyncio.TimeoutError:
                        # Timeout means it's time to run the task
                        pass
                
            # Run the task once or in a loop
            first_run = True
            while self.running and (not run_once or first_run):
                try:
                    # Run the coroutine
                    start_time = datetime.datetime.now()
                    await coroutine(**kwargs)
                    end_time = datetime.datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    logger.debug(f"Task {task_id} completed in {duration:.2f} seconds")
                except Exception as e:
                    logger.error(f"Error in task {task_id}: {e}")
                    logger.debug(traceback.format_exc())
                
                first_run = False
                
                # If this is a one-time task or there's no interval, we're done
                if run_once or interval is None:
                    break
                    
                # Wait for the next interval or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=interval
                    )
                    # If we get here, shutdown was triggered
                    logger.info(f"Task {task_id} cancelled during interval due to shutdown")
                    break
                except asyncio.TimeoutError:
                    # Timeout means it's time to run the task again
                    pass
                    
        except asyncio.CancelledError:
            logger.info(f"Task {task_id} cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in task {task_id}: {e}")
            logger.debug(traceback.format_exc())
        finally:
            # Remove task from the dictionary when it's done
            if task_id in self.tasks:
                del self.tasks[task_id]
                logger.debug(f"Removed task {task_id} from scheduler")
                
    def get_task(self, task_id: str) -> Optional[asyncio.Task]:
        """
        Get a scheduled task by ID
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            Optional[asyncio.Task]: Scheduled task or None if not found
        """
        return self.tasks.get(task_id)
        
    def get_all_tasks(self) -> Dict[str, asyncio.Task]:
        """
        Get all scheduled tasks
        
        Returns:
            Dict[str, asyncio.Task]: Dictionary of task IDs to tasks
        """
        return self.tasks.copy()
        
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            bool: True if the task was cancelled, False if not found
        """
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled task {task_id}")
                return True
                
            del self.tasks[task_id]
            logger.debug(f"Removed completed task {task_id} from scheduler")
            
        return False
        
    def schedule_daily_task(self, task_id: str, coroutine: Callable[..., Awaitable[Any]],
                          time: Tuple[int, int] = (0, 0), **kwargs) -> asyncio.Task:
        """
        Schedule a task to run daily at a specific time
        
        Args:
            task_id: Unique identifier for the task
            coroutine: Coroutine function to run
            time: Tuple of (hour, minute) for the time to run (24-hour format)
            **kwargs: Additional arguments to pass to the coroutine
            
        Returns:
            asyncio.Task: Scheduled task
        """
        hour, minute = time
        
        # Calculate the next occurrence of the specified time
        now = datetime.datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If the time has already passed today, schedule for tomorrow
        if next_run <= now:
            next_run += datetime.timedelta(days=1)
            
        # Define a wrapper function that reschedules itself
        async def daily_wrapper():
            # Run the actual coroutine
            await coroutine(**kwargs)
            
            # Schedule the next run
            next_run = datetime.datetime.now().replace(
                hour=hour, minute=minute, second=0, microsecond=0
            ) + datetime.timedelta(days=1)
            
            self.schedule_task(
                task_id=task_id,
                coroutine=daily_wrapper,
                when=next_run,
                run_once=True
            )
            
        # Schedule the first run
        return self.schedule_task(
            task_id=task_id,
            coroutine=daily_wrapper,
            when=next_run,
            run_once=True
        )
        
    def schedule_weekly_task(self, task_id: str, coroutine: Callable[..., Awaitable[Any]],
                           day: int, time: Tuple[int, int] = (0, 0), **kwargs) -> asyncio.Task:
        """
        Schedule a task to run weekly on a specific day and time
        
        Args:
            task_id: Unique identifier for the task
            coroutine: Coroutine function to run
            day: Day of the week (0 = Monday, 6 = Sunday)
            time: Tuple of (hour, minute) for the time to run (24-hour format)
            **kwargs: Additional arguments to pass to the coroutine
            
        Returns:
            asyncio.Task: Scheduled task
        """
        hour, minute = time
        
        # Calculate the next occurrence of the specified day and time
        now = datetime.datetime.now()
        days_ahead = day - now.weekday()
        if days_ahead <= 0:
            # Target day already happened this week, so schedule for next week
            days_ahead += 7
            
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + \
                  datetime.timedelta(days=days_ahead)
                  
        # Define a wrapper function that reschedules itself
        async def weekly_wrapper():
            # Run the actual coroutine
            await coroutine(**kwargs)
            
            # Schedule the next run
            next_run = datetime.datetime.now().replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            
            # Calculate days until next occurrence
            days_ahead = day - next_run.weekday()
            if days_ahead <= 0:
                days_ahead += 7
                
            next_run += datetime.timedelta(days=days_ahead)
            
            self.schedule_task(
                task_id=task_id,
                coroutine=weekly_wrapper,
                when=next_run,
                run_once=True
            )
            
        # Schedule the first run
        return self.schedule_task(
            task_id=task_id,
            coroutine=weekly_wrapper,
            when=next_run,
            run_once=True
        )

async def run_after_delay(delay: float, coroutine: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
    """
    Run a coroutine after a delay
    
    Args:
        delay: Delay in seconds
        coroutine: Coroutine function to run
        *args: Arguments to pass to the coroutine
        **kwargs: Keyword arguments to pass to the coroutine
        
    Returns:
        Any: Result of the coroutine
    """
    await asyncio.sleep(delay)
    return await coroutine(*args, **kwargs)

def run_delayed(delay: float, coroutine: Callable[..., Awaitable[Any]], *args, **kwargs) -> asyncio.Task:
    """
    Create a task to run a coroutine after a delay
    
    Args:
        delay: Delay in seconds
        coroutine: Coroutine function to run
        *args: Arguments to pass to the coroutine
        **kwargs: Keyword arguments to pass to the coroutine
        
    Returns:
        asyncio.Task: Scheduled task
    """
    return asyncio.create_task(run_after_delay(delay, coroutine, *args, **kwargs))