"""
Configuration settings for the crypto trading bot.
Loads environment variables and provides centralized configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)


class Settings:
    """Centralized configuration management for the trading bot"""

    # Base directories
    BASE_DIR: Path = Path(__file__).parent.parent
    LOGS_DIR: Path = BASE_DIR / 'logs'

    # Trading mode
    TRADING_MODE: str = os.getenv('TRADING_MODE', 'TESTNET')

    # Binance API credentials
    BINANCE_TESTNET_API_KEY: Optional[str] = os.getenv('BINANCE_TESTNET_API_KEY')
    BINANCE_TESTNET_API_SECRET: Optional[str] = os.getenv('BINANCE_TESTNET_API_SECRET')
    BINANCE_API_KEY: Optional[str] = os.getenv('BINANCE_API_KEY')
    BINANCE_API_SECRET: Optional[str] = os.getenv('BINANCE_API_SECRET')

    # Binance URLs
    BINANCE_TESTNET_URL: str = 'https://testnet.binancefuture.com'
    BINANCE_PRODUCTION_URL: str = 'https://fapi.binance.com'

    # Trading parameters
    INITIAL_CAPITAL: float = float(os.getenv('INITIAL_CAPITAL', 100))
    MAX_LEVERAGE: int = int(os.getenv('MAX_LEVERAGE', 2))
    RISK_PER_TRADE: float = float(os.getenv('RISK_PER_TRADE', 0.01))
    TRADING_PAIR: str = os.getenv('TRADING_PAIR', 'BTCUSDT')

    # Risk management
    MAX_DAILY_LOSS_PERCENT: float = 0.05  # 5% maximum daily loss
    STOP_LOSS_PERCENT: float = 0.02  # 2% stop loss
    TAKE_PROFIT_PERCENT: float = 0.06  # 6% take profit

    # Strategy parameters
    EMA_FAST_PERIOD: int = 9
    EMA_SLOW_PERIOD: int = 21
    TIMEFRAME: str = '4h'  # 4-hour candles
    VOLUME_PERIOD: int = 20  # Volume average period

    # Bot behavior
    UPDATE_INTERVAL: int = 300  # 5 minutes in seconds
    MAX_OPEN_POSITIONS: int = 1  # Only one position at a time

    # API rate limiting
    MAX_REQUESTS_PER_MINUTE: int = 1200
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 1  # seconds
    BACKOFF_MULTIPLIER: float = 2.0  # Exponential backoff

    # Telegram notifications (optional)
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv('TELEGRAM_CHAT_ID')

    @classmethod
    def get_api_credentials(cls) -> tuple[str, str]:
        """
        Get API credentials based on trading mode.

        Returns:
            tuple[str, str]: API key and secret

        Raises:
            ValueError: If credentials are not set for the current mode
        """
        if cls.TRADING_MODE == 'TESTNET':
            if not cls.BINANCE_TESTNET_API_KEY or not cls.BINANCE_TESTNET_API_SECRET:
                raise ValueError(
                    "Testnet API credentials not found. "
                    "Please set BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET in .env"
                )
            return cls.BINANCE_TESTNET_API_KEY, cls.BINANCE_TESTNET_API_SECRET
        else:
            if not cls.BINANCE_API_KEY or not cls.BINANCE_API_SECRET:
                raise ValueError(
                    "Production API credentials not found. "
                    "Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env"
                )
            return cls.BINANCE_API_KEY, cls.BINANCE_API_SECRET

    @classmethod
    def get_base_url(cls) -> str:
        """
        Get Binance API base URL based on trading mode.

        Returns:
            str: Base URL for API calls
        """
        if cls.TRADING_MODE == 'TESTNET':
            return cls.BINANCE_TESTNET_URL
        return cls.BINANCE_PRODUCTION_URL

    @classmethod
    def validate_settings(cls) -> bool:
        """
        Validate that all required settings are properly configured.

        Returns:
            bool: True if settings are valid

        Raises:
            ValueError: If any required setting is invalid
        """
        # Validate capital
        if cls.INITIAL_CAPITAL <= 0:
            raise ValueError("INITIAL_CAPITAL must be greater than 0")

        # Validate leverage
        if cls.MAX_LEVERAGE < 1 or cls.MAX_LEVERAGE > 125:
            raise ValueError("MAX_LEVERAGE must be between 1 and 125")

        # Validate risk
        if cls.RISK_PER_TRADE <= 0 or cls.RISK_PER_TRADE > 0.1:
            raise ValueError("RISK_PER_TRADE must be between 0 and 0.1 (10%)")

        # Validate trading pair
        if not cls.TRADING_PAIR:
            raise ValueError("TRADING_PAIR must be set")

        # Create logs directory if it doesn't exist
        cls.LOGS_DIR.mkdir(exist_ok=True)

        return True


# Validate settings on import
Settings.validate_settings()
