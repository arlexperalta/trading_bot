"""
Telegram command handler for interactive bot control.
Allows users to control and monitor the trading bot via Telegram commands.
"""

import threading
import time
import requests
from typing import Optional, Callable, Dict, Any
from config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__, Settings.LOGS_DIR)


class TelegramCommandHandler:
    """Handles incoming Telegram commands for bot control"""

    def __init__(self):
        """Initialize the command handler"""
        self.bot_token = Settings.TELEGRAM_BOT_TOKEN
        self.chat_id = Settings.TELEGRAM_CHAT_ID
        self.enabled = bool(self.bot_token and self.chat_id)
        self.running = False
        self.last_update_id = 0
        self.poll_thread: Optional[threading.Thread] = None

        # Callbacks for bot control
        self.status_callback: Optional[Callable] = None
        self.balance_callback: Optional[Callable] = None
        self.daily_callback: Optional[Callable] = None
        self.position_callback: Optional[Callable] = None
        self.stop_callback: Optional[Callable] = None
        self.start_callback: Optional[Callable] = None

        if not self.enabled:
            logger.warning("Telegram commands disabled - credentials not configured")
        else:
            logger.info("Telegram command handler initialized")

    def set_callbacks(self,
                      status_cb: Callable = None,
                      balance_cb: Callable = None,
                      daily_cb: Callable = None,
                      position_cb: Callable = None,
                      stop_cb: Callable = None,
                      start_cb: Callable = None):
        """Set callback functions for commands"""
        self.status_callback = status_cb
        self.balance_callback = balance_cb
        self.daily_callback = daily_cb
        self.position_callback = position_cb
        self.stop_callback = stop_cb
        self.start_callback = start_cb

    def send_message(self, text: str, parse_mode: str = "HTML",
                     reply_markup: dict = None) -> bool:
        """Send a message to Telegram"""
        if not self.enabled:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def get_updates(self) -> list:
        """Get new messages from Telegram"""
        if not self.enabled:
            return []

        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        params = {
            "offset": self.last_update_id + 1,
            "timeout": 30,
            "allowed_updates": ["message"]
        }

        try:
            response = requests.get(url, params=params, timeout=35)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("result", [])
        except Exception as e:
            logger.error(f"Error getting updates: {e}")

        return []

    def process_command(self, message: dict):
        """Process a command message"""
        text = message.get("text", "").strip().lower()
        from_chat = message.get("chat", {}).get("id")

        # Only respond to our configured chat
        if str(from_chat) != str(self.chat_id):
            logger.warning(f"Ignoring message from unauthorized chat: {from_chat}")
            return

        if text.startswith("/"):
            command = text.split()[0]
            self.handle_command(command)

    def handle_command(self, command: str):
        """Handle a specific command"""
        handlers = {
            "/start": self.cmd_start,
            "/stop": self.cmd_stop,
            "/status": self.cmd_status,
            "/balance": self.cmd_balance,
            "/daily": self.cmd_daily,
            "/position": self.cmd_position,
            "/profit": self.cmd_daily,  # Alias
            "/performance": self.cmd_daily,  # Alias
            "/strategy": self.cmd_strategy,
            "/strategies": self.cmd_strategies,
            "/funding": self.cmd_funding,
            "/help": self.cmd_help,
        }

        handler = handlers.get(command, self.cmd_unknown)
        handler()

    def cmd_help(self):
        """Show help message"""
        message = """
<b>Trading Bot Commands</b>

<b>Status & Info:</b>
/status - Bot status and current state
/balance - Account balance
/position - Current open positions
/daily - Today's trading stats
/profit - Same as /daily

<b>Strategy:</b>
/strategy - Current strategy info
/strategies - List all strategies
/funding - Check funding rates

<b>Control:</b>
/start - Start trading
/stop - Stop trading (pauses bot)

/help - Show this help
        """
        self.send_message(message.strip())

    def cmd_strategy(self):
        """Show current strategy info"""
        if self.status_callback:
            data = self.status_callback()
            strategy_name = data.get("strategy_name", "Unknown")
            regime = data.get("market_regime", "N/A")
            confidence = data.get("regime_confidence", 0)

            message = f"""
<b>Current Strategy</b>

<b>Strategy:</b> <code>{strategy_name}</code>
<b>Market Regime:</b> <code>{regime}</code>
<b>Confidence:</b> <code>{confidence:.1%}</code>

<b>Available Strategies:</b>
• <code>adaptive</code> - Auto-adjusts to market
• <code>ema</code> - EMA Crossover (Aggressive)
• <code>volume</code> - Alpha Volume Farming
• <code>funding</code> - Funding Arbitrage

To change: Edit BOT_STRATEGY in .env
            """
            self.send_message(message.strip())
        else:
            self.send_message("Strategy info not available")

    def cmd_strategies(self):
        """List all available strategies"""
        message = """
<b>Available Strategies</b>

<b>1. Adaptive Multi-Strategy</b> (adaptive)
Auto-adjusts to market conditions
• Detects: Trend, Range, Volatility
• Best for: General trading
• Risk: Medium

<b>2. EMA Crossover</b> (ema)
Aggressive scalping on EMA crosses
• Timeframe: 5m
• Best for: Trending markets
• Risk: Medium-High

<b>3. Alpha Volume Farming</b> (volume)
Generates volume for Binance airdrops
• 100-500 trades/day
• Best for: Alpha Events
• Risk: Low

<b>4. Funding Arbitrage</b> (funding)
Earns funding rate payments
• 4-33% annual passive
• Best for: Passive income
• Risk: Very Low

<b>Change strategy:</b>
Restart bot with: <code>python main.py [strategy]</code>
        """
        self.send_message(message.strip())

    def cmd_funding(self):
        """Check current funding rates"""
        try:
            import requests
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
            results = []

            for symbol in symbols:
                url = "https://fapi.binance.com/fapi/v1/premiumIndex"
                response = requests.get(url, params={'symbol': symbol}, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    rate = float(data.get('lastFundingRate', 0)) * 100
                    emoji = "+" if rate > 0 else ""
                    results.append(f"• {symbol}: <code>{emoji}{rate:.4f}%</code>")

            message = f"""
<b>Current Funding Rates</b>

{chr(10).join(results)}

<b>Next funding:</b> Every 8 hours
<b>Opportunity:</b> Rate > 0.05% = Good for arbitrage

Positive rate = Longs pay Shorts
Negative rate = Shorts pay Longs
            """
            self.send_message(message.strip())

        except Exception as e:
            self.send_message(f"Error fetching funding rates: {e}")

    def cmd_status(self):
        """Show bot status"""
        if self.status_callback:
            data = self.status_callback()
            status = "Running" if data.get("running", True) else "Stopped"
            iteration = data.get("iteration", 0)
            price = data.get("current_price", 0)
            has_pos = data.get("has_position", False)

            pos_info = ""
            if has_pos:
                side = data.get("position_side", "N/A")
                pnl = data.get("unrealized_pnl", 0)
                pos_info = f"\n<b>Position:</b> {side} (P/L: ${pnl:+.2f})"

            message = f"""
<b>Bot Status</b>

<b>Status:</b> <code>{status}</code>
<b>Iteration:</b> <code>{iteration}</code>
<b>Price:</b> <code>${price:,.2f}</code>
<b>Mode:</b> <code>{Settings.TRADING_MODE}</code>
<b>Timeframe:</b> <code>{Settings.TIMEFRAME}</code>
<b>Strategy:</b> EMA {Settings.EMA_FAST_PERIOD}/{Settings.EMA_SLOW_PERIOD}{pos_info}
            """
            self.send_message(message.strip())
        else:
            self.send_message("Bot is running (no detailed status available)")

    def cmd_balance(self):
        """Show balance"""
        if self.balance_callback:
            data = self.balance_callback()
            total = data.get("total", 0)
            available = data.get("available", 0)
            unrealized = data.get("unrealized_pnl", 0)

            message = f"""
<b>Account Balance</b>

<b>Total:</b> <code>${total:,.2f}</code>
<b>Available:</b> <code>${available:,.2f}</code>
<b>Unrealized P/L:</b> <code>${unrealized:+,.2f}</code>
<b>Equity:</b> <code>${total + unrealized:,.2f}</code>
            """
            self.send_message(message.strip())
        else:
            self.send_message("Balance info not available")

    def cmd_daily(self):
        """Show daily stats"""
        if self.daily_callback:
            data = self.daily_callback()
            trades = data.get("total_trades", 0)
            wins = data.get("winning_trades", 0)
            losses = data.get("losing_trades", 0)
            pnl = data.get("daily_pnl", 0)
            win_rate = data.get("win_rate", 0)

            emoji = "+" if pnl >= 0 else ""

            message = f"""
<b>Daily Statistics</b>

<b>Total Trades:</b> <code>{trades}</code>
<b>Wins:</b> <code>{wins}</code>
<b>Losses:</b> <code>{losses}</code>
<b>Win Rate:</b> <code>{win_rate:.1f}%</code>
<b>P/L Today:</b> <code>${pnl:+,.2f}</code>
            """
            self.send_message(message.strip())
        else:
            self.send_message("No trades today")

    def cmd_position(self):
        """Show current position"""
        if self.position_callback:
            data = self.position_callback()

            if data and data.get("has_position"):
                side = data.get("side", "N/A")
                entry = data.get("entry_price", 0)
                qty = data.get("quantity", 0)
                sl = data.get("stop_loss", 0)
                tp = data.get("take_profit", 0)
                pnl = data.get("unrealized_pnl", 0)

                emoji = "Long" if side == "LONG" else "Short"

                message = f"""
<b>Current Position</b>

<b>Side:</b> <code>{emoji}</code>
<b>Entry:</b> <code>${entry:,.2f}</code>
<b>Quantity:</b> <code>{qty:.6f}</code>
<b>Stop Loss:</b> <code>${sl:,.2f}</code>
<b>Take Profit:</b> <code>${tp:,.2f}</code>
<b>Unrealized P/L:</b> <code>${pnl:+,.2f}</code>
                """
            else:
                message = "No open positions"

            self.send_message(message.strip())
        else:
            self.send_message("Position info not available")

    def cmd_start(self):
        """Start the bot"""
        if self.start_callback:
            self.start_callback()
            self.send_message("Trading bot started")
        else:
            self.send_message("Bot is already running")

    def cmd_stop(self):
        """Stop the bot"""
        if self.stop_callback:
            self.stop_callback()
            self.send_message("Trading paused. Use /start to resume.")
        else:
            self.send_message("Cannot stop bot remotely (callback not set)")

    def cmd_unknown(self):
        """Handle unknown command"""
        self.send_message("Unknown command. Use /help for available commands.")

    def setup_commands_menu(self):
        """Set up the commands menu in Telegram"""
        if not self.enabled:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/setMyCommands"
        commands = [
            {"command": "status", "description": "Bot status and current state"},
            {"command": "balance", "description": "Account balance"},
            {"command": "position", "description": "Current open positions"},
            {"command": "daily", "description": "Today's trading stats"},
            {"command": "strategy", "description": "Current strategy info"},
            {"command": "strategies", "description": "List all strategies"},
            {"command": "funding", "description": "Check funding rates"},
            {"command": "start", "description": "Start trading"},
            {"command": "stop", "description": "Pause trading"},
            {"command": "help", "description": "Show all commands"},
        ]

        try:
            response = requests.post(url, json={"commands": commands}, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram commands menu set up successfully")
                return True
            else:
                logger.error(f"Failed to set commands: {response.text}")
        except Exception as e:
            logger.error(f"Error setting up commands: {e}")

        return False

    def polling_loop(self):
        """Main polling loop to receive commands"""
        logger.info("Starting Telegram command polling...")
        self.setup_commands_menu()

        while self.running:
            try:
                updates = self.get_updates()

                for update in updates:
                    self.last_update_id = update.get("update_id", self.last_update_id)
                    message = update.get("message")

                    if message and message.get("text", "").startswith("/"):
                        self.process_command(message)

            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                time.sleep(5)

    def start_polling(self):
        """Start the polling thread"""
        if not self.enabled:
            return False

        if self.running:
            return True

        self.running = True
        self.poll_thread = threading.Thread(target=self.polling_loop, daemon=True)
        self.poll_thread.start()
        logger.info("Telegram command handler started")
        return True

    def stop_polling(self):
        """Stop the polling thread"""
        self.running = False
        logger.info("Telegram command handler stopped")


# Singleton instance
command_handler = TelegramCommandHandler()
