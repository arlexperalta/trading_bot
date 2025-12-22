# Crypto Trading Bot - Binance Futures

A conservative, modular, and secure automated trading system for Binance Futures built with Python. Designed for safe trading with proper risk management and scalable architecture.

## Features

- **Conservative Risk Management**: Maximum 2x leverage, 1% risk per trade, 5% daily loss limit
- **EMA Crossover Strategy**: Simple and effective EMA 9/21 crossover with volume confirmation
- **Modular Architecture**: Easy to add new strategies and features
- **Comprehensive Logging**: Detailed logging system with rotation and colored console output
- **Testnet Support**: Full testnet support for safe strategy testing
- **Error Handling**: Robust error handling with automatic retry logic
- **Position Management**: Automated stop-loss and take-profit orders

## Project Structure

```
crypto-trading-bot/
├── config/
│   ├── __init__.py
│   ├── settings.py         # Configuration management
│   └── .env.example        # Environment template
├── src/
│   ├── core/
│   │   ├── exchange.py     # Binance API connector
│   │   └── trader.py       # Main trading logic
│   ├── strategies/
│   │   ├── base_strategy.py    # Abstract strategy class
│   │   └── ema_crossover.py    # EMA crossover strategy
│   ├── risk/
│   │   └── position_manager.py # Risk management
│   ├── data/
│   │   └── market_data.py      # Market data processing
│   └── utils/
│       ├── logger.py           # Logging system
│       └── helpers.py          # Utility functions
├── logs/                   # Log files (auto-generated)
├── tests/
│   └── test_connection.py  # Connection tests
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── .gitignore
└── README.md
```

## Installation

### 1. Prerequisites

- Python 3.8 or higher
- Binance Futures account (for testnet or production)
- API keys from Binance

### 2. Clone/Download the Project

```bash
cd crypto-trading-bot
```

### 3. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: TA-Lib installation may require additional steps:

**Windows:**
```bash
# Download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
pip install TA_Lib‑0.4.28‑cp3X‑cp3Xm‑win_amd64.whl
```

**Linux:**
```bash
# Install TA-Lib C library first
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install

# Then install Python wrapper
pip install TA-Lib
```

**Mac:**
```bash
brew install ta-lib
pip install TA-Lib
```

### 5. Configure Environment Variables

```bash
# Copy the example file
cp config/.env.example config/.env

# Edit config/.env with your API credentials
```

**For Testnet (Recommended for testing):**

1. Get testnet API keys from: https://testnet.binancefuture.com
2. Update `config/.env`:

```env
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_API_SECRET=your_testnet_secret
TRADING_MODE=TESTNET
```

**For Production (Use with caution):**

```env
BINANCE_API_KEY=your_production_api_key
BINANCE_API_SECRET=your_production_secret
TRADING_MODE=PRODUCTION
```

## Configuration

Edit `config/.env` to customize trading parameters:

```env
# Trading Configuration
INITIAL_CAPITAL=100          # Starting capital
MAX_LEVERAGE=2               # Maximum leverage (1-125)
RISK_PER_TRADE=0.01         # Risk per trade (1% = 0.01)
TRADING_PAIR=BTCUSDT        # Trading pair

# Strategy Parameters (configured in settings.py)
# EMA_FAST_PERIOD=9
# EMA_SLOW_PERIOD=21
# TIMEFRAME=4h
# STOP_LOSS_PERCENT=0.02    # 2%
# TAKE_PROFIT_PERCENT=0.06  # 6%
```

## Usage

### 1. Test Connection

Before running the bot, test your connection and configuration:

```bash
python tests/test_connection.py
```

This will verify:
- API connection to Binance
- Balance retrieval
- Market data fetching
- Indicator calculations
- Position sizing logic

### 2. Run the Bot

```bash
python main.py
```

The bot will:
1. Connect to Binance (testnet or production)
2. Set up margin type (ISOLATED) and leverage
3. Enter a continuous loop that:
   - Fetches market data every 5 minutes
   - Calculates technical indicators
   - Evaluates trading strategy
   - Executes trades if conditions are met
   - Logs all activity

### 3. Monitor Logs

Logs are stored in the `logs/` directory:

- `trading.log` - General trading activity (INFO level)
- `errors.log` - Errors and warnings
- `debug.log` - Detailed debug information
- `trades.log` - Trade execution records

### 4. Stop the Bot

Press `Ctrl+C` to gracefully shut down the bot.

## Strategy Details

### EMA Crossover Strategy

**Entry Conditions:**
- **LONG**: EMA(9) crosses above EMA(21) AND current volume > 20-period average volume
- **SHORT**: EMA(9) crosses below EMA(21) AND current volume > 20-period average volume

**Exit Conditions:**
- Stop Loss: 2% from entry price
- Take Profit: 6% from entry price (1:3 risk-reward ratio)
- Opposite crossover signal

**Risk Management:**
- Maximum 1 open position at a time
- Position sized to risk 1% of capital per trade
- Maximum leverage: 2x
- Daily loss limit: 5% of capital

**Timeframe:**
- 4-hour candles (reduces noise and false signals)

## Risk Management

The bot implements multiple layers of risk protection:

1. **Position Sizing**: Fixed Fractional method (1% risk per trade)
2. **Leverage Limit**: Maximum 2x leverage (configurable)
3. **Stop Loss**: Automatic 2% stop loss on every trade
4. **Daily Loss Limit**: Stops trading if 5% daily loss is reached
5. **Isolated Margin**: Each position uses isolated margin (safer than cross)
6. **Single Position**: Only one position open at a time

## Safety Features

- **Testnet First**: Always test on testnet before production
- **API Key Security**: Keys stored in `.env` file (not committed to git)
- **Retry Logic**: Automatic retry with exponential backoff for API calls
- **Rate Limiting**: Prevents API rate limit bans
- **Graceful Shutdown**: Proper cleanup on exit (Ctrl+C)
- **Error Logging**: All errors logged with full stack traces

## Extending the Bot

### Adding a New Strategy

1. Create a new file in `src/strategies/`:

```python
from src.strategies.base_strategy import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("MyStrategy")

    def should_enter(self, df: pd.DataFrame, current_price: float):
        # Your entry logic
        return 'LONG' or 'SHORT' or None

    def should_exit(self, df, current_price, position):
        # Your exit logic
        return True or False

    def get_stop_loss(self, entry_price: float, side: str):
        # Your stop loss calculation
        return stop_loss_price

    def get_take_profit(self, entry_price: float, side: str):
        # Your take profit calculation
        return take_profit_price
```

2. Update `main.py`:

```python
from src.strategies.my_strategy import MyStrategy

# In main()
strategy = MyStrategy()
trader = Trader(strategy)
```

### Adding Technical Indicators

Add new indicators in `src/data/market_data.py`:

```python
def calculate_my_indicator(self, df: pd.DataFrame) -> pd.Series:
    # Your indicator calculation
    return indicator_values
```

## Troubleshooting

### Common Issues

**1. TA-Lib Installation Failed**
- See installation section for OS-specific instructions
- Try installing from binary wheel (Windows)

**2. API Connection Failed**
- Verify API keys are correct
- Check if using testnet keys with TESTNET mode
- Ensure API keys have futures trading permissions
- Check internet connection and firewall

**3. "Insufficient Balance" Error**
- Transfer funds to Futures wallet
- Check minimum order size for the trading pair
- Reduce position size in configuration

**4. "Leverage Not Supported" Error**
- Some pairs have maximum leverage limits
- Reduce MAX_LEVERAGE in settings

## Logs and Monitoring

### Log Files

Check logs regularly:

```bash
# View recent trading activity
tail -f logs/trading.log

# Check for errors
tail -f logs/errors.log

# View trade executions
cat logs/trades.log
```

### What to Monitor

- **Daily P/L**: Track profitability
- **Win Rate**: Percentage of winning trades
- **Execution Quality**: Verify trades execute at expected prices
- **API Errors**: Watch for connection issues

## Future Enhancements (Fase 2+)

Planned features for future versions:

- [ ] Backtesting framework
- [ ] Machine learning integration (XGBoost)
- [ ] Multi-timeframe analysis
- [ ] Telegram notifications
- [ ] Web dashboard
- [ ] Multiple strategy portfolio
- [ ] Advanced order types
- [ ] Paper trading mode

## Security Warning

**IMPORTANT SECURITY NOTES:**

1. **Never commit `.env` file** - Contains sensitive API keys
2. **Use API restrictions** - Limit API keys to specific IPs if possible
3. **Enable withdrawal whitelist** - Disable withdrawals from API keys
4. **Start with testnet** - Always test thoroughly before using real funds
5. **Use ISOLATED margin** - Protects other funds if position liquidates
6. **Monitor actively** - Especially in the beginning

## Disclaimer

**USE AT YOUR OWN RISK**

This bot is for educational purposes. Cryptocurrency trading carries substantial risk of loss. The authors are not responsible for any financial losses incurred through the use of this software.

- Never invest more than you can afford to lose
- Past performance does not guarantee future results
- Always test strategies thoroughly on testnet first
- Market conditions can change rapidly
- Bugs in code can lead to losses

## Support

For issues and questions:

1. Check the logs in `logs/` directory
2. Review this README thoroughly
3. Test with `test_connection.py`
4. Verify configuration in `config/.env`

## License

This project is provided as-is for educational purposes.

## Acknowledgments

- Binance for providing the API
- python-binance library
- TA-Lib for technical analysis

---

**Happy Trading! Remember: Test on TESTNET first!**
