"""
Market Volatility Analysis Module
Provides real-time volatility analysis and trading windows
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from logging_utils import get_logger

logger = get_logger(__name__)

class MarketVolatilityAnalyzer:
    """Analyzes market volatility for optimal trade timing"""
    
    def __init__(self, lookback_periods: int = 20):
        self.lookback = lookback_periods
        self.volatility_history = {}
        self.session_volatility = {}
        self.optimal_windows = {}
        
    def analyze_volatility(self,
                         symbol: str,
                         price_data: pd.DataFrame) -> Dict[str, float]:
        """
        Analyze current market volatility and trading conditions
        Returns volatility metrics and trading recommendations
        """
        try:
            # Calculate various volatility measures
            close_prices = price_data['close'].values
            high_prices = price_data['high'].values
            low_prices = price_data['low'].values
            
            # Recent volatility (standard deviation of returns)
            returns = np.diff(np.log(close_prices))
            current_vol = np.std(returns[-self.lookback:]) * np.sqrt(252)
            
            # Garman-Klass volatility
            gk_vol = self._calculate_garman_klass(
                high_prices[-self.lookback:],
                low_prices[-self.lookback:],
                close_prices[-self.lookback:]
            )
            
            # Parkinson volatility (high-low range based)
            park_vol = self._calculate_parkinson(
                high_prices[-self.lookback:],
                low_prices[-self.lookback:]
            )
            
            # Update volatility history
            if symbol not in self.volatility_history:
                self.volatility_history[symbol] = []
            
            self.volatility_history[symbol].append({
                'timestamp': datetime.now(),
                'std_vol': current_vol,
                'gk_vol': gk_vol,
                'park_vol': park_vol
            })
            
            # Keep last 100 readings
            if len(self.volatility_history[symbol]) > 100:
                self.volatility_history[symbol].pop(0)
            
            # Analyze volatility regime
            vol_regime = self._determine_volatility_regime(
                current_vol,
                self.volatility_history[symbol]
            )
            
            # Calculate trading thresholds
            thresholds = self._calculate_trading_thresholds(
                current_vol,
                vol_regime
            )
            
            # Update session volatility
            self._update_session_volatility(symbol, current_vol)
            
            # Find optimal trading windows
            trading_windows = self._find_trading_windows(symbol)
            
            return {
                'current_volatility': current_vol,
                'garman_klass_vol': gk_vol,
                'parkinson_vol': park_vol,
                'volatility_regime': vol_regime,
                'trading_thresholds': thresholds,
                'trading_windows': trading_windows
            }
            
        except Exception as e:
            logger.error(f"Error analyzing volatility: {e}")
            return {}
            
    def _calculate_garman_klass(self,
                              high: np.ndarray,
                              low: np.ndarray,
                              close: np.ndarray) -> float:
        """Calculate Garman-Klass volatility estimator"""
        try:
            log_hl = np.log(high / low)
            log_co = np.log(close[1:] / close[:-1])
            
            hl_term = 0.5 * np.mean(log_hl ** 2)
            co_term = np.mean(log_co ** 2)
            
            vol = np.sqrt(252 * (hl_term - (2 * np.log(2) - 1) * co_term))
            return float(vol)
        except:
            return 0.0
            
    def _calculate_parkinson(self,
                           high: np.ndarray,
                           low: np.ndarray) -> float:
        """Calculate Parkinson volatility estimator"""
        try:
            log_hl = np.log(high / low)
            vol = np.sqrt(252 * np.mean(log_hl ** 2) / (4 * np.log(2)))
            return float(vol)
        except:
            return 0.0
            
    def _determine_volatility_regime(self,
                                   current_vol: float,
                                   history: List[Dict]) -> str:
        """Determine current volatility regime"""
        if not history:
            return "normal"
            
        # Get historical volatilities
        hist_vols = [h['std_vol'] for h in history]
        vol_mean = np.mean(hist_vols)
        vol_std = np.std(hist_vols)
        
        if current_vol > vol_mean + (2 * vol_std):
            return "extreme"
        elif current_vol > vol_mean + vol_std:
            return "high"
        elif current_vol < vol_mean - vol_std:
            return "low"
        else:
            return "normal"
            
    def _calculate_trading_thresholds(self,
                                    current_vol: float,
                                    regime: str) -> Dict[str, float]:
        """Calculate adaptive trading thresholds"""
        # Base thresholds
        thresholds = {
            'entry_threshold': 0.001,  # 0.1% move
            'stop_loss_mult': 2.0,     # 2x ATR
            'take_profit_mult': 3.0,   # 3x ATR
            'position_size_factor': 1.0
        }
        
        # Adjust for volatility regime
        regime_adjustments = {
            'low': {
                'entry_threshold': 0.8,
                'stop_loss_mult': 1.5,
                'take_profit_mult': 2.5,
                'position_size_factor': 1.2
            },
            'normal': {
                'entry_threshold': 1.0,
                'stop_loss_mult': 2.0,
                'take_profit_mult': 3.0,
                'position_size_factor': 1.0
            },
            'high': {
                'entry_threshold': 1.3,
                'stop_loss_mult': 2.5,
                'take_profit_mult': 3.5,
                'position_size_factor': 0.8
            },
            'extreme': {
                'entry_threshold': 1.5,
                'stop_loss_mult': 3.0,
                'take_profit_mult': 4.0,
                'position_size_factor': 0.5
            }
        }
        
        # Apply adjustments
        adj = regime_adjustments.get(regime, regime_adjustments['normal'])
        for k, v in thresholds.items():
            thresholds[k] = v * adj[k]
            
        # Scale by current volatility
        vol_scale = min(max(current_vol / 0.2, 0.5), 2.0)  # 0.5x to 2x based on 20% vol
        thresholds['position_size_factor'] *= vol_scale
        
        return thresholds
        
    def _update_session_volatility(self,
                                 symbol: str,
                                 current_vol: float) -> None:
        """Track volatility by trading session"""
        now = datetime.now()
        session_key = now.strftime("%Y-%m-%d-%H")
        
        if symbol not in self.session_volatility:
            self.session_volatility[symbol] = {}
            
        if session_key not in self.session_volatility[symbol]:
            self.session_volatility[symbol][session_key] = []
            
        self.session_volatility[symbol][session_key].append(current_vol)
        
        # Clean old sessions (keep last 7 days)
        cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        self.session_volatility[symbol] = {
            k: v for k, v in self.session_volatility[symbol].items()
            if k.startswith(cutoff) or k > cutoff
        }
        
    def _find_trading_windows(self, symbol: str) -> Dict[str, List[int]]:
        """Identify optimal trading windows based on historical volatility"""
        if symbol not in self.session_volatility:
            return {}
            
        # Analyze volatility by hour
        hourly_vol = {}
        for session, vols in self.session_volatility[symbol].items():
            hour = int(session.split('-')[-1])
            if hour not in hourly_vol:
                hourly_vol[hour] = []
            hourly_vol[hour].extend(vols)
            
        # Calculate average volatility by hour
        avg_vol = {
            hour: np.mean(vols)
            for hour, vols in hourly_vol.items()
            if vols
        }
        
        if not avg_vol:
            return {}
            
        # Find high and low volatility windows
        mean_vol = np.mean(list(avg_vol.values()))
        std_vol = np.std(list(avg_vol.values()))
        
        high_vol_hours = [
            h for h, v in avg_vol.items()
            if v > mean_vol + (0.5 * std_vol)
        ]
        
        low_vol_hours = [
            h for h, v in avg_vol.items()
            if v < mean_vol - (0.5 * std_vol)
        ]
        
        return {
            'high_volatility': sorted(high_vol_hours),
            'low_volatility': sorted(low_vol_hours)
        }
        
    def get_trading_recommendation(self,
                                 symbol: str,
                                 current_vol: float) -> Dict[str, any]:
        """Get trading recommendations based on volatility analysis"""
        now = datetime.now()
        current_hour = now.hour
        
        # Get volatility windows
        windows = self._find_trading_windows(symbol)
        
        # Determine current volatility regime
        if symbol in self.volatility_history:
            regime = self._determine_volatility_regime(
                current_vol,
                self.volatility_history[symbol]
            )
        else:
            regime = "normal"
            
        # Get trading thresholds
        thresholds = self._calculate_trading_thresholds(current_vol, regime)
        
        # Trading suitability score (0-100)
        score = 50  # Base score
        
        # Adjust for volatility regime
        regime_scores = {
            "low": -10,
            "normal": 0,
            "high": 10,
            "extreme": -20
        }
        score += regime_scores.get(regime, 0)
        
        # Adjust for trading window
        if current_hour in windows.get('high_volatility', []):
            score += 20
        elif current_hour in windows.get('low_volatility', []):
            score -= 10
            
        # Adjust for volatility trend
        if symbol in self.volatility_history and len(self.volatility_history[symbol]) > 1:
            recent_vols = [h['std_vol'] for h in self.volatility_history[symbol][-5:]]
            vol_trend = np.polyfit(range(len(recent_vols)), recent_vols, 1)[0]
            
            if vol_trend > 0:
                score += 10  # Increasing volatility
            elif vol_trend < 0:
                score -= 10  # Decreasing volatility
                
        # Clamp score
        score = max(0, min(100, score))
        
        return {
            'trading_score': score,
            'volatility_regime': regime,
            'thresholds': thresholds,
            'current_hour': current_hour,
            'is_high_vol_window': current_hour in windows.get('high_volatility', []),
            'is_low_vol_window': current_hour in windows.get('low_volatility', []),
            'recommendation': 'high' if score >= 70 else 'moderate' if score >= 40 else 'low'
        }