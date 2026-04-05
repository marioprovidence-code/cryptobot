"""
Advanced Entry/Exit Strategy Module
Provides sophisticated entry and exit conditions
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from logging_utils import get_logger

logger = get_logger(__name__)

class AdvancedEntryExit:
    """Sophisticated entry and exit strategy management"""
    
    def __init__(self):
        self.entry_conditions = {}
        self.exit_conditions = {}
        self.position_stats = {}
        
    def analyze_entry(self,
                     symbol: str,
                     data: pd.DataFrame,
                     micro_metrics: Dict,
                     volatility: Dict,
                     ml_signal: Dict) -> Dict[str, any]:
        """
        Analyze entry conditions using multiple factors
        """
        try:
            # Price action analysis
            price_signals = self._analyze_price_action(data)
            
            # Volume profile
            volume_signals = self._analyze_volume_profile(data)
            
            # Trend strength
            trend_signals = self._analyze_trend_strength(data)
            
            # Combine with microstructure and ML signals
            entry_score = self._calculate_entry_score(
                price_signals,
                volume_signals,
                trend_signals,
                micro_metrics,
                volatility,
                ml_signal
            )
            
            return {
                'entry_score': entry_score,
                'price_signals': price_signals,
                'volume_signals': volume_signals,
                'trend_signals': trend_signals
            }
            
        except Exception as e:
            logger.error(f"Entry analysis error: {e}")
            return {}
            
    def analyze_exit(self,
                    symbol: str,
                    data: pd.DataFrame,
                    position: Dict,
                    micro_metrics: Dict,
                    volatility: Dict) -> Dict[str, any]:
        """
        Analyze exit conditions for open position
        """
        try:
            current_price = data['close'].iloc[-1]
            position_age = (datetime.now() - position['entry_time']).total_seconds() / 3600
            
            # Calculate position metrics
            unrealized_pnl = (current_price - position['entry_price']) * position['size']
            pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            
            # Analyze exit conditions
            time_signals = self._analyze_time_based_exit(position_age, pnl_pct)
            price_signals = self._analyze_price_based_exit(data, position)
            risk_signals = self._analyze_risk_based_exit(
                position,
                micro_metrics,
                volatility
            )
            
            # Calculate exit score
            exit_score = self._calculate_exit_score(
                time_signals,
                price_signals,
                risk_signals,
                position
            )
            
            return {
                'exit_score': exit_score,
                'time_signals': time_signals,
                'price_signals': price_signals,
                'risk_signals': risk_signals,
                'metrics': {
                    'unrealized_pnl': unrealized_pnl,
                    'pnl_pct': pnl_pct,
                    'position_age': position_age
                }
            }
            
        except Exception as e:
            logger.error(f"Exit analysis error: {e}")
            return {}
            
    def _analyze_price_action(self, data: pd.DataFrame) -> Dict[str, float]:
        """Analyze price action patterns"""
        try:
            close = data['close']
            high = data['high']
            low = data['low']
            
            # Candlestick patterns
            doji = self._check_doji(data)
            hammer = self._check_hammer(data)
            engulfing = self._check_engulfing(data)
            
            # Support/Resistance
            sr_levels = self._find_support_resistance(data)
            
            # Price momentum
            roc = close.pct_change(5)
            momentum = roc.mean()
            
            return {
                'patterns': {
                    'doji': doji,
                    'hammer': hammer,
                    'engulfing': engulfing
                },
                'sr_levels': sr_levels,
                'momentum': momentum,
                'volatility': close.pct_change().std()
            }
            
        except Exception as e:
            logger.error(f"Price action analysis error: {e}")
            return {}
            
    def _analyze_volume_profile(self, data: pd.DataFrame) -> Dict[str, float]:
        """Analyze volume characteristics"""
        try:
            volume = data['volume']
            close = data['close']
            
            # Volume metrics
            rel_vol = volume / volume.rolling(20).mean()
            vol_ma = volume.rolling(20).mean()
            
            # Price-volume relationship
            price_vol_corr = close.pct_change().corr(volume.pct_change())
            
            return {
                'relative_volume': float(rel_vol.iloc[-1]),
                'volume_trend': float((vol_ma.iloc[-1] / vol_ma.iloc[-5]) - 1),
                'price_vol_corr': float(price_vol_corr),
                'volume_momentum': float(volume.pct_change(5).mean())
            }
            
        except Exception as e:
            logger.error(f"Volume analysis error: {e}")
            return {}
            
    def _analyze_trend_strength(self, data: pd.DataFrame) -> Dict[str, float]:
        """Analyze trend strength and momentum"""
        try:
            close = data['close']
            
            # ADX calculation
            tr1 = data['high'] - data['low']
            tr2 = abs(data['high'] - close.shift(1))
            tr3 = abs(data['low'] - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            
            # Directional movement
            plus_dm = data['high'].diff()
            minus_dm = -data['low'].diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            
            # Smooth DM
            plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
            
            # ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(14).mean()
            
            return {
                'adx': float(adx.iloc[-1]),
                'plus_di': float(plus_di.iloc[-1]),
                'minus_di': float(minus_di.iloc[-1]),
                'trend_strength': float(adx.iloc[-1] / 100),
                'trend_direction': 1 if plus_di.iloc[-1] > minus_di.iloc[-1] else -1
            }
            
        except Exception as e:
            logger.error(f"Trend analysis error: {e}")
            return {}
            
    def _calculate_entry_score(self,
                             price_signals: Dict,
                             volume_signals: Dict,
                             trend_signals: Dict,
                             micro_metrics: Dict,
                             volatility: Dict,
                             ml_signal: Dict) -> float:
        """Calculate composite entry score"""
        try:
            score = 50  # Base score
            
            # Price action contribution (25%)
            if price_signals:
                patterns = price_signals.get('patterns', {})
                score += 5 if patterns.get('engulfing', False) else 0
                score += 3 if patterns.get('hammer', False) else 0
                score += 2 if patterns.get('doji', False) else 0
                score += 10 * price_signals.get('momentum', 0)
                
            # Volume contribution (20%)
            if volume_signals:
                rel_vol = volume_signals.get('relative_volume', 1.0)
                score += 10 if rel_vol > 1.5 else -5 if rel_vol < 0.5 else 0
                score += 5 if volume_signals.get('volume_trend', 0) > 0 else -5
                
            # Trend contribution (20%)
            if trend_signals:
                adx = trend_signals.get('adx', 0)
                score += 10 if adx > 25 else -5 if adx < 15 else 0
                score += 10 * trend_signals.get('trend_strength', 0) * trend_signals.get('trend_direction', 0)
                
            # Microstructure contribution (15%)
            if micro_metrics:
                flow = micro_metrics.get('trade_flow', {})
                score += 15 * flow.get('order_flow_imbalance', 0)
                
            # Volatility contribution (10%)
            if volatility:
                regime = volatility.get('volatility_regime', 'normal')
                score += 5 if regime == 'normal' else -5 if regime == 'extreme' else 0
                
            # ML signal contribution (10%)
            if ml_signal:
                score += 10 if ml_signal.get('signal', 0) == 1 else -10
                score += 10 * (ml_signal.get('confidence', 0.5) - 0.5)
                
            # Normalize score
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Entry score calculation error: {e}")
            return 0
            
    def _analyze_time_based_exit(self,
                               position_age: float,
                               pnl_pct: float) -> Dict[str, float]:
        """Analyze time-based exit conditions"""
        try:
            # Base time score
            time_score = 100 - min(100, position_age / 24 * 100)  # Decay over 24 hours
            
            # Adjust for profitability
            if pnl_pct > 0:
                time_score *= (1 - pnl_pct)  # Reduce urgency when profitable
            else:
                time_score *= (1 + abs(pnl_pct))  # Increase urgency when losing
                
            return {
                'time_score': time_score,
                'age_hours': position_age,
                'time_urgency': 'high' if time_score < 30 else 'medium' if time_score < 60 else 'low'
            }
            
        except Exception as e:
            logger.error(f"Time-based exit analysis error: {e}")
            return {}
            
    def _analyze_price_based_exit(self,
                                data: pd.DataFrame,
                                position: Dict) -> Dict[str, float]:
        """Analyze price-based exit conditions"""
        try:
            current_price = data['close'].iloc[-1]
            entry_price = position['entry_price']
            
            # Calculate price metrics
            pnl_pct = (current_price - entry_price) / entry_price
            
            # Analyze momentum
            momentum = data['close'].pct_change(5).mean()
            
            # Price weakness signals
            weakness_score = 0
            if momentum < 0:
                weakness_score += abs(momentum) * 100
            
            return {
                'pnl_pct': pnl_pct,
                'momentum': momentum,
                'weakness_score': weakness_score,
                'price_signal': 'exit' if weakness_score > 50 else 'hold'
            }
            
        except Exception as e:
            logger.error(f"Price-based exit analysis error: {e}")
            return {}
            
    def _analyze_risk_based_exit(self,
                               position: Dict,
                               micro_metrics: Dict,
                               volatility: Dict) -> Dict[str, float]:
        """Analyze risk-based exit conditions"""
        try:
            risk_score = 0
            
            # Microstructure risk
            if micro_metrics:
                flow = micro_metrics.get('trade_flow', {})
                if flow.get('order_flow_imbalance', 0) < -0.2:
                    risk_score += 30
                    
            # Volatility risk
            if volatility:
                regime = volatility.get('volatility_regime', 'normal')
                if regime == 'extreme':
                    risk_score += 40
                elif regime == 'high':
                    risk_score += 20
                    
            return {
                'risk_score': risk_score,
                'risk_level': 'high' if risk_score > 60 else 'medium' if risk_score > 30 else 'low'
            }
            
        except Exception as e:
            logger.error(f"Risk-based exit analysis error: {e}")
            return {}
            
    def _calculate_exit_score(self,
                            time_signals: Dict,
                            price_signals: Dict,
                            risk_signals: Dict,
                            position: Dict) -> float:
        """Calculate composite exit score"""
        try:
            score = 0
            
            # Time component (30%)
            if time_signals:
                score += 0.3 * (100 - time_signals.get('time_score', 0))
                
            # Price component (40%)
            if price_signals:
                score += 0.4 * price_signals.get('weakness_score', 0)
                
            # Risk component (30%)
            if risk_signals:
                score += 0.3 * risk_signals.get('risk_score', 0)
                
            return score
            
        except Exception as e:
            logger.error(f"Exit score calculation error: {e}")
            return 0
            
    def _check_doji(self, data: pd.DataFrame) -> bool:
        """Check for doji pattern"""
        try:
            row = data.iloc[-1]
            body = abs(row['close'] - row['open'])
            wick = row['high'] - row['low']
            return body <= wick * 0.1
            
        except Exception as e:
            logger.error(f"Doji check error: {e}")
            return False
            
    def _check_hammer(self, data: pd.DataFrame) -> bool:
        """Check for hammer pattern"""
        try:
            row = data.iloc[-1]
            body = abs(row['close'] - row['open'])
            upper_wick = row['high'] - max(row['open'], row['close'])
            lower_wick = min(row['open'], row['close']) - row['low']
            return (lower_wick > body * 2) and (upper_wick < body * 0.5)
            
        except Exception as e:
            logger.error(f"Hammer check error: {e}")
            return False
            
    def _check_engulfing(self, data: pd.DataFrame) -> bool:
        """Check for engulfing pattern"""
        try:
            if len(data) < 2:
                return False
                
            prev = data.iloc[-2]
            curr = data.iloc[-1]
            
            prev_body = abs(prev['close'] - prev['open'])
            curr_body = abs(curr['close'] - curr['open'])
            
            is_bullish = (prev['close'] < prev['open'] and  # Previous red
                         curr['close'] > curr['open'] and  # Current green
                         curr['close'] > prev['open'] and  # Current closes above prev open
                         curr['open'] < prev['close'])     # Current opens below prev close
                         
            return is_bullish and curr_body > prev_body
            
        except Exception as e:
            logger.error(f"Engulfing check error: {e}")
            return False
            
    def _find_support_resistance(self, data: pd.DataFrame) -> Dict[str, List[float]]:
        """Find support and resistance levels"""
        try:
            high = data['high']
            low = data['low']
            
            # Find local maxima and minima
            resistance = []
            support = []
            
            for i in range(2, len(data) - 2):
                # Resistance
                if high.iloc[i] > high.iloc[i-1] and \
                   high.iloc[i] > high.iloc[i-2] and \
                   high.iloc[i] > high.iloc[i+1] and \
                   high.iloc[i] > high.iloc[i+2]:
                    resistance.append(high.iloc[i])
                    
                # Support
                if low.iloc[i] < low.iloc[i-1] and \
                   low.iloc[i] < low.iloc[i-2] and \
                   low.iloc[i] < low.iloc[i+1] and \
                   low.iloc[i] < low.iloc[i+2]:
                    support.append(low.iloc[i])
                    
            return {
                'support': support[-3:] if support else [],  # Last 3 levels
                'resistance': resistance[-3:] if resistance else []  # Last 3 levels
            }
            
        except Exception as e:
            logger.error(f"Support/Resistance analysis error: {e}")
            return {'support': [], 'resistance': []}