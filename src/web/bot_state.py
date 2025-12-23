"""
Global bot state management for the dashboard.
Thread-safe state sharing between trading bot and web server.
"""

from datetime import datetime
from threading import Lock
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class BotState:
    """Singleton class to manage bot state across threads."""

    # Bot status
    is_running: bool = False
    started_at: Optional[datetime] = None
    last_update: Optional[datetime] = None

    # Trading configuration
    trading_mode: str = "TESTNET"
    trading_pair: str = "BTCUSDT"
    timeframe: str = "4h"
    leverage: int = 2

    # Account info
    balance_total: float = 0.0
    balance_available: float = 0.0
    initial_capital: float = 100.0

    # Current position
    has_position: bool = False
    position_side: Optional[str] = None
    position_entry_price: float = 0.0
    position_quantity: float = 0.0
    position_unrealized_pnl: float = 0.0
    position_stop_loss: float = 0.0
    position_take_profit: float = 0.0

    # Market data
    current_price: float = 0.0
    price_change_24h: float = 0.0

    # Strategy indicators
    ema_fast: float = 0.0
    ema_slow: float = 0.0
    rsi: float = 0.0

    # Daily stats
    daily_trades: int = 0
    daily_wins: int = 0
    daily_losses: int = 0
    daily_pnl: float = 0.0
    daily_win_rate: float = 0.0

    # Trade history (last 50)
    trade_history: List[Dict[str, Any]] = field(default_factory=list)

    # Errors and logs
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    recent_logs: List[Dict[str, Any]] = field(default_factory=list)

    # Iteration counter
    iteration: int = 0


class BotStateManager:
    """Thread-safe bot state manager."""

    _instance: Optional['BotStateManager'] = None
    _lock: Lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._state = BotState()
                    cls._instance._state_lock = Lock()
        return cls._instance

    def update(self, **kwargs) -> None:
        """Update state with new values."""
        with self._state_lock:
            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)
            self._state.last_update = datetime.now()

    def get_state(self) -> Dict[str, Any]:
        """Get current state as dictionary."""
        with self._state_lock:
            return {
                "is_running": self._state.is_running,
                "started_at": self._state.started_at.isoformat() if self._state.started_at else None,
                "last_update": self._state.last_update.isoformat() if self._state.last_update else None,
                "trading_mode": self._state.trading_mode,
                "trading_pair": self._state.trading_pair,
                "timeframe": self._state.timeframe,
                "leverage": self._state.leverage,
                "balance_total": self._state.balance_total,
                "balance_available": self._state.balance_available,
                "initial_capital": self._state.initial_capital,
                "has_position": self._state.has_position,
                "position_side": self._state.position_side,
                "position_entry_price": self._state.position_entry_price,
                "position_quantity": self._state.position_quantity,
                "position_unrealized_pnl": self._state.position_unrealized_pnl,
                "position_stop_loss": self._state.position_stop_loss,
                "position_take_profit": self._state.position_take_profit,
                "current_price": self._state.current_price,
                "price_change_24h": self._state.price_change_24h,
                "ema_fast": self._state.ema_fast,
                "ema_slow": self._state.ema_slow,
                "rsi": self._state.rsi,
                "daily_trades": self._state.daily_trades,
                "daily_wins": self._state.daily_wins,
                "daily_losses": self._state.daily_losses,
                "daily_pnl": self._state.daily_pnl,
                "daily_win_rate": self._state.daily_win_rate,
                "trade_history": self._state.trade_history[-50:],
                "last_error": self._state.last_error,
                "last_error_time": self._state.last_error_time.isoformat() if self._state.last_error_time else None,
                "recent_logs": self._state.recent_logs[-100:],
                "iteration": self._state.iteration,
            }

    def add_trade(self, trade: Dict[str, Any]) -> None:
        """Add a trade to history."""
        with self._state_lock:
            trade["timestamp"] = datetime.now().isoformat()
            self._state.trade_history.append(trade)
            # Keep only last 50 trades
            if len(self._state.trade_history) > 50:
                self._state.trade_history = self._state.trade_history[-50:]

    def add_log(self, level: str, message: str) -> None:
        """Add a log entry."""
        with self._state_lock:
            self._state.recent_logs.append({
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "message": message
            })
            # Keep only last 100 logs
            if len(self._state.recent_logs) > 100:
                self._state.recent_logs = self._state.recent_logs[-100:]

    def set_error(self, error: str) -> None:
        """Set last error."""
        with self._state_lock:
            self._state.last_error = error
            self._state.last_error_time = datetime.now()

    def clear_error(self) -> None:
        """Clear last error."""
        with self._state_lock:
            self._state.last_error = None
            self._state.last_error_time = None

    def start_bot(self) -> None:
        """Mark bot as started."""
        with self._state_lock:
            self._state.is_running = True
            self._state.started_at = datetime.now()
            self._state.iteration = 0

    def stop_bot(self) -> None:
        """Mark bot as stopped."""
        with self._state_lock:
            self._state.is_running = False


# Global instance
bot_state = BotStateManager()
