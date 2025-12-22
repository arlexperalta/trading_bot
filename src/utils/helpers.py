"""
Helper functions for the crypto trading bot.
"""

import time
from typing import Callable, Any, Optional
from functools import wraps
from datetime import datetime


def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry a function on exception with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise last_exception

        return wrapper
    return decorator


def format_price(price: float, decimals: int = 2) -> str:
    """
    Format price for display.

    Args:
        price: Price value
        decimals: Number of decimal places

    Returns:
        Formatted price string
    """
    return f"${price:,.{decimals}f}"


def format_quantity(quantity: float, decimals: int = 8) -> str:
    """
    Format quantity for display.

    Args:
        quantity: Quantity value
        decimals: Number of decimal places

    Returns:
        Formatted quantity string
    """
    return f"{quantity:.{decimals}f}"


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values.

    Args:
        old_value: Original value
        new_value: New value

    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


def round_step_size(quantity: float, step_size: float) -> float:
    """
    Round quantity to match exchange step size.

    Args:
        quantity: Quantity to round
        step_size: Exchange step size

    Returns:
        Rounded quantity
    """
    precision = len(str(step_size).split('.')[-1])
    return round(quantity - (quantity % step_size), precision)


def is_within_trading_hours(
    start_hour: int = 0,
    end_hour: int = 24
) -> bool:
    """
    Check if current time is within trading hours.

    Args:
        start_hour: Start hour (0-23)
        end_hour: End hour (0-23)

    Returns:
        True if within trading hours
    """
    current_hour = datetime.now().hour
    return start_hour <= current_hour < end_hour


def truncate_float(value: float, decimals: int) -> float:
    """
    Truncate float to specific number of decimals.

    Args:
        value: Value to truncate
        decimals: Number of decimal places

    Returns:
        Truncated value
    """
    multiplier = 10 ** decimals
    return int(value * multiplier) / multiplier


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero

    Returns:
        Result of division or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def timestamp_to_datetime(timestamp: int) -> datetime:
    """
    Convert millisecond timestamp to datetime.

    Args:
        timestamp: Timestamp in milliseconds

    Returns:
        datetime object
    """
    return datetime.fromtimestamp(timestamp / 1000)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to millisecond timestamp.

    Args:
        dt: datetime object

    Returns:
        Timestamp in milliseconds
    """
    return int(dt.timestamp() * 1000)


class RateLimiter:
    """Simple rate limiter to prevent API abuse"""

    def __init__(self, max_calls: int, period: float):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []

    def __call__(self, func: Callable) -> Callable:
        """
        Decorator to apply rate limiting.

        Args:
            func: Function to rate limit

        Returns:
            Decorated function
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()

            # Remove old calls outside the period
            self.calls = [call for call in self.calls if now - call < self.period]

            # Check if we've hit the limit
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.calls = []

            # Record this call
            self.calls.append(time.time())

            return func(*args, **kwargs)

        return wrapper

    def wait_if_needed(self):
        """Wait if rate limit is reached"""
        now = time.time()
        self.calls = [call for call in self.calls if now - call < self.period]

        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
            self.calls = []

        self.calls.append(time.time())
