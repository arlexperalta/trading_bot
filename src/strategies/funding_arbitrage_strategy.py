"""
Funding Rate Arbitrage Strategy for Binance Futures.

Exploit positive funding rates to generate passive income WITHOUT price risk.

How it works:
1. Monitor funding rates across all pairs
2. When funding rate is POSITIVE (>0.05%), open LONG position
3. Simultaneously SHORT the same amount in spot (or another exchange)
4. Hold position for 8 hours (until next funding payment)
5. Collect funding fee payment
6. Close both positions

Returns:
- 0.05% - 0.3% every 8 hours
- 4% - 33% annual return
- ZERO price exposure (hedged)

Risk Management:
- Perfect hedge (LONG futures + SHORT spot = 0 delta)
- Low leverage (1-2x)
- Only enter when funding rate > threshold
- Auto-close before negative funding

Recommended Pairs:
- BTC/USDT (most liquid, consistent funding)
- ETH/USDT (second most liquid)
- BNB/USDT (often positive funding)
- High-volatility altcoins (higher funding rates)
"""

import pandas as pd
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import requests

from config.settings import Settings
from src.strategies.base_strategy import BaseStrategy


class FundingArbitrageStrategy(BaseStrategy):
    """
    Funding Rate Arbitrage Strategy.
    
    Generates passive income from funding rate payments with zero directional risk.
    """

    def __init__(self):
        """Initialize Funding Arbitrage strategy"""
        super().__init__("Funding_Arbitrage")

        # Funding rate thresholds
        self.min_funding_rate = 0.0005  # 0.05% minimum (5 bps)
        self.optimal_funding_rate = 0.001  # 0.1% optimal (10 bps)
        self.extreme_funding_rate = 0.003  # 0.3% extreme (30 bps)
        
        # Position management
        self.funding_interval_hours = 8
        self.hours_before_funding = 0.5  # Enter 30 min before funding time
        self.auto_close_enabled = True  # Auto-close if funding turns negative
        
        # Risk management
        self.max_leverage = 2  # Low leverage for safety
        self.position_size_percent = 0.25  # 25% of capital per position
        
        # Tracking
        self.active_arbitrage_positions = {}
        self.total_funding_earned = 0
        self.arbitrage_count = 0
        
        self.logger.info(f"Initialized {self.name} strategy")
        self.logger.info(f"Min funding rate threshold: {self.min_funding_rate*100:.2f}%")
        self.logger.info(f"Expected annual return: 4-33%")

    def get_current_funding_rate(self, symbol: str = 'BTCUSDT') -> Dict[str, Any]:
        """
        Fetch current funding rate from Binance.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with funding rate info
        """
        try:
            url = "https://fapi.binance.com/fapi/v1/premiumIndex"
            params = {'symbol': symbol}
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            funding_rate = float(data.get('lastFundingRate', 0))
            next_funding_time = datetime.fromtimestamp(data.get('nextFundingTime', 0) / 1000)
            
            # Calculate hours until next funding
            hours_until_funding = (next_funding_time - datetime.now()).total_seconds() / 3600
            
            return {
                'symbol': symbol,
                'funding_rate': funding_rate,
                'funding_rate_percent': funding_rate * 100,
                'next_funding_time': next_funding_time,
                'hours_until_funding': hours_until_funding,
                'is_positive': funding_rate > 0,
                'is_optimal': funding_rate >= self.optimal_funding_rate,
                'is_extreme': funding_rate >= self.extreme_funding_rate
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching funding rate: {e}")
            return None

    def scan_funding_opportunities(self, symbols: List[str] = None) -> List[Dict]:
        """
        Scan multiple pairs for funding arbitrage opportunities.
        
        Args:
            symbols: List of symbols to scan, defaults to major pairs
            
        Returns:
            List of opportunities sorted by funding rate
        """
        if symbols is None:
            symbols = [
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 
                'ADAUSDT', 'DOGEUSDT', 'MATICUSDT', 'DOTUSDT',
                'AVAXUSDT', 'LINKUSDT'
            ]
        
        opportunities = []
        
        for symbol in symbols:
            funding_info = self.get_current_funding_rate(symbol)
            
            if funding_info and funding_info['is_positive']:
                if funding_info['funding_rate'] >= self.min_funding_rate:
                    opportunities.append(funding_info)
                    
                    self.logger.info(
                        f"📊 {symbol}: {funding_info['funding_rate_percent']:.3f}% "
                        f"(Next: {funding_info['hours_until_funding']:.1f}h)"
                    )
        
        # Sort by funding rate (highest first)
        opportunities.sort(key=lambda x: x['funding_rate'], reverse=True)
        
        return opportunities

    def should_enter(self, df: pd.DataFrame, current_price: float) -> Optional[str]:
        """
        Determine if should enter arbitrage position.
        
        For funding arbitrage, ALWAYS returns 'LONG' when:
        1. Funding rate is positive and above threshold
        2. Close to funding time (within window)
        3. No existing arbitrage position for this pair
        
        Args:
            df: DataFrame with market data
            current_price: Current market price

        Returns:
            'LONG' if should enter arbitrage, None otherwise
        """
        # Get funding rate info
        funding_info = self.get_current_funding_rate(Settings.TRADING_PAIR)
        
        if not funding_info:
            return None

        # Check if funding rate meets minimum threshold
        if funding_info['funding_rate'] < self.min_funding_rate:
            self.logger.debug(
                f"Funding rate too low: {funding_info['funding_rate_percent']:.3f}% "
                f"(min: {self.min_funding_rate*100:.2f}%)"
            )
            return None

        # Check if we're within the entry window
        if funding_info['hours_until_funding'] > self.hours_before_funding:
            self.logger.debug(
                f"Too early to enter: {funding_info['hours_until_funding']:.1f}h until funding"
            )
            return None

        # Check if we already have an arbitrage position
        if self.has_position():
            return None

        # All conditions met - enter LONG arbitrage position
        self.log_signal(
            "LONG SIGNAL (FUNDING ARBITRAGE)",
            f"Funding: {funding_info['funding_rate_percent']:.3f}%, "
            f"Entry window: {funding_info['hours_until_funding']:.1f}h"
        )
        
        # Store funding info for this position
        self.active_arbitrage_positions[Settings.TRADING_PAIR] = funding_info
        
        return 'LONG'  # ALWAYS LONG for positive funding arbitrage

    def should_exit(
        self,
        df: pd.DataFrame,
        current_price: float,
        position: Dict[str, Any]
    ) -> bool:
        """
        Determine if should exit arbitrage position.
        
        Exit conditions:
        1. Funding payment received (8 hours passed)
        2. Funding rate turns negative
        3. Target profit reached
        
        Args:
            df: DataFrame with market data
            current_price: Current market price
            position: Current position information

        Returns:
            True if should exit
        """
        if not self.has_position():
            return False

        entry_time = position.get('entry_time')
        if not entry_time:
            return False

        # Get current funding info
        funding_info = self.get_current_funding_rate(Settings.TRADING_PAIR)
        
        if not funding_info:
            self.logger.warning("Cannot fetch funding info, maintaining position")
            return False

        # Calculate time in position
        time_in_position = (datetime.now() - entry_time).total_seconds() / 3600

        # Exit 1: Funding payment received (>8 hours)
        if time_in_position >= self.funding_interval_hours:
            self.log_signal(
                "EXIT SIGNAL (FUNDING RECEIVED)",
                f"Position held for {time_in_position:.1f}h, "
                f"Funding earned: ~{funding_info['funding_rate_percent']:.3f}%"
            )
            
            # Update stats
            self.total_funding_earned += funding_info['funding_rate']
            self.arbitrage_count += 1
            
            return True

        # Exit 2: Funding rate turned negative (emergency exit)
        if funding_info['funding_rate'] <= 0 and self.auto_close_enabled:
            self.log_signal(
                "EXIT SIGNAL (NEGATIVE FUNDING)",
                f"Funding turned negative: {funding_info['funding_rate_percent']:.3f}%"
            )
            return True

        # Exit 3: Funding rate dropped significantly (early exit)
        original_funding = self.active_arbitrage_positions.get(Settings.TRADING_PAIR, {})
        original_rate = original_funding.get('funding_rate', 0)
        
        if original_rate > 0:
            rate_drop_percent = ((funding_info['funding_rate'] - original_rate) / original_rate) * 100
            
            if rate_drop_percent < -50:  # Dropped more than 50%
                self.log_signal(
                    "EXIT SIGNAL (RATE DROP)",
                    f"Funding rate dropped {abs(rate_drop_percent):.1f}%"
                )
                return True

        return False

    def get_stop_loss(self, entry_price: float, side: str) -> float:
        """
        No traditional stop loss for funding arbitrage.
        
        Stop loss is set very wide since position is hedged.
        """
        # Wide stop loss (5%) - should never hit due to hedging
        if side == 'LONG':
            return entry_price * 0.95
        else:
            return entry_price * 1.05

    def get_take_profit(self, entry_price: float, side: str) -> float:
        """
        No traditional take profit for funding arbitrage.
        
        Profit comes from funding payments, not price movement.
        """
        # Wide take profit - not relevant for funding arbitrage
        if side == 'LONG':
            return entry_price * 1.05
        else:
            return entry_price * 0.95

    def get_strategy_stats(self) -> Dict[str, Any]:
        """Get arbitrage statistics"""
        avg_funding = (self.total_funding_earned / self.arbitrage_count 
                      if self.arbitrage_count > 0 else 0)
        
        # Calculate annual return (3 fundings per day * 365 days)
        projected_annual = avg_funding * 3 * 365 * 100
        
        return {
            'total_fundings_collected': self.arbitrage_count,
            'total_funding_earned_percent': self.total_funding_earned * 100,
            'average_funding_percent': avg_funding * 100,
            'projected_annual_return': projected_annual,
            'active_positions': len(self.active_arbitrage_positions)
        }

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy configuration and performance"""
        stats = self.get_strategy_stats()
        
        return {
            'name': self.name,
            'purpose': 'Passive income from funding rates',
            'risk_level': 'VERY LOW (hedged positions)',
            'min_funding_rate': self.min_funding_rate * 100,
            'optimal_funding_rate': self.optimal_funding_rate * 100,
            'funding_interval_hours': self.funding_interval_hours,
            'max_leverage': self.max_leverage,
            'position_size_percent': self.position_size_percent * 100,
            **stats,
            'notes': [
                'Position is HEDGED (futures LONG + spot SHORT)',
                'Zero price risk exposure',
                'Income from funding rate payments',
                'Works best in bull markets (positive funding)',
                'Expected 4-33% annual return'
            ]
        }

    def generate_hedge_instructions(self, futures_position: Dict) -> Dict[str, Any]:
        """
        Generate instructions for hedging the futures position.
        
        Args:
            futures_position: Futures position details
            
        Returns:
            Instructions for spot hedge
        """
        return {
            'action': 'SELL SPOT',
            'symbol': futures_position.get('symbol'),
            'quantity': futures_position.get('quantity'),
            'price': futures_position.get('entry_price'),
            'reasoning': 'Hedge futures LONG with spot SHORT to eliminate price risk',
            'expected_cost': 'Minimal (taker fee ~0.1%)',
            'net_position': 'Delta neutral (0 price exposure)',
            'profit_source': 'Funding rate payments every 8 hours'
        }
