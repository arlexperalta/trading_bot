"""
Telegram notification system for the trading bot.
Sends real-time alerts about trading activity, errors, and status updates.
"""

import requests
import time
from typing import Optional
from config.settings import Settings
from src.utils.logger import get_logger

logger = get_logger(__name__, Settings.LOGS_DIR)


class TelegramNotifier:
    """Handles sending notifications to Telegram"""

    def __init__(self):
        """Initialize the Telegram notifier"""
        self.bot_token = Settings.TELEGRAM_BOT_TOKEN
        self.chat_id = Settings.TELEGRAM_CHAT_ID
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.warning("Telegram notifications disabled - credentials not configured")
        else:
            logger.info("Telegram notifications enabled")

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message to Telegram.

        Args:
            message: Message text to send
            parse_mode: Message formatting (HTML or Markdown)

        Returns:
            bool: True if message sent successfully
        """
        if not self.enabled:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=10)

                if response.status_code == 200:
                    logger.debug(f"Telegram message sent successfully")
                    return True
                else:
                    logger.error(f"Failed to send Telegram message: {response.text}")

            except Exception as e:
                logger.error(f"Error sending Telegram message (attempt {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        return False

    def notify_bot_start(self):
        """Notify that the bot has started"""
        message = f"""
🤖 <b>Trading Bot Started</b>

📊 <b>Configuration:</b>
• Mode: <code>{Settings.TRADING_MODE}</code>
• Pair: <code>{Settings.TRADING_PAIR}</code>
• Timeframe: <code>{Settings.TIMEFRAME}</code>
• Strategy: <code>EMA {Settings.EMA_FAST_PERIOD}/{Settings.EMA_SLOW_PERIOD}</code>
• Max Leverage: <code>{Settings.MAX_LEVERAGE}x</code>
• Risk per Trade: <code>{Settings.RISK_PER_TRADE * 100}%</code>

✅ Bot is now monitoring the market...
        """
        self.send_message(message.strip())

    def notify_bot_stop(self, reason: str = "User requested"):
        """Notify that the bot has stopped"""
        message = f"""
🛑 <b>Trading Bot Stopped</b>

Reason: <code>{reason}</code>

The bot has been shut down gracefully.
        """
        self.send_message(message.strip())

    def notify_trade_entry(self, side: str, price: float, quantity: float,
                          stop_loss: float, take_profit: float):
        """
        Notify about a new trade entry.

        Args:
            side: LONG or SHORT
            price: Entry price
            quantity: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        emoji = "🟢" if side == "LONG" else "🔴"

        message = f"""
{emoji} <b>New {side} Position Opened</b>

💰 <b>Entry Details:</b>
• Pair: <code>{Settings.TRADING_PAIR}</code>
• Side: <code>{side}</code>
• Entry Price: <code>${price:,.2f}</code>
• Quantity: <code>{quantity:.6f}</code>
• Notional: <code>${price * quantity:,.2f}</code>

🎯 <b>Targets:</b>
• Stop Loss: <code>${stop_loss:,.2f}</code> ({((stop_loss - price) / price * 100):.2f}%)
• Take Profit: <code>${take_profit:,.2f}</code> ({((take_profit - price) / price * 100):.2f}%)

⏰ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
        """
        self.send_message(message.strip())

    def notify_trade_exit(self, side: str, entry_price: float, exit_price: float,
                         quantity: float, pnl: float, pnl_percent: float, reason: str):
        """
        Notify about a trade exit.

        Args:
            side: LONG or SHORT
            entry_price: Entry price
            exit_price: Exit price
            quantity: Position size
            pnl: Profit/Loss in USD
            pnl_percent: Profit/Loss percentage
            reason: Exit reason (TP/SL/Signal)
        """
        emoji = "✅" if pnl > 0 else "❌"

        message = f"""
{emoji} <b>{side} Position Closed</b>

📈 <b>Trade Summary:</b>
• Pair: <code>{Settings.TRADING_PAIR}</code>
• Side: <code>{side}</code>
• Entry: <code>${entry_price:,.2f}</code>
• Exit: <code>${exit_price:,.2f}</code>
• Quantity: <code>{quantity:.6f}</code>

💵 <b>Results:</b>
• P/L: <code>${pnl:+,.2f}</code> ({pnl_percent:+.2f}%)
• Reason: <code>{reason}</code>

⏰ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
        """
        self.send_message(message.strip())

    def notify_balance_update(self, balance: float, unrealized_pnl: float = 0):
        """
        Notify about balance update.

        Args:
            balance: Current balance
            unrealized_pnl: Unrealized P/L
        """
        message = f"""
💰 <b>Balance Update</b>

• Available Balance: <code>${balance:,.2f}</code>
• Unrealized P/L: <code>${unrealized_pnl:+,.2f}</code>
• Total Equity: <code>${balance + unrealized_pnl:,.2f}</code>

⏰ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
        """
        self.send_message(message.strip())

    def notify_error(self, error_type: str, error_message: str):
        """
        Notify about an error.

        Args:
            error_type: Type of error
            error_message: Error description
        """
        message = f"""
⚠️ <b>Error Alert</b>

• Type: <code>{error_type}</code>
• Message: <code>{error_message}</code>

⏰ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}

Please check the logs for more details.
        """
        self.send_message(message.strip())

    def notify_daily_summary(self, trades_today: int, wins: int, losses: int,
                            total_pnl: float, win_rate: float):
        """
        Send daily trading summary.

        Args:
            trades_today: Number of trades executed today
            wins: Number of winning trades
            losses: Number of losing trades
            total_pnl: Total profit/loss
            win_rate: Win rate percentage
        """
        emoji = "📊"

        message = f"""
{emoji} <b>Daily Trading Summary</b>

📈 <b>Performance:</b>
• Total Trades: <code>{trades_today}</code>
• Wins: <code>{wins}</code> | Losses: <code>{losses}</code>
• Win Rate: <code>{win_rate:.1f}%</code>
• Total P/L: <code>${total_pnl:+,.2f}</code>

⏰ {time.strftime('%Y-%m-%d', time.gmtime())}
        """
        self.send_message(message.strip())

    def notify_daily_loss_limit(self, loss_amount: float, limit_percent: float):
        """
        Notify that daily loss limit has been reached.

        Args:
            loss_amount: Current loss amount
            limit_percent: Loss limit percentage
        """
        message = f"""
🚨 <b>DAILY LOSS LIMIT REACHED</b>

• Current Loss: <code>${loss_amount:,.2f}</code>
• Limit: <code>{limit_percent * 100}%</code>

⚠️ Trading has been stopped for today to protect your capital.
The bot will resume tomorrow.

⏰ {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}
        """
        self.send_message(message.strip())


# Create singleton instance
notifier = TelegramNotifier()
