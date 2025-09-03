"""
Rate limiting utilities for API calls to prevent hitting rate limits.

This module provides intelligent rate limiting for AI model API calls,
with configurable delays, exponential backoff, and fallback strategies.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Import structured logging
try:
    from .logging_config import get_api_logger
except ImportError:
    try:
        from rulectl.logging_config import get_api_logger
    except ImportError:
        # Fallback if logging config not available
        def get_api_logger():
            class FallbackLogger:
                def info(self, msg, **kwargs): logger.info(msg)
                def warning(self, msg, **kwargs): logger.warning(msg)
                def error(self, msg, **kwargs): logger.error(msg)
                def debug(self, msg, **kwargs): logger.debug(msg)
                def verbose(self, msg, **kwargs): logger.info(msg)  # Fallback to info for verbose
            return FallbackLogger()

class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    CONSTANT = "constant"
    EXPONENTIAL = "exponential"
    ADAPTIVE = "adaptive"

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 5
    base_delay_ms: int = 1000
    max_delay_ms: int = 60000
    exponential_multiplier: float = 2.0
    jitter_ms: int = 100
    strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE
    
    # Fallback configuration
    enable_fallback: bool = True
    fallback_delay_ms: int = 5000  # 5 second delay before trying fallback
    
    # Batch processing
    enable_batching: bool = True
    max_batch_size: int = 3
    batch_delay_ms: int = 2000  # 2 second delay between batches

class RateLimiter:
    """
    Intelligent rate limiter for API calls with multiple strategies.
    
    Features:
    - Configurable rate limits per minute
    - Multiple delay strategies (constant, exponential, adaptive)
    - Automatic fallback to cheaper models when rate limited
    - Batch processing to reduce API calls
    - Jitter to prevent thundering herd problems
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Initialize the rate limiter.
        
        Args:
            config: Rate limiting configuration. If None, uses sensible defaults.
        """
        self.config = config or RateLimitConfig()
        self.last_request_time = 0.0
        self.request_count = 0
        self.window_start = time.time()
        self.consecutive_failures = 0
        self.current_delay = self.config.base_delay_ms
        self.api_logger = get_api_logger()
        
        # Log initialization
        self.api_logger.info("Rate limiter initialized",
                           requests_per_minute=self.config.requests_per_minute,
                           base_delay_ms=self.config.base_delay_ms,
                           strategy=self.config.strategy.value,
                           enable_batching=self.config.enable_batching,
                           max_batch_size=self.config.max_batch_size)
        
    def _reset_window(self):
        """Reset the rate limiting window."""
        self.window_start = time.time()
        self.request_count = 0
        
    def _should_rate_limit(self) -> bool:
        """Check if we should rate limit based on current usage."""
        current_time = time.time()
        
        # Reset window if more than 1 minute has passed
        if current_time - self.window_start >= 60:
            self._reset_window()
            return False
            
        # Check if we're at the limit
        return self.request_count >= self.config.requests_per_minute
        
    def _calculate_delay(self) -> float:
        """Calculate the delay needed based on the current strategy."""
        if self.consecutive_failures == 0:
            # No failures, use base delay
            delay = self.config.base_delay_ms
        elif self.config.strategy == RateLimitStrategy.CONSTANT:
            delay = self.config.base_delay_ms
        elif self.config.strategy == RateLimitStrategy.EXPONENTIAL:
            delay = min(
                self.config.base_delay_ms * (self.config.exponential_multiplier ** self.consecutive_failures),
                self.config.max_delay_ms
            )
        else:  # ADAPTIVE
            # Start with exponential, but cap it
            delay = min(
                self.config.base_delay_ms * (self.config.exponential_multiplier ** min(self.consecutive_failures, 3)),
                self.config.max_delay_ms
            )
            
        # Add jitter to prevent thundering herd
        import random
        jitter = random.randint(-self.config.jitter_ms, self.config.jitter_ms)
        delay = max(0, delay + jitter)
        
        return delay / 1000.0  # Convert to seconds
        
    async def wait_if_needed(self) -> None:
        """Wait if rate limiting is needed."""
        if self._should_rate_limit():
            delay = self._calculate_delay()
            self.api_logger.warning("Rate limit reached - applying delay",
                                  delay_seconds=delay,
                                  current_requests=self.request_count,
                                  max_requests=self.config.requests_per_minute,
                                  consecutive_failures=self.consecutive_failures,
                                  strategy=self.config.strategy.value)
            logger.info(f"Rate limit reached. Waiting {delay:.2f} seconds...")
            await asyncio.sleep(delay)
            self._reset_window()
            
    def record_request(self) -> None:
        """Record that a request was made."""
        current_time = time.time()
        
        # Reset window if needed
        if current_time - self.window_start >= 60:
            self._reset_window()
            
        self.request_count += 1
        self.last_request_time = current_time
        
        # Log API call (VERBOSE level for detailed request tracking)
        self.api_logger.verbose("API request recorded",
                              request_count=self.request_count,
                              max_requests=self.config.requests_per_minute,
                              window_elapsed=current_time - self.window_start,
                              time_since_last=current_time - self.last_request_time if self.last_request_time else 0)
        
    def record_success(self) -> None:
        """Record a successful request."""
        self.consecutive_failures = 0
        self.current_delay = self.config.base_delay_ms
        
        # Log successful API call
        self.api_logger.debug("API request succeeded",
                            consecutive_failures_reset=True,
                            current_delay_ms=self.current_delay)
        
    def record_failure(self, error: Exception) -> None:
        """Record a failed request and adjust strategy."""
        self.consecutive_failures += 1
        
        # Check if it's a rate limit error
        error_str = str(error).lower()
        is_rate_limit_error = "rate_limit" in error_str or "429" in error_str or "too many requests" in error_str
        
        if is_rate_limit_error:
            logger.warning(f"Rate limit error detected: {error}")
            # Increase delay more aggressively for rate limit errors
            old_delay = self.current_delay
            self.current_delay = min(
                self.current_delay * 2,
                self.config.max_delay_ms
            )
            
            # Log rate limit error with details
            self.api_logger.error("Rate limit error detected",
                                error_type="rate_limit",
                                error_message=str(error),
                                consecutive_failures=self.consecutive_failures,
                                old_delay_ms=old_delay,
                                new_delay_ms=self.current_delay)
        else:
            # Regular error, use normal backoff
            old_delay = self.current_delay
            self.current_delay = self._calculate_delay() * 1000  # Convert back to ms
            
            # Log general API error
            self.api_logger.error("API request failed",
                                error_type="general",
                                error_message=str(error),
                                consecutive_failures=self.consecutive_failures,
                                old_delay_ms=old_delay,
                                new_delay_ms=self.current_delay)
            
    async def execute_with_rate_limiting(
        self, 
        func: Callable[..., Awaitable[Any]], 
        *args, 
        **kwargs
    ) -> Any:
        """
        Execute a function with rate limiting.
        
        Args:
            func: Async function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function execution
            
        Raises:
            Exception: Any exception from the function execution
        """
        function_name = getattr(func, '__name__', 'unknown_function')
        start_time = time.time()
        
        # Log API call start (VERBOSE level for detailed tracking)
        self.api_logger.verbose("API call starting",
                               function=function_name,
                               current_request_count=self.request_count,
                               consecutive_failures=self.consecutive_failures)
        
        try:
            await self.wait_if_needed()
            result = await func(*args, **kwargs)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            self.record_request()
            self.record_success()
            
            # Log successful API call (VERBOSE level for detailed tracking)
            self.api_logger.verbose("API call completed successfully",
                                   function=function_name,
                                   execution_time_seconds=execution_time,
                                   result_type=type(result).__name__)
            
            return result
        except Exception as e:
            # Calculate execution time for failed calls
            execution_time = time.time() - start_time
            
            self.record_failure(e)
            
            # Log failed API call
            self.api_logger.error("API call failed",
                                function=function_name,
                                execution_time_seconds=execution_time,
                                error_type=type(e).__name__,
                                error_message=str(e))
            raise
            
    async def execute_batch_with_rate_limiting(
        self,
        func: Callable[..., Awaitable[Any]],
        items: list,
        *args,
        **kwargs
    ) -> list:
        """
        Execute a function on a batch of items with rate limiting.
        
        Args:
            func: Async function to execute on each item
            items: List of items to process
            *args: Additional arguments for the function
            **kwargs: Additional keyword arguments for the function
            
        Returns:
            List of results from processing each item
        """
        if not self.config.enable_batching:
            # Process items one by one
            results = []
            for item in items:
                result = await self.execute_with_rate_limiting(func, item, *args, **kwargs)
                results.append(result)
            return results
            
        # Process items in batches
        results = []
        batch_size = self.config.max_batch_size
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Process batch
            batch_results = []
            for item in batch:
                result = await self.execute_with_rate_limiting(func, item, *args, **kwargs)
                batch_results.append(result)
                
            results.extend(batch_results)
            
            # Add delay between batches if not the last batch
            if i + batch_size < len(items):
                delay = self.config.batch_delay_ms / 1000.0
                logger.info(f"Batch completed. Waiting {delay:.2f} seconds before next batch...")
                await asyncio.sleep(delay)
                
        return results
        
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        current_time = time.time()
        window_remaining = max(0, 60 - (current_time - self.window_start))
        
        return {
            "requests_this_window": self.request_count,
            "max_requests_per_window": self.config.requests_per_minute,
            "window_remaining_seconds": window_remaining,
            "consecutive_failures": self.consecutive_failures,
            "current_delay_ms": self.current_delay,
            "last_request_time": self.last_request_time,
            "rate_limited": self._should_rate_limit()
        }
        
    def reset(self) -> None:
        """Reset the rate limiter state."""
        self.last_request_time = 0.0
        self.request_count = 0
        self.window_start = time.time()
        self.consecutive_failures = 0
        self.current_delay = self.config.base_delay_ms
