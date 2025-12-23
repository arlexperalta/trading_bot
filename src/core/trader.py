"""
Main trading logic coordinator.
Orchestrates strategy, risk management, and order execution.
"""

import time
from typing import Optional, Dict, Any

from config.settings import Settings
from src.core.exchange import BinanceConnector
from src.data.market_data import MarketData
from src.strategies.base_strategy import BaseStrategy
from src.risk.position_manager import PositionManager
from src.utils.logger import get_logger
from src.utils.telegram_notifier import notifier

# Import bot state for dashboard integration
try:
    from src.web.bot_state import bot_state
    DASHBOARD_ENABLED = True
except ImportError:
    DASHBOARD_ENABLED = False
    bot_state = None


class Trader:
    """
    Main trading engine.
    Coordinates market data, strategy signals, risk management, and order execution.
    """

    def __init__(self, strategy: BaseStrategy):
        """
        Initialize trader with a trading strategy.

        Args:
            strategy: Trading strategy instance
        """
        self.logger = get_logger(__name__, Settings.LOGS_DIR)
        self.strategy = strategy
        self.symbol = Settings.TRADING_PAIR

        # Initialize components
        self.logger.info("Initializing trading bot components...")
        self.exchange = BinanceConnector()
        self.market_data = MarketData(self.exchange)
        self.position_manager = PositionManager()

        # Set initial configuration
        self._setup_exchange()

        # Track current position
        self.current_position: Optional[Dict[str, Any]] = None

        self.logger.info(f"Trader initialized with {strategy.name} strategy")
        self.logger.info(f"Trading pair: {self.symbol}")
        self.logger.info(f"Timeframe: {Settings.TIMEFRAME}")
        self.logger.info(f"Max leverage: {Settings.MAX_LEVERAGE}x")

    def _setup_exchange(self):
        """Setup exchange configuration (leverage, margin type)"""
        try:
            # Set margin type to ISOLATED (safer than CROSS)
            self.exchange.set_margin_type(self.symbol, 'ISOLATED')

            # Set leverage
            self.exchange.set_leverage(self.symbol, Settings.MAX_LEVERAGE)

            self.logger.info("Exchange configuration completed")

        except Exception as e:
            self.logger.error(f"Failed to setup exchange: {e}", exc_info=True)
            raise

    def _update_dashboard_state(self, **kwargs):
        """Update dashboard state if enabled."""
        if DASHBOARD_ENABLED and bot_state:
            bot_state.update(**kwargs)

    def _add_dashboard_log(self, level: str, message: str):
        """Add log to dashboard if enabled."""
        if DASHBOARD_ENABLED and bot_state:
            bot_state.add_log(level, message)

    def run_trading_loop(self):
        """
        Main trading loop.
        Continuously monitors market and executes strategy.
        """
        self.logger.info("=" * 60)
        self.logger.info("TRADING BOT STARTED")
        self.logger.info("=" * 60)

        # Send Telegram notification
        notifier.notify_bot_start()

        iteration = 0

        try:
            while True:
                iteration += 1
                self.logger.info(f"\n--- Iteration {iteration} ---")
                self._add_dashboard_log("INFO", f"Starting iteration {iteration}")

                # Update iteration in dashboard
                self._update_dashboard_state(iteration=iteration)

                # Execute one trading cycle
                self._execute_trading_cycle()

                # Wait before next iteration
                self.logger.info(
                    f"Waiting {Settings.UPDATE_INTERVAL} seconds until next update..."
                )
                time.sleep(Settings.UPDATE_INTERVAL)

        except KeyboardInterrupt:
            self.logger.info("\nShutdown signal received. Closing gracefully...")
            self._shutdown("User requested")
        except Exception as e:
            self.logger.error(f"Critical error in trading loop: {e}", exc_info=True)
            notifier.notify_error("Critical Error", str(e))
            self._shutdown(f"Critical error: {str(e)}")
            raise

    def _execute_trading_cycle(self):
        """Execute one complete trading cycle"""
        try:
            # 1. Get current balance
            balance_info = self.exchange.get_balance()
            current_balance = balance_info['available']

            self.logger.log_balance(balance_info['total'], balance_info['available'])

            # Update dashboard with balance
            self._update_dashboard_state(
                balance_total=balance_info['total'],
                balance_available=balance_info['available']
            )

            # 2. Check if we can trade today (daily loss limit)
            if not self.position_manager.check_daily_loss_limit():
                self.logger.warning("Daily loss limit reached. No trading today.")

                # Notify via Telegram (only once)
                if not hasattr(self, '_daily_limit_notified'):
                    stats = self.position_manager.get_daily_stats()
                    notifier.notify_daily_loss_limit(
                        abs(stats['daily_pnl']),
                        Settings.MAX_DAILY_LOSS_PERCENT
                    )
                    self._daily_limit_notified = True

                return

            # 3. Get market data
            df = self.market_data.get_klines_dataframe(
                self.symbol,
                Settings.TIMEFRAME,
                limit=100
            )

            # 4. Add technical indicators
            df = self.market_data.add_all_indicators(df)

            # 5. Get current price
            current_price = self.exchange.get_ticker_price(self.symbol)
            self.logger.info(f"Current {self.symbol} price: ${current_price:.2f}")

            # Update dashboard with price and indicators
            self._update_dashboard_state(
                current_price=current_price,
                ema_fast=float(df['ema_fast'].iloc[-1]) if 'ema_fast' in df.columns else 0,
                ema_slow=float(df['ema_slow'].iloc[-1]) if 'ema_slow' in df.columns else 0,
                rsi=float(df['rsi'].iloc[-1]) if 'rsi' in df.columns else 0
            )

            # 6. Check for open positions
            open_positions = self.exchange.get_open_positions()
            has_open_position = any(
                pos['symbol'] == self.symbol and float(pos['positionAmt']) != 0
                for pos in open_positions
            )

            # Update current position tracking
            if has_open_position and not self.current_position:
                self._sync_position_from_exchange(open_positions)

            if not has_open_position and self.current_position:
                self.current_position = None
                self.strategy.set_position(None)

            # Update dashboard with position info
            if self.current_position:
                unrealized_pnl = self._calculate_unrealized_pnl(current_price)
                self._update_dashboard_state(
                    has_position=True,
                    position_side=self.current_position['side'],
                    position_entry_price=self.current_position['entry_price'],
                    position_quantity=self.current_position['quantity'],
                    position_unrealized_pnl=unrealized_pnl,
                    position_stop_loss=self.current_position.get('stop_loss', 0),
                    position_take_profit=self.current_position.get('take_profit', 0)
                )
            else:
                self._update_dashboard_state(
                    has_position=False,
                    position_side=None,
                    position_entry_price=0,
                    position_quantity=0,
                    position_unrealized_pnl=0,
                    position_stop_loss=0,
                    position_take_profit=0
                )

            # 7. Evaluate strategy
            if self.current_position:
                # Check if we should exit
                self._check_exit_conditions(df, current_price)
            else:
                # Check if we should enter
                self._check_entry_conditions(df, current_price, current_balance)

            # 8. Log daily stats
            stats = self.position_manager.get_daily_stats()
            if stats['total_trades'] > 0:
                self.logger.info(
                    f"Daily Stats: Trades: {stats['total_trades']}, "
                    f"Win Rate: {stats['win_rate']:.1f}%, "
                    f"P/L: ${stats['daily_pnl']:.2f}"
                )

            # Update dashboard with daily stats
            self._update_dashboard_state(
                daily_trades=stats['total_trades'],
                daily_wins=stats['winning_trades'],
                daily_losses=stats['losing_trades'],
                daily_pnl=stats['daily_pnl'],
                daily_win_rate=stats['win_rate']
            )

        except Exception as e:
            self.logger.error(f"Error in trading cycle: {e}", exc_info=True)
            self._add_dashboard_log("ERROR", f"Trading cycle error: {e}")

    def _check_entry_conditions(
        self,
        df,
        current_price: float,
        available_balance: float
    ):
        """
        Check if entry conditions are met and execute entry.

        Args:
            df: Market data DataFrame
            current_price: Current market price
            available_balance: Available balance for trading
        """
        # Check if we can open a new position
        if not self.position_manager.can_open_position(0):
            return

        # Get entry signal from strategy
        signal = self.strategy.should_enter(df, current_price)

        if signal is None:
            self.logger.debug("No entry signal")
            return

        self.logger.info(f"Entry signal detected: {signal}")

        # Calculate position parameters
        stop_loss_price = self.strategy.get_stop_loss(current_price, signal)
        take_profit_price = self.strategy.get_take_profit(current_price, signal)

        # Calculate position size
        position_size = self.position_manager.calculate_position_size(
            capital=available_balance,
            entry_price=current_price,
            stop_loss_price=stop_loss_price,
            leverage=Settings.MAX_LEVERAGE
        )

        if position_size == 0:
            self.logger.warning("Position size calculated as 0, skipping entry")
            return

        # Calculate risk-reward ratio
        rr_ratio = self.position_manager.calculate_risk_reward_ratio(
            current_price,
            stop_loss_price,
            take_profit_price
        )

        self.logger.info(
            f"Position parameters: Size: {position_size}, "
            f"SL: ${stop_loss_price:.2f}, TP: ${take_profit_price:.2f}, "
            f"R/R: 1:{rr_ratio:.2f}"
        )

        # Execute entry order
        self._execute_entry(signal, position_size, current_price, stop_loss_price, take_profit_price)

    def _execute_entry(
        self,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float
    ):
        """
        Execute entry order.

        Args:
            side: 'LONG' or 'SHORT'
            quantity: Position size
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        try:
            # Determine order side
            order_side = 'BUY' if side == 'LONG' else 'SELL'

            # Place market order
            order = self.exchange.place_market_order(
                symbol=self.symbol,
                side=order_side,
                quantity=quantity
            )

            # Log trade
            self.logger.log_trade(
                side=order_side,
                symbol=self.symbol,
                price=entry_price,
                quantity=quantity,
                trade_type='OPEN'
            )

            # Store position information
            self.current_position = {
                'side': side,
                'entry_price': entry_price,
                'quantity': quantity,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'order_id': order['orderId']
            }

            # Update strategy
            self.strategy.set_position(self.current_position)

            self.logger.info(f"Position opened successfully: {side} {quantity} {self.symbol}")

            # Send Telegram notification
            notifier.notify_trade_entry(
                side=side,
                price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit
            )

            # Update dashboard
            self._add_dashboard_log("INFO", f"Opened {side} position: {quantity} @ ${entry_price:.2f}")

        except Exception as e:
            self.logger.error(f"Failed to execute entry: {e}", exc_info=True)
            self._add_dashboard_log("ERROR", f"Failed to execute entry: {e}")

    def _check_exit_conditions(self, df, current_price: float):
        """
        Check if exit conditions are met and execute exit.

        Args:
            df: Market data DataFrame
            current_price: Current market price
        """
        if not self.current_position:
            return

        # Log current position status
        self.logger.log_position(
            symbol=self.symbol,
            side=self.current_position['side'],
            quantity=self.current_position['quantity'],
            entry_price=self.current_position['entry_price'],
            current_price=current_price,
            unrealized_pnl=self._calculate_unrealized_pnl(current_price)
        )

        # Check if strategy signals exit
        should_exit = self.strategy.should_exit(df, current_price, self.current_position)

        if should_exit:
            self.logger.info("Exit signal detected")
            self._execute_exit(current_price)

    def _execute_exit(self, exit_price: float):
        """
        Execute exit order.

        Args:
            exit_price: Exit price
        """
        try:
            if not self.current_position:
                return

            # Determine order side (opposite of position)
            order_side = 'SELL' if self.current_position['side'] == 'LONG' else 'BUY'

            # Place market order to close position
            order = self.exchange.place_market_order(
                symbol=self.symbol,
                side=order_side,
                quantity=self.current_position['quantity']
            )

            # Calculate profit/loss
            pnl = self._calculate_unrealized_pnl(exit_price)
            entry_price = self.current_position['entry_price']
            pnl_percent = (pnl / (entry_price * self.current_position['quantity'])) * 100

            # Log trade
            self.logger.log_trade(
                side=order_side,
                symbol=self.symbol,
                price=exit_price,
                quantity=self.current_position['quantity'],
                profit=pnl,
                trade_type='CLOSE'
            )

            # Record trade in position manager
            self.position_manager.record_trade(pnl)

            self.logger.info(
                f"Position closed successfully. P/L: "
                f"{'+ $' if pnl > 0 else '- $'}{abs(pnl):.2f}"
            )

            # Send Telegram notification
            notifier.notify_trade_exit(
                side=self.current_position['side'],
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=self.current_position['quantity'],
                pnl=pnl,
                pnl_percent=pnl_percent,
                reason="Strategy Signal"
            )

            # Update dashboard with trade
            self._add_dashboard_log(
                "INFO",
                f"Closed {self.current_position['side']} position @ ${exit_price:.2f} | P/L: ${pnl:.2f}"
            )

            # Add trade to history
            if DASHBOARD_ENABLED and bot_state:
                bot_state.add_trade({
                    "side": self.current_position['side'],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "quantity": self.current_position['quantity'],
                    "pnl": pnl,
                    "pnl_percent": pnl_percent
                })

            # Clear position
            self.current_position = None
            self.strategy.set_position(None)

        except Exception as e:
            self.logger.error(f"Failed to execute exit: {e}", exc_info=True)
            self._add_dashboard_log("ERROR", f"Failed to execute exit: {e}")

    def _calculate_unrealized_pnl(self, current_price: float) -> float:
        """
        Calculate unrealized profit/loss for current position.

        Args:
            current_price: Current market price

        Returns:
            Unrealized P/L
        """
        if not self.current_position:
            return 0.0

        entry_price = self.current_position['entry_price']
        quantity = self.current_position['quantity']
        side = self.current_position['side']

        if side == 'LONG':
            pnl = (current_price - entry_price) * quantity
        else:  # SHORT
            pnl = (entry_price - current_price) * quantity

        return pnl

    def _sync_position_from_exchange(self, positions):
        """
        Sync position tracking with exchange state.

        Args:
            positions: List of positions from exchange
        """
        for pos in positions:
            if pos['symbol'] == self.symbol:
                amount = float(pos['positionAmt'])
                if amount != 0:
                    self.current_position = {
                        'side': 'LONG' if amount > 0 else 'SHORT',
                        'entry_price': float(pos['entryPrice']),
                        'quantity': abs(amount),
                        'stop_loss': 0,  # Not tracked by exchange
                        'take_profit': 0  # Not tracked by exchange
                    }
                    self.strategy.set_position(self.current_position)
                    self.logger.info("Synced existing position from exchange")
                    break

    def _shutdown(self, reason: str = "Unknown"):
        """
        Graceful shutdown.

        Args:
            reason: Reason for shutdown
        """
        self.logger.info("=" * 60)
        self.logger.info("SHUTTING DOWN TRADING BOT")
        self.logger.info("=" * 60)

        # Log final stats
        stats = self.position_manager.get_daily_stats()
        self.logger.info(f"Final daily stats: {stats}")

        # Send daily summary if there were trades
        if stats['total_trades'] > 0:
            notifier.notify_daily_summary(
                trades_today=stats['total_trades'],
                wins=stats['winning_trades'],
                losses=stats['losing_trades'],
                total_pnl=stats['daily_pnl'],
                win_rate=stats['win_rate']
            )

        # Warning if position is still open
        if self.current_position:
            self.logger.warning(
                f"WARNING: Position still open! "
                f"{self.current_position['side']} {self.current_position['quantity']} {self.symbol}"
            )

        # Send shutdown notification
        notifier.notify_bot_stop(reason)

        self.logger.info("Bot shutdown complete")
