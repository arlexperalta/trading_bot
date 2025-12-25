"""
Binance Futures exchange connector.
Handles all API communication with Binance Futures exchange.
"""

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from typing import Dict, List, Optional, Any
import time

from config.settings import Settings
from src.utils.logger import get_logger
from src.utils.helpers import retry_on_exception


class BinanceConnector:
    """
    Manages connection and communication with Binance Futures API.
    Includes error handling, retry logic, and rate limiting.
    """

    def __init__(self):
        """Initialize Binance connector with API credentials"""
        self.logger = get_logger(__name__, Settings.LOGS_DIR)

        # Get API credentials
        api_key, api_secret = Settings.get_api_credentials()

        # Symbol precision cache
        self.symbol_info_cache = {}

        # Initialize Binance client
        try:
            # Configure testnet mode
            if Settings.TRADING_MODE == 'TESTNET':
                self.client = Client(api_key, api_secret, testnet=True)
                self.logger.info("Connected to Binance TESTNET")
            else:
                self.client = Client(api_key, api_secret)
                self.logger.warning("Connected to Binance PRODUCTION - Real money at risk!")

            # Test connection
            self._test_connection()

            # Load symbol precision info
            self._load_symbol_info()

        except Exception as e:
            self.logger.error(f"Failed to initialize Binance client: {e}", exc_info=True)
            raise

    def _load_symbol_info(self):
        """Load symbol precision information from exchange"""
        try:
            exchange_info = self.client.futures_exchange_info()
            for symbol_data in exchange_info['symbols']:
                symbol = symbol_data['symbol']
                self.symbol_info_cache[symbol] = {
                    'quantity_precision': symbol_data['quantityPrecision'],
                    'price_precision': symbol_data['pricePrecision'],
                    'min_qty': None,
                    'step_size': None
                }
                # Get filters
                for f in symbol_data['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        self.symbol_info_cache[symbol]['min_qty'] = float(f['minQty'])
                        self.symbol_info_cache[symbol]['step_size'] = float(f['stepSize'])
                    elif f['filterType'] == 'MIN_NOTIONAL':
                        self.symbol_info_cache[symbol]['min_notional'] = float(f.get('notional', 5))

            self.logger.info(f"Loaded precision info for {len(self.symbol_info_cache)} symbols")
        except Exception as e:
            self.logger.warning(f"Failed to load symbol info: {e}")
            # Set defaults for BTCUSDT
            self.symbol_info_cache['BTCUSDT'] = {
                'quantity_precision': 3,
                'price_precision': 2,
                'min_qty': 0.001,
                'step_size': 0.001
            }

    def format_quantity(self, symbol: str, quantity: float) -> float:
        """
        Format quantity according to symbol precision.

        Args:
            symbol: Trading pair symbol
            quantity: Raw quantity

        Returns:
            Formatted quantity with correct precision
        """
        info = self.symbol_info_cache.get(symbol, {})
        precision = info.get('quantity_precision', 3)
        step_size = info.get('step_size', 0.001)

        # Round to step size
        if step_size:
            quantity = round(quantity / step_size) * step_size

        # Round to precision
        formatted = round(quantity, precision)

        self.logger.debug(f"Formatted quantity: {quantity} -> {formatted} (precision: {precision})")

        return formatted

    def format_price(self, symbol: str, price: float) -> float:
        """
        Format price according to symbol precision.

        Args:
            symbol: Trading pair symbol
            price: Raw price

        Returns:
            Formatted price with correct precision
        """
        info = self.symbol_info_cache.get(symbol, {})
        precision = info.get('price_precision', 2)

        formatted = round(price, precision)
        return formatted

    def _test_connection(self):
        """Test connection to Binance API"""
        try:
            self.client.futures_ping()
            self.logger.info("Binance API connection successful")
        except Exception as e:
            self.logger.error(f"Binance API connection failed: {e}", exc_info=True)
            raise

    @retry_on_exception(
        max_attempts=Settings.RETRY_ATTEMPTS,
        delay=Settings.RETRY_DELAY,
        backoff=Settings.BACKOFF_MULTIPLIER,
        exceptions=(BinanceRequestException, BinanceAPIException)
    )
    def get_balance(self) -> Dict[str, float]:
        """
        Get account balance for futures trading.

        Returns:
            Dict with total balance and available balance

        Raises:
            BinanceAPIException: If API call fails
        """
        try:
            account_info = self.client.futures_account_balance()

            # Find USDT balance
            usdt_balance = next(
                (item for item in account_info if item['asset'] == 'USDT'),
                None
            )

            if usdt_balance:
                balance = float(usdt_balance['balance'])
                available = float(usdt_balance['availableBalance'])

                self.logger.debug(f"Balance: {balance} USDT, Available: {available} USDT")

                return {
                    'total': balance,
                    'available': available
                }
            else:
                self.logger.warning("USDT balance not found")
                return {'total': 0.0, 'available': 0.0}

        except BinanceAPIException as e:
            self.logger.error(f"Failed to get balance: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error getting balance: {e}", exc_info=True)
            raise

    @retry_on_exception(
        max_attempts=Settings.RETRY_ATTEMPTS,
        delay=Settings.RETRY_DELAY,
        backoff=Settings.BACKOFF_MULTIPLIER,
        exceptions=(BinanceRequestException, BinanceAPIException)
    )
    def get_ticker_price(self, symbol: str) -> float:
        """
        Get current ticker price for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')

        Returns:
            Current price

        Raises:
            BinanceAPIException: If API call fails
        """
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])

            self.logger.debug(f"{symbol} price: {price}")

            return price

        except BinanceAPIException as e:
            self.logger.error(f"Failed to get ticker price for {symbol}: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error getting ticker price: {e}", exc_info=True)
            raise

    @retry_on_exception(
        max_attempts=Settings.RETRY_ATTEMPTS,
        delay=Settings.RETRY_DELAY,
        backoff=Settings.BACKOFF_MULTIPLIER,
        exceptions=(BinanceRequestException, BinanceAPIException)
    )
    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500
    ) -> List[List]:
        """
        Get historical candlestick data.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '1h', '4h', '1d')
            limit: Number of candles to retrieve (max 1500)

        Returns:
            List of klines (OHLCV data)

        Raises:
            BinanceAPIException: If API call fails
        """
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )

            self.logger.debug(f"Retrieved {len(klines)} klines for {symbol} ({interval})")

            return klines

        except BinanceAPIException as e:
            self.logger.error(
                f"Failed to get klines for {symbol} ({interval}): {e}",
                exc_info=True
            )
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error getting klines: {e}", exc_info=True)
            raise

    @retry_on_exception(
        max_attempts=Settings.RETRY_ATTEMPTS,
        delay=Settings.RETRY_DELAY,
        backoff=Settings.BACKOFF_MULTIPLIER,
        exceptions=(BinanceRequestException, BinanceAPIException)
    )
    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float
    ) -> Dict[str, Any]:
        """
        Place a market order.

        Args:
            symbol: Trading pair symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity

        Returns:
            Order response from Binance

        Raises:
            BinanceAPIException: If order fails
        """
        try:
            # Format quantity with correct precision
            formatted_qty = self.format_quantity(symbol, quantity)

            self.logger.info(f"Placing {side} market order: {formatted_qty} {symbol}")

            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=formatted_qty
            )

            self.logger.info(f"Order placed successfully: {order['orderId']}")

            return order

        except BinanceAPIException as e:
            self.logger.error(f"Failed to place order: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error placing order: {e}", exc_info=True)
            raise

    @retry_on_exception(
        max_attempts=Settings.RETRY_ATTEMPTS,
        delay=Settings.RETRY_DELAY,
        backoff=Settings.BACKOFF_MULTIPLIER,
        exceptions=(BinanceRequestException, BinanceAPIException)
    )
    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> Dict[str, Any]:
        """
        Place a limit order.

        Args:
            symbol: Trading pair symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Limit price

        Returns:
            Order response from Binance

        Raises:
            BinanceAPIException: If order fails
        """
        try:
            # Format quantity and price with correct precision
            formatted_qty = self.format_quantity(symbol, quantity)
            formatted_price = self.format_price(symbol, price)

            self.logger.info(
                f"Placing {side} limit order: {formatted_qty} {symbol} @ {formatted_price}"
            )

            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                timeInForce='GTC',
                quantity=formatted_qty,
                price=formatted_price
            )

            self.logger.info(f"Limit order placed successfully: {order['orderId']}")

            return order

        except BinanceAPIException as e:
            self.logger.error(f"Failed to place limit order: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error placing limit order: {e}", exc_info=True)
            raise

    @retry_on_exception(
        max_attempts=Settings.RETRY_ATTEMPTS,
        delay=Settings.RETRY_DELAY,
        backoff=Settings.BACKOFF_MULTIPLIER,
        exceptions=(BinanceRequestException, BinanceAPIException)
    )
    def set_leverage(self, symbol: str, leverage: int):
        """
        Set leverage for a symbol.

        Args:
            symbol: Trading pair symbol
            leverage: Leverage value (1-125)

        Raises:
            BinanceAPIException: If setting leverage fails
        """
        try:
            if leverage < 1 or leverage > Settings.MAX_LEVERAGE:
                raise ValueError(
                    f"Leverage must be between 1 and {Settings.MAX_LEVERAGE}"
                )

            response = self.client.futures_change_leverage(
                symbol=symbol,
                leverage=leverage
            )

            self.logger.info(f"Leverage set to {leverage}x for {symbol}")

            return response

        except BinanceAPIException as e:
            self.logger.error(f"Failed to set leverage: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error setting leverage: {e}", exc_info=True)
            raise

    @retry_on_exception(
        max_attempts=Settings.RETRY_ATTEMPTS,
        delay=Settings.RETRY_DELAY,
        backoff=Settings.BACKOFF_MULTIPLIER,
        exceptions=(BinanceRequestException, BinanceAPIException)
    )
    def set_margin_type(self, symbol: str, margin_type: str = 'ISOLATED'):
        """
        Set margin type for a symbol.

        Args:
            symbol: Trading pair symbol
            margin_type: 'ISOLATED' or 'CROSSED'

        Raises:
            BinanceAPIException: If setting margin type fails
        """
        try:
            response = self.client.futures_change_margin_type(
                symbol=symbol,
                marginType=margin_type
            )

            self.logger.info(f"Margin type set to {margin_type} for {symbol}")

            return response

        except BinanceAPIException as e:
            # Margin type already set - not an error
            if e.code == -4046:
                self.logger.debug(f"Margin type already set to {margin_type} for {symbol}")
            else:
                self.logger.error(f"Failed to set margin type: {e}", exc_info=True)
                raise
        except Exception as e:
            self.logger.error(f"Unexpected error setting margin type: {e}", exc_info=True)
            raise

    @retry_on_exception(
        max_attempts=Settings.RETRY_ATTEMPTS,
        delay=Settings.RETRY_DELAY,
        backoff=Settings.BACKOFF_MULTIPLIER,
        exceptions=(BinanceRequestException, BinanceAPIException)
    )
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.

        Returns:
            List of open positions

        Raises:
            BinanceAPIException: If API call fails
        """
        try:
            positions = self.client.futures_position_information()

            # Filter only positions with non-zero amount
            open_positions = [
                pos for pos in positions
                if float(pos['positionAmt']) != 0
            ]

            self.logger.debug(f"Found {len(open_positions)} open positions")

            return open_positions

        except BinanceAPIException as e:
            self.logger.error(f"Failed to get open positions: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error getting open positions: {e}", exc_info=True)
            raise

    @retry_on_exception(
        max_attempts=Settings.RETRY_ATTEMPTS,
        delay=Settings.RETRY_DELAY,
        backoff=Settings.BACKOFF_MULTIPLIER,
        exceptions=(BinanceRequestException, BinanceAPIException)
    )
    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Cancel an open order.

        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel

        Returns:
            Cancellation response

        Raises:
            BinanceAPIException: If cancellation fails
        """
        try:
            self.logger.info(f"Cancelling order {order_id} for {symbol}")

            response = self.client.futures_cancel_order(
                symbol=symbol,
                orderId=order_id
            )

            self.logger.info(f"Order {order_id} cancelled successfully")

            return response

        except BinanceAPIException as e:
            self.logger.error(f"Failed to cancel order: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error cancelling order: {e}", exc_info=True)
            raise
