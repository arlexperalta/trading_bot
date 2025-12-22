"""
EMA Crossover trading strategy.
Conservative strategy using EMA 9/21 crossover with volume confirmation.
"""

import pandas as pd
from typing import Optional, Dict, Any

from config.settings import Settings
from src.strategies.base_strategy import BaseStrategy


class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover Strategy with volume confirmation.

    Entry Rules:
    - LONG: EMA(9) crosses above EMA(21) + volume > average volume
    - SHORT: EMA(9) crosses below EMA(21) + volume > average volume

    Exit Rules:
    - Stop Loss: 2% from entry
    - Take Profit: 6% from entry (1:3 risk-reward ratio)

    Additional Rules:
    - Only one position at a time
    - Uses 4-hour timeframe for reduced noise
    - Conservative position sizing with max 2x leverage
    """

    def __init__(self):
        """Initialize EMA Crossover strategy"""
        super().__init__("EMA_Crossover")

        self.ema_fast_period = Settings.EMA_FAST_PERIOD
        self.ema_slow_period = Settings.EMA_SLOW_PERIOD
        self.volume_period = Settings.VOLUME_PERIOD

        self.logger.info(
            f"Initialized {self.name} strategy "
            f"(EMA {self.ema_fast_period}/{self.ema_slow_period}, "
            f"Volume period: {self.volume_period})"
        )

    def should_enter(self, df: pd.DataFrame, current_price: float) -> Optional[str]:
        """
        Determine if strategy should enter a position.

        Args:
            df: DataFrame with market data and indicators
            current_price: Current market price

        Returns:
            'LONG' for bullish signal, 'SHORT' for bearish signal, None otherwise
        """
        # Validate data
        if not self.validate_signal(df):
            return None

        # Already in a position
        if self.has_position():
            return None

        # Need at least 2 candles to detect crossover
        if len(df) < 2:
            return None

        # Get current and previous candles
        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Check for required indicators
        required_cols = ['ema_fast', 'ema_slow', 'volume', 'volume_avg']
        if not all(col in df.columns for col in required_cols):
            self.logger.warning("Missing required indicators")
            return None

        # Check for NaN values
        if pd.isna([current['ema_fast'], current['ema_slow'],
                   current['volume'], current['volume_avg']]).any():
            return None

        # Volume confirmation: current volume > average volume
        volume_confirmed = current['volume'] > current['volume_avg']

        if not volume_confirmed:
            self.logger.debug("Volume confirmation failed")
            return None

        # Bullish crossover: EMA fast crosses above EMA slow
        bullish_cross = (
            previous['ema_fast'] <= previous['ema_slow'] and
            current['ema_fast'] > current['ema_slow']
        )

        if bullish_cross:
            self.log_signal(
                "LONG SIGNAL",
                f"EMA({self.ema_fast_period}) crossed above EMA({self.ema_slow_period}) "
                f"with volume confirmation"
            )
            return 'LONG'

        # Bearish crossover: EMA fast crosses below EMA slow
        bearish_cross = (
            previous['ema_fast'] >= previous['ema_slow'] and
            current['ema_fast'] < current['ema_slow']
        )

        if bearish_cross:
            self.log_signal(
                "SHORT SIGNAL",
                f"EMA({self.ema_fast_period}) crossed below EMA({self.ema_slow_period}) "
                f"with volume confirmation"
            )
            return 'SHORT'

        return None

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
        if not self.has_position():
            return False

        # Validate data
        if not self.validate_signal(df):
            return False

        entry_price = position.get('entry_price')
        side = position.get('side')
        stop_loss = position.get('stop_loss')
        take_profit = position.get('take_profit')

        if not all([entry_price, side, stop_loss, take_profit]):
            self.logger.warning("Incomplete position information")
            return False

        # Check stop loss
        if side == 'LONG' and current_price <= stop_loss:
            self.log_signal("EXIT SIGNAL", f"Stop loss hit at ${current_price:.2f}")
            return True

        if side == 'SHORT' and current_price >= stop_loss:
            self.log_signal("EXIT SIGNAL", f"Stop loss hit at ${current_price:.2f}")
            return True

        # Check take profit
        if side == 'LONG' and current_price >= take_profit:
            self.log_signal("EXIT SIGNAL", f"Take profit hit at ${current_price:.2f}")
            return True

        if side == 'SHORT' and current_price <= take_profit:
            self.log_signal("EXIT SIGNAL", f"Take profit hit at ${current_price:.2f}")
            return True

        # Check for opposite crossover (optional early exit)
        if len(df) >= 2:
            current = df.iloc[-1]
            previous = df.iloc[-2]

            # Exit long on bearish crossover
            if side == 'LONG':
                bearish_cross = (
                    previous['ema_fast'] >= previous['ema_slow'] and
                    current['ema_fast'] < current['ema_slow']
                )
                if bearish_cross:
                    self.log_signal("EXIT SIGNAL", "Opposite EMA crossover detected")
                    return True

            # Exit short on bullish crossover
            if side == 'SHORT':
                bullish_cross = (
                    previous['ema_fast'] <= previous['ema_slow'] and
                    current['ema_fast'] > current['ema_slow']
                )
                if bullish_cross:
                    self.log_signal("EXIT SIGNAL", "Opposite EMA crossover detected")
                    return True

        return False

    def get_stop_loss(self, entry_price: float, side: str) -> float:
        """
        Calculate stop loss price (2% from entry).

        Args:
            entry_price: Entry price of position
            side: 'LONG' or 'SHORT'

        Returns:
            Stop loss price
        """
        stop_distance = entry_price * Settings.STOP_LOSS_PERCENT

        if side == 'LONG':
            stop_loss = entry_price - stop_distance
        else:  # SHORT
            stop_loss = entry_price + stop_distance

        self.logger.debug(
            f"Stop loss for {side} at ${entry_price:.2f}: ${stop_loss:.2f} "
            f"({Settings.STOP_LOSS_PERCENT * 100:.1f}%)"
        )

        return stop_loss

    def get_take_profit(self, entry_price: float, side: str) -> float:
        """
        Calculate take profit price (6% from entry for 1:3 R/R).

        Args:
            entry_price: Entry price of position
            side: 'LONG' or 'SHORT'

        Returns:
            Take profit price
        """
        profit_distance = entry_price * Settings.TAKE_PROFIT_PERCENT

        if side == 'LONG':
            take_profit = entry_price + profit_distance
        else:  # SHORT
            take_profit = entry_price - profit_distance

        self.logger.debug(
            f"Take profit for {side} at ${entry_price:.2f}: ${take_profit:.2f} "
            f"({Settings.TAKE_PROFIT_PERCENT * 100:.1f}%)"
        )

        return take_profit

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get strategy configuration information.

        Returns:
            Dictionary with strategy settings
        """
        return {
            'name': self.name,
            'ema_fast': self.ema_fast_period,
            'ema_slow': self.ema_slow_period,
            'volume_period': self.volume_period,
            'stop_loss_percent': Settings.STOP_LOSS_PERCENT,
            'take_profit_percent': Settings.TAKE_PROFIT_PERCENT,
            'timeframe': Settings.TIMEFRAME,
            'max_positions': Settings.MAX_OPEN_POSITIONS
        }
