"""
Market data retrieval and processing.
Converts raw exchange data into pandas DataFrames with technical indicators.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional

from config.settings import Settings
from src.utils.logger import get_logger
from src.core.exchange import BinanceConnector


class MarketData:
    """
    Handles market data retrieval and processing.
    Converts klines to DataFrame and calculates technical indicators.
    """

    def __init__(self, exchange: BinanceConnector):
        """
        Initialize market data handler.

        Args:
            exchange: BinanceConnector instance
        """
        self.exchange = exchange
        self.logger = get_logger(__name__, Settings.LOGS_DIR)

    def get_klines_dataframe(
        self,
        symbol: str,
        interval: str,
        limit: int = 500
    ) -> pd.DataFrame:
        """
        Get historical klines as a pandas DataFrame.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval (e.g., '1h', '4h')
            limit: Number of candles to retrieve

        Returns:
            DataFrame with OHLCV data
        """
        try:
            klines = self.exchange.get_historical_klines(symbol, interval, limit)

            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert columns to appropriate types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)

            # Set timestamp as index
            df.set_index('timestamp', inplace=True)

            # Keep only OHLCV columns
            df = df[['open', 'high', 'low', 'close', 'volume']]

            self.logger.debug(f"Retrieved {len(df)} candles for {symbol} ({interval})")

            return df

        except Exception as e:
            self.logger.error(f"Failed to get klines dataframe: {e}", exc_info=True)
            raise

    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average.

        Args:
            df: DataFrame with price data
            period: EMA period

        Returns:
            Series with EMA values
        """
        try:
            ema = df['close'].ewm(span=period, adjust=False).mean()
            self.logger.debug(f"Calculated EMA({period})")
            return ema

        except Exception as e:
            self.logger.error(f"Failed to calculate EMA: {e}", exc_info=True)
            raise

    def calculate_sma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average.

        Args:
            df: DataFrame with price data
            period: SMA period

        Returns:
            Series with SMA values
        """
        try:
            sma = df['close'].rolling(window=period).mean()
            self.logger.debug(f"Calculated SMA({period})")
            return sma

        except Exception as e:
            self.logger.error(f"Failed to calculate SMA: {e}", exc_info=True)
            raise

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range.

        Args:
            df: DataFrame with OHLC data
            period: ATR period

        Returns:
            Series with ATR values
        """
        try:
            high = df['high']
            low = df['low']
            close = df['close']

            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())

            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Calculate ATR as moving average of TR
            atr = tr.rolling(window=period).mean()

            self.logger.debug(f"Calculated ATR({period})")

            return atr

        except Exception as e:
            self.logger.error(f"Failed to calculate ATR: {e}", exc_info=True)
            raise

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index.

        Args:
            df: DataFrame with price data
            period: RSI period

        Returns:
            Series with RSI values
        """
        try:
            # Calculate price changes
            delta = df['close'].diff()

            # Separate gains and losses
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # Calculate average gains and losses
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()

            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            self.logger.debug(f"Calculated RSI({period})")

            return rsi

        except Exception as e:
            self.logger.error(f"Failed to calculate RSI: {e}", exc_info=True)
            raise

    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.

        Args:
            df: DataFrame with price data
            period: Moving average period
            std_dev: Number of standard deviations

        Returns:
            Dictionary with upper, middle, and lower bands
        """
        try:
            # Calculate middle band (SMA)
            middle = df['close'].rolling(window=period).mean()

            # Calculate standard deviation
            std = df['close'].rolling(window=period).std()

            # Calculate upper and lower bands
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)

            self.logger.debug(f"Calculated Bollinger Bands({period}, {std_dev})")

            return {
                'upper': upper,
                'middle': middle,
                'lower': lower
            }

        except Exception as e:
            self.logger.error(f"Failed to calculate Bollinger Bands: {e}", exc_info=True)
            raise

    def calculate_volume_average(self, df: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate volume moving average.

        Args:
            df: DataFrame with volume data
            period: Period for average

        Returns:
            Series with volume average
        """
        try:
            vol_avg = df['volume'].rolling(window=period).mean()
            self.logger.debug(f"Calculated Volume Average({period})")
            return vol_avg

        except Exception as e:
            self.logger.error(f"Failed to calculate volume average: {e}", exc_info=True)
            raise

    def add_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all technical indicators to the DataFrame.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with added indicators
        """
        try:
            # EMAs for strategy
            df['ema_fast'] = self.calculate_ema(df, Settings.EMA_FAST_PERIOD)
            df['ema_slow'] = self.calculate_ema(df, Settings.EMA_SLOW_PERIOD)

            # ATR for stop loss
            df['atr'] = self.calculate_atr(df, 14)

            # Volume average
            df['volume_avg'] = self.calculate_volume_average(df, Settings.VOLUME_PERIOD)

            # RSI for additional confirmation
            df['rsi'] = self.calculate_rsi(df, 14)

            # Bollinger Bands
            bb = self.calculate_bollinger_bands(df, 20, 2.0)
            df['bb_upper'] = bb['upper']
            df['bb_middle'] = bb['middle']
            df['bb_lower'] = bb['lower']

            self.logger.debug("Added all technical indicators to DataFrame")

            return df

        except Exception as e:
            self.logger.error(f"Failed to add indicators: {e}", exc_info=True)
            raise

    def get_latest_candle(self, df: pd.DataFrame) -> pd.Series:
        """
        Get the most recent completed candle.

        Args:
            df: DataFrame with market data

        Returns:
            Series with latest candle data
        """
        return df.iloc[-1]

    def detect_ema_crossover(self, df: pd.DataFrame) -> Optional[str]:
        """
        Detect EMA crossover signals.

        Args:
            df: DataFrame with EMA data

        Returns:
            'BULLISH' for golden cross, 'BEARISH' for death cross, None otherwise
        """
        try:
            if len(df) < 2:
                return None

            # Current and previous candles
            current = df.iloc[-1]
            previous = df.iloc[-2]

            # Bullish crossover (EMA fast crosses above EMA slow)
            if (previous['ema_fast'] <= previous['ema_slow'] and
                current['ema_fast'] > current['ema_slow']):
                self.logger.info("Detected BULLISH EMA crossover")
                return 'BULLISH'

            # Bearish crossover (EMA fast crosses below EMA slow)
            if (previous['ema_fast'] >= previous['ema_slow'] and
                current['ema_fast'] < current['ema_slow']):
                self.logger.info("Detected BEARISH EMA crossover")
                return 'BEARISH'

            return None

        except Exception as e:
            self.logger.error(f"Failed to detect EMA crossover: {e}", exc_info=True)
            return None
