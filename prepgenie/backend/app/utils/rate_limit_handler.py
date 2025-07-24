"""
Rate Limit Handler for OpenAI API
Implements exponential backoff, retry logic, and request optimization
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
import random

logger = logging.getLogger(__name__)

class RateLimitHandler:
    """Handles OpenAI API rate limiting with exponential backoff"""
    
    def __init__(self):
        self.last_request_time = 0.0
        self.min_interval = 2.0  # Minimum 2 seconds between requests (more conservative)
        self.backoff_factor = 2.5  # More aggressive backoff
        self.max_retries = 7  # More retries
        self.base_delay = 5.0  # Higher base delay for rate limit errors
        self.max_delay = 120.0  # Higher maximum delay (2 minutes)
        
        # Track consecutive rate limit errors
        self.consecutive_rate_limits = 0
        
    async def execute_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff on rate limits"""
        
        for attempt in range(self.max_retries):
            try:
                # Enforce minimum interval between requests
                await self._enforce_rate_limit()
                
                # Execute the function
                result = await func(*args, **kwargs)
                
                # Reset consecutive rate limits on success
                self.consecutive_rate_limits = 0
                return result
                
            except Exception as e:
                if "rate limit" in str(e).lower() or "429" in str(e):
                    self.consecutive_rate_limits += 1
                    delay = await self._calculate_backoff_delay(attempt)
                    
                    logger.warning(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}). "
                                 f"Waiting {delay:.1f}s before retry...")
                    
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Non-rate-limit error, re-raise immediately
                    raise e
        
        # All retries exhausted
        raise Exception(f"Failed after {self.max_retries} attempts due to rate limiting")
    
    async def _enforce_rate_limit(self):
        """Enforce minimum interval between requests"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter"""
        # Base delay increases with consecutive rate limits
        base = self.base_delay * (self.backoff_factor ** self.consecutive_rate_limits)
        
        # Add attempt-based exponential backoff
        delay = base * (self.backoff_factor ** attempt)
        
        # Add jitter to avoid thundering herd
        jitter = random.uniform(0.5, 1.5)
        delay *= jitter
        
        # Cap at maximum delay
        return min(delay, self.max_delay)

# Global rate limit handler
rate_limit_handler = RateLimitHandler()

def with_rate_limit(func):
    """Decorator to add rate limiting to async functions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await rate_limit_handler.execute_with_backoff(func, *args, **kwargs)
    return wrapper
