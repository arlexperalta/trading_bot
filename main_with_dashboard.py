#!/usr/bin/env python3
"""
Crypto Trading Bot with Web Dashboard
Runs the trading bot and FastAPI dashboard server concurrently.
"""

import os
import sys
import threading
import signal
from typing import Optional

import uvicorn

from config.settings import Settings
from src.strategies.ema_crossover import EMACrossoverStrategy
from src.core.trader import Trader
from src.web.server import app
from src.web.bot_state import bot_state
from src.utils.logger import get_logger

# Global references for graceful shutdown
trader_instance: Optional[Trader] = None
shutdown_event = threading.Event()


def display_banner():
    """Display startup banner with configuration info."""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║         CRYPTO TRADING BOT WITH DASHBOARD                     ║
    ║                   Binance Futures                             ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    print(f"  Mode:          {Settings.TRADING_MODE}")
    print(f"  Trading Pair:  {Settings.TRADING_PAIR}")
    print(f"  Timeframe:     {Settings.TIMEFRAME}")
    print(f"  Leverage:      {Settings.MAX_LEVERAGE}x")
    print(f"  Risk/Trade:    {Settings.RISK_PER_TRADE * 100}%")
    print(f"  Dashboard:     http://0.0.0.0:{os.getenv('DASHBOARD_PORT', 8000)}")
    print("=" * 65)


def validate_environment():
    """Validate that required environment variables are set."""
    try:
        Settings.get_api_credentials()
        return True
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease set the required environment variables:")
        print("  - BINANCE_TESTNET_API_KEY")
        print("  - BINANCE_TESTNET_API_SECRET")
        print("\nOr for production:")
        print("  - BINANCE_API_KEY")
        print("  - BINANCE_API_SECRET")
        return False


def run_dashboard():
    """Run the FastAPI dashboard server."""
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    port = int(os.getenv("DASHBOARD_PORT", 8000))

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
    server = uvicorn.Server(config)

    # Run until shutdown event is set
    server.run()


def run_trading_bot():
    """Run the trading bot."""
    global trader_instance

    logger = get_logger(__name__, Settings.LOGS_DIR)

    try:
        # Initialize bot state
        bot_state.update(
            trading_mode=Settings.TRADING_MODE,
            trading_pair=Settings.TRADING_PAIR,
            timeframe=Settings.TIMEFRAME,
            leverage=Settings.MAX_LEVERAGE,
            initial_capital=Settings.INITIAL_CAPITAL
        )

        # Create strategy and trader
        strategy = EMACrossoverStrategy()
        trader_instance = Trader(strategy)

        # Mark bot as started
        bot_state.start_bot()
        bot_state.add_log("INFO", "Trading bot started")

        # Run trading loop
        trader_instance.run_trading_loop()

    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        bot_state.set_error(str(e))
        bot_state.add_log("ERROR", f"Bot error: {e}")
    finally:
        bot_state.stop_bot()
        bot_state.add_log("INFO", "Trading bot stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n\nShutdown signal received. Stopping services...")
    shutdown_event.set()

    if trader_instance:
        # The trader will handle its own cleanup
        pass

    sys.exit(0)


def main():
    """Main entry point."""
    # Display banner
    display_banner()

    # Validate environment
    if not validate_environment():
        sys.exit(1)

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start dashboard in a separate thread
    dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
    dashboard_thread.start()
    print("\n✅ Dashboard server started")

    # Give dashboard a moment to start
    import time
    time.sleep(2)

    # Run trading bot in main thread
    print("✅ Starting trading bot...\n")
    run_trading_bot()


if __name__ == "__main__":
    main()
