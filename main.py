"""
Main entry point for the crypto trading bot.
Initializes and runs the trading system with multiple strategy support.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from src.core.trader import Trader
from src.utils.logger import get_logger

# Import all strategies
from src.strategies.ema_crossover import EMACrossoverStrategy
from src.strategies.adaptive_multi_strategy import AdaptiveStrategy
from src.strategies.alpha_volume_farming_strategy import AlphaVolumeFarmingStrategy
from src.strategies.funding_arbitrage_strategy import FundingArbitrageStrategy

# Strategy registry
STRATEGIES = {
    'ema': EMACrossoverStrategy,
    'adaptive': AdaptiveStrategy,
    'volume': AlphaVolumeFarmingStrategy,
    'funding': FundingArbitrageStrategy,
}

# Default strategy
DEFAULT_STRATEGY = 'adaptive'


def get_strategy_name(strategy_key: str) -> str:
    """Get human-readable strategy name"""
    names = {
        'ema': 'EMA Crossover (Aggressive)',
        'adaptive': 'Adaptive Multi-Strategy',
        'volume': 'Alpha Volume Farming',
        'funding': 'Funding Rate Arbitrage',
    }
    return names.get(strategy_key, strategy_key)


def print_banner(strategy_key: str):
    """Print startup banner"""
    strategy_name = get_strategy_name(strategy_key)

    print("\n" + "=" * 70)
    print("  CRYPTO TRADING BOT - Binance Futures")
    print("=" * 70)
    print(f"  Mode:          {Settings.TRADING_MODE}")
    print(f"  Trading Pair:  {Settings.TRADING_PAIR}")
    print(f"  Timeframe:     {Settings.TIMEFRAME}")
    print(f"  Strategy:      {strategy_name}")
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
        print(f"\n Error: {e}")
        print("\nPlease ensure:")
        print("1. You have copied config/.env.example to config/.env")
        print("2. You have filled in your Binance API credentials")
        print("3. All required settings are properly configured\n")
        return False


def get_strategy_from_args() -> str:
    """Get strategy from command line args or environment"""
    # Check command line args
    if len(sys.argv) > 1:
        strategy_key = sys.argv[1].lower()
        if strategy_key in STRATEGIES:
            return strategy_key
        else:
            print(f"\n Unknown strategy: {strategy_key}")
            print(f"Available strategies: {', '.join(STRATEGIES.keys())}")
            sys.exit(1)

    # Check environment variable
    env_strategy = os.getenv('BOT_STRATEGY', DEFAULT_STRATEGY).lower()
    if env_strategy in STRATEGIES:
        return env_strategy

    return DEFAULT_STRATEGY


def main():
    """Main entry point"""
    # Get strategy
    strategy_key = get_strategy_from_args()

    # Print banner
    print_banner(strategy_key)

    # Setup logger
    logger = get_logger(__name__, Settings.LOGS_DIR)

    try:
        # Validate environment
        if not validate_environment():
            sys.exit(1)

        logger.info("Starting Crypto Trading Bot")
        logger.info(f"Trading mode: {Settings.TRADING_MODE}")
        logger.info(f"Symbol: {Settings.TRADING_PAIR}")
        logger.info(f"Strategy: {get_strategy_name(strategy_key)}")

        # Initialize strategy
        StrategyClass = STRATEGIES[strategy_key]
        strategy = StrategyClass()

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
        print(f"\n\n Critical Error: {e}")
        print("Check logs/errors.log for details\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
