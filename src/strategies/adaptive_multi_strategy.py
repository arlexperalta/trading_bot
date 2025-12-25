"""
Adaptive Multi-Strategy Trading System.

Automatically switches between different trading strategies based on market conditions.

Market Regimes:
1. TRENDING UP: Aggressive long bias, wider stops
2. TRENDING DOWN: Aggressive short bias, wider stops  
3. RANGING: Mean reversion, tight stops
4. HIGH VOLATILITY: Reduced positions, wider stops
5. LOW VOLATILITY: Larger positions, tighter stops

Strategy Selection:
- Analyzes last 100 candles for trend and volatility
- Calculates ADX (trend strength)
- Measures ATR (volatility)
- Adjusts parameters dynamically
- Re-evaluates every hour

Dynamic Parameters:
- Leverage: 2x-10x based on confidence
- Position size: 0.5%-5% based on volatility
- Stop loss: 0.5%-3% based on volatility
- Take profit: 1.5%-9% based on trend strength
- EMA periods: Faster in trends, slower in ranges
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from datetime import datetime, timedelta

from config.settings import Settings
from src.strategies.base_strategy import BaseStrategy


class MarketRegime(Enum):
    """Market regime classification"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNCERTAIN = "uncertain"


class AdaptiveStrategy(BaseStrategy):
    """
    Adaptive Multi-Strategy that adjusts to market conditions.
    
    Combines multiple strategies and adjusts parameters dynamically.
    """

    def __init__(self):
        """Initialize Adaptive Strategy"""
        super().__init__("Adaptive_Multi_Strategy")

        # Analysis periods
        self.trend_analysis_period = 100  # Candles to analyze
        self.volatility_analysis_period = 50
        self.regime_update_interval = 3600  # 1 hour in seconds
        self.last_regime_update = datetime.now()
        
        # Current market regime
        self.current_regime = MarketRegime.UNCERTAIN
        self.regime_confidence = 0.0  # 0-1 scale
        
        # Dynamic parameters (will be updated by regime)
        self.current_leverage = 3
        self.current_stop_loss_percent = 0.01
        self.current_take_profit_percent = 0.03
        self.current_ema_fast = 9
        self.current_ema_slow = 21
        self.current_position_size_percent = 0.02
        
        # Regime-specific configurations
        self.regime_configs = {
            MarketRegime.TRENDING_UP: {
                'leverage': 8,
                'stop_loss': 0.015,
                'take_profit': 0.06,
                'ema_fast': 5,
                'ema_slow': 13,
                'position_size': 0.03,
                'entry_bias': 'LONG',
                'aggressiveness': 0.8
            },
            MarketRegime.TRENDING_DOWN: {
                'leverage': 8,
                'stop_loss': 0.015,
                'take_profit': 0.06,
                'ema_fast': 5,
                'ema_slow': 13,
                'position_size': 0.03,
                'entry_bias': 'SHORT',
                'aggressiveness': 0.8
            },
            MarketRegime.RANGING: {
                'leverage': 3,
                'stop_loss': 0.008,
                'take_profit': 0.02,
                'ema_fast': 13,
                'ema_slow': 34,
                'position_size': 0.02,
                'entry_bias': 'NEUTRAL',
                'aggressiveness': 0.5
            },
            MarketRegime.HIGH_VOLATILITY: {
                'leverage': 2,
                'stop_loss': 0.025,
                'take_profit': 0.08,
                'ema_fast': 9,
                'ema_slow': 21,
                'position_size': 0.01,
                'entry_bias': 'NEUTRAL',
                'aggressiveness': 0.3
            },
            MarketRegime.LOW_VOLATILITY: {
                'leverage': 10,
                'stop_loss': 0.005,
                'take_profit': 0.015,
                'ema_fast': 7,
                'ema_slow': 17,
                'position_size': 0.04,
                'entry_bias': 'NEUTRAL',
                'aggressiveness': 0.9
            }
        }
        
        # Statistics
        self.regime_history = []
        self.trades_by_regime = {regime: {'wins': 0, 'losses': 0} for regime in MarketRegime}
        
        self.logger.info(f"Initialized {self.name} strategy")
        self.logger.info("Strategy adapts to: Trend, Volatility, Market conditions")

    def analyze_market_regime(self, df: pd.DataFrame) -> Tuple[MarketRegime, float]:
        """
        Analyze current market regime.
        
        Args:
            df: DataFrame with market data and indicators
            
        Returns:
            Tuple of (regime, confidence)
        """
        if len(df) < self.trend_analysis_period:
            return MarketRegime.UNCERTAIN, 0.0

        # Get recent data
        recent_df = df.tail(self.trend_analysis_period)
        
        # Calculate trend indicators
        price_change = (recent_df['close'].iloc[-1] - recent_df['close'].iloc[0]) / recent_df['close'].iloc[0]
        price_change_percent = price_change * 100
        
        # Calculate ADX (Average Directional Index) for trend strength
        adx = self.calculate_adx(recent_df)
        
        # Calculate ATR for volatility
        if 'atr' in recent_df.columns and not pd.isna(recent_df['atr'].iloc[-1]):
            current_atr = recent_df['atr'].iloc[-1]
            avg_atr = recent_df['atr'].mean()
            atr_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0
        else:
            atr_ratio = 1.0
        
        # Classify regime
        regime = MarketRegime.UNCERTAIN
        confidence = 0.0
        
        # Check for trending markets (ADX > 25)
        if adx > 25:
            if price_change_percent > 5:  # Strong uptrend
                regime = MarketRegime.TRENDING_UP
                confidence = min(adx / 50, 1.0)  # Higher ADX = higher confidence
            elif price_change_percent < -5:  # Strong downtrend
                regime = MarketRegime.TRENDING_DOWN
                confidence = min(adx / 50, 1.0)
            else:  # Weak trend
                regime = MarketRegime.RANGING
                confidence = 0.5
        
        # Check for ranging markets (ADX < 20)
        elif adx < 20:
            regime = MarketRegime.RANGING
            confidence = (20 - adx) / 20  # Lower ADX = higher confidence in ranging
        
        # Volatility overrides
        if atr_ratio > 1.5:  # High volatility
            regime = MarketRegime.HIGH_VOLATILITY
            confidence = min(atr_ratio / 2, 1.0)
        elif atr_ratio < 0.5:  # Low volatility
            regime = MarketRegime.LOW_VOLATILITY
            confidence = 1.0 - atr_ratio
        
        self.logger.info(
            f"📊 Market Regime: {regime.value.upper()} "
            f"(Confidence: {confidence:.1%}, ADX: {adx:.1f}, "
            f"Price Δ: {price_change_percent:+.2f}%, ATR ratio: {atr_ratio:.2f})"
        )
        
        return regime, confidence

    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average Directional Index (trend strength).
        
        Args:
            df: DataFrame with OHLC data
            period: ADX period
            
        Returns:
            ADX value (0-100)
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
            atr = tr.rolling(window=period).mean()
            
            # Calculate Directional Movement
            up_move = high - high.shift()
            down_move = low.shift() - low
            
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            
            plus_dm_series = pd.Series(plus_dm, index=df.index)
            minus_dm_series = pd.Series(minus_dm, index=df.index)
            
            plus_di = 100 * (plus_dm_series.rolling(window=period).mean() / atr)
            minus_di = 100 * (minus_dm_series.rolling(window=period).mean() / atr)
            
            # Calculate ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=period).mean()
            
            return adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 25.0
            
        except Exception as e:
            self.logger.warning(f"ADX calculation error: {e}")
            return 25.0  # Default neutral value

    def update_regime_parameters(self, regime: MarketRegime, confidence: float):
        """
        Update strategy parameters based on current regime.
        
        Args:
            regime: Current market regime
            confidence: Confidence level (0-1)
        """
        if regime == MarketRegime.UNCERTAIN:
            return
        
        config = self.regime_configs.get(regime, {})
        
        # Update parameters with confidence weighting
        self.current_leverage = int(config['leverage'] * confidence + 3 * (1 - confidence))
        self.current_stop_loss_percent = config['stop_loss']
        self.current_take_profit_percent = config['take_profit']
        self.current_ema_fast = config['ema_fast']
        self.current_ema_slow = config['ema_slow']
        self.current_position_size_percent = config['position_size'] * confidence
        
        # Clamp values to safe ranges
        self.current_leverage = max(2, min(10, self.current_leverage))
        self.current_stop_loss_percent = max(0.005, min(0.03, self.current_stop_loss_percent))
        self.current_take_profit_percent = max(0.015, min(0.1, self.current_take_profit_percent))
        
        self.logger.info(
            f"⚙️ Adapted Parameters: Leverage={self.current_leverage}x, "
            f"SL={self.current_stop_loss_percent*100:.2f}%, "
            f"TP={self.current_take_profit_percent*100:.2f}%, "
            f"EMA={self.current_ema_fast}/{self.current_ema_slow}"
        )

    def should_update_regime(self) -> bool:
        """Check if it's time to update regime analysis"""
        time_since_update = (datetime.now() - self.last_regime_update).total_seconds()
        return time_since_update >= self.regime_update_interval

    def should_enter(self, df: pd.DataFrame, current_price: float) -> Optional[str]:
        """
        Determine entry based on adaptive strategy.
        
        Args:
            df: DataFrame with market data
            current_price: Current price

        Returns:
            'LONG', 'SHORT', or None
        """
        # Update regime if needed
        if self.should_update_regime():
            regime, confidence = self.analyze_market_regime(df)
            self.current_regime = regime
            self.regime_confidence = confidence
            self.update_regime_parameters(regime, confidence)
            self.last_regime_update = datetime.now()
            
            # Log regime change
            self.regime_history.append({
                'timestamp': datetime.now(),
                'regime': regime.value,
                'confidence': confidence
            })

        # Validate data
        if not self.validate_signal(df):
            return None

        if len(df) < 3:
            return None

        # Get current and previous data
        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Check for required indicators
        required_cols = ['ema_fast', 'ema_slow', 'volume', 'volume_avg']
        if not all(col in df.columns for col in required_cols):
            return None

        if pd.isna([current['ema_fast'], current['ema_slow'],
                   current['volume'], current['volume_avg']]).any():
            return None

        # Get regime configuration
        config = self.regime_configs.get(self.current_regime, {})
        entry_bias = config.get('entry_bias', 'NEUTRAL')
        aggressiveness = config.get('aggressiveness', 0.5)

        # Volume confirmation (adjusted by aggressiveness)
        volume_threshold = 1.0 - (aggressiveness * 0.3)  # More aggressive = lower threshold
        volume_confirmed = current['volume'] > (current['volume_avg'] * volume_threshold)

        # EMA crossover detection
        bullish_cross = (
            previous['ema_fast'] <= previous['ema_slow'] and
            current['ema_fast'] > current['ema_slow']
        )
        
        bearish_cross = (
            previous['ema_fast'] >= previous['ema_slow'] and
            current['ema_fast'] < current['ema_slow']
        )

        # EMA momentum (for aggressive entries)
        ema_spread = abs(current['ema_fast'] - current['ema_slow']) / current['ema_slow'] * 100
        strong_momentum = ema_spread > (0.1 * aggressiveness)

        # Generate signals based on regime bias
        if entry_bias in ['LONG', 'NEUTRAL']:
            if (bullish_cross or (strong_momentum and current['ema_fast'] > current['ema_slow'])) and volume_confirmed:
                self.log_signal(
                    "LONG SIGNAL (ADAPTIVE)",
                    f"Regime: {self.current_regime.value}, Confidence: {self.regime_confidence:.1%}"
                )
                return 'LONG'

        if entry_bias in ['SHORT', 'NEUTRAL']:
            if (bearish_cross or (strong_momentum and current['ema_fast'] < current['ema_slow'])) and volume_confirmed:
                self.log_signal(
                    "SHORT SIGNAL (ADAPTIVE)",
                    f"Regime: {self.current_regime.value}, Confidence: {self.regime_confidence:.1%}"
                )
                return 'SHORT'

        return None

    def should_exit(
        self,
        df: pd.DataFrame,
        current_price: float,
        position: Dict[str, Any]
    ) -> bool:
        """
        Adaptive exit logic.
        
        Args:
            df: DataFrame with market data
            current_price: Current price
            position: Position info

        Returns:
            True if should exit
        """
        if not self.has_position():
            return False

        entry_price = position.get('entry_price')
        side = position.get('side')
        stop_loss = position.get('stop_loss')
        take_profit = position.get('take_profit')

        if not all([entry_price, side, stop_loss, take_profit]):
            return False

        # Check stop loss
        if side == 'LONG' and current_price <= stop_loss:
            self.log_signal("EXIT (STOP LOSS)", f"Regime: {self.current_regime.value}")
            self.record_trade_result(side, False)
            return True

        if side == 'SHORT' and current_price >= stop_loss:
            self.log_signal("EXIT (STOP LOSS)", f"Regime: {self.current_regime.value}")
            self.record_trade_result(side, False)
            return True

        # Check take profit
        if side == 'LONG' and current_price >= take_profit:
            self.log_signal("EXIT (TAKE PROFIT)", f"Regime: {self.current_regime.value}")
            self.record_trade_result(side, True)
            return True

        if side == 'SHORT' and current_price <= take_profit:
            self.log_signal("EXIT (TAKE PROFIT)", f"Regime: {self.current_regime.value}")
            self.record_trade_result(side, True)
            return True

        # Adaptive exit: regime changed significantly
        if self.regime_confidence > 0.7:
            config = self.regime_configs.get(self.current_regime, {})
            entry_bias = config.get('entry_bias', 'NEUTRAL')
            
            # Exit long if regime shifted to short bias
            if side == 'LONG' and entry_bias == 'SHORT':
                self.log_signal("EXIT (REGIME SHIFT)", "Shifted to bearish regime")
                return True
            
            # Exit short if regime shifted to long bias
            if side == 'SHORT' and entry_bias == 'LONG':
                self.log_signal("EXIT (REGIME SHIFT)", "Shifted to bullish regime")
                return True

        return False

    def record_trade_result(self, side: str, won: bool):
        """Record trade result by regime"""
        if won:
            self.trades_by_regime[self.current_regime]['wins'] += 1
        else:
            self.trades_by_regime[self.current_regime]['losses'] += 1

    def get_stop_loss(self, entry_price: float, side: str) -> float:
        """Calculate stop loss using current regime parameters"""
        stop_distance = entry_price * self.current_stop_loss_percent

        if side == 'LONG':
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance

    def get_take_profit(self, entry_price: float, side: str) -> float:
        """Calculate take profit using current regime parameters"""
        profit_distance = entry_price * self.current_take_profit_percent

        if side == 'LONG':
            return entry_price + profit_distance
        else:
            return entry_price - profit_distance

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get comprehensive strategy info"""
        # Calculate win rates by regime
        regime_stats = {}
        for regime, results in self.trades_by_regime.items():
            total = results['wins'] + results['losses']
            win_rate = (results['wins'] / total * 100) if total > 0 else 0
            regime_stats[regime.value] = {
                'trades': total,
                'win_rate': win_rate,
                'wins': results['wins'],
                'losses': results['losses']
            }

        return {
            'name': self.name,
            'current_regime': self.current_regime.value,
            'regime_confidence': f"{self.regime_confidence:.1%}",
            'current_parameters': {
                'leverage': self.current_leverage,
                'stop_loss': f"{self.current_stop_loss_percent*100:.2f}%",
                'take_profit': f"{self.current_take_profit_percent*100:.2f}%",
                'ema_fast': self.current_ema_fast,
                'ema_slow': self.current_ema_slow,
                'position_size': f"{self.current_position_size_percent*100:.2f}%"
            },
            'regime_history_count': len(self.regime_history),
            'performance_by_regime': regime_stats,
            'last_regime_update': self.last_regime_update.strftime('%Y-%m-%d %H:%M:%S')
        }
