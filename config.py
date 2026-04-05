"""
Configuration and constants for the Crypto Trading Bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ==================== API Configuration ====================
BINANCE_TESTNET_API_KEY = 'nAtJK6jUclH3BzI9TLChcYuJbkk2KOKmlHgwFRcYPULkSyI8RgL7OiQeUUaGFEOV'
BINANCE_TESTNET_API_SECRET = 'kyHwb4qUysdYEknyCRMORQGh702vOvlSt30ecDDpTrxLF1NvvauVPD5Q8EpZFUPD'
LIVE_API_KEY = os.getenv('BINANCE_API_KEY')
LIVE_API_SECRET = os.getenv('BINANCE_API_SECRET')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ==================== Trading Configuration ====================
SYMBOLS = ['SOLUSDT', 'BTCUSDT', 'ETHUSDT', 'ADAUSDT']
DEFAULT_SYMBOL = 'SOLUSDT'
BACKTESTING_DAYS = 360
KLINE_INTERVAL = '1h'

# ==================== Risk Management Configuration ====================
class RiskConfig:
    RISK_PER_TRADE = 0.02          # 2%
    STOP_LOSS_ATR_MULT = 2.0
    TAKE_PROFIT_RR = 2.0
    MAX_DRAWDOWN = 0.15
    DAILY_LOSS_LIMIT = 6.0
    TRAILING_STOP_PCT = 0.015
    POSITION_TIMEOUT_HOURS = 6
    MIN_VOLATILITY_ATR = 0.5

# ==================== ML Model Configuration ====================
class MLConfig:
    DEFAULT_PARAMS = {
        'n_estimators': 300,
        'max_depth': 5,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'eval_metric': 'logloss'
    }
    
    TIME_SERIES_SPLITS = 5
    OPTUNA_TRIALS = 30

# ==================== Technical Indicators ====================
INDICATORS = {
    'SMA_20': {'window': 20},
    'SMA_50': {'window': 50},
    'EMA_12': {'span': 12},
    'EMA_26': {'span': 26},
    'RSI_14': {'window': 14},
    'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
    'BB': {'window': 20, 'std_dev': 2},
    'ATR_14': {'window': 14},
    'STOCH': {'window': 14, 'smooth_k': 3},
    'OBV': {},
    'VWAP': {}
}

# ==================== GUI Configuration ====================
class GUIConfig:
    WINDOW_WIDTH = 1050
    WINDOW_HEIGHT = 750
    CHART_WIDTH = 12
    CHART_HEIGHT = 5
    
    THEMES = {
        'dark': {
            'bg': '#1a1a1a', 'fg': '#ffffff', 'select_bg': '#404040',
            'select_fg': '#ffffff', 'button_bg': '#2d2d2d',
            'button_fg': '#ffffff', 'frame_bg': '#262626', 'accent': '#007acc'
        },
        'light': {
            'bg': '#ffffff', 'fg': '#000000', 'select_bg': '#0078d7',
            'select_fg': '#ffffff', 'button_bg': '#f0f0f0',
            'button_fg': '#000000', 'frame_bg': '#f5f5f5', 'accent': '#0078d7'
        }
    }
    
    DEFAULT_THEME = 'dark'

# ==================== Market Analysis Configuration ====================
class MarketAnalysisConfig:
    VOLATILITY_LOOKBACK = 20
    VOLATILITY_HISTORY_LIMIT = 200
    SESSION_VOLATILITY_DAYS = 7
    
    VOLATILITY_REGIMES = {
        'low': {'entry_threshold': 0.8, 'stop_loss_mult': 1.5, 'take_profit_mult': 2.5, 'position_size_factor': 1.2},
        'normal': {'entry_threshold': 1.0, 'stop_loss_mult': 2.0, 'take_profit_mult': 3.0, 'position_size_factor': 1.0},
        'high': {'entry_threshold': 1.3, 'stop_loss_mult': 2.5, 'take_profit_mult': 3.5, 'position_size_factor': 0.8},
        'extreme': {'entry_threshold': 1.5, 'stop_loss_mult': 3.0, 'take_profit_mult': 4.0, 'position_size_factor': 0.5}
    }

# ==================== Trading Modes ====================
class TradingMode:
    SPOT = 'Spot'
    MARGIN = 'Margin'
    FUTURES = 'Futures'

class TimeFrame:
    SCALP = 'Scalp'
    SHORT = 'Short'
    MEDIUM = 'Medium'
    LONG = 'Long'

# ==================== Logging ====================
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)