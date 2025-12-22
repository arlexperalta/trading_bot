"""
Base strategy class for trading strategies.
Provides abstract interface that all strategies must implement.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, Any

from config.settings import Settings
from src.utils.logger import get_logger


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    All trading strategies must inherit from this class.
    """

    def __init__(self, name: str):
        """
        Initialize base strategy.

        Args:
            name: Strategy name
        """
        self.name = name
        self.logger = get_logger(f"Strategy.{name}", Settings.LOGS_DIR)
        self.position = None  # Current position info

    @abstractmethod
    def should_enter(self, df: pd.DataFrame, current_price: float) -> Optional[str]:
        """
        Determine if strategy should enter a position.

        Args:
            df: DataFrame with market data and indicators
            current_price: Current market price

        Returns:
            'LONG' for long position, 'SHORT' for short position, None for no entry
        """
        pass

    @abstractmethod
    def should_exit(
        self,
        df: pd.DataFrame,
        current_price: float,
        position: Dict[str, Any]
    ) -> bool:
        """
        Determine if strategy should exit current position.

        Args:
            df: DataFrame with market data and indicators
            current_price: Current market price
            position: Current position information

        Returns:
            True if should exit, False otherwise
        """
        pass

    @abstractmethod
    def get_stop_loss(self, entry_price: float, side: str) -> float:
        """
        Calculate stop loss price for a position.

        Args:
            entry_price: Entry price of position
            side: 'LONG' or 'SHORT'

        Returns:
            Stop loss price
        """
        pass

    @abstractmethod
    def get_take_profit(self, entry_price: float, side: str) -> float:
        """
        Calculate take profit price for a position.

        Args:
            entry_price: Entry price of position
            side: 'LONG' or 'SHORT'

        Returns:
            Take profit price
        """
        pass

    def log_signal(self, signal: str, details: str = ""):
        """
        Log trading signal.

        Args:
            signal: Signal description
            details: Additional details
        """
        self.logger.info(f"[{self.name}] {signal} {details}")

    def validate_signal(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame has enough data for signal generation.

        Args:
            df: DataFrame with market data

        Returns:
            True if valid, False otherwise
        """
        if df is None or len(df) < 2:
            self.logger.warning("Insufficient data for signal generation")
            return False

        # Check for NaN values in critical columns
        if df[['close', 'volume']].isnull().any().any():
            self.logger.warning("DataFrame contains NaN values")
            return False

        return True

    def set_position(self, position: Optional[Dict[str, Any]]):
        """
        Set current position information.

        Args:
            position: Position dictionary or None
        """
        self.position = position

    def has_position(self) -> bool:
        """
        Check if strategy currently has an open position.

        Returns:
            True if position is open
        """
        return self.position is not None

    def get_position_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current position information.

        Returns:
            Position dictionary or None
        """
        return self.position
