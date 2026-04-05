"""
Market Microstructure Analysis Module
Analyzes order flow, liquidity, and market impact
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from logging_utils import get_logger

logger = get_logger(__name__)

class MarketMicrostructure:
    """Advanced market microstructure analysis"""
    
    def __init__(self, lookback_periods: int = 50):
        self.lookback = lookback_periods
        self.order_flow_history = {}
        self.liquidity_metrics = {}
        self.vwap_levels = {}
        
    def analyze_microstructure(self,
                             symbol: str,
                             trades: pd.DataFrame,
                             orderbook: Optional[pd.DataFrame] = None) -> Dict:
        """
        Analyze market microstructure metrics
        """
        try:
            # Calculate basic metrics
            metrics = {
                'vwap': self._calculate_vwap(trades),
                'trade_flow': self._analyze_trade_flow(trades),
                'liquidity': self._analyze_liquidity(trades, orderbook),
                'impact': self._estimate_market_impact(trades)
            }
            
            # Store historical data
            if symbol not in self.order_flow_history:
                self.order_flow_history[symbol] = []
            
            self.order_flow_history[symbol].append({
                'timestamp': datetime.now(),
                **metrics
            })
            
            # Keep limited history
            if len(self.order_flow_history[symbol]) > self.lookback:
                self.order_flow_history[symbol].pop(0)
                
            # Calculate trends
            metrics.update(self._calculate_trends(symbol))
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in microstructure analysis: {e}")
            return {}
            
    def _calculate_vwap(self, trades: pd.DataFrame) -> Dict:
        """Calculate VWAP and related metrics"""
        try:
            # Basic VWAP
            trades['volume_price'] = trades['price'] * trades['volume']
            vwap = trades['volume_price'].sum() / trades['volume'].sum()
            
            # VWAP bands
            std_dev = np.std(trades['price'])
            
            return {
                'vwap': vwap,
                'vwap_upper': vwap + (2 * std_dev),
                'vwap_lower': vwap - (2 * std_dev),
                'price_to_vwap': trades['price'].iloc[-1] / vwap - 1
            }
            
        except Exception as e:
            logger.error(f"VWAP calculation error: {e}")
            return {}
            
    def _analyze_trade_flow(self, trades: pd.DataFrame) -> Dict:
        """Analyze trade flow and order imbalance"""
        try:
            # Classify trades as buy/sell
            trades['buy_volume'] = trades.apply(
                lambda x: x['volume'] if x['price'] >= x['price'].shift(1)
                else 0, axis=1
            )
            trades['sell_volume'] = trades['volume'] - trades['buy_volume']
            
            # Calculate metrics
            total_volume = trades['volume'].sum()
            buy_volume = trades['buy_volume'].sum()
            sell_volume = trades['sell_volume'].sum()
            
            # Order flow imbalance
            ofi = (buy_volume - sell_volume) / total_volume if total_volume > 0 else 0
            
            # Trade size analysis
            avg_trade_size = trades['volume'].mean()
            large_trades = trades[trades['volume'] > avg_trade_size * 2]
            
            return {
                'order_flow_imbalance': ofi,
                'buy_ratio': buy_volume / total_volume if total_volume > 0 else 0,
                'avg_trade_size': avg_trade_size,
                'large_trade_ratio': len(large_trades) / len(trades) if len(trades) > 0 else 0,
                'trade_count': len(trades)
            }
            
        except Exception as e:
            logger.error(f"Trade flow analysis error: {e}")
            return {}
            
    def _analyze_liquidity(self, trades: pd.DataFrame,
                          orderbook: Optional[pd.DataFrame]) -> Dict:
        """Analyze market liquidity"""
        try:
            metrics = {}
            
            # Time-based liquidity
            trades['time_diff'] = trades['timestamp'].diff()
            metrics['avg_time_between_trades'] = trades['time_diff'].mean()
            
            # Volume-based liquidity
            metrics['rolling_volume'] = trades['volume'].rolling(20).mean().iloc[-1]
            
            # Spread and depth metrics
            if orderbook is not None:
                spread = orderbook['ask_price'].iloc[0] - orderbook['bid_price'].iloc[0]
                metrics.update({
                    'spread': spread,
                    'spread_bps': spread / orderbook['bid_price'].iloc[0] * 10000,
                    'bid_depth': orderbook['bid_volume'].sum(),
                    'ask_depth': orderbook['ask_volume'].sum(),
                    'depth_imbalance': (orderbook['bid_volume'].sum() - 
                                      orderbook['ask_volume'].sum()) /
                                     (orderbook['bid_volume'].sum() + 
                                      orderbook['ask_volume'].sum())
                })
                
            return metrics
            
        except Exception as e:
            logger.error(f"Liquidity analysis error: {e}")
            return {}
            
    def _estimate_market_impact(self, trades: pd.DataFrame) -> Dict:
        """Estimate market impact of trades"""
        try:
            # Calculate price impact
            trades['price_impact'] = trades['price'].pct_change()
            trades['abs_impact'] = abs(trades['price_impact'])
            
            # Volume-weighted impact
            trades['vol_impact'] = trades['price_impact'] * trades['volume']
            
            avg_impact = trades['abs_impact'].mean()
            vol_weighted_impact = (trades['vol_impact'].sum() / 
                                 trades['volume'].sum() if trades['volume'].sum() > 0 else 0)
            
            return {
                'avg_price_impact': avg_impact,
                'vol_weighted_impact': vol_weighted_impact,
                'impact_std': trades['abs_impact'].std(),
                'max_impact': trades['abs_impact'].max()
            }
            
        except Exception as e:
            logger.error(f"Market impact calculation error: {e}")
            return {}
            
    def _calculate_trends(self, symbol: str) -> Dict:
        """Calculate trends in microstructure metrics"""
        try:
            if not self.order_flow_history.get(symbol):
                return {}
                
            history = self.order_flow_history[symbol]
            
            # Extract key metrics
            ofi_trend = [h['trade_flow']['order_flow_imbalance'] 
                        for h in history if 'trade_flow' in h]
            impact_trend = [h['impact']['avg_price_impact'] 
                          for h in history if 'impact' in h]
            
            # Calculate trends
            ofi_slope = np.polyfit(range(len(ofi_trend)), ofi_trend, 1)[0]
            impact_slope = np.polyfit(range(len(impact_trend)), impact_trend, 1)[0]
            
            return {
                'trends': {
                    'ofi_trend': ofi_slope,
                    'impact_trend': impact_slope,
                    'ofi_momentum': sum(1 for x in ofi_trend[-5:] if x > 0) / 5,
                    'impact_momentum': sum(1 for x in impact_trend[-5:] if x > 0) / 5
                }
            }
            
        except Exception as e:
            logger.error(f"Trend calculation error: {e}")
            return {}
            
    def get_trade_signals(self, metrics: Dict) -> Dict[str, float]:
        """Generate trading signals from microstructure analysis"""
        try:
            signals = {}
            
            # VWAP-based signals
            if 'vwap' in metrics:
                vwap_data = metrics['vwap']
                signals['vwap_signal'] = (
                    1 if vwap_data['price_to_vwap'] < -0.001
                    else -1 if vwap_data['price_to_vwap'] > 0.001
                    else 0
                )
                
            # Order flow signals
            if 'trade_flow' in metrics:
                flow = metrics['trade_flow']
                signals['flow_signal'] = (
                    1 if flow['order_flow_imbalance'] > 0.2
                    else -1 if flow['order_flow_imbalance'] < -0.2
                    else 0
                )
                
            # Liquidity signals
            if 'liquidity' in metrics and 'depth_imbalance' in metrics['liquidity']:
                liq = metrics['liquidity']
                signals['liquidity_signal'] = (
                    1 if liq['depth_imbalance'] > 0.1
                    else -1 if liq['depth_imbalance'] < -0.1
                    else 0
                )
                
            # Impact signals
            if 'impact' in metrics:
                impact = metrics['impact']
                signals['impact_signal'] = (
                    -1 if impact['vol_weighted_impact'] > 0.0005
                    else 1 if impact['vol_weighted_impact'] < -0.0005
                    else 0
                )
                
            # Trend signals
            if 'trends' in metrics:
                trends = metrics['trends']
                signals['trend_signal'] = (
                    1 if trends['ofi_momentum'] > 0.6
                    else -1 if trends['ofi_momentum'] < 0.4
                    else 0
                )
                
            # Calculate composite signal
            weights = {
                'vwap_signal': 0.3,
                'flow_signal': 0.25,
                'liquidity_signal': 0.2,
                'impact_signal': 0.15,
                'trend_signal': 0.1
            }
            
            composite = 0
            weight_sum = 0
            
            for signal, weight in weights.items():
                if signal in signals:
                    composite += signals[signal] * weight
                    weight_sum += weight
                    
            if weight_sum > 0:
                signals['composite_signal'] = composite / weight_sum
                
            return signals
            
        except Exception as e:
            logger.error(f"Signal generation error: {e}")
            return {}