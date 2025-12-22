"""
Main entry point for the crypto trading bot.
Initializes and runs the trading system.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from src.core.trader import Trader
from src.strategies.ema_crossover import EMACrossoverStrategy
from src.utils.logger import get_logger


def print_banner():
    """Print startup banner"""
    print("\n" + "=" * 70)
    print("  CRYPTO TRADING BOT - Binance Futures")
    print("=" * 70)
    print(f"  Mode:          {Settings.TRADING_MODE}")
    print(f"  Trading Pair:  {Settings.TRADING_PAIR}")
    print(f"  Timeframe:     {Settings.TIMEFRAME}")
    print(f"  Strategy:      EMA Crossover ({Settings.EMA_FAST_PERIOD}/{Settings.EMA_SLOW_PERIOD})")
    print(f"  Max Leverage:  {Settings.MAX_LEVERAGE}x")
    print(f"  Risk/Trade:    {Settings.RISK_PER_TRADE * 100}%")
    print(f"  Stop Loss:     {Settings.STOP_LOSS_PERCENT * 100}%")
    print(f"  Take Profit:   {Settings.TAKE_PROFIT_PERCENT * 100}%")
    print("=" * 70)

    if Settings.TRADING_MODE == 'TESTNET':
        print("\n  *** TESTNET MODE - Using test funds ***\n")
    else:
        print("\n  !!! PRODUCTION MODE - REAL MONEY AT RISK !!!\n")
        response = input("  Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("  Aborted by user.")
            sys.exit(0)

    print("=" * 70 + "\n")


def validate_environment():
    """Validate that environment is properly configured"""
    logger = get_logger(__name__, Settings.LOGS_DIR)

    try:
        # Validate settings
        Settings.validate_settings()

        # Check API credentials
        api_key, api_secret = Settings.get_api_credentials()

        if not api_key or not api_secret:
            raise ValueError("API credentials not found in environment")

        if 'your_' in api_key.lower() or 'your_' in api_secret.lower():
            raise ValueError(
                "Please update your .env file with actual API credentials. "
                "Copy config/.env.example to config/.env and fill in your keys."
            )

        logger.info("Environment validation successful")
        return True

    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        print(f"\n❌ Error: {e}")
        print("\nPlease ensure:")
        print("1. You have copied config/.env.example to config/.env")
        print("2. You have filled in your Binance API credentials")
        print("3. All required settings are properly configured\n")
        return False


def main():
    """Main entry point"""
    # Print banner
    print_banner()

    # Setup logger
    logger = get_logger(__name__, Settings.LOGS_DIR)

    try:
        # Validate environment
        if not validate_environment():
            sys.exit(1)

        logger.info("Starting Crypto Trading Bot")
        logger.info(f"Trading mode: {Settings.TRADING_MODE}")
        logger.info(f"Symbol: {Settings.TRADING_PAIR}")

        # Initialize strategy
        strategy = EMACrossoverStrategy()

        # Initialize trader
        trader = Trader(strategy)

        # Start trading loop
        trader.run_trading_loop()

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
        print("\n\nBot stopped by user. Goodbye!")
        sys.exit(0)

    except Exception as e:
        logger.critical(f"Critical error in main: {e}", exc_info=True)
        print(f"\n\n❌ Critical Error: {e}")
        print("Check logs/errors.log for details\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
