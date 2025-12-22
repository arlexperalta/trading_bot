"""
Logging system for the crypto trading bot.
Provides colored console output and rotating file handlers.
"""

import logging
import colorlog
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from datetime import datetime


class TradingLogger:
    """Custom logger with file rotation and colored console output"""

    def __init__(self, name: str, logs_dir: Path):
        """
        Initialize the trading logger.

        Args:
            name: Logger name (usually module name)
            logs_dir: Directory to store log files
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logs_dir = logs_dir

        # Ensure logs directory exists
        self.logs_dir.mkdir(exist_ok=True)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Setup handlers
        self._setup_console_handler()
        self._setup_file_handlers()

    def _setup_console_handler(self):
        """Setup colored console handler"""
        console_handler = colorlog.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Colored formatter for console
        console_formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def _setup_file_handlers(self):
        """Setup rotating file handlers for different log levels"""
        # General trading log (INFO and above)
        trading_handler = RotatingFileHandler(
            self.logs_dir / 'trading.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        trading_handler.setLevel(logging.INFO)
        trading_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        trading_handler.setFormatter(trading_formatter)
        self.logger.addHandler(trading_handler)

        # Error log (ERROR and above)
        error_handler = RotatingFileHandler(
            self.logs_dir / 'errors.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(trading_formatter)
        self.logger.addHandler(error_handler)

        # Debug log (all levels)
        debug_handler = RotatingFileHandler(
            self.logs_dir / 'debug.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(trading_formatter)
        self.logger.addHandler(debug_handler)

    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)

    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)

    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        """Log error message"""
        self.logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False):
        """Log critical message"""
        self.logger.critical(message, exc_info=exc_info)

    def log_trade(
        self,
        side: str,
        symbol: str,
        price: float,
        quantity: float,
        profit: Optional[float] = None,
        trade_type: str = 'OPEN'
    ):
        """
        Log trade execution details.

        Args:
            side: BUY or SELL
            symbol: Trading pair symbol
            price: Execution price
            quantity: Order quantity
            profit: Profit/loss if closing position
            trade_type: OPEN or CLOSE
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if trade_type == 'OPEN':
            message = (
                f"[TRADE OPEN] {side} {quantity} {symbol} @ ${price:.2f} "
                f"| Total: ${price * quantity:.2f}"
            )
        else:
            profit_str = f"+${profit:.2f}" if profit and profit > 0 else f"-${abs(profit):.2f}" if profit else "$0.00"
            message = (
                f"[TRADE CLOSE] {side} {quantity} {symbol} @ ${price:.2f} "
                f"| Total: ${price * quantity:.2f} | P/L: {profit_str}"
            )

        self.info(message)

        # Also write to a separate trades log
        trades_log = self.logs_dir / 'trades.log'
        with open(trades_log, 'a') as f:
            f.write(f"{timestamp} - {message}\n")

    def log_balance(self, balance: float, available: float):
        """
        Log account balance.

        Args:
            balance: Total balance
            available: Available balance
        """
        message = f"[BALANCE] Total: ${balance:.2f} | Available: ${available:.2f}"
        self.info(message)

    def log_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        current_price: float,
        unrealized_pnl: float
    ):
        """
        Log current position details.

        Args:
            symbol: Trading pair symbol
            side: LONG or SHORT
            quantity: Position size
            entry_price: Entry price
            current_price: Current market price
            unrealized_pnl: Unrealized profit/loss
        """
        pnl_str = f"+${unrealized_pnl:.2f}" if unrealized_pnl > 0 else f"-${abs(unrealized_pnl):.2f}"
        pnl_percent = ((current_price - entry_price) / entry_price * 100)

        message = (
            f"[POSITION] {side} {quantity} {symbol} | "
            f"Entry: ${entry_price:.2f} | Current: ${current_price:.2f} | "
            f"P/L: {pnl_str} ({pnl_percent:+.2f}%)"
        )
        self.info(message)

    def log_signal(self, signal: str, symbol: str, details: str = ""):
        """
        Log trading signal.

        Args:
            signal: Signal type (BUY, SELL, HOLD)
            symbol: Trading pair symbol
            details: Additional signal details
        """
        message = f"[SIGNAL] {signal} {symbol}"
        if details:
            message += f" | {details}"
        self.info(message)


def get_logger(name: str, logs_dir: Optional[Path] = None) -> TradingLogger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name
        logs_dir: Directory for log files (defaults to ./logs)

    Returns:
        TradingLogger instance
    """
    if logs_dir is None:
        logs_dir = Path(__file__).parent.parent.parent / 'logs'

    return TradingLogger(name, logs_dir)
