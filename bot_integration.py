"""
Complete Bot Integration Module
Centralizes all imports and provides unified API for the trading bot
"""

# ==================== Core Engine ====================
from crypto_engine import (
    # Functions
    reconnect_client,
    get_historical_data_with_indicators,
    send_telegram,
    tune_xgboost,
    run_backtest,
    live_trading_loop,
    update_risk_config,
    # Classes
    MLModel,
    RiskManagedMLStrategy,
    MockClient,
    # State
    client,
    is_running,
    is_testing,
    auto_switch_enabled
)

# ==================== Configuration ====================
from config import (
    # API Keys
    BINANCE_TESTNET_API_KEY,
    BINANCE_TESTNET_API_SECRET,
    LIVE_API_KEY,
    LIVE_API_SECRET,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
    # Settings
    SYMBOLS,
    DEFAULT_SYMBOL,
    BACKTESTING_DAYS,
    KLINE_INTERVAL,
    # Classes
    RiskConfig,
    MLConfig,
    GUIConfig,
    MarketAnalysisConfig,
    TradingMode,
    TimeFrame,
    # Logger
    get_logger
)

# ==================== Market Analysis ====================
from market_analysis import (
    MarketVolatilityAnalyzer,
    MarketTracker
)

# ==================== Market Microstructure ====================
from market_microstructure import (
    MarketMicrostructure
)

# ==================== Advanced Features ====================
from advanced_backtest import (
    BacktestEngine
)

from advanced_entry_exit import (
    AdvancedEntryExit
)

from advanced_orders import (
    Order,
    OrderType,
    TimeInForce,
    OrderStatus,
    BracketOrder,
    OCOOrder,
    OrderManager,
    TrailingStopOrder,
    IcebergOrder,
    TWAPOrder,
    VWAPOrder
)

# ==================== Indicators ====================
from indicators import (
    add_indicators,
    add_moving_averages,
    add_oscillators,
    add_volatility,
    add_volume,
    add_pattern_recognition
)

# ==================== Logging ====================
from logging_utils import (
    get_logger as get_file_logger
)

# ==================== Re-export Main Classes ====================
__all__ = [
    # Engine
    'reconnect_client',
    'get_historical_data_with_indicators',
    'send_telegram',
    'tune_xgboost',
    'run_backtest',
    'live_trading_loop',
    'update_risk_config',
    'MLModel',
    'RiskManagedMLStrategy',
    'MockClient',
    # Config
    'SYMBOLS',
    'DEFAULT_SYMBOL',
    'BACKTESTING_DAYS',
    'KLINE_INTERVAL',
    'RiskConfig',
    'MLConfig',
    'GUIConfig',
    'MarketAnalysisConfig',
    'TradingMode',
    'TimeFrame',
    # Market Analysis
    'MarketVolatilityAnalyzer',
    'MarketTracker',
    'MarketMicrostructure',
    # Advanced Features
    'BacktestEngine',
    'AdvancedEntryExit',
    'Order',
    'OrderType',
    'TimeInForce',
    'OrderStatus',
    'BracketOrder',
    'OCOOrder',
    'OrderManager',
    'TrailingStopOrder',
    'IcebergOrder',
    'TWAPOrder',
    'VWAPOrder',
    # Indicators
    'add_indicators',
    'add_moving_averages',
    'add_oscillators',
    'add_volatility',
    'add_volume',
    'add_pattern_recognition',
    # Logging
    'get_logger',
    'get_file_logger'
]

logger = get_logger('bot_integration')
logger.info("Bot integration module loaded successfully")