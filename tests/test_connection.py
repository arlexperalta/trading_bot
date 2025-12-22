"""
Connection and functionality test for the trading bot.
Tests Binance API connection, data retrieval, and indicator calculations.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from src.core.exchange import BinanceConnector
from src.data.market_data import MarketData
from src.utils.logger import get_logger


def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_connection():
    """Test Binance API connection"""
    print_section("Testing Binance Connection")

    try:
        logger = get_logger("test_connection", Settings.LOGS_DIR)
        logger.info("Starting connection test")

        # Initialize exchange
        print("Initializing Binance connector...")
        exchange = BinanceConnector()
        print("✓ Connection successful")

        # Test balance retrieval
        print_section("Testing Balance Retrieval")
        balance = exchange.get_balance()
        print(f"Total Balance:     ${balance['total']:.2f} USDT")
        print(f"Available Balance: ${balance['available']:.2f} USDT")
        print("✓ Balance retrieved successfully")

        # Test ticker price
        print_section("Testing Ticker Price")
        symbol = Settings.TRADING_PAIR
        price = exchange.get_ticker_price(symbol)
        print(f"{symbol} Current Price: ${price:,.2f}")
        print("✓ Ticker price retrieved successfully")

        # Test historical data
        print_section("Testing Historical Data Retrieval")
        print(f"Fetching last 100 candles for {symbol} ({Settings.TIMEFRAME})...")
        klines = exchange.get_historical_klines(
            symbol=symbol,
            interval=Settings.TIMEFRAME,
            limit=100
        )
        print(f"✓ Retrieved {len(klines)} candles")

        # Test market data processing
        print_section("Testing Market Data Processing")
        market_data = MarketData(exchange)

        print("Converting klines to DataFrame...")
        df = market_data.get_klines_dataframe(symbol, Settings.TIMEFRAME, 100)
        print(f"✓ DataFrame created with {len(df)} rows")

        print("\nDataFrame columns:", list(df.columns))
        print("\nLast 5 candles:")
        print(df[['open', 'high', 'low', 'close', 'volume']].tail())

        # Test indicator calculations
        print_section("Testing Technical Indicators")

        print("Calculating EMAs...")
        df = market_data.add_all_indicators(df)
        print("✓ Indicators calculated successfully")

        print("\nAvailable indicators:")
        indicator_cols = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
        for col in indicator_cols:
            print(f"  - {col}")

        # Display latest indicator values
        latest = df.iloc[-1]
        print(f"\nLatest indicator values:")
        print(f"  Close Price:    ${latest['close']:.2f}")
        print(f"  EMA({Settings.EMA_FAST_PERIOD}):         ${latest['ema_fast']:.2f}")
        print(f"  EMA({Settings.EMA_SLOW_PERIOD}):        ${latest['ema_slow']:.2f}")
        print(f"  ATR(14):        ${latest['atr']:.2f}")
        print(f"  RSI(14):        {latest['rsi']:.2f}")
        print(f"  Volume:         {latest['volume']:,.2f}")
        print(f"  Volume Avg:     {latest['volume_avg']:,.2f}")

        # Check for EMA crossover
        print_section("Testing EMA Crossover Detection")
        crossover = market_data.detect_ema_crossover(df)
        if crossover:
            print(f"✓ EMA Crossover detected: {crossover}")
        else:
            print("○ No EMA crossover at this time")

        # Test position manager
        print_section("Testing Position Manager")
        from src.risk.position_manager import PositionManager

        pm = PositionManager()
        print("Calculating position size...")

        entry_price = latest['close']
        stop_loss = pm.calculate_stop_loss(entry_price, 'LONG')

        position_size = pm.calculate_position_size(
            capital=balance['available'],
            entry_price=entry_price,
            stop_loss_price=stop_loss,
            leverage=Settings.MAX_LEVERAGE
        )

        take_profit = pm.calculate_take_profit(entry_price, 'LONG')

        print(f"\nPosition sizing for LONG trade:")
        print(f"  Capital:        ${balance['available']:.2f}")
        print(f"  Entry Price:    ${entry_price:.2f}")
        print(f"  Stop Loss:      ${stop_loss:.2f} ({Settings.STOP_LOSS_PERCENT * 100}%)")
        print(f"  Take Profit:    ${take_profit:.2f} ({Settings.TAKE_PROFIT_PERCENT * 100}%)")
        print(f"  Position Size:  {position_size:.6f} {symbol.replace('USDT', '')}")
        print(f"  Leverage:       {Settings.MAX_LEVERAGE}x")
        print(f"  Risk Amount:    ${balance['available'] * Settings.RISK_PER_TRADE:.2f}")

        rr_ratio = pm.calculate_risk_reward_ratio(entry_price, stop_loss, take_profit)
        print(f"  Risk/Reward:    1:{rr_ratio:.2f}")
        print("✓ Position calculations successful")

        # Summary
        print_section("Test Summary")
        print("✓ All tests passed successfully!")
        print("\nYour bot is ready to trade.")
        print(f"Mode: {Settings.TRADING_MODE}")
        print(f"Symbol: {Settings.TRADING_PAIR}")
        print(f"Strategy: EMA Crossover ({Settings.EMA_FAST_PERIOD}/{Settings.EMA_SLOW_PERIOD})")

        if Settings.TRADING_MODE == 'TESTNET':
            print("\n*** Remember: You are in TESTNET mode ***")
            print("Use test funds to verify strategy before going live!")
        else:
            print("\n!!! WARNING: You are in PRODUCTION mode !!!")
            print("Real money is at risk. Ensure you have tested thoroughly.")

        print("\nTo start the bot, run: python main.py")
        print("=" * 70 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nPlease check:")
        print("1. Your .env file has valid API credentials")
        print("2. You are using the correct API keys (testnet or production)")
        print("3. Your internet connection is stable")
        print("4. Binance API is accessible from your location")
        print("\nCheck logs/errors.log for details\n")

        import traceback
        traceback.print_exc()

        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
