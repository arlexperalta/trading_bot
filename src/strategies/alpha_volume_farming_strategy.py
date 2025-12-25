"""
Binance Alpha Volume Farming Strategy.

Optimized for generating MAXIMUM TRADING VOLUME with MINIMUM RISK.
Perfect for Binance Alpha Events, airdrops, and volume-based rewards.

Strategy Goals:
- Generate $50,000-200,000 monthly volume
- Maintain near-zero P/L (win/loss ratio ~1:1)
- Execute 100-500 trades per day
- Keep fees under 0.5% of volume

Entry Rules:
- Ultra-tight entry: ANY small EMA divergence
- Minimal volume confirmation (50% of average)
- Enter on minor price movements (0.05%+)
- No directional bias (equal longs and shorts)

Exit Rules:
- Ultra-tight stop loss: 0.1-0.2%
- Ultra-tight take profit: 0.15-0.3%
- Auto-exit after 1-5 minutes regardless of P/L
- Force-close positions before funding time

Risk Management:
- Low leverage (1-2x maximum)
- Small position sizes (0.5-1% capital per trade)
- Maximum 5 simultaneous positions
- Daily volume target tracking
"""

import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from config.settings import Settings
from src.strategies.base_strategy import BaseStrategy


class AlphaVolumeFarmingStrategy(BaseStrategy):
    """
    Volume Farming Strategy for Binance Alpha Events.
    
    Generates high trading volume with minimal P/L exposure.
    """

    def __init__(self):
        """Initialize Alpha Volume Farming strategy"""
        super().__init__("Alpha_Volume_Farming")

        # Ultra-aggressive scalping settings
        self.ema_fast_period = 3  # Extremely fast EMA
        self.ema_slow_period = 8  # Short slow EMA
        self.volume_confirmation_threshold = 0.2  # Only 20% volume needed (very aggressive)
        
        # Volume farming specific settings
        self.daily_volume_target = 50000  # $50k daily target
        self.current_daily_volume = 0
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0)
        
        # Trade timing
        self.max_trade_duration_minutes = 5  # Force close after 5 minutes
        self.position_entry_times = {}  # Track when positions opened
        
        # Ultra-tight risk parameters
        self.stop_loss_percent = 0.0015  # 0.15% stop loss
        self.take_profit_percent = 0.0025  # 0.25% take profit
        self.max_leverage = 2  # Low leverage for safety
        
        self.logger.info(
            f"Initialized {self.name} strategy for VOLUME GENERATION"
        )
        self.logger.info(f"Daily volume target: ${self.daily_volume_target:,.0f}")
        self.logger.info(f"Expected trades/day: 100-500")

    def reset_daily_stats(self):
        """Reset daily volume tracking"""
        current_time = datetime.now()
        if current_time.date() > self.daily_reset_time.date():
            self.logger.info(
                f"Daily reset - Volume generated: ${self.current_daily_volume:,.2f}"
            )
            self.current_daily_volume = 0
            self.daily_reset_time = current_time.replace(hour=0, minute=0, second=0)

    def update_volume(self, trade_volume: float):
        """Update daily volume counter"""
        self.reset_daily_stats()
        self.current_daily_volume += trade_volume
        
        progress = (self.current_daily_volume / self.daily_volume_target) * 100
        self.logger.info(
            f"Daily volume: ${self.current_daily_volume:,.2f} / "
            f"${self.daily_volume_target:,.2f} ({progress:.1f}%)"
        )

    def get_volume_progress(self) -> Dict[str, float]:
        """Get current volume progress"""
        self.reset_daily_stats()
        return {
            'current_volume': self.current_daily_volume,
            'target_volume': self.daily_volume_target,
            'progress_percent': (self.current_daily_volume / self.daily_volume_target) * 100,
            'remaining': self.daily_volume_target - self.current_daily_volume
        }

    def should_enter(self, df: pd.DataFrame, current_price: float) -> Optional[str]:
        """
        Determine if strategy should enter a position.
        
        VERY LOOSE entry criteria to maximize trade frequency.
        
        Args:
            df: DataFrame with market data and indicators
            current_price: Current market price

        Returns:
            'LONG' or 'SHORT' signal, or None
        """
        # Check if we've hit daily volume target
        progress = self.get_volume_progress()
        if progress['current_volume'] >= self.daily_volume_target:
            self.logger.info("Daily volume target achieved! No more entries today.")
            return None

        # Validate data
        if not self.validate_signal(df):
            return None

        if len(df) < 3:
            return None

        # Get current and previous data
        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Check for required indicators
        required_cols = ['ema_fast', 'ema_slow', 'volume', 'volume_avg']
        if not all(col in df.columns for col in required_cols):
            return None

        if pd.isna([current['ema_fast'], current['ema_slow'],
                   current['volume'], current['volume_avg']]).any():
            return None

        # LOOSE volume confirmation (only 50% of average needed)
        volume_confirmed = current['volume'] > (current['volume_avg'] * 
                                               self.volume_confirmation_threshold)

        # Calculate EMA spread
        ema_spread = abs(current['ema_fast'] - current['ema_slow']) / current['ema_slow'] * 100

        # Price movement percentage
        price_change = abs(current['close'] - previous['close']) / previous['close'] * 100

        # VERY LOOSE entry conditions
        
        # Entry 1: Any upward EMA movement
        bullish_signal = (
            current['ema_fast'] > previous['ema_fast'] and
            current['ema_fast'] > current['ema_slow']
        )

        # Entry 2: Any downward EMA movement  
        bearish_signal = (
            current['ema_fast'] < previous['ema_fast'] and
            current['ema_fast'] < current['ema_slow']
        )

        # Entry 3: Minor price spike (for momentum entries)
        price_spike_up = price_change > 0.05  # 0.05% move
        price_spike_down = price_change > 0.05

        # Entry 4: EMA proximity (they're very close = expect movement)
        emas_close = ema_spread < 0.05  # Less than 0.05% apart

        # Generate signals with minimal criteria
        if (bullish_signal or (emas_close and current['close'] > previous['close'])) and volume_confirmed:
            self.log_signal(
                "LONG SIGNAL (VOLUME FARM)",
                f"EMA spread: {ema_spread:.4f}%, Volume factor: {current['volume']/current['volume_avg']:.2f}x"
            )
            return 'LONG'

        if (bearish_signal or (emas_close and current['close'] < previous['close'])) and volume_confirmed:
            self.log_signal(
                "SHORT SIGNAL (VOLUME FARM)",
                f"EMA spread: {ema_spread:.4f}%, Volume factor: {current['volume']/current['volume_avg']:.2f}x"
            )
            return 'SHORT'

        # Fallback: If no clear signal but market is moving, enter randomly
        # This maximizes volume generation
        if price_change > 0.03 and volume_confirmed:  # 0.03% movement
            # Alternate between LONG and SHORT to keep balanced
            import random
            signal = random.choice(['LONG', 'SHORT'])
            self.log_signal(
                f"{signal} SIGNAL (RANDOM VOLUME)",
                f"Price movement: {price_change:.3f}%"
            )
            return signal

        # Debug logging when no signal
        vol_ratio = current['volume'] / current['volume_avg'] if current['volume_avg'] > 0 else 0
        self.logger.info(
            f"No signal - Vol: {vol_ratio:.2f}x (need >0.5), "
            f"Bullish: {bullish_signal}, Bearish: {bearish_signal}, "
            f"PriceChg: {price_change:.3f}%, EMAs close: {emas_close}"
        )

        return None

    def should_exit(
        self,
        df: pd.DataFrame,
        current_price: float,
        position: Dict[str, Any]
    ) -> bool:
        """
        Determine if strategy should exit current position.
        
        AGGRESSIVE exits to close positions quickly and generate volume.
        
        Args:
            df: DataFrame with market data
            current_price: Current market price
            position: Current position information

        Returns:
            True if should exit
        """
        if not self.has_position():
            return False

        entry_price = position.get('entry_price')
        side = position.get('side')
        entry_time = position.get('entry_time')

        if not all([entry_price, side, entry_time]):
            return False

        # Force exit after max duration (volume farming priority)
        time_in_position = (datetime.now() - entry_time).total_seconds() / 60
        if time_in_position >= self.max_trade_duration_minutes:
            self.log_signal(
                "EXIT SIGNAL (TIME LIMIT)",
                f"Position held for {time_in_position:.1f} minutes"
            )
            return True

        # Check stop loss and take profit
        pnl_percent = self.calculate_pnl_percent(entry_price, current_price, side)

        if pnl_percent <= -self.stop_loss_percent * 100:
            self.log_signal(
                "EXIT SIGNAL (STOP LOSS)",
                f"P/L: {pnl_percent:.2f}%"
            )
            return True

        if pnl_percent >= self.take_profit_percent * 100:
            self.log_signal(
                "EXIT SIGNAL (TAKE PROFIT)",
                f"P/L: {pnl_percent:.2f}%"
            )
            return True

        # Quick exit on any opposite signal (maximize volume)
        if len(df) >= 2:
            current = df.iloc[-1]
            previous = df.iloc[-2]

            if side == 'LONG':
                # Exit long on any downward movement
                if current['close'] < previous['close']:
                    self.log_signal("EXIT SIGNAL (QUICK EXIT)", "Price moving down")
                    return True

            if side == 'SHORT':
                # Exit short on any upward movement
                if current['close'] > previous['close']:
                    self.log_signal("EXIT SIGNAL (QUICK EXIT)", "Price moving up")
                    return True

        return False

    def calculate_pnl_percent(self, entry_price: float, current_price: float, side: str) -> float:
        """Calculate P/L percentage"""
        if side == 'LONG':
            return ((current_price - entry_price) / entry_price) * 100
        else:  # SHORT
            return ((entry_price - current_price) / entry_price) * 100

    def get_stop_loss(self, entry_price: float, side: str) -> float:
        """Ultra-tight stop loss for volume farming"""
        stop_distance = entry_price * self.stop_loss_percent

        if side == 'LONG':
            stop_loss = entry_price - stop_distance
        else:  # SHORT
            stop_loss = entry_price + stop_distance

        return stop_loss

    def get_take_profit(self, entry_price: float, side: str) -> float:
        """Ultra-tight take profit for volume farming"""
        profit_distance = entry_price * self.take_profit_percent

        if side == 'LONG':
            take_profit = entry_price + profit_distance
        else:  # SHORT
            take_profit = entry_price - profit_distance

        return take_profit

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy configuration and stats"""
        progress = self.get_volume_progress()
        
        return {
            'name': self.name,
            'purpose': 'Volume farming for Binance Alpha Events',
            'ema_fast': self.ema_fast_period,
            'ema_slow': self.ema_slow_period,
            'stop_loss_percent': self.stop_loss_percent * 100,
            'take_profit_percent': self.take_profit_percent * 100,
            'max_leverage': self.max_leverage,
            'max_trade_duration_min': self.max_trade_duration_minutes,
            'daily_volume_target': self.daily_volume_target,
            'current_daily_volume': progress['current_volume'],
            'volume_progress_percent': progress['progress_percent'],
            'expected_trades_per_day': '100-500',
            'expected_daily_fees': '$50-200',
            'expected_airdrop_value': '$200-1000'
        }
