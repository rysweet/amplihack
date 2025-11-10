"""Performance monitoring utilities - Batch 262"""

import time
from functools import wraps
from typing import Callable

def monitor_performance(threshold_ms: float = 1000.0):
    """Decorator to monitor function performance.

    Args:
        threshold_ms: Performance threshold in milliseconds

    Returns:
        Decorated function with performance monitoring
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                if elapsed_ms > threshold_ms:
                    print(f"Warning: {func.__name__} took {elapsed_ms:.2f}ms (threshold: {threshold_ms}ms)")
                else:
                    print(f"OK: {func.__name__} completed in {elapsed_ms:.2f}ms")
        return wrapper
    return decorator
