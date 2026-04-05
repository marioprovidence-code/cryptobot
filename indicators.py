"""
Technical Indicator Functions
Standard and custom technical indicators for trading.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to DataFrame"""
    df = df.copy()
    
    # Basic indicators
    add_moving_averages(df)
    add_oscillators(df)
    add_volatility(df)
    add_volume(df)
    add_pattern_recognition(df)
    
    return df
    

def add_moving_averages(df: pd.DataFrame) -> None:
    """Add moving average indicators"""
    # Simple moving averages
    for period in [5, 10, 20, 50, 200]:
        df[f'SMA_{period}'] = df['close'].rolling(
            window=period
        ).mean()
        
    # Exponential moving averages
    for period in [9, 21]:
        df[f'EMA_{period}'] = df['close'].ewm(
            span=period,
            adjust=False
        ).mean()
        
    # Hull moving average
    def hma(data: pd.Series, period: int) -> pd.Series:
        wma1 = data.rolling(
            period // 2
        ).apply(
            lambda x: (
                np.average(x, weights=range(1, len(x) + 1))
            )
        )
        wma2 = data.rolling(period).apply(
            lambda x: (
                np.average(x, weights=range(1, len(x) + 1))
            )
        )
        return pd.Series(
            data.rolling(
                int(np.sqrt(period))
            ).apply(
                lambda x: (
                    np.average(x, weights=range(1, len(x) + 1))
                )
            ),
            index=data.index
        )
    df['HMA_9'] = hma(df['close'], 9)
    

def add_oscillators(df: pd.DataFrame) -> None:
    """Add oscillator indicators"""
    # RSI
    for period in [7, 14, 21]:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(
            window=period
        ).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(
            window=period
        ).mean()
        rs = gain / loss
        df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
        
    # Stochastic
    for period in [14, 21]:
        low_min = df['low'].rolling(period).min()
        high_max = df['high'].rolling(period).max()
        
        k = 100 * (
            (df['close'] - low_min) /
            (high_max - low_min)
        )
        df[f'STOCH_{period}'] = k
        df[f'STOCH_D_{period}'] = k.rolling(3).mean()
        
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(
        span=9,
        adjust=False
    ).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    

def add_volatility(df: pd.DataFrame) -> None:
    """Add volatility indicators"""
    # ATR
    for period in [7, 14, 21]:
        high_low = df['high'] - df['low']
        high_close = np.abs(
            df['high'] - df['close'].shift()
        )
        low_close = np.abs(
            df['low'] - df['close'].shift()
        )
        ranges = pd.concat(
            [high_low, high_close, low_close],
            axis=1
        )
        true_range = np.max(ranges, axis=1)
        df[f'ATR_{period}'] = true_range.rolling(
            period
        ).mean()
        
    # Bollinger Bands
    for period in [20]:
        std = df['close'].rolling(period).std()
        middle = df['close'].rolling(period).mean()
        df[f'BB_Upper_{period}'] = middle + (std * 2)
        df[f'BB_Lower_{period}'] = middle - (std * 2)
        
    # Keltner Channels
    for period in [20]:
        middle = df['close'].rolling(period).mean()
        atr = df[f'ATR_{period}']
        df[f'KC_Upper_{period}'] = middle + (atr * 2)
        df[f'KC_Lower_{period}'] = middle - (atr * 2)
        

def add_volume(df: pd.DataFrame) -> None:
    """Add volume indicators"""
    # On-balance volume
    df['OBV'] = (
        np.sign(df['close'].diff()) *
        df['volume']
    ).fillna(0).cumsum()
    
    # Volume moving averages
    for period in [20, 50]:
        df[f'Volume_SMA_{period}'] = df['volume'].rolling(
            period
        ).mean()
        
    # Money flow index
    for period in [14]:
        # Calculate typical price
        tp = (df['high'] + df['low'] + df['close']) / 3
        
        # Calculate money flow
        mf = tp * df['volume']
        
        # Get positive and negative money flow
        pmf = pd.Series(
            np.where(tp > tp.shift(1), mf, 0),
            index=df.index
        )
        nmf = pd.Series(
            np.where(tp < tp.shift(1), mf, 0),
            index=df.index
        )
        
        # Calculate money ratio
        mr = (
            pmf.rolling(period).sum() /
            nmf.rolling(period).sum()
        )
        
        # Calculate MFI
        df[f'MFI_{period}'] = 100 - (100 / (1 + mr))
        

def add_pattern_recognition(df: pd.DataFrame) -> None:
    """Add candlestick pattern indicators"""
    # Doji
    df['Doji'] = (
        (abs(df['open'] - df['close']) <= 
         (0.1 * (df['high'] - df['low'])))
    ).astype(int)
    
    # Hammer
    df['Hammer'] = (
        (df['close'] > df['open']) &
        ((df['high'] - df['low']) > 
         (3 * (df['open'] - df['close']))) &
        ((df['close'] - df['low']) / 
         (0.001 + df['high'] - df['low']) > 0.6)
    ).astype(int)
    
    # Shooting Star
    df['ShootingStar'] = (
        (df['open'] > df['close']) &
        ((df['high'] - df['low']) > 
         (3 * (df['open'] - df['close']))) &
        ((df['high'] - df['open']) / 
         (0.001 + df['high'] - df['low']) > 0.6)
    ).astype(int)
    
    # Engulfing
    df['Bullish_Engulfing'] = (
        (df['close'] > df['open']) &
        (df['open'] <= df['close'].shift(1)) &
        (df['close'] >= df['open'].shift(1))
    ).astype(int)
    
    df['Bearish_Engulfing'] = (
        (df['close'] < df['open']) &
        (df['open'] >= df['close'].shift(1)) &
        (df['close'] <= df['open'].shift(1))
    ).astype(int)
    

def calculate_support_resistance(
    df: pd.DataFrame,
    window: int = 20,
    num_points: int = 5
) -> pd.DataFrame:
    """Calculate support and resistance levels"""
    df = df.copy()
    
    for i in range(window, len(df)):
        # Get window data
        window_high = df['high'].iloc[i-window:i]
        window_low = df['low'].iloc[i-window:i]
        
        # Find peaks
        peaks = []
        for j in range(1, len(window_high)-1):
            if (window_high.iloc[j] > window_high.iloc[j-1] and
                window_high.iloc[j] > window_high.iloc[j+1]):
                peaks.append(window_high.iloc[j])
                
        # Find troughs
        troughs = []
        for j in range(1, len(window_low)-1):
            if (window_low.iloc[j] < window_low.iloc[j-1] and
                window_low.iloc[j] < window_low.iloc[j+1]):
                troughs.append(window_low.iloc[j])
                
        # Get top resistance levels
        resistance = sorted(
            peaks,
            reverse=True
        )[:num_points]
        
        # Get bottom support levels
        support = sorted(
            troughs
        )[:num_points]
        
        # Store levels
        df.loc[
            df.index[i],
            [f'Resistance_{j+1}' for j in range(len(resistance))]
        ] = resistance
        
        df.loc[
            df.index[i],
            [f'Support_{j+1}' for j in range(len(support))]
        ] = support
        
    return df


def get_indicator_info() -> Dict[str, Dict[str, Any]]:
    """Get information about available indicators"""
    return {
        'Moving Averages': {
            'SMA': 'Simple Moving Average',
            'EMA': 'Exponential Moving Average',
            'HMA': 'Hull Moving Average'
        },
        'Oscillators': {
            'RSI': 'Relative Strength Index',
            'STOCH': 'Stochastic Oscillator',
            'MACD': 'Moving Average Convergence Divergence'
        },
        'Volatility': {
            'ATR': 'Average True Range',
            'BB': 'Bollinger Bands',
            'KC': 'Keltner Channels'
        },
        'Volume': {
            'OBV': 'On-Balance Volume',
            'Volume_SMA': 'Volume Simple Moving Average',
            'MFI': 'Money Flow Index'
        },
        'Patterns': {
            'Doji': 'Doji Pattern',
            'Hammer': 'Hammer Pattern',
            'ShootingStar': 'Shooting Star Pattern',
            'Bullish_Engulfing': 'Bullish Engulfing Pattern',
            'Bearish_Engulfing': 'Bearish Engulfing Pattern'
        }
    }