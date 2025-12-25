"""
Position and risk management for the trading bot.
Handles position sizing, leverage validation, and risk limits.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta

from config.settings import Settings
from src.utils.logger import get_logger
from src.utils.helpers import truncate_float


class PositionManager:
    """
    Manages position sizing and risk parameters.
    Ensures conservative trading with proper risk management.
    """

    def __init__(self):
        """Initialize position manager"""
        self.logger = get_logger(__name__, Settings.LOGS_DIR)
        self.daily_trades = []
        self.daily_pnl = 0.0
        self.last_reset = datetime.now().date()

    def _reset_daily_counters(self):
        """Reset daily counters if it's a new day"""
        current_date = datetime.now().date()
        if current_date > self.last_reset:
            self.logger.info(f"Resetting daily counters. Previous P/L: {self.daily_pnl:.2f}")
            self.daily_trades = []
            self.daily_pnl = 0.0
            self.last_reset = current_date

    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        leverage: int = 1
    ) -> float:
        """
        Calculate position size using Fixed Fractional position sizing.

        Args:
            capital: Available trading capital
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price
            leverage: Leverage to use (default 1x)

        Returns:
            Position size in base currency

        Formula:
            Position Size = (Capital * Risk%) / (Entry Price - Stop Loss Price)
            Limited by: Max Notional Value = Capital * Leverage
        """
        self._reset_daily_counters()

        # Validate inputs
        if capital <= 0:
            self.logger.error("Capital must be greater than 0")
            return 0.0

        if entry_price <= 0 or stop_loss_price <= 0:
            self.logger.error("Prices must be greater than 0")
            return 0.0

        if leverage < 1 or leverage > Settings.MAX_LEVERAGE:
            self.logger.error(f"Leverage must be between 1 and {Settings.MAX_LEVERAGE}")
            return 0.0

        # Calculate risk amount
        risk_amount = capital * Settings.RISK_PER_TRADE

        # Calculate price difference (risk per unit)
        price_diff = abs(entry_price - stop_loss_price)

        if price_diff == 0:
            self.logger.error("Stop loss price must be different from entry price")
            return 0.0

        # Calculate base position size based on risk
        position_size_by_risk = risk_amount / price_diff

        # Calculate maximum position size based on position limit (5% of capital)
        # This ensures we don't use too much capital per position
        max_position_percent = getattr(Settings, 'MAX_POSITION_PERCENT', 0.05)
        max_notional = capital * max_position_percent * leverage
        max_position_size = max_notional / entry_price

        # Use the smaller of risk-based or position-limit-based size
        position_size = min(position_size_by_risk, max_position_size)

        # Truncate to reasonable precision (3 decimals for BTC)
        position_size_final = truncate_float(position_size, 3)

        # Ensure minimum position size
        if position_size_final < 0.001:
            self.logger.warning(f"Position size too small: {position_size_final}, using minimum 0.001")
            position_size_final = 0.001

        self.logger.info(
            f"Position size calculated: {position_size_final} "
            f"(Capital: ${capital:.2f}, Max {max_position_percent*100:.0f}% = ${max_notional:.2f}, "
            f"Leverage: {leverage}x)"
        )

        return position_size_final

    def validate_leverage(self, leverage: int) -> bool:
        """
        Validate that leverage is within acceptable limits.

        Args:
            leverage: Leverage value to validate

        Returns:
            True if leverage is valid
        """
        if leverage < 1:
            self.logger.error("Leverage cannot be less than 1")
            return False

        if leverage > Settings.MAX_LEVERAGE:
            self.logger.error(
                f"Leverage {leverage}x exceeds maximum allowed {Settings.MAX_LEVERAGE}x"
            )
            return False

        return True

    def calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        atr: Optional[float] = None,
        use_fixed_percent: bool = True
    ) -> float:
        """
        Calculate stop loss price.

        Args:
            entry_price: Entry price
            side: 'LONG' or 'SHORT'
            atr: Average True Range (optional, for ATR-based stops)
            use_fixed_percent: Use fixed percentage instead of ATR

        Returns:
            Stop loss price
        """
        if use_fixed_percent:
            # Use fixed percentage stop loss
            stop_distance = entry_price * Settings.STOP_LOSS_PERCENT

            if side == 'LONG':
                stop_loss = entry_price - stop_distance
            else:  # SHORT
                stop_loss = entry_price + stop_distance

        else:
            # Use ATR-based stop loss
            if atr is None or atr <= 0:
                self.logger.warning("Invalid ATR, falling back to fixed percentage")
                return self.calculate_stop_loss(entry_price, side, use_fixed_percent=True)

            # Stop loss at 2 * ATR
            stop_distance = atr * 2

            if side == 'LONG':
                stop_loss = entry_price - stop_distance
            else:  # SHORT
                stop_loss = entry_price + stop_distance

        stop_loss = truncate_float(stop_loss, 2)

        self.logger.debug(
            f"Stop loss calculated: ${stop_loss:.2f} for {side} at ${entry_price:.2f}"
        )

        return stop_loss

    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """
        Calculate take profit price based on risk-reward ratio.

        Args:
            entry_price: Entry price
            side: 'LONG' or 'SHORT'

        Returns:
            Take profit price
        """
        profit_distance = entry_price * Settings.TAKE_PROFIT_PERCENT

        if side == 'LONG':
            take_profit = entry_price + profit_distance
        else:  # SHORT
            take_profit = entry_price - profit_distance

        take_profit = truncate_float(take_profit, 2)

        self.logger.debug(
            f"Take profit calculated: ${take_profit:.2f} for {side} at ${entry_price:.2f}"
        )

        return take_profit

    def check_daily_loss_limit(self) -> bool:
        """
        Check if daily loss limit has been reached.

        Returns:
            True if trading is allowed, False if limit reached
        """
        self._reset_daily_counters()

        max_daily_loss = Settings.INITIAL_CAPITAL * Settings.MAX_DAILY_LOSS_PERCENT

        if self.daily_pnl <= -max_daily_loss:
            self.logger.warning(
                f"Daily loss limit reached: ${self.daily_pnl:.2f} / "
                f"-${max_daily_loss:.2f}. Trading halted for today."
            )
            return False

        return True

    def record_trade(self, pnl: float):
        """
        Record a completed trade.

        Args:
            pnl: Profit or loss from the trade
        """
        self._reset_daily_counters()

        self.daily_trades.append({
            'timestamp': datetime.now(),
            'pnl': pnl
        })
        self.daily_pnl += pnl

        self.logger.info(
            f"Trade recorded. P/L: ${pnl:.2f} | "
            f"Daily P/L: ${self.daily_pnl:.2f} | "
            f"Daily trades: {len(self.daily_trades)}"
        )

    def get_daily_stats(self) -> Dict[str, float]:
        """
        Get daily trading statistics.

        Returns:
            Dictionary with daily stats
        """
        self._reset_daily_counters()

        winning_trades = [t for t in self.daily_trades if t['pnl'] > 0]
        losing_trades = [t for t in self.daily_trades if t['pnl'] < 0]

        total_trades = len(self.daily_trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0

        return {
            'daily_pnl': self.daily_pnl,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }

    def can_open_position(self, current_positions: int) -> bool:
        """
        Check if a new position can be opened.

        Args:
            current_positions: Number of currently open positions

        Returns:
            True if new position can be opened
        """
        if current_positions >= Settings.MAX_OPEN_POSITIONS:
            self.logger.warning(
                f"Maximum positions ({Settings.MAX_OPEN_POSITIONS}) already open"
            )
            return False

        if not self.check_daily_loss_limit():
            return False

        return True

    def calculate_risk_reward_ratio(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: float
    ) -> float:
        """
        Calculate risk-reward ratio for a trade.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Risk-reward ratio
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        if risk == 0:
            return 0.0

        ratio = reward / risk

        self.logger.debug(f"Risk-reward ratio: 1:{ratio:.2f}")

        return ratio
