"""
Core crypto trading engine with ML model, risk management, and backtesting
"""
import os
import time
import json
import math
import requests
import threading
import numpy as np
import pandas as pd
import xgboost as xgb
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from collections import deque
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score
import optuna

try:
    import websocket
except Exception:
    websocket = None

from binance.client import Client
from binance.exceptions import BinanceAPIException

from config import (
    BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_API_SECRET,
    LIVE_API_KEY, LIVE_API_SECRET, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
    RiskConfig, MLConfig, SYMBOLS, BACKTESTING_DAYS, KLINE_INTERVAL,
    get_logger
)

logger = get_logger(__name__)

# ==================== Public API ====================
__all__ = [
    # Core functions
    'reconnect_client',
    'get_historical_data_with_indicators',
    'send_telegram',
    'tune_xgboost',
    'run_backtest',
    'live_trading_loop',
    'update_risk_config',
    # Classes
    'MLModel',
    'RiskManagedMLStrategy',
    'MockClient',
    'BookTickerScalper',
    # State
    'client',
    'is_running',
    'is_testing',
    'auto_switch_enabled'
]

# ==================== Global State ====================
client = None
auto_switch_enabled = False
is_running = False
is_testing = True


# ==================== Mock Client ====================
class MockClient:
    """Mock Binance client for testing without API keys"""
    
    def __init__(self):
        self.initial_balance = 10000.0
        self.balance = self.initial_balance
        self.symbol_info_cache = {}
    
    def get_historical_klines(self, symbol: str, interval: str, start_str, end_str, limit: int):
        """Return mock OHLCV data"""
        mock_data = {
            'open_time': pd.to_datetime(pd.date_range(start='2024-01-01', periods=1000, freq='H')),
            'open': np.random.uniform(50, 100, 1000),
            'high': np.random.uniform(101, 105, 1000),
            'low': np.random.uniform(45, 49, 1000),
            'close': np.random.uniform(50, 100, 1000),
            'volume': np.random.uniform(1000, 5000, 1000),
        }
        return mock_data.values()
    
    def get_asset_balance(self, asset: str):
        return {'free': str(self.balance)}
    
    def get_symbol_info(self, symbol: str):
        if symbol not in self.symbol_info_cache:
            self.symbol_info_cache[symbol] = {
                'filters': [
                    {'filterType': 'LOT_SIZE', 'minQty': '0.001', 'stepSize': '0.001'},
                    {'filterType': 'PRICE_FILTER', 'tickSize': '0.01'},
                    {'filterType': 'MIN_NOTIONAL', 'minNotional': '10.0'},
                ]
            }
        return self.symbol_info_cache[symbol]
    
    def order_market_buy(self, **kwargs):
        self.balance += 5
        return {'status': 'FILLED'}
    
    def order_market_sell(self, **kwargs):
        self.balance -= 5
        return {'status': 'FILLED'}


# ==================== Client Management ====================
def reconnect_client(use_testnet: bool = True) -> None:
    """Reconfigure Binance client based on environment"""
    global client, is_testing
    is_testing = use_testnet
    
    if use_testnet:
        if BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET:
            client = Client(BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_API_SECRET, testnet=True)
            logger.info("Connected to Binance TESTNET")
        else:
            client = MockClient()
            logger.warning("TestNet keys missing, using mock client")
    else:
        if LIVE_API_KEY and LIVE_API_SECRET:
            client = Client(LIVE_API_KEY, LIVE_API_SECRET)
            logger.info("Connected to Binance LIVE")
        else:
            client = MockClient()
            logger.warning("Live keys missing, using mock client")


# Initialize client
try:
    reconnect_client(use_testnet=True)
except Exception as e:
    logger.warning(f"Could not connect to Binance on startup: {e}")
    logger.warning("Will attempt connection on first use, or using MockClient")
    client = MockClient()


# ==================== Notifications ====================
def send_telegram(message: str) -> None:
    """Send message via Telegram"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        logger.exception(f"Failed to send Telegram message: {e}")


# ==================== Data Fetching ====================
def get_historical_data_with_indicators(symbol: str = 'SOLUSDT', days: int = BACKTESTING_DAYS) -> pd.DataFrame:
    """Fetch historical data and compute technical indicators"""
    limit = 1000
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
    klines = []
    cur = start_ts

    while cur < end_ts:
        try:
            batch = client.get_historical_klines(symbol, KLINE_INTERVAL,
                                                start_str=cur, end_str=end_ts, limit=limit)
        except BinanceAPIException as e:
            logger.error(f"Binance API error: {e}")
            time.sleep(2 ** min(e.status_code // 100, 4))
            continue
        except Exception as e:
            logger.error(f"Data fetch error: {e}")
            time.sleep(5)
            continue
        
        if not batch:
            break
        
        klines.extend(batch)
        cur = batch[-1][0] + 1
        time.sleep(0.05)

    # Fallback to mock data if fetch fails
    if not klines:
        if isinstance(client, MockClient):
            logger.info("Using mock historical data")
            mock_data = {
                'open_time': pd.to_datetime(pd.date_range(start='2024-01-01', periods=1000, freq='H')),
                'open': np.random.uniform(50, 100, 1000),
                'high': np.random.uniform(101, 105, 1000),
                'low': np.random.uniform(45, 49, 1000),
                'close': np.random.uniform(50, 100, 1000),
                'volume': np.random.uniform(1000, 5000, 1000),
            }
            df = pd.DataFrame(mock_data)
        else:
            raise RuntimeError(f"No data available for {symbol}")
    else:
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_vol', 'trades', 'taker_base', 'taker_quote', 'ignore'
        ])[['open_time', 'open', 'high', 'low', 'close', 'volume']]

    # Convert types
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)

    # Calculate technical indicators
    close = df['close']
    high = df['high']
    low = df['low']
    vol = df['volume']

    # Trend indicators
    df['SMA_20'] = close.rolling(20).mean()
    df['SMA_50'] = close.rolling(50).mean()
    df['EMA_12'] = close.ewm(span=12, adjust=False).mean()
    df['EMA_26'] = close.ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']

    # Momentum indicators
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    df['RSI_14'] = 100 - (100 / (1 + gain / loss))

    # Volatility indicators
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df['BB_upper'] = bb_mid + 2 * bb_std
    df['BB_middle'] = bb_mid
    df['BB_lower'] = bb_mid - 2 * bb_std

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(14).mean()

    # Stochastic
    l14 = low.rolling(14).min()
    h14 = high.rolling(14).max()
    df['Stoch_K'] = 100 * (close - l14) / (h14 - l14)
    df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()

    # Volume indicators
    obv = [0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.append(obv[-1] + vol.iloc[i])
        elif close.iloc[i] < close.iloc[i-1]:
            obv.append(obv[-1] - vol.iloc[i])
        else:
            obv.append(obv[-1])
    df['OBV'] = obv

    # VWAP
    df['date'] = df['open_time'].dt.date
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['cum_price_vol'] = (df['close'] * df['volume']).groupby(df['date']).cumsum()
    df['VWAP'] = df['cum_price_vol'] / df['cum_vol']
    df.drop(['date', 'cum_vol', 'cum_price_vol'], axis=1, inplace=True)

    # Target variable
    df['future_close'] = df['close'].shift(-1)
    df['target'] = (df['future_close'] > df['close']).astype(int)
    df.drop('future_close', axis=1, inplace=True)

    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    return df


# ==================== ML Model ====================
def tune_xgboost(df: pd.DataFrame, n_trials: int = MLConfig.OPTUNA_TRIALS) -> Dict[str, Any]:
    """Optimize XGBoost hyperparameters using Optuna"""
    feature_cols = [c for c in df.columns if c not in ['open_time', 'target']]
    X, y = df[feature_cols].values, df['target'].values

    def objective(trial):
        param = {
            'n_estimators': trial.suggest_int('n_estimators', 100, 800),
            'max_depth': trial.suggest_int('max_depth', 3, 8),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'gamma': trial.suggest_float('gamma', 1e-8, 1.0, log=True),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'random_state': 42,
            'eval_metric': 'logloss'
        }
        
        tscv = TimeSeriesSplit(n_splits=MLConfig.TIME_SERIES_SPLITS)
        scores = []
        
        for train_idx, val_idx in tscv.split(X):
            m = xgb.XGBClassifier(**param)
            m.fit(X[train_idx], y[train_idx])
            pred = (m.predict_proba(X[val_idx])[:, 1] > 0.5).astype(int)
            scores.append(accuracy_score(y[val_idx], pred))
        
        return np.mean(scores)

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    
    best_params = study.best_params
    with open('best_params.json', 'w') as f:
        json.dump(best_params, f, indent=2)
    
    logger.info(f"Optuna optimization complete. Best params: {best_params}")
    return best_params


class MLModel:
    """XGBoost classification model for price direction prediction"""
    
    def __init__(self, df: pd.DataFrame):
        self.feature_cols = [c for c in df.columns if c not in ['open_time', 'target']]
        self.model = self.train(df)

    def train(self, df: pd.DataFrame) -> xgb.XGBClassifier:
        """Train the ML model"""
        X, y = df[self.feature_cols].values, df['target'].values
        
        try:
            with open('best_params.json', 'r') as f:
                params = json.load(f)
                logger.info(f"Loaded optimized params: {params}")
        except FileNotFoundError:
            params = MLConfig.DEFAULT_PARAMS
            logger.info(f"Using default params: {params}")
        
        model = xgb.XGBClassifier(**params)
        model.fit(X, y)
        return model

    def predict_proba(self, data: np.ndarray) -> np.ndarray:
        """Get prediction probabilities"""
        return self.model.predict_proba(data)

    def predict(self, data: np.ndarray) -> np.ndarray:
        """Get class predictions"""
        return self.model.predict(data)


# ==================== Risk Management ====================
def update_risk_config(new_vals: Dict[str, float]) -> None:
    """Update risk configuration dynamically"""
    RiskConfig.RISK_PER_TRADE = new_vals.get('risk_per_trade', RiskConfig.RISK_PER_TRADE)
    RiskConfig.STOP_LOSS_ATR_MULT = new_vals.get('stop_loss_mult', RiskConfig.STOP_LOSS_ATR_MULT)
    RiskConfig.TAKE_PROFIT_RR = new_vals.get('take_profit_rr', RiskConfig.TAKE_PROFIT_RR)
    RiskConfig.MAX_DRAWDOWN = new_vals.get('max_dd', RiskConfig.MAX_DRAWDOWN)
    RiskConfig.DAILY_LOSS_LIMIT = new_vals.get('daily_loss', RiskConfig.DAILY_LOSS_LIMIT)
    RiskConfig.TRAILING_STOP_PCT = new_vals.get('trailing_pct', RiskConfig.TRAILING_STOP_PCT)
    RiskConfig.POSITION_TIMEOUT_HOURS = new_vals.get('timeout_hours', RiskConfig.POSITION_TIMEOUT_HOURS)
    RiskConfig.MIN_VOLATILITY_ATR = new_vals.get('min_vol_atr', RiskConfig.MIN_VOLATILITY_ATR)
    logger.info("Risk config updated!")


class RiskManagedMLStrategy:
    """Trading strategy with risk management and ML predictions"""
    
    symbol_info_cache = {}

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.position = None
        self.equity_curve = []
        self.initial_balance = self._get_balance()
        self.balance = self.initial_balance
        self.equity_curve.append(self.initial_balance)
        self.daily_loss = 0.0

    def _get_balance(self) -> float:
        """Get current balance from exchange"""
        try:
            balance = client.get_asset_balance(asset='USDT')
            return float(balance['free'])
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return 10000.0

    def calculate_position_size(self, atr: float, close_price: float) -> float:
        """Calculate position size based on risk management"""
        stop_distance = atr * RiskConfig.STOP_LOSS_ATR_MULT
        risk_amount = self.balance * RiskConfig.RISK_PER_TRADE
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0
        return min(position_size, self.balance / close_price)

    def evaluate_entry_signal(self, df: pd.DataFrame, model: MLModel) -> Tuple[bool, float]:
        """Evaluate entry signal from ML model"""
        latest = df.iloc[-1]
        feature_cols = [c for c in df.columns if c not in ['open_time', 'target']]
        up_prob = model.predict_proba(latest[feature_cols].values.reshape(1, -1))[0][1]
        
        signal = up_prob > 0.6
        return signal, up_prob

    def evaluate_symbols(self, model: MLModel, symbols: List[str] = SYMBOLS, lookback_hours: int = 24) -> str:
        """Evaluate and rank symbols by multiple metrics"""
        scores = {}
        
        for sym in symbols:
            try:
                df = get_historical_data_with_indicators(sym, days=lookback_hours // 24 + 1)
                recent = df.tail(lookback_hours)
                returns = recent['close'].pct_change().dropna()
                sharpe = returns.mean() / returns.std() * np.sqrt(24) if returns.std() > 0 else 0

                latest = recent.iloc[-1]
                feature_cols = [c for c in df.columns if c not in ['open_time', 'target']]
                up_prob = model.predict_proba(latest[feature_cols].values.reshape(1, -1))[0][1]
                volatility = latest['ATR_14'] / latest['close']

                if volatility < 0.05:
                    score = 0.5 * sharpe + 0.3 * up_prob + 0.2 * (1 - volatility)
                    scores[sym] = score
            except Exception as e:
                logger.warning(f"Symbol evaluation error for {sym}: {e}")
        
        return max(scores, key=scores.get) if scores else SYMBOLS[0]


# ==================== Backtesting ====================
def run_backtest(symbol: str = 'SOLUSDT') -> Dict[str, Any]:
    """Run backtest on historical data"""
    try:
        logger.info(f"Starting backtest for {symbol}")
        
        df = get_historical_data_with_indicators(symbol)
        logger.info(f"Loaded {len(df)} candles for {symbol}")
        
        model = MLModel(df)
        strategy = RiskManagedMLStrategy(symbol)
        
        trades = []
        feature_cols = [c for c in df.columns if c not in ['open_time', 'target']]
        
        for idx in range(100, len(df) - 1):
            row = df.iloc[idx]
            signal, prob = strategy.evaluate_entry_signal(df.iloc[:idx+1], model)
            
            if signal and strategy.position is None:
                entry_price = row['close']
                atr = row['ATR_14']
                stop_price = entry_price - (atr * RiskConfig.STOP_LOSS_ATR_MULT)
                target_price = entry_price + (atr * RiskConfig.STOP_LOSS_ATR_MULT * RiskConfig.TAKE_PROFIT_RR)
                
                strategy.position = {
                    'entry_price': entry_price,
                    'stop_price': stop_price,
                    'target_price': target_price,
                    'entry_idx': idx,
                    'size': strategy.calculate_position_size(atr, entry_price)
                }
            
            elif strategy.position:
                exit_price = row['close']
                
                if exit_price <= strategy.position['stop_price']:
                    loss = (exit_price - strategy.position['entry_price']) * strategy.position['size']
                    strategy.balance += loss
                    strategy.daily_loss += loss
                    trades.append({'type': 'stop_loss', 'profit': loss})
                    strategy.position = None
                
                elif exit_price >= strategy.position['target_price']:
                    profit = (exit_price - strategy.position['entry_price']) * strategy.position['size']
                    strategy.balance += profit
                    trades.append({'type': 'take_profit', 'profit': profit})
                    strategy.position = None
            
            strategy.equity_curve.append(strategy.balance)

        # Calculate metrics
        returns = np.diff(strategy.equity_curve) / np.array(strategy.equity_curve[:-1])
        total_return = (strategy.equity_curve[-1] - strategy.initial_balance) / strategy.initial_balance
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        max_dd = (np.min(strategy.equity_curve) - strategy.initial_balance) / strategy.initial_balance
        win_rate = len([t for t in trades if t['profit'] > 0]) / len(trades) if trades else 0

        result = {
            'symbol': symbol,
            'total_return': total_return,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd,
            'total_trades': len(trades),
            'equity_curve': strategy.equity_curve,
            'final_balance': strategy.balance
        }
        
        logger.info(f"Backtest complete for {symbol}: Return={total_return:.2%}, Win Rate={win_rate:.2%}, Sharpe={sharpe:.2f}")
        return result
    
    except Exception as e:
        logger.exception(f"Backtest failed: {e}")
        return {'error': str(e), 'equity_curve': [10000]}


# ==================== Live Trading ====================
def live_trading_loop(symbol: str, update_callback: Optional[Callable] = None) -> None:
    """Live trading loop with real-time price data"""
    global is_running
    
    try:
        df = get_historical_data_with_indicators(symbol)
        model = MLModel(df)
        strategy = RiskManagedMLStrategy(symbol)
        
        logger.info(f"Started live trading for {symbol}")
        send_telegram(f"ðŸš€ Live trading started for {symbol}")
        
        while is_running:
            try:
                df = get_historical_data_with_indicators(symbol, days=1)
                signal, prob = strategy.evaluate_entry_signal(df, model)
                
                if signal and strategy.position is None:
                    latest = df.iloc[-1]
                    atr = latest['ATR_14']
                    entry_price = latest['close']
                    size = strategy.calculate_position_size(atr, entry_price)
                    
                    logger.info(f"BUY signal for {symbol}: {entry_price:.2f}")
                    send_telegram(f"ðŸ“ˆ BUY {symbol} @ {entry_price:.2f} (Prob: {prob:.2f})")
                    
                    strategy.position = {
                        'entry_price': entry_price,
                        'stop_price': entry_price - atr * RiskConfig.STOP_LOSS_ATR_MULT,
                        'target_price': entry_price + atr * RiskConfig.STOP_LOSS_ATR_MULT * RiskConfig.TAKE_PROFIT_RR,
                        'size': size,
                        'entry_time': datetime.now()
                    }
                
                elif strategy.position:
                    latest = df.iloc[-1]
                    close_price = latest['close']
                    
                    if close_price <= strategy.position['stop_price']:
                        logger.info(f"STOP LOSS for {symbol}: {close_price:.2f}")
                        send_telegram(f"ðŸ›‘ STOP LOSS {symbol} @ {close_price:.2f}")
                        strategy.position = None
                    
                    elif close_price >= strategy.position['target_price']:
                        logger.info(f"TAKE PROFIT for {symbol}: {close_price:.2f}")
                        send_telegram(f"âœ… TAKE PROFIT {symbol} @ {close_price:.2f}")
                        strategy.position = None
                
                strategy.equity_curve.append(strategy.balance)
                
                if update_callback:
                    update_callback(strategy.balance, strategy.equity_curve)
                
                time.sleep(60)  # Update every minute
            
            except Exception as e:
                logger.error(f"Live trading error: {e}")
                time.sleep(5)
    
    except Exception as e:
        logger.exception(f"Live trading setup failed: {e}")
        send_telegram(f"âŒ Live trading error: {str(e)}")
    finally:
        logger.info("Live trading stopped")
        send_telegram("ðŸ›‘ Live trading stopped")


class BookTickerScalper:
    DEFAULT_SYMBOLS = (
        'BTCUSDT',
        'ETHUSDT',
        'BNBUSDT',
        'SOLUSDT',
        'XRPUSDT',
        'ADAUSDT',
        'DOGEUSDT',
        'TRXUSDT',
        'AVAXUSDT',
        'LINKUSDT',
        'DOTUSDT',
        'MATICUSDT',
        'LTCUSDT',
        'BCHUSDT',
        'XLMUSDT',
        'UNIUSDT',
        'ATOMUSDT',
        'FILUSDT',
        'NEARUSDT',
        'ICPUSDT'
    )

    def __init__(self, symbols: Optional[List[str]] = None, trade_notional: float = 50.0, window_seconds: float = 10.0, spike_threshold: float = 0.001, pullback_ticks: int = 5, pullback_drop: float = 0.0002, exit_delay: float = 2.0):
        symbols = symbols or self.DEFAULT_SYMBOLS
        ordered = dict.fromkeys(s.upper() for s in symbols)
        self.symbols = tuple(ordered)
        self.trade_notional = float(trade_notional)
        self.window_seconds = float(window_seconds)
        self.spike_threshold = float(spike_threshold)
        self.pullback_ticks = int(pullback_ticks)
        self.pullback_drop = float(pullback_drop)
        self.exit_delay = float(exit_delay)
        self.price_history = {s: deque() for s in self.symbols}
        self.states = {s: {'mode': 'idle'} for s in self.symbols}
        self.symbol_info = {}
        self._lock = threading.Lock()
        self._log_lock = threading.Lock()
        self._running = threading.Event()
        self._thread = None
        self._ws = None
        trades_dir = os.path.join(os.getcwd(), 'trades')
        os.makedirs(trades_dir, exist_ok=True)
        self.log_path = os.path.join(trades_dir, 'book_ticker_scalps.csv')
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w', encoding='utf-8') as fh:
                fh.write('timestamp,symbol,side,price,quantity,profit\n')

    def start(self) -> None:
        if websocket is None:
            raise RuntimeError('websocket-client not available')
        if self._running.is_set():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1)

    def _run(self) -> None:
        backoff = 1.0
        while self._running.is_set():
            try:
                self._connect()
                backoff = 1.0
            except Exception as exc:
                logger.error(f"Scalper websocket error: {exc}")
                if not self._running.is_set():
                    break
                time.sleep(backoff)
                backoff = min(backoff * 2.0, 30.0)

    def _connect(self) -> None:
        url = "wss://stream.binance.com:9443/ws/!bookTicker"
        ws = websocket.create_connection(url, timeout=5)
        ws.settimeout(5)
        self._ws = ws
        try:
            while self._running.is_set():
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except Exception:
                    continue
                symbol = data.get('s')
                if symbol not in self.symbols:
                    continue
                bid = data.get('b')
                ask = data.get('a')
                if bid is None or ask is None:
                    continue
                price = (float(bid) + float(ask)) * 0.5
                self._handle_tick(symbol, price, time.time())
        finally:
            try:
                ws.close()
            except Exception:
                pass
            self._ws = None

    def _handle_tick(self, symbol: str, price: float, ts: float) -> None:
        action = None
        try:
            with self._lock:
                history = self.price_history[symbol]
                history.append((ts, price))
                limit_ts = ts - self.window_seconds
                while history and history[0][0] < limit_ts:
                    history.popleft()
                state = self.states[symbol]
                mode = state.get('mode', 'idle')
                if mode == 'idle':
                    if len(history) > 1:
                        base_price = history[0][1]
                        if base_price > 0:
                            change = (price - base_price) / base_price
                            if change >= self.spike_threshold:
                                self.states[symbol] = {
                                    'mode': 'waiting',
                                    'trigger_price': price,
                                    'peak_price': price,
                                    'pullback_count': 0,
                                    'created': ts
                                }
                elif mode == 'waiting':
                    state['peak_price'] = max(state.get('peak_price', price), price)
                    if price <= state['peak_price'] * (1 - self.pullback_drop):
                        state['pullback_count'] += 1
                    if state['pullback_count'] >= self.pullback_ticks:
                        self.states[symbol] = {'mode': 'entering', 'trigger_price': state['trigger_price']}
                        action = ('enter', symbol, price)
                    elif ts - state['created'] > self.window_seconds:
                        self.states[symbol] = {'mode': 'idle'}
                elif mode == 'in_position':
                    if ts - state['entry_time'] >= self.exit_delay:
                        self.states[symbol]['mode'] = 'exiting'
                        action = ('exit', symbol, state['quantity'], state['entry_price'], price)
        except Exception as exc:
            logger.error(f"Tick handling error for {symbol}: {exc}")
            with self._lock:
                self.states[symbol] = {'mode': 'idle'}
            return
        if action:
            if action[0] == 'enter':
                self._execute_entry(symbol, action[2])
            elif action[0] == 'exit':
                self._execute_exit(symbol, action[2], action[3], action[4])

    def _execute_entry(self, symbol: str, reference_price: float) -> None:
        if client is None:
            logger.error("Binance client not initialized")
            with self._lock:
                self.states[symbol] = {'mode': 'idle'}
            return
        quote_qty = max(self.trade_notional, self._min_notional(symbol))
        try:
            order = client.order_market_buy(symbol=symbol, quoteOrderQty=quote_qty)
            qty, price = self._extract_fill(order, reference_price, 0.0)
        except Exception as exc:
            logger.error(f"Entry failed for {symbol}: {exc}")
            with self._lock:
                self.states[symbol] = {'mode': 'idle'}
            return
        if price <= 0:
            price = reference_price
        qty = self._round_quantity(symbol, qty)
        if qty <= 0:
            with self._lock:
                self.states[symbol] = {'mode': 'idle'}
            return
        timestamp = time.time()
        with self._lock:
            self.states[symbol] = {
                'mode': 'in_position',
                'entry_price': price,
                'entry_time': timestamp,
                'quantity': qty
            }
        self._log_event(symbol, 'entry', price, qty, 0.0)

    def _execute_exit(self, symbol: str, quantity: float, entry_price: float, reference_price: float) -> None:
        if client is None:
            logger.error("Binance client not initialized")
            with self._lock:
                self.states[symbol] = {
                    'mode': 'in_position',
                    'entry_price': entry_price,
                    'entry_time': time.time(),
                    'quantity': quantity
                }
            return
        rounded_qty = self._round_quantity(symbol, quantity)
        if rounded_qty <= 0:
            with self._lock:
                self.states[symbol] = {'mode': 'idle'}
            return
        try:
            order = client.order_market_sell(symbol=symbol, quantity=rounded_qty)
            qty, price = self._extract_fill(order, reference_price, rounded_qty)
        except Exception as exc:
            logger.error(f"Exit failed for {symbol}: {exc}")
            with self._lock:
                self.states[symbol] = {
                    'mode': 'in_position',
                    'entry_price': entry_price,
                    'entry_time': time.time(),
                    'quantity': quantity
                }
            return
        if price <= 0:
            price = reference_price
        if qty <= 0:
            qty = rounded_qty
        profit = (price - entry_price) * qty
        with self._lock:
            self.states[symbol] = {'mode': 'idle'}
        self._log_event(symbol, 'exit', price, qty, profit)

    def _ensure_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        info = self.symbol_info.get(symbol)
        if info is None:
            try:
                info = client.get_symbol_info(symbol)
                self.symbol_info[symbol] = info
            except Exception as exc:
                logger.error(f"Symbol info error for {symbol}: {exc}")
                return None
        return info

    def _min_notional(self, symbol: str) -> float:
        info = self._ensure_symbol_info(symbol)
        if not info:
            return 0.0
        for filt in info.get('filters', []):
            if filt.get('filterType') == 'MIN_NOTIONAL':
                try:
                    return float(filt.get('minNotional', 0.0))
                except Exception:
                    return 0.0
        return 0.0

    def _round_quantity(self, symbol: str, quantity: float) -> float:
        info = self._ensure_symbol_info(symbol)
        if not info:
            return quantity
        step = None
        min_qty = 0.0
        for filt in info.get('filters', []):
            if filt.get('filterType') == 'LOT_SIZE':
                try:
                    step = float(filt.get('stepSize', '0.000001'))
                    min_qty = float(filt.get('minQty', '0'))
                except Exception:
                    step = None
                break
        if step and step > 0:
            steps = math.floor(quantity / step)
            quantity = steps * step
            precision = max(0, int(round(-math.log10(step))))
            quantity = float(format(quantity, f'.{precision}f'))
            if quantity < min_qty:
                quantity = min_qty
        return quantity

    def _extract_fill(self, order: Any, fallback_price: float, fallback_qty: float) -> Tuple[float, float]:
        qty = 0.0
        quote = 0.0
        if isinstance(order, dict):
            fills = order.get('fills')
            if isinstance(fills, list):
                for fill in fills:
                    try:
                        q = float(fill.get('qty') or fill.get('quantity') or 0.0)
                        p = float(fill.get('price') or fill.get('p') or fallback_price)
                    except Exception:
                        continue
                    qty += q
                    quote += q * p
            try:
                exec_qty = order.get('executedQty') or order.get('executed_qty')
                if exec_qty:
                    qty = max(qty, float(exec_qty))
            except Exception:
                pass
            try:
                quote_qty = order.get('cummulativeQuoteQty') or order.get('cummulative_quote_qty')
                if quote_qty:
                    quote = max(quote, float(quote_qty))
            except Exception:
                pass
        if qty <= 0:
            if fallback_qty > 0:
                qty = fallback_qty
            elif fallback_price > 0:
                qty = self.trade_notional / fallback_price
        price = fallback_price if fallback_price > 0 else 0.0
        if qty > 0 and quote > 0:
            calc_price = quote / qty
            if calc_price > 0:
                price = calc_price
        return qty, price

    def _log_event(self, symbol: str, side: str, price: float, quantity: float, profit: float) -> None:
        timestamp = datetime.utcnow().isoformat()
        row = f"{timestamp},{symbol},{side},{price:.8f},{quantity:.8f},{profit:.8f}\n"
        with self._log_lock:
            with open(self.log_path, 'a', encoding='utf-8') as fh:
                fh.write(row)
        logger.info(f"{side.upper()} {symbol} price={price:.6f} qty={quantity:.6f} profit={profit:.6f}")
