"""
Market analysis module including volatility analysis and market tracking
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random
import logging

from config import MarketAnalysisConfig, get_logger

logger = get_logger(__name__)

# ==================== Market Volatility Analyzer ====================
class MarketVolatilityAnalyzer:
    """Analyzes market volatility for optimal trade timing"""
    
    def __init__(self, lookback_periods: int = MarketAnalysisConfig.VOLATILITY_LOOKBACK):
        self.lookback = lookback_periods
        self.volatility_history: Dict[str, List[Dict[str, Any]]] = {}
        self.session_volatility: Dict[str, Dict[str, List[float]]] = {}

    def analyze_volatility(self, symbol: str, price_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market volatility with multiple methodologies"""
        try:
            close_prices = price_data['close'].values
            high_prices = price_data['high'].values
            low_prices = price_data['low'].values
            
            if len(close_prices) < 2:
                return {}
            
            # Calculate different volatility measures
            returns = np.diff(np.log(close_prices))
            current_vol = float(np.std(returns[-self.lookback:]) * np.sqrt(252))
            gk_vol = self._calculate_garman_klass(high_prices[-self.lookback:], 
                                                   low_prices[-self.lookback:], 
                                                   close_prices[-self.lookback:])
            park_vol = self._calculate_parkinson(high_prices[-self.lookback:], 
                                                  low_prices[-self.lookback:])

            # Store volatility history
            self.volatility_history.setdefault(symbol, []).append({
                'timestamp': datetime.now(),
                'std_vol': current_vol,
                'gk_vol': gk_vol,
                'park_vol': park_vol
            })
            
            if len(self.volatility_history[symbol]) > MarketAnalysisConfig.VOLATILITY_HISTORY_LIMIT:
                self.volatility_history[symbol].pop(0)

            # Determine volatility regime and thresholds
            vol_regime = self._determine_volatility_regime(current_vol, self.volatility_history[symbol])
            thresholds = self._calculate_trading_thresholds(current_vol, vol_regime)
            self._update_session_volatility(symbol, current_vol)
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
            logger.exception(f"Error analyzing volatility for {symbol}: {e}")
            return {}

    def _calculate_garman_klass(self, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> float:
        """Calculate Garman-Klass volatility estimator"""
        try:
            log_hl = np.log(high / low)
            log_co = np.log(close[1:] / close[:-1])
            hl_term = 0.5 * np.mean(log_hl ** 2)
            co_term = np.mean(log_co ** 2)
            vol = np.sqrt(max(0.0, 252 * (hl_term - (2 * np.log(2) - 1) * co_term)))
            return float(vol)
        except Exception:
            return 0.0

    def _calculate_parkinson(self, high: np.ndarray, low: np.ndarray) -> float:
        """Calculate Parkinson volatility estimator"""
        try:
            log_hl = np.log(high / low)
            vol = np.sqrt(max(0.0, 252 * np.mean(log_hl ** 2) / (4 * np.log(2))))
            return float(vol)
        except Exception:
            return 0.0

    def _determine_volatility_regime(self, current_vol: float, history: List[Dict]) -> str:
        """Determine current volatility regime (low/normal/high/extreme)"""
        if not history:
            return "normal"
        
        hist_vols = [h['std_vol'] for h in history]
        mean = float(np.mean(hist_vols))
        std = float(np.std(hist_vols))
        
        if current_vol > mean + 2 * std:
            return "extreme"
        if current_vol > mean + std:
            return "high"
        if current_vol < mean - std:
            return "low"
        return "normal"

    def _calculate_trading_thresholds(self, current_vol: float, regime: str) -> Dict[str, float]:
        """Calculate trading thresholds based on volatility regime"""
        thresholds = {
            'entry_threshold': 0.001,
            'stop_loss_mult': 2.0,
            'take_profit_mult': 3.0,
            'position_size_factor': 1.0
        }
        
        config = MarketAnalysisConfig.VOLATILITY_REGIMES
        adj = config.get(regime, config['normal'])
        
        for k in thresholds.keys():
            thresholds[k] = thresholds[k] * adj[k]
        
        vol_scale = min(max(current_vol / 0.2, 0.5), 2.0)
        thresholds['position_size_factor'] *= vol_scale
        
        return thresholds

    def _update_session_volatility(self, symbol: str, current_vol: float) -> None:
        """Track volatility by hourly sessions"""
        now = datetime.utcnow()
        session_key = now.strftime("%Y-%m-%d-%H")
        self.session_volatility.setdefault(symbol, {}).setdefault(session_key, []).append(current_vol)
        
        # Keep only recent 7 days
        cutoff_date = (now - timedelta(days=MarketAnalysisConfig.SESSION_VOLATILITY_DAYS)).strftime("%Y-%m-%d")
        keep = {k: v for k, v in self.session_volatility[symbol].items() 
                if k.startswith(cutoff_date) or k > cutoff_date}
        self.session_volatility[symbol] = keep

    def _find_trading_windows(self, symbol: str) -> Dict[str, List[int]]:
        """Identify high and low volatility trading windows by hour"""
        if symbol not in self.session_volatility:
            return {}
        
        hourly_vol = {}
        for session, vols in self.session_volatility[symbol].items():
            try:
                hour = int(session.split('-')[-1])
                hourly_vol.setdefault(hour, []).extend(vols)
            except Exception:
                continue
        
        avg_vol = {h: float(np.mean(vs)) for h, vs in hourly_vol.items() if vs}
        if not avg_vol:
            return {}
        
        mean_vol = float(np.mean(list(avg_vol.values())))
        std_vol = float(np.std(list(avg_vol.values())))
        
        high = [h for h, v in avg_vol.items() if v > mean_vol + 0.5 * std_vol]
        low = [h for h, v in avg_vol.items() if v < mean_vol - 0.5 * std_vol]
        
        return {'high_volatility': sorted(high), 'low_volatility': sorted(low)}

    def get_trading_recommendation(self, symbol: str, current_vol: float) -> Dict[str, Any]:
        """Get trading recommendation based on volatility analysis"""
        now = datetime.utcnow()
        current_hour = now.hour
        windows = self._find_trading_windows(symbol)
        regime = self._determine_volatility_regime(current_vol, self.volatility_history.get(symbol, []))
        thresholds = self._calculate_trading_thresholds(current_vol, regime)
        
        score = 50
        regime_scores = {"low": -10, "normal": 0, "high": 10, "extreme": -20}
        score += regime_scores.get(regime, 0)
        
        if current_hour in windows.get('high_volatility', []):
            score += 20
        elif current_hour in windows.get('low_volatility', []):
            score -= 10
        
        # Trend analysis
        recent = [h['std_vol'] for h in self.volatility_history.get(symbol, [])[-5:]] \
            if symbol in self.volatility_history else []
        if len(recent) > 1:
            try:
                trend = np.polyfit(range(len(recent)), recent, 1)[0]
                score += 10 if trend > 0 else -10 if trend < 0 else 0
            except Exception:
                pass
        
        score = max(0, min(100, int(score)))
        rec = 'high' if score >= 70 else 'moderate' if score >= 40 else 'low'
        
        return {
            'trading_score': score,
            'volatility_regime': regime,
            'thresholds': thresholds,
            'current_hour': current_hour,
            'is_high_vol_window': current_hour in windows.get('high_volatility', []),
            'is_low_vol_window': current_hour in windows.get('low_volatility', []),
            'recommendation': rec
        }


# ==================== Market Tracker ====================
class MarketTracker:
    """Track market data including gainers, losers, and new listings"""
    
    def __init__(self):
        self.gainers = []
        self.losers = []
        self.new_listings = []
        self.available_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT', 'SOLUSDT']
        self.last_update = None

    def search_pairs(self, text: str) -> List[str]:
        """Search for trading pairs"""
        txt = (text or "").upper()
        if not txt:
            return list(self.available_pairs)
        return [p for p in self.available_pairs if txt in p]

    def update_market_data(self) -> None:
        """Update market data (simulated)"""
        try:
            self.gainers = [
                {
                    'symbol': f'PAIR{idx}',
                    'change': random.uniform(0, 10),
                    'volume': random.uniform(1000, 5000),
                    'price': random.uniform(1000, 50000)
                }
                for idx in range(5)
            ]
            self.losers = [
                {
                    'symbol': f'PAIR{idx}',
                    'change': -random.uniform(0, 10),
                    'volume': random.uniform(1000, 5000),
                    'price': random.uniform(1000, 50000)
                }
                for idx in range(5)
            ]
            now_ts = datetime.now().timestamp()
            self.new_listings = [
                {
                    'symbol': f'NEW{idx}',
                    'time': now_ts,
                    'price': random.uniform(0.1, 100),
                    'volume': random.uniform(1000, 5000)
                }
                for idx in range(3)
            ]
            self.last_update = datetime.now()
        except Exception as e:
            logger.exception(f"Failed to update market data: {e}")

    def get_gainers(self) -> List[Dict]:
        """Get top gainers"""
        return self.gainers

    def get_losers(self) -> List[Dict]:
        """Get top losers"""
        return self.losers

    def get_new_listings(self) -> List[Dict]:
        """Get new listings"""
        return self.new_listings